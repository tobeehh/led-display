"""Network module for WiFi and captive portal management."""

from .manager import NetworkManager, get_network_manager
from .wifi import WiFiManager

__all__ = ["NetworkManager", "get_network_manager", "WiFiManager"]
