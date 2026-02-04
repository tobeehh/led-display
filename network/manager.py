"""Network manager for coordinating WiFi and captive portal."""

import threading
import time
from typing import Callable

from config import get_config

from .captive_portal import CaptivePortal
from .wifi import WiFiManager


class NetworkManager:
    """Manages network connectivity and captive portal."""

    def __init__(
        self,
        on_connected: Callable[[], None] | None = None,
        on_disconnected: Callable[[], None] | None = None,
    ):
        """Initialize the network manager.

        Args:
            on_connected: Callback when WiFi connects.
            on_disconnected: Callback when WiFi disconnects.
        """
        self._config = get_config()
        self._wifi = WiFiManager()
        self._captive_portal = CaptivePortal(on_connected=self._handle_portal_connected)

        self._on_connected = on_connected
        self._on_disconnected = on_disconnected

        self._running = False
        self._monitor_thread: threading.Thread | None = None
        self._was_connected = False
        self._captive_portal_active = False

    def _handle_portal_connected(self) -> None:
        """Handle successful connection from captive portal."""
        # Stop captive portal after successful connection
        time.sleep(2)  # Give time for the success page to be shown
        self.stop_captive_portal()

        if self._on_connected:
            self._on_connected()

    def start(self) -> None:
        """Start the network manager."""
        if self._running:
            return

        self._running = True

        # Check if WiFi is configured
        if not self._config.is_wifi_configured():
            print("[NetworkManager] No WiFi configured, starting captive portal")
            self.start_captive_portal()
        else:
            # Try to connect to configured network
            wifi_config = self._config.get("wifi")
            ssid = wifi_config.get("ssid", "")
            password = wifi_config.get("password", "")

            if ssid:
                print(f"[NetworkManager] Attempting to connect to {ssid}")
                if not self._wifi.is_connected():
                    success = self._wifi.connect(ssid, password)
                    if not success:
                        print("[NetworkManager] Connection failed, starting captive portal")
                        self.start_captive_portal()
                    else:
                        self._was_connected = True
                        if self._on_connected:
                            self._on_connected()
                else:
                    self._was_connected = True
                    if self._on_connected:
                        self._on_connected()

        # Start connection monitor
        self._monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop the network manager."""
        self._running = False

        if self._captive_portal_active:
            self._captive_portal.stop()
            self._captive_portal_active = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    def _monitor_connection(self) -> None:
        """Monitor WiFi connection status."""
        while self._running:
            try:
                is_connected = self._wifi.is_connected()

                # Connection lost
                if self._was_connected and not is_connected:
                    print("[NetworkManager] Connection lost")
                    self._was_connected = False
                    if self._on_disconnected:
                        self._on_disconnected()

                # Connection restored
                elif not self._was_connected and is_connected:
                    print("[NetworkManager] Connection restored")
                    self._was_connected = True
                    if self._on_connected:
                        self._on_connected()

                    # Stop captive portal if running
                    if self._captive_portal_active:
                        self.stop_captive_portal()

                time.sleep(5)

            except Exception as e:
                print(f"[NetworkManager] Monitor error: {e}")
                time.sleep(5)

    def start_captive_portal(self) -> bool:
        """Start the captive portal.

        Returns:
            True if started successfully.
        """
        if self._captive_portal_active:
            return True

        self._captive_portal_active = self._captive_portal.start()
        return self._captive_portal_active

    def stop_captive_portal(self) -> None:
        """Stop the captive portal."""
        if self._captive_portal_active:
            self._captive_portal.stop()
            self._captive_portal_active = False

    def is_connected(self) -> bool:
        """Check if WiFi is connected."""
        return self._wifi.is_connected()

    def has_internet(self) -> bool:
        """Check if internet is accessible."""
        return self._wifi.has_internet()

    def get_connection_info(self) -> dict:
        """Get current connection information."""
        info = self._wifi.get_connection_info()
        info["captive_portal_active"] = self._captive_portal_active
        info["has_internet"] = self.has_internet() if info["connected"] else False
        return info

    def scan_networks(self) -> list[dict]:
        """Scan for available WiFi networks."""
        return self._wifi.scan_networks()

    def connect(self, ssid: str, password: str) -> bool:
        """Connect to a WiFi network.

        Args:
            ssid: Network SSID.
            password: Network password.

        Returns:
            True if connection successful.
        """
        success = self._wifi.connect(ssid, password)
        if success:
            self._was_connected = True
            if self._on_connected:
                self._on_connected()
        return success

    def disconnect(self) -> None:
        """Disconnect from the current network."""
        self._wifi.disconnect()
        self._was_connected = False
        if self._on_disconnected:
            self._on_disconnected()

    def forget_network(self) -> None:
        """Forget the saved WiFi configuration."""
        self._config.clear_wifi_config()
        self.disconnect()


# Global network manager instance
_network_manager: NetworkManager | None = None


def get_network_manager() -> NetworkManager | None:
    """Get the global network manager instance."""
    return _network_manager


def set_network_manager(manager: NetworkManager) -> None:
    """Set the global network manager instance."""
    global _network_manager
    _network_manager = manager
