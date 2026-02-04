"""Secure WiFi management using NetworkManager/nmcli.

Provides safe WiFi operations without shell injection vulnerabilities.
Uses nmcli for all network operations (Trixie compatible).
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

from ..core.errors import NetworkError
from ..core.retry import async_retry, RetryConfig

logger = logging.getLogger(__name__)


@dataclass
class WiFiNetwork:
    """Represents a discovered WiFi network."""

    ssid: str
    signal: int  # 0-100
    security: str  # "open", "wpa", "wpa2", "wpa3", etc.
    in_use: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "ssid": self.ssid,
            "signal": self.signal,
            "security": self.security,
            "in_use": self.in_use,
        }


class WiFiManager:
    """Secure WiFi management using NetworkManager/nmcli.

    All operations use nmcli with list arguments (no shell).
    SSID and password validation prevents injection attacks.

    Usage:
        wifi = WiFiManager()
        networks = await wifi.scan_networks()
        await wifi.connect("MyNetwork", "password123")
    """

    # Regex for SSID validation (alphanumeric, spaces, common punctuation)
    SSID_PATTERN = re.compile(r"^[\w\s\-\.\!\@\#\$\%\&\*\(\)]+$")

    # Connection name prefix for managed connections
    CONNECTION_PREFIX = "led-display"

    def __init__(self, interface: str = "wlan0") -> None:
        """Initialize WiFi manager.

        Args:
            interface: WiFi interface name
        """
        self._interface = interface
        self._connection_name = f"{self.CONNECTION_PREFIX}-wifi"

    def _validate_ssid(self, ssid: str) -> None:
        """Validate SSID to prevent injection.

        Args:
            ssid: SSID to validate

        Raises:
            NetworkError: If SSID is invalid
        """
        if not ssid:
            raise NetworkError("SSID cannot be empty")
        if len(ssid) > 32:
            raise NetworkError("SSID too long (max 32 characters)")
        if not self.SSID_PATTERN.match(ssid):
            raise NetworkError("SSID contains invalid characters")

    def _validate_password(self, password: str) -> None:
        """Validate password.

        Args:
            password: Password to validate

        Raises:
            NetworkError: If password is invalid
        """
        if password and len(password) > 63:
            raise NetworkError("Password too long (max 63 characters)")

    async def _run_nmcli(
        self,
        *args: str,
        check: bool = True,
        timeout: float = 30.0,
    ) -> str:
        """Run nmcli command safely.

        Args:
            *args: nmcli arguments
            check: Raise on non-zero exit
            timeout: Command timeout in seconds

        Returns:
            Command stdout

        Raises:
            NetworkError: If command fails
        """
        cmd = ["nmcli", *args]
        logger.debug("Running: nmcli %s", " ".join(args))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise NetworkError("nmcli command timed out", details={"args": args})

        if check and proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            raise NetworkError(
                f"nmcli failed: {error_msg}",
                details={"args": args, "returncode": proc.returncode},
            )

        return stdout.decode().strip() if stdout else ""

    @async_retry(RetryConfig(max_attempts=2, base_delay=1.0))
    async def scan_networks(self) -> list[WiFiNetwork]:
        """Scan for available WiFi networks.

        Returns:
            List of discovered networks sorted by signal strength
        """
        logger.info("Scanning WiFi networks")

        # Force rescan
        await self._run_nmcli("device", "wifi", "rescan", check=False)
        await asyncio.sleep(2)  # Wait for scan

        # Get network list
        output = await self._run_nmcli(
            "-t",
            "-f",
            "SSID,SIGNAL,SECURITY,IN-USE",
            "device",
            "wifi",
            "list",
        )

        networks: list[WiFiNetwork] = []
        seen_ssids: set[str] = set()

        for line in output.split("\n"):
            if not line.strip():
                continue

            # nmcli uses : as separator in terse mode
            # Handle SSIDs that might contain colons
            parts = line.split(":")

            if len(parts) >= 4:
                # Last three parts are signal, security, in-use
                in_use = parts[-1] == "*"
                security = parts[-2] if parts[-2] else "open"
                try:
                    signal = int(parts[-3]) if parts[-3] else 0
                except ValueError:
                    signal = 0

                # SSID is everything before the last 3 parts
                ssid = ":".join(parts[:-3])

                if not ssid or ssid in seen_ssids:
                    continue

                seen_ssids.add(ssid)

                networks.append(
                    WiFiNetwork(
                        ssid=ssid,
                        signal=signal,
                        security=security.lower().replace("wpa2", "wpa2").replace("wpa3", "wpa3"),
                        in_use=in_use,
                    )
                )

        # Sort by signal strength
        networks.sort(key=lambda n: n.signal, reverse=True)

        logger.info("Found %d WiFi networks", len(networks))
        return networks

    async def connect(self, ssid: str, password: str = "") -> bool:
        """Connect to a WiFi network securely.

        Args:
            ssid: Network SSID
            password: Network password (empty for open networks)

        Returns:
            True if connection successful
        """
        # Validate inputs
        self._validate_ssid(ssid)
        self._validate_password(password)

        logger.info("Connecting to WiFi: %s", ssid)

        try:
            # Delete existing connection with this name
            await self._run_nmcli("connection", "delete", self._connection_name, check=False)

            # Create new connection
            # nmcli properly handles argument escaping
            if password:
                await self._run_nmcli(
                    "device",
                    "wifi",
                    "connect",
                    ssid,
                    "password",
                    password,
                    "name",
                    self._connection_name,
                )
            else:
                await self._run_nmcli(
                    "device",
                    "wifi",
                    "connect",
                    ssid,
                    "name",
                    self._connection_name,
                )

            # Verify connection
            await asyncio.sleep(5)
            if await self.is_connected():
                logger.info("Successfully connected to %s", ssid)
                return True
            else:
                logger.warning("Connection to %s may have failed", ssid)
                return False

        except NetworkError as e:
            logger.error("Connection failed: %s", e)
            return False

    async def disconnect(self) -> None:
        """Disconnect from current WiFi network."""
        logger.info("Disconnecting WiFi")
        await self._run_nmcli("device", "disconnect", self._interface, check=False)

    async def is_connected(self) -> bool:
        """Check if connected to a WiFi network.

        Returns:
            True if connected
        """
        try:
            output = await self._run_nmcli("-t", "-f", "STATE", "device", "status")
            return "connected" in output.lower()
        except NetworkError:
            return False

    async def get_current_ssid(self) -> str | None:
        """Get the SSID of the currently connected network.

        Returns:
            SSID string or None if not connected
        """
        try:
            output = await self._run_nmcli("-t", "-f", "ACTIVE,SSID", "device", "wifi")
            for line in output.split("\n"):
                if line.startswith("yes:"):
                    return line.split(":", 1)[1]
            return None
        except NetworkError:
            return None

    async def get_ip_address(self) -> str | None:
        """Get the current IP address.

        Returns:
            IP address string or None
        """
        try:
            output = await self._run_nmcli(
                "-t",
                "-f",
                "IP4.ADDRESS",
                "device",
                "show",
                self._interface,
            )
            for line in output.split("\n"):
                if "IP4.ADDRESS" in line:
                    # Format: IP4.ADDRESS[1]:192.168.1.100/24
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if match:
                        return match.group(1)
            return None
        except NetworkError:
            return None

    async def get_connection_info(self) -> dict[str, Any]:
        """Get comprehensive connection information.

        Returns:
            Dict with connection details
        """
        connected = await self.is_connected()

        return {
            "connected": connected,
            "ssid": await self.get_current_ssid() if connected else None,
            "ip_address": await self.get_ip_address() if connected else None,
            "interface": self._interface,
        }

    async def forget_network(self, connection_name: str | None = None) -> None:
        """Forget a saved network.

        Args:
            connection_name: Connection name to forget (default: managed connection)
        """
        name = connection_name or self._connection_name
        await self._run_nmcli("connection", "delete", name, check=False)
        logger.info("Forgot network: %s", name)

    async def get_saved_connections(self) -> list[str]:
        """Get list of saved WiFi connections.

        Returns:
            List of connection names
        """
        try:
            output = await self._run_nmcli(
                "-t",
                "-f",
                "NAME,TYPE",
                "connection",
                "show",
            )

            connections = []
            for line in output.split("\n"):
                if ":802-11-wireless" in line or ":wifi" in line:
                    name = line.split(":")[0]
                    if name:
                        connections.append(name)

            return connections
        except NetworkError:
            return []
