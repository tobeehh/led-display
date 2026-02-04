"""Pydantic schemas for API request/response validation.

Provides type-safe request parsing and response serialization.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator


# =============================================================================
# Request Schemas
# =============================================================================


class LoginRequest(BaseModel):
    """Login request."""

    password: SecretStr


class SetupPasswordRequest(BaseModel):
    """Initial password setup request."""

    password: SecretStr = Field(..., min_length=8)
    confirm_password: SecretStr = Field(..., min_length=8)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: SecretStr, info) -> SecretStr:
        if "password" in info.data and v.get_secret_value() != info.data["password"].get_secret_value():
            raise ValueError("Passwords do not match")
        return v


class WiFiConnectRequest(BaseModel):
    """WiFi connection request."""

    ssid: str = Field(..., min_length=1, max_length=32)
    password: str = Field(default="", max_length=63)

    @field_validator("ssid")
    @classmethod
    def validate_ssid(cls, v: str) -> str:
        if not re.match(r"^[\w\s\-\.\!\@\#\$\%\&\*\(\)]+$", v):
            raise ValueError("SSID contains invalid characters")
        return v


class AppConfigRequest(BaseModel):
    """App configuration update request."""

    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class BrightnessRequest(BaseModel):
    """Display brightness request."""

    brightness: int = Field(..., ge=0, le=100)


class RotationRequest(BaseModel):
    """App rotation settings request."""

    enabled: bool
    interval: int = Field(30, ge=5, le=3600)


class ActivateAppRequest(BaseModel):
    """App activation request."""

    app_name: str = Field(..., min_length=1)


# =============================================================================
# Response Schemas
# =============================================================================


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool
    message: str = ""
    data: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: str
    detail: str | None = None


class StatusResponse(BaseModel):
    """System status response."""

    active_app: str | None
    brightness: int
    rotation_enabled: bool
    rotation_interval: int
    network: dict[str, Any]
    uptime: float


class AppInfo(BaseModel):
    """App information for API responses."""

    name: str
    display_name: str
    description: str
    enabled: bool
    active: bool
    requires_network: bool
    requires_credentials: bool
    config_schema: dict[str, Any]
    current_config: dict[str, Any]


class AppsListResponse(BaseModel):
    """List of apps response."""

    apps: list[AppInfo]


class WiFiNetwork(BaseModel):
    """WiFi network information."""

    ssid: str
    signal: int
    security: str
    in_use: bool


class WiFiNetworksResponse(BaseModel):
    """WiFi networks scan response."""

    networks: list[WiFiNetwork]


class WiFiStatusResponse(BaseModel):
    """WiFi connection status response."""

    connected: bool
    ssid: str | None
    ip_address: str | None
    has_internet: bool
    portal_active: bool
