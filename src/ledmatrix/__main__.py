"""LED Matrix Display System entry point.

Usage:
    python -m ledmatrix [options]

Options:
    --config PATH     Path to config file (default: /opt/led-display/config/config.yaml)
    --test-display    Run display test pattern and exit
    --mock            Force mock mode (no hardware required)
    --debug           Enable debug logging
"""

import argparse
import asyncio
import logging
import signal
import sys
import threading
from pathlib import Path

from .core.config import ConfigManager, get_config
from .core.logging import setup_logging, get_logger

logger = get_logger(__name__)


class LEDDisplaySystem:
    """Main application coordinator.

    Manages all system components and their lifecycle.
    """

    def __init__(self, config_path: Path, mock_mode: bool = False) -> None:
        """Initialize the LED Display System.

        Args:
            config_path: Path to configuration file
            mock_mode: Force mock mode for development
        """
        self._config_path = config_path
        self._mock_mode = mock_mode
        self._running = False
        self._shutdown_event = threading.Event()

        # Component references (initialized in start)
        self._display_manager = None
        self._app_scheduler = None
        self._network_manager = None
        self._button_handler = None
        self._web_server = None

    def start(self) -> None:
        """Start all system components."""
        logger.info("Starting LED Display System")

        try:
            # Initialize config
            ConfigManager.get_instance(self._config_path)
            config = get_config()

            # Setup logging from config
            setup_logging(
                level=config.logging.level,
                log_format=config.logging.format,
                log_file=config.logging.file,
            )

            # Start display
            self._start_display()

            # Start apps
            self._start_apps()

            # Start button handler
            self._start_button()

            # Start network manager
            self._start_network()

            # Start web server
            self._start_web_server()

            self._running = True
            logger.info("LED Display System started successfully")

        except Exception as e:
            logger.exception("Failed to start system: %s", e)
            self.stop()
            raise

    def _start_display(self) -> None:
        """Initialize and start the display manager."""
        from .display import get_display_manager

        self._display_manager = get_display_manager()
        self._display_manager.start()

        logger.info(
            "Display started: %dx%d (mock=%s)",
            self._display_manager.width,
            self._display_manager.height,
            self._display_manager.is_mock,
        )

    def _start_apps(self) -> None:
        """Initialize and start the app scheduler."""
        from .apps.scheduler import init_app_scheduler
        from .apps.clock import ClockApp
        from .apps.wordclock import WordClockApp
        from .apps.weather import WeatherApp
        from .apps.stocks import StocksApp
        from .apps.spotify import SpotifyApp
        from .apps.text import TextApp

        config = get_config()

        # Create scheduler
        self._app_scheduler = init_app_scheduler(
            on_frame_ready=self._display_manager.render_image,
            width=self._display_manager.width,
            height=self._display_manager.height,
        )

        # Register apps with their configs
        self._app_scheduler.register_app(ClockApp(config.apps.clock.model_dump()))
        self._app_scheduler.register_app(WordClockApp(config.apps.wordclock.model_dump()))
        self._app_scheduler.register_app(WeatherApp(config.apps.weather.model_dump()))
        self._app_scheduler.register_app(StocksApp(config.apps.stocks.model_dump()))
        self._app_scheduler.register_app(SpotifyApp(config.apps.spotify.model_dump()))
        self._app_scheduler.register_app(TextApp(config.apps.text.model_dump()))

        # Configure rotation
        self._app_scheduler.set_rotation(
            config.apps.rotation_enabled,
            config.apps.rotation_interval,
        )

        # Start scheduler
        self._app_scheduler.start()

        # Set active app
        if config.apps.active_app:
            self._app_scheduler.set_active_app(config.apps.active_app)

        logger.info("Apps started: %d registered", len(self._app_scheduler.get_all_apps()))

    def _start_button(self) -> None:
        """Initialize and start the button handler."""
        from .hardware import get_button_handler

        self._button_handler = get_button_handler()

        # Configure callbacks
        self._button_handler.on_short_press = self._on_short_press
        self._button_handler.on_long_press = self._on_long_press

        self._button_handler.start()
        logger.info("Button handler started (mock=%s)", self._button_handler.is_mock)

    def _start_network(self) -> None:
        """Initialize and start the network manager."""
        from .network import get_network_manager

        self._network_manager = get_network_manager()

        # Configure callbacks
        self._network_manager.on_connected = self._on_network_connected
        self._network_manager.on_disconnected = self._on_network_disconnected
        self._network_manager.on_captive_portal_started = self._on_portal_started
        self._network_manager.on_captive_portal_stopped = self._on_portal_stopped

        self._network_manager.start()

        # Start captive portal if WiFi not configured
        # (This is handled by the network manager monitoring)

        logger.info("Network manager started")

    def _start_web_server(self) -> None:
        """Start the web server in a background thread."""
        import uvicorn
        from .web import get_app

        config = get_config()
        app = get_app()

        # Run uvicorn in a thread
        server_config = uvicorn.Config(
            app,
            host=config.web.host,
            port=config.web.port,
            log_level="warning",
        )

        self._web_server = uvicorn.Server(server_config)

        def run_server():
            asyncio.run(self._web_server.serve())

        thread = threading.Thread(target=run_server, name="WebServer", daemon=True)
        thread.start()

        logger.info("Web server started on http://%s:%d", config.web.host, config.web.port)

    def _on_short_press(self) -> None:
        """Handle short button press - switch to next app."""
        logger.debug("Short press detected")
        if self._app_scheduler:
            self._app_scheduler.next_app()

    def _on_long_press(self) -> None:
        """Handle long button press - toggle captive portal."""
        logger.debug("Long press detected")
        if self._network_manager:
            if self._network_manager.is_portal_active:
                asyncio.run(self._network_manager.stop_captive_portal())
            else:
                asyncio.run(self._network_manager.start_captive_portal())

    def _on_network_connected(self) -> None:
        """Handle network connection."""
        logger.info("Network connected")
        # Could show a notification here

    def _on_network_disconnected(self) -> None:
        """Handle network disconnection."""
        logger.info("Network disconnected")

    def _on_portal_started(self) -> None:
        """Handle captive portal start."""
        logger.info("Captive portal started")
        # Could show portal info on display

    def _on_portal_stopped(self) -> None:
        """Handle captive portal stop."""
        logger.info("Captive portal stopped")

    def stop(self) -> None:
        """Stop all system components."""
        if not self._running:
            return

        logger.info("Stopping LED Display System")
        self._running = False

        # Stop components in reverse order
        if self._web_server:
            self._web_server.should_exit = True

        if self._network_manager:
            self._network_manager.stop()

        if self._button_handler:
            self._button_handler.stop()

        if self._app_scheduler:
            self._app_scheduler.stop()

        if self._display_manager:
            self._display_manager.stop()

        self._shutdown_event.set()
        logger.info("LED Display System stopped")

    def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        self._shutdown_event.wait()

    def run_test_pattern(self) -> None:
        """Run display test pattern."""
        from .display import get_display_manager

        display = get_display_manager()
        display.start()
        display.draw_test_pattern()

        logger.info("Test pattern displayed. Press Ctrl+C to exit.")

        try:
            signal.pause()
        except KeyboardInterrupt:
            pass

        display.stop()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LED Matrix Display System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/opt/led-display/config/config.yaml"),
        help="Path to config file",
    )
    parser.add_argument(
        "--test-display",
        action="store_true",
        help="Run display test pattern and exit",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock mode (no hardware required)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup initial logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level)

    logger.info("LED Matrix Display System v1.0.0")

    # Test pattern mode
    if args.test_display:
        system = LEDDisplaySystem(args.config, mock_mode=args.mock)
        system.run_test_pattern()
        return 0

    # Normal operation
    system = LEDDisplaySystem(args.config, mock_mode=args.mock)

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down...", sig)
        system.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        system.start()
        system.wait_for_shutdown()
        return 0

    except Exception as e:
        logger.exception("Fatal error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
