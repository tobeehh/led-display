"""Web API routes."""

from .api import router as api_router
from .apps import router as apps_router
from .wifi import router as wifi_router

__all__ = [
    "api_router",
    "apps_router",
    "wifi_router",
]
