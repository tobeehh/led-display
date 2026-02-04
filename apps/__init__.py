"""Apps module for LED display applications."""

from .base import BaseApp
from .manager import AppManager, get_app_manager

__all__ = ["BaseApp", "AppManager", "get_app_manager"]
