"""Core infrastructure module.

Provides foundational components:
- Configuration management with validation
- Custom exception hierarchy
- Structured logging
- Retry logic with exponential backoff
- Thread-safe primitives
"""

from .config import Config, ConfigManager, get_config
from .errors import (
    LEDDisplayError,
    ConfigurationError,
    HardwareError,
    NetworkError,
    APIError,
    AppError,
)
from .logging import setup_logging, get_logger
from .retry import retry, async_retry, RetryConfig
from .threading import LockedValue, ThreadSafeDict, StoppableThread

__all__ = [
    # Config
    "Config",
    "ConfigManager",
    "get_config",
    # Errors
    "LEDDisplayError",
    "ConfigurationError",
    "HardwareError",
    "NetworkError",
    "APIError",
    "AppError",
    # Logging
    "setup_logging",
    "get_logger",
    # Retry
    "retry",
    "async_retry",
    "RetryConfig",
    # Threading
    "LockedValue",
    "ThreadSafeDict",
    "StoppableThread",
]
