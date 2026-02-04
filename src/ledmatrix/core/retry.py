"""Retry logic with exponential backoff for resilient operations.

Provides decorators for both sync and async functions with configurable
retry behavior, jitter, and exception handling.
"""

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Callable, ParamSpec, TypeVar

from .errors import RateLimitError

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (including first try)
        base_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types that trigger retry
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (
            ConnectionError,
            TimeoutError,
            OSError,
        )
    )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.base_delay * (self.exponential_base**attempt),
            self.max_delay,
        )
        if self.jitter:
            # Add jitter: 50% to 100% of calculated delay
            delay *= 0.5 + random.random() * 0.5
        return delay


# Default config for network operations
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError),
)

# Aggressive retry for critical operations
CRITICAL_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
)


def retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for synchronous retry with exponential backoff.

    Usage:
        @retry()
        def fetch_data():
            ...

        @retry(RetryConfig(max_attempts=5))
        def critical_operation():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)

                except RateLimitError as e:
                    # Respect rate limit retry-after header
                    delay = e.retry_after or config.calculate_delay(attempt)
                    logger.warning(
                        "Rate limited, waiting %ds before retry",
                        delay,
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": config.max_attempts,
                        },
                    )
                    if attempt < config.max_attempts - 1:
                        time.sleep(delay)
                    last_exception = e

                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            "Retry %d/%d after %.1fs: %s",
                            attempt + 1,
                            config.max_attempts,
                            delay,
                            str(e),
                            extra={
                                "function": func.__name__,
                                "error_type": type(e).__name__,
                            },
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts failed for %s",
                            config.max_attempts,
                            func.__name__,
                            extra={"last_error": str(e)},
                        )

            if last_exception:
                raise last_exception
            raise RuntimeError("Retry failed with no exception")

        return wrapper

    return decorator


def async_retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for async retry with exponential backoff.

    Usage:
        @async_retry()
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)

                except RateLimitError as e:
                    delay = e.retry_after or config.calculate_delay(attempt)
                    logger.warning(
                        "Rate limited, waiting %ds before retry",
                        delay,
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                        },
                    )
                    if attempt < config.max_attempts - 1:
                        await asyncio.sleep(delay)
                    last_exception = e

                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)
                        logger.warning(
                            "Async retry %d/%d after %.1fs: %s",
                            attempt + 1,
                            config.max_attempts,
                            delay,
                            str(e),
                            extra={
                                "function": func.__name__,
                                "error_type": type(e).__name__,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d async attempts failed for %s",
                            config.max_attempts,
                            func.__name__,
                        )

            if last_exception:
                raise last_exception
            raise RuntimeError("Async retry failed with no exception")

        return wrapper

    return decorator
