"""Captive Portal for WiFi configuration."""

import socket
import subprocess
import threading
from typing import Any, Callable

from flask import Flask, redirect, render_template, request

from config import get_config

from .wifi import WiFiManager


class CaptivePortal:
    """Captive portal for WiFi setup."""

    def __init__(self, on_connected: Callable[[], None] | None = None):
        """Initialize the captive portal.

        Args:
            on_connected: Callback when WiFi connection is successful.
        """
        self._config = get_config()
        network_config = self._config.get("network")

        self._ap_ssid = network_config.get("ap_ssid", "LED-Display-Setup")
        self._ap_password = network_config.get("ap_password", "")
        self._ap_ip = network_config.get("ap_ip", "192.168.4.1")
        self._portal_port = network_config.get("captive_portal_port", 80)
        self._dns_port = network_config.get("dns_port", 53)

        self._wifi = WiFiManager()
        self._on_connected = on_connected

        self._running = False
        self._app: Flask | None = None
        self._dns_thread: threading.Thread | None = None
        self._web_thread: threading.Thread | None = None

    def _create_flask_app(self) -> Flask:
        """Create the Flask app for the captive portal."""
        app = Flask(
            __name__,
            template_folder="../web/templates",
            static_folder="../web/static",
        )

        @app.route("/")
        def index():
            networks = self._wifi.scan_networks()
            return render_template(
                "captive_portal.html",
                networks=networks,
                ap_ssid=self._ap_ssid,
            )

        @app.route("/connect", methods=["POST"])
        def connect():
            ssid = request.form.get("ssid", "")
            password = request.form.get("password", "")

            if not ssid:
                return render_template(
                    "captive_portal.html",
                    networks=self._wifi.scan_networks(),
                    error="Please select a network",
                    ap_ssid=self._ap_ssid,
                )

            # Try to connect
            success = self._wifi.connect(ssid, password)

            if success:
                if self._on_connected:
                    self._on_connected()
                return render_template(
                    "captive_portal.html",
                    success=True,
                    ssid=ssid,
                    ip_address=self._wifi.get_ip_address(),
                    ap_ssid=self._ap_ssid,
                )
            else:
                return render_template(
                    "captive_portal.html",
                    networks=self._wifi.scan_networks(),
                    error="Connection failed. Check password and try again.",
                    ap_ssid=self._ap_ssid,
                )

        @app.route("/scan")
        def scan():
            networks = self._wifi.scan_networks()
            return {"networks": networks}

        # Captive portal detection endpoints
        @app.route("/generate_204")
        @app.route("/gen_204")
        @app.route("/hotspot-detect.html")
        @app.route("/library/test/success.html")
        @app.route("/ncsi.txt")
        @app.route("/connecttest.txt")
        @app.route("/redirect")
        def captive_redirect():
            return redirect("/")

        return app

    def _start_access_point(self) -> bool:
        """Start the WiFi access point.

        Returns:
            True if AP started successfully.
        """
        try:
            # Stop any existing services
            subprocess.run(["sudo", "systemctl", "stop", "hostapd"], capture_output=True)
            subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"], capture_output=True)

            # Configure hostapd
            hostapd_conf = f"""
interface=wlan0
driver=nl80211
ssid={self._ap_ssid}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
"""
            if self._ap_password:
                hostapd_conf = f"""
interface=wlan0
driver=nl80211
ssid={self._ap_ssid}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={self._ap_password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""

            with open("/tmp/hostapd.conf", "w") as f:
                f.write(hostapd_conf)

            subprocess.run(
                ["sudo", "cp", "/tmp/hostapd.conf", "/etc/hostapd/hostapd.conf"],
                check=True,
            )

            # Configure dnsmasq
            dnsmasq_conf = f"""
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
address=/#/{self._ap_ip}
"""
            with open("/tmp/dnsmasq.conf", "w") as f:
                f.write(dnsmasq_conf)

            subprocess.run(
                ["sudo", "cp", "/tmp/dnsmasq.conf", "/etc/dnsmasq.d/captive.conf"],
                check=True,
            )

            # Set static IP for wlan0
            subprocess.run(
                ["sudo", "ip", "addr", "flush", "dev", "wlan0"], capture_output=True
            )
            subprocess.run(
                ["sudo", "ip", "addr", "add", f"{self._ap_ip}/24", "dev", "wlan0"],
                check=True,
            )
            subprocess.run(["sudo", "ip", "link", "set", "wlan0", "up"], check=True)

            # Start services
            subprocess.run(["sudo", "systemctl", "start", "hostapd"], check=True)
            subprocess.run(["sudo", "systemctl", "start", "dnsmasq"], check=True)

            print(f"[CaptivePortal] AP started: {self._ap_ssid}")
            return True

        except Exception as e:
            print(f"[CaptivePortal] Failed to start AP: {e}")
            return False

    def _stop_access_point(self) -> None:
        """Stop the WiFi access point."""
        try:
            subprocess.run(["sudo", "systemctl", "stop", "hostapd"], capture_output=True)
            subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"], capture_output=True)
            subprocess.run(
                ["sudo", "rm", "-f", "/etc/dnsmasq.d/captive.conf"], capture_output=True
            )
            print("[CaptivePortal] AP stopped")
        except Exception as e:
            print(f"[CaptivePortal] Error stopping AP: {e}")

    def _run_dns_server(self) -> None:
        """Run a simple DNS server that redirects all queries to the portal."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", self._dns_port))
            sock.settimeout(1.0)

            while self._running:
                try:
                    data, addr = sock.recvfrom(512)
                    if data:
                        # Simple DNS response pointing to our IP
                        response = self._build_dns_response(data)
                        sock.sendto(response, addr)
                except socket.timeout:
                    continue
                except Exception:
                    continue

            sock.close()
        except Exception as e:
            print(f"[CaptivePortal] DNS server error: {e}")

    def _build_dns_response(self, query: bytes) -> bytes:
        """Build a DNS response pointing to the portal IP.

        Args:
            query: The DNS query bytes.

        Returns:
            DNS response bytes.
        """
        # Parse transaction ID from query
        transaction_id = query[:2]

        # Build response header
        # Flags: Standard response, no error
        flags = b"\x81\x80"
        # Questions: 1, Answers: 1, Authority: 0, Additional: 0
        counts = b"\x00\x01\x00\x01\x00\x00\x00\x00"

        # Copy the question section from query
        question_start = 12
        question_end = query.find(b"\x00", question_start) + 5
        question = query[question_start:question_end]

        # Build answer section
        # Name pointer to question
        answer_name = b"\xc0\x0c"
        # Type A, Class IN
        answer_type = b"\x00\x01\x00\x01"
        # TTL: 60 seconds
        answer_ttl = b"\x00\x00\x00\x3c"
        # Data length: 4 (IPv4)
        answer_len = b"\x00\x04"
        # IP address
        ip_parts = [int(p) for p in self._ap_ip.split(".")]
        answer_ip = bytes(ip_parts)

        response = (
            transaction_id
            + flags
            + counts
            + question
            + answer_name
            + answer_type
            + answer_ttl
            + answer_len
            + answer_ip
        )

        return response

    def _run_web_server(self) -> None:
        """Run the Flask web server."""
        if self._app:
            self._app.run(host="0.0.0.0", port=self._portal_port, threaded=True)

    def start(self) -> bool:
        """Start the captive portal.

        Returns:
            True if started successfully.
        """
        if self._running:
            return True

        # Start AP
        if not self._start_access_point():
            return False

        self._running = True

        # Create Flask app
        self._app = self._create_flask_app()

        # Start DNS server thread
        self._dns_thread = threading.Thread(target=self._run_dns_server, daemon=True)
        self._dns_thread.start()

        # Start web server thread
        self._web_thread = threading.Thread(target=self._run_web_server, daemon=True)
        self._web_thread.start()

        print(f"[CaptivePortal] Started on {self._ap_ip}:{self._portal_port}")
        return True

    def stop(self) -> None:
        """Stop the captive portal."""
        self._running = False

        self._stop_access_point()

        if self._dns_thread:
            self._dns_thread.join(timeout=2.0)
            self._dns_thread = None

        # Web server will stop when thread is terminated
        self._web_thread = None
        self._app = None

        print("[CaptivePortal] Stopped")

    @property
    def is_running(self) -> bool:
        """Check if the captive portal is running."""
        return self._running
