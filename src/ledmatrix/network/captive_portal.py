"""Captive portal for WiFi setup.

Creates a WiFi access point and serves a web interface
for initial network configuration.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from ..core.config import get_config
from ..core.errors import NetworkError

if TYPE_CHECKING:
    from .manager import NetworkManager

logger = logging.getLogger(__name__)


class CaptivePortal:
    """Captive portal for WiFi configuration.

    Creates a WiFi access point and runs a simple web server
    to allow users to configure WiFi credentials.

    Uses NetworkManager/nmcli for AP creation (no hostapd needed).
    """

    def __init__(self, network_manager: "NetworkManager") -> None:
        """Initialize captive portal.

        Args:
            network_manager: Parent network manager
        """
        self._network_manager = network_manager
        self._running = False
        self._web_task: asyncio.Task | None = None
        self._connection_name = "led-display-hotspot"

    @property
    def is_running(self) -> bool:
        """Check if portal is running."""
        return self._running

    async def start(self) -> None:
        """Start the captive portal.

        Creates WiFi AP and starts web server.
        """
        if self._running:
            return

        config = get_config()
        network_config = config.network

        logger.info("Starting captive portal AP: %s", network_config.ap_ssid)

        try:
            # Create hotspot using nmcli
            await self._create_hotspot(
                ssid=network_config.ap_ssid,
                password=network_config.ap_password,
            )

            # Start web server
            self._web_task = asyncio.create_task(self._run_web_server())
            self._running = True

            logger.info("Captive portal started on %s", network_config.ap_ip)

        except Exception as e:
            logger.error("Failed to start captive portal: %s", e)
            await self.stop()
            raise NetworkError("Failed to start captive portal", cause=e)

    async def stop(self) -> None:
        """Stop the captive portal."""
        if not self._running:
            return

        logger.info("Stopping captive portal")

        # Stop web server
        if self._web_task:
            self._web_task.cancel()
            try:
                await self._web_task
            except asyncio.CancelledError:
                pass
            self._web_task = None

        # Stop hotspot
        await self._stop_hotspot()

        self._running = False

    async def _create_hotspot(self, ssid: str, password: str | None = None) -> None:
        """Create WiFi hotspot using nmcli.

        Args:
            ssid: Hotspot SSID
            password: Optional password (None = open network)
        """
        # Delete existing hotspot connection
        await self._run_nmcli("connection", "delete", self._connection_name, check=False)

        # Create hotspot
        cmd = [
            "device",
            "wifi",
            "hotspot",
            "ifname",
            "wlan0",
            "ssid",
            ssid,
            "con-name",
            self._connection_name,
        ]

        if password:
            cmd.extend(["password", password])

        await self._run_nmcli(*cmd)
        logger.info("Hotspot created: %s", ssid)

    async def _stop_hotspot(self) -> None:
        """Stop the WiFi hotspot."""
        await self._run_nmcli("connection", "down", self._connection_name, check=False)
        await self._run_nmcli("connection", "delete", self._connection_name, check=False)
        logger.info("Hotspot stopped")

    async def _run_nmcli(self, *args: str, check: bool = True) -> str:
        """Run nmcli command.

        Args:
            *args: nmcli arguments
            check: Raise on error

        Returns:
            Command output
        """
        cmd = ["nmcli", *args]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except asyncio.TimeoutError:
            proc.kill()
            raise NetworkError("nmcli timeout")

        if check and proc.returncode != 0:
            error = stderr.decode() if stderr else "Unknown error"
            raise NetworkError(f"nmcli failed: {error}")

        return stdout.decode() if stdout else ""

    async def _run_web_server(self) -> None:
        """Run the captive portal web server."""
        from fastapi import FastAPI, Request, Form
        from fastapi.responses import HTMLResponse, RedirectResponse
        import uvicorn

        app = FastAPI(title="LED Display Setup")

        config = get_config()
        network_config = config.network

        @app.get("/", response_class=HTMLResponse)
        async def index():
            """Captive portal home page."""
            networks = await self._network_manager.scan_networks()

            network_options = "\n".join(
                f'<option value="{n.ssid}">{n.ssid} ({n.signal}%)</option>'
                for n in networks
            )

            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>LED Display Setup</title>
                <style>
                    * {{ box-sizing: border-box; }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        color: #fff;
                        min-height: 100vh;
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 400px;
                        margin: 0 auto;
                        padding: 30px;
                        background: rgba(255,255,255,0.1);
                        border-radius: 20px;
                        backdrop-filter: blur(10px);
                    }}
                    h1 {{
                        text-align: center;
                        margin-bottom: 30px;
                        font-size: 24px;
                    }}
                    .form-group {{
                        margin-bottom: 20px;
                    }}
                    label {{
                        display: block;
                        margin-bottom: 8px;
                        font-size: 14px;
                        opacity: 0.8;
                    }}
                    select, input {{
                        width: 100%;
                        padding: 15px;
                        border: none;
                        border-radius: 10px;
                        background: rgba(255,255,255,0.1);
                        color: #fff;
                        font-size: 16px;
                    }}
                    select option {{
                        background: #16213e;
                    }}
                    button {{
                        width: 100%;
                        padding: 15px;
                        border: none;
                        border-radius: 10px;
                        background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
                        color: #fff;
                        font-size: 16px;
                        font-weight: bold;
                        cursor: pointer;
                        margin-top: 20px;
                    }}
                    button:hover {{
                        opacity: 0.9;
                    }}
                    .logo {{
                        text-align: center;
                        font-size: 48px;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="logo">LED</div>
                    <h1>WiFi Setup</h1>
                    <form action="/connect" method="post">
                        <div class="form-group">
                            <label>Network</label>
                            <select name="ssid" required>
                                <option value="">Select network...</option>
                                {network_options}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" name="password" placeholder="Enter password">
                        </div>
                        <button type="submit">Connect</button>
                    </form>
                </div>
            </body>
            </html>
            """

        @app.post("/connect")
        async def connect(ssid: str = Form(...), password: str = Form("")):
            """Handle WiFi connection request."""
            logger.info("Connecting to WiFi: %s", ssid)

            # Connect in background (portal will be stopped)
            asyncio.create_task(self._connect_and_close(ssid, password))

            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Connecting...</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        color: #fff;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                    }}
                    .message {{
                        text-align: center;
                        padding: 40px;
                    }}
                    h1 {{ margin-bottom: 20px; }}
                    p {{ opacity: 0.7; }}
                </style>
            </head>
            <body>
                <div class="message">
                    <h1>Connecting to {ssid}...</h1>
                    <p>The display will restart momentarily.</p>
                    <p>You can close this page.</p>
                </div>
            </body>
            </html>
            """)

        # Captive portal detection endpoints
        @app.get("/generate_204")
        @app.get("/gen_204")
        async def generate_204():
            return RedirectResponse(url="/", status_code=302)

        @app.get("/hotspot-detect.html")
        @app.get("/library/test/success.html")
        async def apple_detect():
            return RedirectResponse(url="/", status_code=302)

        @app.get("/connecttest.txt")
        @app.get("/ncsi.txt")
        async def windows_detect():
            return RedirectResponse(url="/", status_code=302)

        # Run server
        server_config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=network_config.captive_portal_port,
            log_level="warning",
        )
        server = uvicorn.Server(server_config)
        await server.serve()

    async def _connect_and_close(self, ssid: str, password: str) -> None:
        """Connect to WiFi and close portal.

        Args:
            ssid: Network SSID
            password: Network password
        """
        await asyncio.sleep(2)  # Give time for response to be sent

        try:
            # This will stop the portal and connect
            await self._network_manager.connect(ssid, password)
        except Exception as e:
            logger.error("Failed to connect: %s", e)
            # Restart portal on failure
            await self.start()
