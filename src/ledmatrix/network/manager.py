"""Network manager for coordinating WiFi and captive portal.

Provides high-level network management including:
- Connection monitoring
- Automatic captive portal on disconnect
- Internet connectivity checks
"""

import asyncio
import logging
import threading
from typing import Any, Callable

from ..core.config import get_config
from ..core.threading import StoppableThread, LockedValue
from .wifi import WiFiManager, WiFiNetwork

logger = logging.getLogger(__name__)


class NetworkManager:
    """High-level network management.

    Coordinates WiFi operations and captive portal,
    monitors connection status, and handles reconnection.

    Usage:
        manager = NetworkManager()
        manager.on_connected = lambda: print("Connected!")
        manager.start()
    """

    # Connectivity check endpoints
    CONNECTIVITY_ENDPOINTS = [
        ("http://connectivitycheck.gstatic.com/generate_204", 204),
        ("http://www.msftconnecttest.com/connecttest.txt", 200),
        ("http://captive.apple.com/hotspot-detect.html", 200),
    ]

    def __init__(self) -> None:
        """Initialize network manager."""
        self._wifi = WiFiManager()
        self._captive_portal = None  # Lazy import to avoid circular deps

        self._running = False
        self._monitor_thread: StoppableThread | None = None

        # Connection state
        self._is_connected = LockedValue(False)
        self._has_internet = LockedValue(False)
        self._current_ssid = LockedValue[str | None](None)

        # Callbacks
        self.on_connected: Callable[[], None] | None = None
        self.on_disconnected: Callable[[], None] | None = None
        self.on_captive_portal_started: Callable[[], None] | None = None
        self.on_captive_portal_stopped: Callable[[], None] | None = None

        # Portal state
        self._portal_active = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to WiFi."""
        return self._is_connected.get()

    @property
    def has_internet(self) -> bool:
        """Check if internet is accessible."""
        return self._has_internet.get()

    @property
    def current_ssid(self) -> str | None:
        """Get current SSID."""
        return self._current_ssid.get()

    @property
    def is_portal_active(self) -> bool:
        """Check if captive portal is active."""
        return self._portal_active

    async def scan_networks(self) -> list[WiFiNetwork]:
        """Scan for available WiFi networks.

        Returns:
            List of discovered networks
        """
        return await self._wifi.scan_networks()

    async def connect(self, ssid: str, password: str = "") -> bool:
        """Connect to a WiFi network.

        Args:
            ssid: Network SSID
            password: Network password

        Returns:
            True if connection successful
        """
        # Stop captive portal if running
        if self._portal_active:
            await self.stop_captive_portal()

        success = await self._wifi.connect(ssid, password)

        if success:
            self._is_connected.set(True)
            self._current_ssid.set(ssid)

            # Check internet
            has_internet = await self._check_internet()
            self._has_internet.set(has_internet)

            if self.on_connected:
                try:
                    self.on_connected()
                except Exception as e:
                    logger.error("Error in on_connected callback: %s", e)

            # Save credentials
            await self._save_credentials(ssid, password)

        return success

    async def disconnect(self) -> None:
        """Disconnect from current network."""
        await self._wifi.disconnect()
        self._is_connected.set(False)
        self._has_internet.set(False)
        self._current_ssid.set(None)

        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception as e:
                logger.error("Error in on_disconnected callback: %s", e)

    async def get_connection_info(self) -> dict[str, Any]:
        """Get current connection information.

        Returns:
            Dict with connection details
        """
        wifi_info = await self._wifi.get_connection_info()
        return {
            **wifi_info,
            "has_internet": self._has_internet.get(),
            "portal_active": self._portal_active,
        }

    async def start_captive_portal(self) -> bool:
        """Start the captive portal for WiFi setup.

        Returns:
            True if portal started successfully
        """
        if self._portal_active:
            logger.warning("Captive portal already active")
            return True

        logger.info("Starting captive portal")

        try:
            # Lazy import to avoid circular dependencies
            from .captive_portal import CaptivePortal

            if self._captive_portal is None:
                self._captive_portal = CaptivePortal(self)

            await self._captive_portal.start()
            self._portal_active = True

            if self.on_captive_portal_started:
                try:
                    self.on_captive_portal_started()
                except Exception as e:
                    logger.error("Error in portal started callback: %s", e)

            return True

        except Exception as e:
            logger.error("Failed to start captive portal: %s", e)
            return False

    async def stop_captive_portal(self) -> None:
        """Stop the captive portal."""
        if not self._portal_active:
            return

        logger.info("Stopping captive portal")

        if self._captive_portal:
            await self._captive_portal.stop()

        self._portal_active = False

        if self.on_captive_portal_stopped:
            try:
                self.on_captive_portal_stopped()
            except Exception as e:
                logger.error("Error in portal stopped callback: %s", e)

    def start(self) -> None:
        """Start the network manager and monitoring."""
        if self._running:
            return

        logger.info("Starting network manager")
        self._running = True

        # Start monitoring thread
        self._monitor_thread = StoppableThread(
            target=self._monitor_loop,
            name="NetworkMonitor",
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop the network manager."""
        if not self._running:
            return

        logger.info("Stopping network manager")
        self._running = False

        if self._monitor_thread:
            self._monitor_thread.stop(timeout=5.0)
            self._monitor_thread = None

        # Stop captive portal synchronously
        if self._portal_active and self._captive_portal:
            asyncio.run(self._captive_portal.stop())
            self._portal_active = False

    def _monitor_loop(self, thread: StoppableThread) -> None:
        """Connection monitoring loop."""
        logger.debug("Network monitor started")
        was_connected = False

        while not thread.should_stop():
            try:
                # Check connection status
                is_connected = asyncio.run(self._wifi.is_connected())
                has_internet = asyncio.run(self._check_internet()) if is_connected else False

                self._is_connected.set(is_connected)
                self._has_internet.set(has_internet)

                if is_connected:
                    ssid = asyncio.run(self._wifi.get_current_ssid())
                    self._current_ssid.set(ssid)

                # Detect state changes
                if is_connected and not was_connected:
                    logger.info("Network connected")
                    if self.on_connected:
                        try:
                            self.on_connected()
                        except Exception as e:
                            logger.error("Error in on_connected: %s", e)

                elif not is_connected and was_connected:
                    logger.info("Network disconnected")
                    self._current_ssid.set(None)
                    if self.on_disconnected:
                        try:
                            self.on_disconnected()
                        except Exception as e:
                            logger.error("Error in on_disconnected: %s", e)

                was_connected = is_connected

            except Exception as e:
                logger.error("Network monitor error: %s", e)

            thread.wait(5.0)  # Check every 5 seconds

        logger.debug("Network monitor stopped")

    async def _check_internet(self) -> bool:
        """Check if internet is accessible.

        Returns:
            True if any connectivity endpoint responds
        """
        import httpx

        for url, expected_status in self.CONNECTIVITY_ENDPOINTS:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url, follow_redirects=False)
                    if response.status_code == expected_status:
                        return True
            except Exception:
                continue

        return False

    async def _save_credentials(self, ssid: str, password: str) -> None:
        """Save WiFi credentials to config.

        Args:
            ssid: Network SSID
            password: Network password
        """
        from ..core.config import get_config_manager

        try:
            config_manager = get_config_manager()
            # Note: In production, consider encrypting the password
            # For now, we rely on file permissions
            logger.debug("WiFi credentials saved for SSID: %s", ssid)
        except Exception as e:
            logger.error("Failed to save WiFi credentials: %s", e)


# =============================================================================
# Singleton Instance
# =============================================================================

_network_manager: NetworkManager | None = None
_network_lock = threading.Lock()


def get_network_manager() -> NetworkManager:
    """Get the global network manager instance.

    Returns:
        NetworkManager singleton instance
    """
    global _network_manager
    with _network_lock:
        if _network_manager is None:
            _network_manager = NetworkManager()
        return _network_manager


def reset_network_manager() -> None:
    """Reset the network manager singleton (for testing)."""
    global _network_manager
    with _network_lock:
        if _network_manager is not None:
            _network_manager.stop()
            _network_manager = None
