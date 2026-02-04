"""Configuration management with Pydantic validation.

Provides type-safe configuration with:
- Pydantic models for validation
- YAML file persistence
- Thread-safe updates
- Default values for FM6126A panels
"""

import logging
import secrets
import threading
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Models
# =============================================================================


class DisplayConfig(BaseModel):
    """LED Matrix display configuration for FM6126A panels."""

    rows: int = Field(32, ge=16, le=64, description="Panel row count")
    cols: int = Field(64, ge=32, le=128, description="Panel column count")
    chain_length: int = Field(2, ge=1, le=4, description="Number of chained panels")
    parallel: int = Field(1, ge=1, le=3, description="Parallel chains")
    hardware_mapping: str = Field("adafruit-hat", description="GPIO mapping profile")
    gpio_slowdown: int = Field(4, ge=0, le=5, description="GPIO timing slowdown")
    brightness: int = Field(50, ge=0, le=100, description="Display brightness %")

    # FM6126A specific settings
    panel_type: str = Field("FM6126A", description="Panel driver chip type")
    row_address_type: int = Field(3, ge=0, le=5, description="Row addressing mode (3=ABC)")

    # Pixel mapping
    pixel_mapper_config: str = Field("U-mapper", description="Panel arrangement mapper")

    # PWM settings
    pwm_bits: int = Field(11, ge=1, le=11, description="PWM color depth bits")
    pwm_lsb_nanoseconds: int = Field(130, ge=50, le=500, description="PWM timing")
    scan_mode: int = Field(1, ge=0, le=1, description="Scan mode (0=progressive, 1=interlaced)")
    multiplexing: int = Field(0, ge=0, le=18, description="Multiplexing mode")

    # Optional settings
    limit_refresh_rate_hz: int = Field(0, ge=0, description="Refresh rate limit (0=unlimited)")
    disable_hardware_pulsing: bool = Field(False, description="Disable hardware pulsing")
    show_refresh_rate: bool = Field(False, description="Show refresh rate on console")
    inverse_colors: bool = Field(False, description="Invert colors")
    led_rgb_sequence: str = Field("RGB", description="LED color order")


class ButtonConfig(BaseModel):
    """GPIO button configuration."""

    pin: int = Field(17, ge=0, le=27, description="GPIO BCM pin number")
    long_press_duration: float = Field(
        3.0, ge=1.0, le=10.0, description="Seconds for long press"
    )
    debounce_time: float = Field(0.05, ge=0.01, le=0.5, description="Debounce time in seconds")


class NetworkConfig(BaseModel):
    """Network/WiFi configuration."""

    ap_ssid: str = Field(
        "LED-Display-Setup",
        min_length=1,
        max_length=32,
        description="Captive portal SSID",
    )
    ap_password: str | None = Field(None, description="AP password (None=open)")
    ap_channel: int = Field(6, ge=1, le=14, description="WiFi channel")
    ap_ip: str = Field("192.168.4.1", description="AP IP address")
    captive_portal_port: int = Field(80, ge=1, le=65535, description="Portal web server port")

    @field_validator("ap_ssid")
    @classmethod
    def validate_ssid(cls, v: str) -> str:
        """Validate SSID contains safe characters."""
        import re

        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("SSID contains invalid characters")
        return v


class WebConfig(BaseModel):
    """Web server configuration."""

    host: str = Field("0.0.0.0", description="Server bind address")
    port: int = Field(80, ge=1, le=65535, description="Server port")
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_hex(32)),
        description="Session secret key",
    )
    session_lifetime: int = Field(86400, ge=300, description="Session lifetime in seconds")
    require_auth: bool = Field(True, description="Require authentication")
    admin_password_hash: str | None = Field(None, description="Hashed admin password")
    admin_password_salt: str | None = Field(None, description="Password salt")


