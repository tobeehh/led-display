"""Base class for LED display applications."""

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image


class BaseApp(ABC):
    """Base class for all LED display applications."""

    # App metadata - override in subclasses
    name: str = "base"
    display_name: str = "Base App"
    description: str = "Base application class"
    requires_credentials: bool = False

    # Configuration schema for the web UI
    # Format: {"field_name": {"type": "string|int|bool|password", "label": "...", "default": ...}}
    config_schema: dict[str, dict[str, Any]] = {}

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the app.

        Args:
            config: App-specific configuration dictionary.
        """
        self._config = config or {}
        self._enabled = self._config.get("enabled", True)

    @property
    def config(self) -> dict[str, Any]:
        """Get the app configuration."""
        return self._config

    @config.setter
    def config(self, value: dict[str, Any]) -> None:
        """Set the app configuration."""
        self._config = value
        self._enabled = value.get("enabled", True)

    @property
    def enabled(self) -> bool:
        """Check if the app is enabled."""
        return self._enabled

    def setup(self) -> bool:
        """Set up the app. Called when the app becomes active.

        Override this method to perform initialization like API authentication.

        Returns:
            True if setup was successful, False otherwise.
        """
        return True

    @abstractmethod
    def render(self, width: int, height: int) -> Image.Image:
        """Render the app's display content.

        Args:
            width: Display width in pixels.
            height: Display height in pixels.

        Returns:
            A PIL Image to display.
        """
        pass

    def cleanup(self) -> None:
        """Clean up the app. Called when switching away from this app.

        Override this method to release resources.
        """
        pass

    def update(self) -> None:
        """Update app data (e.g., fetch new weather data).

        Override this method for apps that need periodic data updates.
        This is called independently of render.
        """
        pass

    def get_update_interval(self) -> float:
        """Get the data update interval in seconds.

        Returns:
            Update interval in seconds, or 0 for no updates.
        """
        return 0

    def get_render_interval(self) -> float:
        """Get the render interval in seconds.

        Returns:
            Render interval in seconds. Default is 1.0.
        """
        return 1.0

    def validate_config(self) -> tuple[bool, str]:
        """Validate the app configuration.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if self.requires_credentials:
            # Check that all required credential fields are filled
            for field_name, field_info in self.config_schema.items():
                if field_info.get("required", False):
                    value = self._config.get(field_name, "")
                    if not value:
                        return False, f"Missing required field: {field_info.get('label', field_name)}"
        return True, ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, enabled={self.enabled})>"
