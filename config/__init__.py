"""Configuration module for LED Display system."""

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .defaults import (
    APP_DEFAULTS,
    BUTTON_DEFAULTS,
    CONFIG_FILE,
    DISPLAY_DEFAULTS,
    NETWORK_DEFAULTS,
    WEB_DEFAULTS,
)


class ConfigStore:
    """Manages persistent configuration storage."""

    def __init__(self, config_path: str | None = None):
        """Initialize the config store.

        Args:
            config_path: Path to the config file. Defaults to config/settings.json.
        """
        if config_path is None:
            # Get the project root directory
            project_root = Path(__file__).parent.parent
            config_path = project_root / CONFIG_FILE

        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self._load()

    def _get_defaults(self) -> dict[str, Any]:
        """Get the default configuration."""
        return {
            "display": deepcopy(DISPLAY_DEFAULTS),
            "button": deepcopy(BUTTON_DEFAULTS),
            "network": deepcopy(NETWORK_DEFAULTS),
            "web": deepcopy(WEB_DEFAULTS),
            "apps": deepcopy(APP_DEFAULTS),
            "wifi": {
                "ssid": "",
                "password": "",
                "configured": False,
            },
        }

    def _load(self) -> None:
        """Load configuration from file, creating defaults if needed."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    self._config = json.load(f)
                # Merge with defaults to ensure all keys exist
                defaults = self._get_defaults()
                self._config = self._deep_merge(defaults, self._config)
            except (json.JSONDecodeError, IOError):
                self._config = self._get_defaults()
        else:
            self._config = self._get_defaults()
            self._save()

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def _save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, section: str, key: str | None = None, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            section: The configuration section (e.g., 'display', 'apps').
            key: Optional key within the section.
            default: Default value if key doesn't exist.

        Returns:
            The configuration value.
        """
        if section not in self._config:
            return default

        if key is None:
            return self._config[section]

        return self._config[section].get(key, default)

    def set(self, section: str, key: str | None = None, value: Any = None) -> None:
        """Set a configuration value.

        Args:
            section: The configuration section.
            key: Optional key within the section. If None, sets the entire section.
            value: The value to set.
        """
        if key is None:
            self._config[section] = value
        else:
            if section not in self._config:
                self._config[section] = {}
            self._config[section][key] = value
        self._save()

    def get_app_config(self, app_name: str) -> dict[str, Any]:
        """Get configuration for a specific app.

        Args:
            app_name: The app name (e.g., 'clock', 'weather').

        Returns:
            The app configuration dictionary.
        """
        apps_config = self.get("apps", "apps", {})
        return apps_config.get(app_name, {})

    def set_app_config(self, app_name: str, config: dict[str, Any]) -> None:
        """Set configuration for a specific app.

        Args:
            app_name: The app name.
            config: The app configuration dictionary.
        """
        if "apps" not in self._config:
            self._config["apps"] = deepcopy(APP_DEFAULTS)
        if "apps" not in self._config["apps"]:
            self._config["apps"]["apps"] = {}
        self._config["apps"]["apps"][app_name] = config
        self._save()

    def get_active_app(self) -> str:
        """Get the currently active app name."""
        return self.get("apps", "active_app", "clock")

    def set_active_app(self, app_name: str) -> None:
        """Set the active app."""
        self.set("apps", "active_app", app_name)

    def is_wifi_configured(self) -> bool:
        """Check if WiFi is configured."""
        return self.get("wifi", "configured", False)

    def set_wifi_config(self, ssid: str, password: str) -> None:
        """Set WiFi configuration."""
        self._config["wifi"] = {
            "ssid": ssid,
            "password": password,
            "configured": True,
        }
        self._save()

    def clear_wifi_config(self) -> None:
        """Clear WiFi configuration."""
        self._config["wifi"] = {
            "ssid": "",
            "password": "",
            "configured": False,
        }
        self._save()

    @property
    def all(self) -> dict[str, Any]:
        """Get the entire configuration."""
        return deepcopy(self._config)


# Global config instance
_config_store: ConfigStore | None = None


def get_config() -> ConfigStore:
    """Get the global config store instance."""
    global _config_store
    if _config_store is None:
        _config_store = ConfigStore()
    return _config_store
