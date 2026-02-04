"""WiFi connection management for Raspberry Pi."""

import subprocess
import time
from typing import Any

from config import get_config


class WiFiManager:
    """Manages WiFi connections on Raspberry Pi."""

    def __init__(self):
        """Initialize the WiFi manager."""
        self._config = get_config()

    def scan_networks(self) -> list[dict[str, Any]]:
        """Scan for available WiFi networks.

        Returns:
            List of dictionaries with network info (ssid, signal, security).
        """
        networks = []

        try:
            # Use iwlist to scan for networks
            result = subprocess.run(
                ["sudo", "iwlist", "wlan0", "scan"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"[WiFi] Scan failed: {result.stderr}")
                return networks

            current_network: dict[str, Any] = {}
            for line in result.stdout.split("\n"):
                line = line.strip()

                if "Cell" in line and "Address:" in line:
                    if current_network.get("ssid"):
                        networks.append(current_network)
                    current_network = {"ssid": "", "signal": 0, "security": "Open"}

                elif "ESSID:" in line:
                    ssid = line.split('ESSID:"')[1].rstrip('"')
                    current_network["ssid"] = ssid

                elif "Signal level=" in line:
                    try:
                        # Parse signal level (format varies)
                        if "dBm" in line:
                            signal = int(line.split("Signal level=")[1].split(" ")[0])
                            # Convert dBm to percentage (rough approximation)
                            signal_pct = min(100, max(0, (signal + 100) * 2))
                        else:
                            signal_pct = int(
                                line.split("Signal level=")[1].split("/")[0]
                            )
                        current_network["signal"] = signal_pct
                    except (ValueError, IndexError):
                        current_network["signal"] = 0

                elif "Encryption key:on" in line:
                    current_network["security"] = "Encrypted"

                elif "WPA" in line or "WPA2" in line:
                    current_network["security"] = "WPA/WPA2"

            # Add last network
            if current_network.get("ssid"):
                networks.append(current_network)

            # Remove duplicates and empty SSIDs
            seen = set()
            unique_networks = []
            for net in networks:
                if net["ssid"] and net["ssid"] not in seen:
                    seen.add(net["ssid"])
                    unique_networks.append(net)

            # Sort by signal strength
            unique_networks.sort(key=lambda x: x["signal"], reverse=True)

            return unique_networks

        except subprocess.TimeoutExpired:
            print("[WiFi] Scan timed out")
            return networks
        except Exception as e:
            print(f"[WiFi] Scan error: {e}")
            return networks

    def connect(self, ssid: str, password: str) -> bool:
        """Connect to a WiFi network.

        Args:
            ssid: The network SSID.
            password: The network password.

        Returns:
            True if connection was successful.
        """
        try:
            # Create wpa_supplicant configuration
            wpa_config = f'''
country=DE
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
            # Write configuration
            with open("/tmp/wpa_supplicant.conf", "w") as f:
                f.write(wpa_config)

            # Copy to actual location with sudo
            subprocess.run(
                [
                    "sudo",
                    "cp",
                    "/tmp/wpa_supplicant.conf",
                    "/etc/wpa_supplicant/wpa_supplicant.conf",
                ],
                check=True,
            )

            # Restart networking
            subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], check=True)

            # Wait for connection
            for _ in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if self.is_connected():
                    # Save to config
                    self._config.set_wifi_config(ssid, password)
                    return True

            return False

        except Exception as e:
            print(f"[WiFi] Connection error: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the current WiFi network."""
        try:
            subprocess.run(["sudo", "ip", "link", "set", "wlan0", "down"], check=True)
            subprocess.run(["sudo", "ip", "link", "set", "wlan0", "up"], check=True)
        except Exception as e:
            print(f"[WiFi] Disconnect error: {e}")

    def is_connected(self) -> bool:
        """Check if connected to a WiFi network.

        Returns:
            True if connected.
        """
        try:
            result = subprocess.run(
                ["iwgetid", "-r"], capture_output=True, text=True, timeout=5
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def get_current_ssid(self) -> str:
        """Get the SSID of the currently connected network.

        Returns:
            The SSID or empty string if not connected.
        """
        try:
            result = subprocess.run(
                ["iwgetid", "-r"], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_ip_address(self) -> str:
        """Get the current IP address on wlan0.

        Returns:
            The IP address or empty string.
        """
        try:
            result = subprocess.run(
                ["hostname", "-I"], capture_output=True, text=True, timeout=5
            )
            addresses = result.stdout.strip().split()
            return addresses[0] if addresses else ""
        except Exception:
            return ""

    def get_connection_info(self) -> dict[str, Any]:
        """Get detailed connection information.

        Returns:
            Dictionary with connection details.
        """
        return {
            "connected": self.is_connected(),
            "ssid": self.get_current_ssid(),
            "ip_address": self.get_ip_address(),
        }

    def has_internet(self) -> bool:
        """Check if there's internet connectivity.

        Returns:
            True if internet is accessible.
        """
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
