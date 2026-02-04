"""Custom exception hierarchy for the LED Display system.

Provides structured error handling with severity levels and context.
"""

from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and logging."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LEDDisplayError(Exception):
    """Base exception for all LED display errors.

    Attributes:
        message: Human-readable error message
        details: Additional context as key-value pairs
        severity: Error severity level
    """

    severity: ErrorSeverity = ErrorSeverity.ERROR

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
        }


class ConfigurationError(LEDDisplayError):
    """Configuration validation or loading error.

    Raised when:
    - Config file is malformed
    - Required settings are missing
    - Values fail validation
    """

    pass


class HardwareError(LEDDisplayError):
    """Hardware-related errors (GPIO, LED matrix).

    Raised when:
    - LED matrix initialization fails
    - GPIO operations fail
    - Hardware communication errors

    Always logged at CRITICAL level as it may require restart.
    """

    severity = ErrorSeverity.CRITICAL


class NetworkError(LEDDisplayError):
    """Network operation errors.

    Raised when:
    - WiFi connection fails
    - DNS resolution fails
    - Network interface errors
    """

    pass


class RateLimitError(LEDDisplayError):
    """API rate limit exceeded.

    Provides retry_after for implementing backoff.
    """

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(message, details)
        self.retry_after = retry_after


class APIError(LEDDisplayError):
    """External API errors (weather, stocks, spotify).

    Raised when:
    - API request fails
    - Invalid API response
    - Authentication errors
    """

    pass


class AuthenticationError(LEDDisplayError):
    """Authentication failures.

    Raised when:
    - Invalid credentials
    - Session expired
    - Missing authentication
    """

    severity = ErrorSeverity.WARNING


class AppError(LEDDisplayError):
    """App-specific errors.

    Raised when:
    - App initialization fails
    - App render fails
    - App configuration invalid
    """

    pass


class ValidationError(LEDDisplayError):
    """Input validation errors.

    Raised when:
    - Request data is invalid
    - Config values out of range
    - Type mismatches
    """

    severity = ErrorSeverity.WARNING