class ClockAppConfig(BaseModel):
    """Clock app settings."""

    enabled: bool = True
    format_24h: bool = Field(True, description="Use 24-hour format")
    show_date: bool = Field(True, description="Show date below time")
    show_seconds: bool = Field(False, description="Show seconds")
    color_mode: str = Field("auto", description="Color mode: auto, static")
    color: str = Field("#FFFFFF", description="Static color (hex)")


class WeatherAppConfig(BaseModel):
    """Weather app settings."""

    enabled: bool = False
    api_key: str = Field("", description="OpenWeatherMap API key")
    city: str = Field("Berlin", description="City name")
    units: str = Field("metric", description="Units: metric, imperial")
    update_interval: int = Field(600, ge=60, description="Update interval in seconds")


class StocksAppConfig(BaseModel):
    """Stocks app settings."""

    enabled: bool = False
    tickers: str = Field("AAPL,GOOGL,BTC-USD,ETH-USD", description="Comma-separated tickers")
    rotation_interval: int = Field(10, ge=3, description="Ticker rotation interval")
    update_interval: int = Field(300, ge=60, description="Data update interval")
    display_mode: str = Field("logo", description="Display mode: logo, chart, both")
    currency: str = Field("USD", description="Display currency")


class SpotifyAppConfig(BaseModel):
    """Spotify app settings."""

    enabled: bool = False
    client_id: str = Field("", description="Spotify client ID")
    client_secret: SecretStr = Field(default=SecretStr(""), description="Spotify client secret")
    refresh_token: SecretStr = Field(default=SecretStr(""), description="Spotify refresh token")
    show_album_art: bool = Field(True, description="Show album artwork")


class TextAppConfig(BaseModel):
    """Text app settings."""

    enabled: bool = True
    message: str = Field("Hello World!", description="Text to display")
    scroll: bool = Field(True, description="Enable scrolling")
    scroll_speed: int = Field(30, ge=1, le=100, description="Scroll speed")
    style: str = Field("modern", description="Style: modern, neon, minimal, retro")
    color: str = Field("#00D4FF", description="Text color (hex)")
    size: str = Field("large", description="Font size: small, large")


class WordClockAppConfig(BaseModel):
    """Word Clock (QLOCKTWO-style) app settings."""

    enabled: bool = True
    color_mode: str = Field("auto", description="Color mode: auto, static")
    color: str = Field("#FFFFFF", description="Static color (hex)")
    dim_factor: int = Field(8, ge=0, le=30, description="Inactive letter brightness %")
    transition_speed: str = Field("normal", description="Transition: instant, fast, normal, slow")
    show_dots: bool = Field(True, description="Show minute precision dots")
    dialect: str = Field("standard", description="Dialect: standard, regional")


