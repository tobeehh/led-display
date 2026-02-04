"""Base class and protocols for display applications.

Defines the interface that all display apps must implement,
along with metadata and configuration schemas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from PIL import Image


class AppState(Enum):
    """App lifecycle states."""

    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    ERROR = "error"


class AppPriority(Enum):
    """App rendering priority levels."""

    BACKGROUND = 0  # Always lowest (e.g., clock when nothing else)
    NORMAL = 50  # Standard apps
    HIGH = 100  # Notifications, alerts
    CRITICAL = 200  # System messages


@dataclass(frozen=True)
class AppMetadata:
    """Metadata describing an app for registration and UI.

    Attributes:
        name: Internal app identifier (lowercase, no spaces)
        display_name: Human-readable name for UI
        description: Short description of app functionality
        version: App version string
        author: App author
        requires_network: Whether app needs internet
        requires_credentials: Whether app needs API keys/credentials
        priority: Default rendering priority
    """

    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    requires_network: bool = False
    requires_credentials: bool = False
    priority: AppPriority = AppPriority.NORMAL


@dataclass
class ConfigFieldSchema:
    """Schema for a configuration field.

    Used to generate configuration UI and validate settings.

    Attributes:
        type: Field type (string, int, bool, password, select, color)
        label: Human-readable label
        description: Help text
        default: Default value
        required: Whether field is required
        min_value: Minimum value (for int/float)
        max_value: Maximum value (for int/float)
        options: List of options (for select type)
    """

    type: str  # string, int, bool, password, select, color
    label: str
    description: str = ""
    default: Any = None
    required: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    options: list[dict[str, str]] | None = None


@dataclass
class RenderResult:
    """Result of an app render operation.

    Attributes:
        image: The rendered PIL Image
        next_render_in: Seconds until next render needed
        needs_immediate_update: True for animations needing fast updates
    """

    image: Image.Image
    next_render_in: float = 1.0  # Default: 1 second
    needs_immediate_update: bool = False


class BaseApp(ABC):
    """Abstract base class for display applications.

    Provides common functionality and enforces the app interface.
    All display apps must inherit from this class.

    Lifecycle:
        1. __init__() - Create instance with config
        2. activate() - Called when app becomes active
        3. render() - Called repeatedly to get display content
        4. update_data() - Called periodically to refresh data
        5. deactivate() - Called when switching to another app

    Thread Safety:
        - render() and update_data() may be called from different threads
        - Apps should protect shared state with locks
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the app with configuration.

        Args:
            config: App-specific configuration dict
        """
        self._config = config or {}
        self._state = AppState.INACTIVE
        self._last_error: str | None = None
        self._last_update: datetime | None = None
        self._last_render: datetime | None = None

    @property
    @abstractmethod
    def metadata(self) -> AppMetadata:
        """Return app metadata.

        Must be implemented by subclasses.

        Returns:
            AppMetadata describing the app
        """
        pass

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        """Return configuration schema for the app.

        Override in subclasses to define configurable settings.
        Used for generating configuration UI.

        Returns:
            Dict mapping field names to ConfigFieldSchema
        """
        return {}

    @property
    def state(self) -> AppState:
        """Get current app state."""
        return self._state

    @property
    def config(self) -> dict[str, Any]:
        """Get current configuration (copy)."""
        return self._config.copy()

    @property
    def enabled(self) -> bool:
        """Check if app is enabled in configuration."""
        return self._config.get("enabled", True)

    @property
    def last_error(self) -> str | None:
        """Get the last error message, if any."""
        return self._last_error

    def configure(self, config: dict[str, Any]) -> None:
        """Update app configuration.

        Validates configuration before applying.

        Args:
            config: New configuration dict

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate before applying
        old_config = self._config.copy()
        self._config = config

        is_valid, error = self.validate_config()
        if not is_valid:
            self._config = old_config
            raise ValueError(f"Invalid configuration: {error}")

    def validate_config(self) -> tuple[bool, str]:
        """Validate current configuration against schema.

        Returns:
            Tuple of (is_valid, error_message)
        """
        for field_name, field_schema in self.config_schema.items():
            value = self._config.get(field_name)

            # Check required fields
            if field_schema.required and (value is None or value == ""):
                return False, f"Missing required field: {field_schema.label}"

            # Type validation
            if value is not None and value != "":
                if field_schema.type == "int":
                    try:
                        int_val = int(value)
                        if field_schema.min_value is not None and int_val < field_schema.min_value:
                            return False, f"{field_schema.label} must be >= {field_schema.min_value}"
                        if field_schema.max_value is not None and int_val > field_schema.max_value:
                            return False, f"{field_schema.label} must be <= {field_schema.max_value}"
                    except (TypeError, ValueError):
                        return False, f"{field_schema.label} must be an integer"

                elif field_schema.type == "bool":
                    if not isinstance(value, bool):
                        return False, f"{field_schema.label} must be a boolean"

        return True, ""

    def activate(self) -> None:
        """Activate the app (called when becoming the current app).

        Sets state to ACTIVE and calls _on_activate().

        Raises:
            Exception: If activation fails (state becomes ERROR)
        """
        self._state = AppState.ACTIVATING
        self._last_error = None

        try:
            self._on_activate()
            self._state = AppState.ACTIVE
        except Exception as e:
            self._state = AppState.ERROR
            self._last_error = str(e)
            raise

    def deactivate(self) -> None:
        """Deactivate the app (called when switching away).

        Calls _on_deactivate() and sets state to INACTIVE.
        """
        self._state = AppState.DEACTIVATING
        try:
            self._on_deactivate()
        except Exception:
            pass  # Swallow errors on deactivation
        finally:
            self._state = AppState.INACTIVE

    def _on_activate(self) -> None:
        """Override for app-specific activation logic.

        Called after state is set to ACTIVATING.
        Raise an exception to abort activation.
        """
        pass

    def _on_deactivate(self) -> None:
        """Override for app-specific cleanup logic.

        Called before state is set to INACTIVE.
        """
        pass

    @abstractmethod
    def render(self, width: int, height: int) -> RenderResult:
        """Render the app display.

        Must be implemented by subclasses.

        Args:
            width: Display width in pixels
            height: Display height in pixels

        Returns:
            RenderResult with the rendered image
        """
        pass

    def update_data(self) -> None:
        """Update app data (e.g., fetch from API).

        Override in subclasses that need periodic data updates.
        Called automatically based on get_update_interval().

        Raises:
            Exception: If update fails (will be caught and logged)
        """
        pass

    def get_update_interval(self) -> float:
        """Get the interval between data updates in seconds.

        Override to enable automatic data updates.

        Returns:
            Update interval in seconds (0 = no automatic updates)
        """
        return 0.0

    def get_render_interval(self) -> float:
        """Get the minimum interval between renders in seconds.

        Override for apps that need specific render timing.

        Returns:
            Minimum render interval (default: 0.1 = 10 FPS)
        """
        return 0.1

    def _create_error_image(self, width: int, height: int, message: str) -> Image.Image:
        """Create an error display image.

        Args:
            width: Image width
            height: Image height
            message: Error message to display

        Returns:
            PIL Image showing the error
        """
        from .._display_helpers import create_error_image

        return create_error_image(width, height, message)

    def _create_loading_image(self, width: int, height: int) -> Image.Image:
        """Create a loading display image.

        Args:
            width: Image width
            height: Image height

        Returns:
            PIL Image showing loading state
        """
        from .._display_helpers import create_loading_image

        return create_loading_image(width, height)


# Helper module for error/loading images (avoids circular imports)
def _create_display_helpers_module() -> None:
    """This is a placeholder - actual helpers are in a separate file."""
    pass
