"""Mock hardware implementations for development and testing.

Provides mock versions of hardware interfaces when running
on non-Raspberry Pi systems.
"""

import logging
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class MockRGBMatrixOptions:
    """Mock RGBMatrixOptions for development."""

    def __init__(self) -> None:
        self.rows = 32
        self.cols = 64
        self.chain_length = 2
        self.parallel = 1
        self.hardware_mapping = "adafruit-hat"
        self.gpio_slowdown = 4
        self.brightness = 50
        self.pwm_bits = 11
        self.pwm_lsb_nanoseconds = 130
        self.scan_mode = 1
        self.multiplexing = 0
        self.row_address_type = 3
        self.panel_type = "FM6126A"
        self.pixel_mapper_config = "U-mapper"
        self.disable_hardware_pulsing = False
        self.show_refresh_rate = False
        self.inverse_colors = False
        self.led_rgb_sequence = "RGB"
        self.limit_refresh_rate_hz = 0


class MockCanvas:
    """Mock canvas for development."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._image: Image.Image | None = None

    def Clear(self) -> None:
        """Clear the canvas."""
        logger.debug("MockCanvas: Clear")

    def SetPixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        """Set a single pixel."""
        pass  # No-op in mock

    def SetImage(self, image: Image.Image, offset_x: int = 0, offset_y: int = 0) -> None:
        """Set image on canvas."""
        self._image = image
        logger.debug("MockCanvas: SetImage %dx%d", image.width, image.height)

    def get_image(self) -> Image.Image | None:
        """Get the current image (for testing)."""
        return self._image


class MockMatrix:
    """Mock RGBMatrix for development.

    Provides the same interface as the real RGBMatrix but
    doesn't require hardware.
    """

    def __init__(self, options: MockRGBMatrixOptions | None = None) -> None:
        if options is None:
            options = MockRGBMatrixOptions()

        self._options = options
        self._brightness = options.brightness
        self._canvas: MockCanvas | None = None

        # Calculate dimensions based on options
        if "U-mapper" in (options.pixel_mapper_config or ""):
            self._width = options.cols
            self._height = options.rows * options.chain_length
        else:
            self._width = options.cols * options.chain_length
            self._height = options.rows

        logger.info(
            "MockMatrix initialized: %dx%d (mock mode)",
            self._width,
            self._height,
        )

    @property
    def brightness(self) -> int:
        """Get current brightness."""
        return self._brightness

    @brightness.setter
    def brightness(self, value: int) -> None:
        """Set brightness."""
        self._brightness = max(0, min(100, value))
        logger.debug("MockMatrix: brightness = %d", self._brightness)

    @property
    def width(self) -> int:
        """Get display width."""
        return self._width

    @property
    def height(self) -> int:
        """Get display height."""
        return self._height

    def CreateFrameCanvas(self) -> MockCanvas:
        """Create a frame canvas."""
        self._canvas = MockCanvas(self._width, self._height)
        return self._canvas

    def SwapOnVSync(self, canvas: MockCanvas) -> MockCanvas:
        """Swap canvas (simulated vsync)."""
        # In mock mode, just return a new canvas
        return MockCanvas(self._width, self._height)

    def Clear(self) -> None:
        """Clear the display."""
        logger.debug("MockMatrix: Clear")


class MockGPIO:
    """Mock RPi.GPIO for development.

    Provides the same interface as RPi.GPIO but doesn't
    require Raspberry Pi hardware.
    """

    BCM = 11
    BOARD = 10
    IN = 1
    OUT = 0
    HIGH = 1
    LOW = 0
    PUD_UP = 22
    PUD_DOWN = 21
    PUD_OFF = 20
    RISING = 31
    FALLING = 32
    BOTH = 33

    _mode: int | None = None
    _pin_modes: dict[int, int] = {}
    _pin_values: dict[int, int] = {}
    _callbacks: dict[int, list[tuple[int, Any]]] = {}

    @classmethod
    def setmode(cls, mode: int) -> None:
        """Set the GPIO numbering mode."""
        cls._mode = mode
        logger.debug("MockGPIO: setmode(%d)", mode)

    @classmethod
    def setup(cls, pin: int, mode: int, pull_up_down: int = PUD_OFF) -> None:
        """Set up a GPIO pin."""
        cls._pin_modes[pin] = mode
        cls._pin_values[pin] = cls.HIGH if pull_up_down == cls.PUD_UP else cls.LOW
        logger.debug("MockGPIO: setup(%d, %d, %d)", pin, mode, pull_up_down)

    @classmethod
    def input(cls, pin: int) -> int:
        """Read GPIO pin value."""
        return cls._pin_values.get(pin, cls.HIGH)

    @classmethod
    def output(cls, pin: int, value: int) -> None:
        """Set GPIO pin value."""
        cls._pin_values[pin] = value
        logger.debug("MockGPIO: output(%d, %d)", pin, value)

    @classmethod
    def cleanup(cls, pin: int | None = None) -> None:
        """Clean up GPIO."""
        if pin is None:
            cls._pin_modes.clear()
            cls._pin_values.clear()
            cls._callbacks.clear()
            cls._mode = None
        else:
            cls._pin_modes.pop(pin, None)
            cls._pin_values.pop(pin, None)
            cls._callbacks.pop(pin, None)
        logger.debug("MockGPIO: cleanup(%s)", pin)

    @classmethod
    def add_event_detect(
        cls,
        pin: int,
        edge: int,
        callback: Any = None,
        bouncetime: int = 0,
    ) -> None:
        """Add event detection to a pin."""
        if pin not in cls._callbacks:
            cls._callbacks[pin] = []
        if callback:
            cls._callbacks[pin].append((edge, callback))
        logger.debug("MockGPIO: add_event_detect(%d, %d)", pin, edge)

    @classmethod
    def remove_event_detect(cls, pin: int) -> None:
        """Remove event detection from a pin."""
        cls._callbacks.pop(pin, None)
        logger.debug("MockGPIO: remove_event_detect(%d)", pin)

    @classmethod
    def simulate_press(cls, pin: int) -> None:
        """Simulate a button press (for testing)."""
        cls._pin_values[pin] = cls.LOW
        logger.debug("MockGPIO: simulate_press(%d)", pin)

    @classmethod
    def simulate_release(cls, pin: int) -> None:
        """Simulate a button release (for testing)."""
        cls._pin_values[pin] = cls.HIGH
        logger.debug("MockGPIO: simulate_release(%d)", pin)
