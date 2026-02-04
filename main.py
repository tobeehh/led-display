#!/usr/bin/env python3
"""Main entry point for the LED Display system.

This script initializes all components and starts the LED display system.
"""

import signal
import sys
import time

from config import get_config
from display.manager import DisplayManager, get_display_manager
from hardware.button import ButtonHandler
from apps.manager import AppManager, set_app_manager
from apps.clock import ClockApp
from apps.text import TextApp
from apps.weather import WeatherApp
from apps.spotify import SpotifyApp
from apps.stocks import StocksApp
from network.manager import NetworkManager, set_network_manager
from web.app import start_web_server


class LEDDisplaySystem:
    """Main controller for the LED Display system."""

    def __init__(self):
        """Initialize the LED Display system."""
        self._config = get_config()
        self._running = False

        # Components
        self._display: DisplayManager | None = None
        self._app_manager: AppManager | None = None
        self._button_handler: ButtonHandler | None = None
        self._network_manager: NetworkManager | None = None

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        print("\n[System] Shutdown signal received...")
        self.stop()
        sys.exit(0)

    def _on_network_connected(self) -> None:
        """Handle network connection event."""
        print("[System] Network connected")
        if self._app_manager:
            self._app_manager.render_message("WiFi OK", (0, 255, 0))
            time.sleep(1)

    def _on_network_disconnected(self) -> None:
        """Handle network disconnection event."""
        print("[System] Network disconnected")
        if self._app_manager:
            self._app_manager.render_message("No WiFi", (255, 100, 0))
            time.sleep(1)

    def _on_short_press(self) -> None:
        """Handle short button press - switch to next app."""
        print("[System] Button: short press")
        if self._app_manager:
            new_app = self._app_manager.next_app()
            print(f"[System] Switched to: {new_app}")

    def _on_long_press(self) -> None:
        """Handle long button press - activate captive portal."""
        print("[System] Button: long press - starting captive portal")
        if self._network_manager:
            if self._app_manager:
                self._app_manager.render_message("AP Mode", (100, 100, 255))
            self._network_manager.start_captive_portal()

    def _register_apps(self) -> None:
        """Register all available apps."""
        if not self._app_manager:
            return

        # Clock app
        clock_config = self._config.get_app_config("clock")
        clock_config["enabled"] = clock_config.get("enabled", True)
        self._app_manager.register_app(ClockApp(clock_config))

        # Text app
        text_config = self._config.get_app_config("text")
        text_config["enabled"] = text_config.get("enabled", True)
        self._app_manager.register_app(TextApp(text_config))

        # Weather app
        weather_config = self._config.get_app_config("weather")
        self._app_manager.register_app(WeatherApp(weather_config))

        # Spotify app
        spotify_config = self._config.get_app_config("spotify")
        self._app_manager.register_app(SpotifyApp(spotify_config))

        # Stocks app
        stocks_config = self._config.get_app_config("stocks")
        self._app_manager.register_app(StocksApp(stocks_config))

        print("[System] Apps registered: " + ", ".join(self._app_manager.get_all_apps().keys()))

    def start(self) -> None:
        """Start the LED Display system."""
        if self._running:
            return

        print("[System] Starting LED Display System...")
        self._running = True
        self._setup_signal_handlers()

        # Initialize display manager
        print("[System] Initializing display...")
        self._display = DisplayManager()
        self._display.start()

        if self._display.is_mock:
            print("[System] Running in mock mode (no LED hardware)")

        # Initialize app manager
        print("[System] Initializing app manager...")
        self._app_manager = AppManager(self._display)
        set_app_manager(self._app_manager)
        self._register_apps()

        # Initialize button handler
        print("[System] Initializing button handler...")
        self._button_handler = ButtonHandler(
            on_short_press=self._on_short_press,
            on_long_press=self._on_long_press,
        )
        self._button_handler.start()

        # Initialize network manager
        print("[System] Initializing network manager...")
        self._network_manager = NetworkManager(
            on_connected=self._on_network_connected,
            on_disconnected=self._on_network_disconnected,
        )
        set_network_manager(self._network_manager)
        self._network_manager.start()

        # Start web server
        web_config = self._config.get("web")
        print(f"[System] Starting web server on port {web_config.get('port', 5000)}...")
        start_web_server(
            host=web_config.get("host", "0.0.0.0"),
            port=web_config.get("port", 5000),
        )

        # Start app manager (begins rendering)
        print("[System] Starting app manager...")
        self._app_manager.start()

        # Show startup message
        self._app_manager.render_message("Starting...", (100, 200, 255))
        time.sleep(1)

        print("[System] LED Display System started successfully!")
        print(f"[System] Web UI available at http://0.0.0.0:{web_config.get('port', 80)}")

        # Main loop
        self._run()

    def _run(self) -> None:
        """Main loop."""
        while self._running:
            time.sleep(1)

    def stop(self) -> None:
        """Stop the LED Display system."""
        if not self._running:
            return

        print("[System] Stopping LED Display System...")
        self._running = False

        # Stop components in reverse order
        if self._network_manager:
            self._network_manager.stop()
            self._network_manager = None

        if self._button_handler:
            self._button_handler.stop()
            self._button_handler = None

        if self._app_manager:
            self._app_manager.stop()
            self._app_manager = None
            set_app_manager(None)

        if self._display:
            self._display.clear()
            self._display.stop()
            self._display = None

        print("[System] LED Display System stopped.")


def main():
    """Main entry point."""
    print("=" * 50)
    print("LED Display System")
    print("=" * 50)

    system = LEDDisplaySystem()

    try:
        system.start()
    except KeyboardInterrupt:
        print("\n[System] Interrupted by user")
    except Exception as e:
        print(f"[System] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        system.stop()


if __name__ == "__main__":
    main()