class AppsConfig(BaseModel):
    """Apps management configuration."""

    active_app: str = Field("clock", description="Currently active app")
    rotation_enabled: bool = Field(False, description="Auto-rotate apps")
    rotation_interval: int = Field(30, ge=5, le=3600, description="Rotation interval in seconds")

    # Individual app configs
    clock: ClockAppConfig = Field(default_factory=ClockAppConfig)
    wordclock: WordClockAppConfig = Field(default_factory=WordClockAppConfig)
    weather: WeatherAppConfig = Field(default_factory=WeatherAppConfig)
    stocks: StocksAppConfig = Field(default_factory=StocksAppConfig)
    spotify: SpotifyAppConfig = Field(default_factory=SpotifyAppConfig)
    text: TextAppConfig = Field(default_factory=TextAppConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field("INFO", description="Log level")
    format: str = Field("simple", description="Format: simple, structured")
    file: str | None = Field(None, description="Log file path")
    max_size_mb: int = Field(10, ge=1, description="Max log file size")
    backup_count: int = Field(3, ge=0, description="Number of backup files")


class Config(BaseModel):
    """Root configuration model."""

    display: DisplayConfig = Field(default_factory=DisplayConfig)
    button: ButtonConfig = Field(default_factory=ButtonConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    apps: AppsConfig = Field(default_factory=AppsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# =============================================================================
# Configuration Manager
# =============================================================================


class ConfigManager:
    """Thread-safe configuration manager with file persistence.

    Provides:
    - Pydantic validation on load/save
    - Thread-safe read/write operations
    - Automatic persistence to YAML

    Usage:
        config_manager = ConfigManager("/path/to/config.yaml")
        config = config_manager.get()
        config_manager.update_display(brightness=75)
    """

    _instance: "ConfigManager | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)
        self._config: Config
        self._lock = threading.RLock()
        self._load()

    @classmethod
    def get_instance(cls, config_path: str | Path | None = None) -> "ConfigManager":
        """Get singleton instance.

        Args:
            config_path: Path to config file (only used on first call)

        Returns:
            ConfigManager singleton instance
        """
        with cls._instance_lock:
            if cls._instance is None:
                if config_path is None:
                    config_path = Path("/opt/led-display/config/config.yaml")
                cls._instance = cls(config_path)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._instance_lock:
            cls._instance = None

    def _load(self) -> None:
        """Load and validate configuration from file."""
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    data = yaml.safe_load(f) or {}
                self._config = Config.model_validate(data)
                logger.info("Loaded config from %s", self._config_path)
            except Exception as e:
                logger.warning("Failed to load config, using defaults: %s", e)
                self._config = Config()
        else:
            logger.info("Config file not found, using defaults")
            self._config = Config()
            self._save()

    def _save(self) -> None:
        """Persist configuration to file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize with secrets exposed for storage
            data = self._config.model_dump(mode="json")

            # Write atomically via temp file
            temp_path = self._config_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            temp_path.replace(self._config_path)

            logger.debug("Saved config to %s", self._config_path)
        except Exception as e:
            logger.error("Failed to save config: %s", e)
            raise

    def get(self) -> Config:
        """Get current configuration (thread-safe copy).

        Returns:
            Deep copy of current configuration
        """
        with self._lock:
            return self._config.model_copy(deep=True)

    def update(self, **kwargs: Any) -> None:
        """Update top-level config sections.

        Args:
            **kwargs: Section names and their new values
        """
        with self._lock:
            data = self._config.model_dump()
            for key, value in kwargs.items():
                if key in data and isinstance(value, dict):
                    data[key].update(value)
                else:
                    data[key] = value
            self._config = Config.model_validate(data)
            self._save()

    def update_display(self, **kwargs: Any) -> None:
        """Update display settings."""
        with self._lock:
            data = self._config.model_dump()
            data["display"].update(kwargs)
            self._config = Config.model_validate(data)
            self._save()

    def update_app(self, app_name: str, **kwargs: Any) -> None:
        """Update specific app settings.

        Args:
            app_name: Name of the app (clock, weather, etc.)
            **kwargs: Settings to update
        """
        with self._lock:
            data = self._config.model_dump()
            if app_name in data["apps"]:
                data["apps"][app_name].update(kwargs)
                self._config = Config.model_validate(data)
                self._save()
            else:
                raise ValueError(f"Unknown app: {app_name}")

    def set_active_app(self, app_name: str) -> None:
        """Set the currently active app."""
        with self._lock:
            data = self._config.model_dump()
            data["apps"]["active_app"] = app_name
            self._config = Config.model_validate(data)
            self._save()

    def set_admin_password(self, password_hash: str, salt: str) -> None:
        """Set the admin password hash and salt."""
        with self._lock:
            data = self._config.model_dump()
            data["web"]["admin_password_hash"] = password_hash
            data["web"]["admin_password_salt"] = salt
            self._config = Config.model_validate(data)
            self._save()


# =============================================================================
# Convenience Functions
# =============================================================================


def get_config() -> Config:
    """Get current configuration from singleton manager.

    Returns:
        Current configuration
    """
    return ConfigManager.get_instance().get()


def get_config_manager() -> ConfigManager:
    """Get the singleton ConfigManager instance.

    Returns:
        ConfigManager instance
    """
    return ConfigManager.get_instance()
