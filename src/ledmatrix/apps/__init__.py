"""Display applications module.

Provides:
- BaseApp abstract class for app implementation
- AppScheduler for app lifecycle management
- Built-in apps: clock, weather, stocks, spotify, text
"""

from .base import BaseApp, AppMetadata, AppState, RenderResult, ConfigFieldSchema
from .scheduler import AppScheduler, get_app_scheduler

__all__ = [
    "BaseApp",
    "AppMetadata",
    "AppState",
    "RenderResult",
    "ConfigFieldSchema",
    "AppScheduler",
    "get_app_scheduler",
]
