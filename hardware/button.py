"""Button handler for GPIO input.

Handles button presses on GPIO 17 with support for short and long presses.
"""

import threading
import time
from typing import Callable

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

from config import get_config


class ButtonHandler:
    """Handles button input from GPIO."""

    def __init__(
        self,
        on_short_press: Callable[[], None] | None = None,
        on_long_press: Callable[[], None] | None = None,
    ):
        """Initialize the button handler.

        Args:
            on_short_press: Callback for short button press.
            on_long_press: Callback for long button press (>3 seconds).
        """
        self._config = get_config()
        button_config = self._config.get("button")

        self._pin = button_config.get("pin", 17)
        self._long_press_duration = button_config.get("long_press_duration", 3.0)
        self._debounce_time = button_config.get("debounce_time", 0.05)

        self._on_short_press = on_short_press
        self._on_long_press = on_long_press

        self._running = False
        self._press_start_time: float | None = None
        self._mock_mode = GPIO is None

        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the button handler."""
        if self._running:
            return

        self._running = True

        if self._mock_mode:
            print(f"[ButtonHandler] Running in mock mode (GPIO pin {self._pin})")
            return

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Start monitoring thread
        self._thread = threading.Thread(target=self._monitor_button, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the button handler and clean up GPIO."""
        self._running = False

        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        if not self._mock_mode and GPIO:
            try:
                GPIO.cleanup(self._pin)
            except Exception:
                pass

    def _monitor_button(self) -> None:
        """Monitor button state in a loop."""
        last_state = GPIO.HIGH
        press_start: float | None = None

        while self._running:
            current_state = GPIO.input(self._pin)

            # Button pressed (active low)
            if current_state == GPIO.LOW and last_state == GPIO.HIGH:
                time.sleep(self._debounce_time)  # Debounce
                if GPIO.input(self._pin) == GPIO.LOW:
                    press_start = time.time()

            # Button released
            elif current_state == GPIO.HIGH and last_state == GPIO.LOW:
                if press_start is not None:
                    press_duration = time.time() - press_start

                    if press_duration >= self._long_press_duration:
                        if self._on_long_press:
                            self._on_long_press()
                    else:
                        if self._on_short_press:
                            self._on_short_press()

                    press_start = None

            last_state = current_state
            time.sleep(0.01)  # Small delay to prevent CPU hogging

    def simulate_short_press(self) -> None:
        """Simulate a short button press (for testing/mock mode)."""
        if self._on_short_press:
            print("[ButtonHandler] Simulating short press")
            self._on_short_press()

    def simulate_long_press(self) -> None:
        """Simulate a long button press (for testing/mock mode)."""
        if self._on_long_press:
            print("[ButtonHandler] Simulating long press")
            self._on_long_press()

    def set_short_press_callback(self, callback: Callable[[], None]) -> None:
        """Set the short press callback.

        Args:
            callback: Function to call on short press.
        """
        self._on_short_press = callback

    def set_long_press_callback(self, callback: Callable[[], None]) -> None:
        """Set the long press callback.

        Args:
            callback: Function to call on long press.
        """
        self._on_long_press = callback


# Global button handler instance
_button_handler: ButtonHandler | None = None


def get_button_handler() -> ButtonHandler:
    """Get the global button handler instance."""
    global _button_handler
    if _button_handler is None:
        _button_handler = ButtonHandler()
    return _button_handler
