"""GPIO button handler with debounce and long-press detection.

Provides event-based button handling for the LED display control button.
"""

import logging
import threading
import time
from enum import Enum
from typing import Callable

from ..core.config import get_config
from ..core.threading import StoppableThread

logger = logging.getLogger(__name__)

# Try to import GPIO library
try:
    import RPi.GPIO as GPIO

    GPIO_AVAILABLE = True
except ImportError:
    GPIO = None
    GPIO_AVAILABLE = False
    logger.info("RPi.GPIO not available, button will use mock mode")


class ButtonEvent(Enum):
    """Button event types."""

    SHORT_PRESS = "short_press"
    LONG_PRESS = "long_press"


class ButtonHandler:
    """GPIO button handler with debounce and long-press detection.

    Supports:
    - Debounced input to prevent false triggers
    - Short press detection (< long_press_duration)
    - Long press detection (>= long_press_duration)
    - Callback-based event handling
    - Mock mode for development

    Usage:
        handler = ButtonHandler()
        handler.on_short_press = lambda: print("Short press!")
        handler.on_long_press = lambda: print("Long press!")
        handler.start()
    """

    def __init__(self) -> None:
        """Initialize the button handler."""
        config = get_config()
        button_config = config.button

        self._pin = button_config.pin
        self._long_press_duration = button_config.long_press_duration
        self._debounce_time = button_config.debounce_time

        self._mock_mode = not GPIO_AVAILABLE
        self._running = False
        self._thread: StoppableThread | None = None

        # Callbacks
        self.on_short_press: Callable[[], None] | None = None
        self.on_long_press: Callable[[], None] | None = None

        # State tracking
        self._press_start_time: float | None = None
        self._last_event_time = 0.0

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    @property
    def is_running(self) -> bool:
        """Check if button handler is running."""
        return self._running

    def start(self) -> None:
        """Start the button handler.

        Sets up GPIO and starts the monitoring thread.
        """
        if self._running:
            logger.warning("Button handler already running")
            return

        if self._mock_mode:
            logger.info("Starting button handler in mock mode (GPIO pin %d)", self._pin)
        else:
            logger.info("Starting button handler on GPIO pin %d", self._pin)
            self._setup_gpio()

        self._running = True
        self._thread = StoppableThread(target=self._monitor_loop, name="ButtonThread")
        self._thread.start()

    def stop(self) -> None:
        """Stop the button handler and clean up GPIO."""
        if not self._running:
            return

        logger.info("Stopping button handler")
        self._running = False

        if self._thread:
            self._thread.stop(timeout=2.0)
            self._thread = None

        if not self._mock_mode and GPIO:
            try:
                GPIO.cleanup(self._pin)
            except Exception as e:
                logger.warning("Error cleaning up GPIO: %s", e)

    def _setup_gpio(self) -> None:
        """Set up GPIO pin for button input."""
        if not GPIO:
            return

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.debug("GPIO pin %d configured as input with pull-up", self._pin)

    def _read_button(self) -> bool:
        """Read the current button state.

        Returns:
            True if button is pressed, False otherwise
        """
        if self._mock_mode:
            return False

        # Button is active LOW (pull-up resistor)
        return GPIO.input(self._pin) == GPIO.LOW

    def _monitor_loop(self, thread: StoppableThread) -> None:
        """Main button monitoring loop.

        Runs at ~100 Hz to detect button presses with debouncing.
        """
        logger.debug("Button monitor loop started")

        while not thread.should_stop():
            try:
                self._check_button()
            except Exception as e:
                logger.exception("Error in button monitoring: %s", e)

            # Sleep for ~10ms (100 Hz polling)
            thread.wait(0.01)

        logger.debug("Button monitor loop stopped")

    def _check_button(self) -> None:
        """Check button state and handle press/release events."""
        is_pressed = self._read_button()
        now = time.monotonic()

        # Debounce check
        if now - self._last_event_time < self._debounce_time:
            return

        if is_pressed and self._press_start_time is None:
            # Button just pressed
            self._press_start_time = now
            logger.debug("Button pressed")

        elif not is_pressed and self._press_start_time is not None:
            # Button just released
            press_duration = now - self._press_start_time
            self._press_start_time = None
            self._last_event_time = now

            if press_duration >= self._long_press_duration:
                self._emit_event(ButtonEvent.LONG_PRESS)
            else:
                self._emit_event(ButtonEvent.SHORT_PRESS)

        elif is_pressed and self._press_start_time is not None:
            # Button still held - check for long press trigger
            press_duration = now - self._press_start_time

            if press_duration >= self._long_press_duration:
                # Trigger long press immediately (don't wait for release)
                self._emit_event(ButtonEvent.LONG_PRESS)
                self._press_start_time = None  # Reset to prevent re-trigger
                self._last_event_time = now

    def _emit_event(self, event: ButtonEvent) -> None:
        """Emit a button event to the appropriate callback.

        Args:
            event: The button event type
        """
        logger.info("Button event: %s", event.value)

        try:
            if event == ButtonEvent.SHORT_PRESS and self.on_short_press:
                self.on_short_press()
            elif event == ButtonEvent.LONG_PRESS and self.on_long_press:
                self.on_long_press()
        except Exception as e:
            logger.exception("Error in button callback: %s", e)

    def simulate_short_press(self) -> None:
        """Simulate a short button press (for testing/mock mode)."""
        logger.debug("Simulating short press")
        self._emit_event(ButtonEvent.SHORT_PRESS)

    def simulate_long_press(self) -> None:
        """Simulate a long button press (for testing/mock mode)."""
        logger.debug("Simulating long press")
        self._emit_event(ButtonEvent.LONG_PRESS)


# =============================================================================
# Singleton Instance
# =============================================================================

_button_handler: ButtonHandler | None = None
_button_lock = threading.Lock()


def get_button_handler() -> ButtonHandler:
    """Get the global button handler instance.

    Returns:
        ButtonHandler singleton instance
    """
    global _button_handler
    with _button_lock:
        if _button_handler is None:
            _button_handler = ButtonHandler()
        return _button_handler


def reset_button_handler() -> None:
    """Reset the button handler singleton (for testing)."""
    global _button_handler
    with _button_lock:
        if _button_handler is not None:
            _button_handler.stop()
            _button_handler = None
