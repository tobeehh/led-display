"""Network management module.

Provides:
- WiFiManager for nmcli-based WiFi control
- NetworkManager for connection coordination
- CaptivePortal for initial setup
"""

from .wifi import WiFiManager, WiFiNetwork
from .manager import NetworkManager, get_network_manager
from .captive_portal import CaptivePortal

__all__ = [
    "WiFiManager",
    "WiFiNetwork",
    "NetworkManager",
    "get_network_manager",
    "CaptivePortal",
]
