"""LED Matrix Display Manager.

Handles the rpi-rgb-led-matrix library for controlling FM6126A LED panels.
Provides thread-safe rendering with proper locking.
"""

import logging
import threading
from typing import Any

from PIL import Image

from ..core.config import get_config
from ..core.errors import HardwareError

logger = logging.getLogger(__name__)

# Try to import the RGB matrix library
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

    RGB_MATRIX_AVAILABLE = True
except ImportError:
    RGBMatrix = None
    RGBMatrixOptions = None
    RGB_MATRIX_AVAILABLE = False
    logger.info("rgbmatrix not available, will use mock mode")


class DisplayManager:
    """Manages the LED matrix display with thread-safe rendering.

    Supports FM6126A panels with proper initialization and provides
    a mock mode for development without hardware.

    Usage:
        manager = DisplayManager()
        manager.start()
        manager.render_image(pil_image)
        manager.stop()
    """

    def __init__(self) -> None:
        """Initialize the display manager."""
        self._matrix: Any = None
        self._canvas: Any = None
        self._lock = threading.RLock()
        self._running = False
        self._mock_mode = not RGB_MATRIX_AVAILABLE

        # Cache dimensions
        self._width = 0
        self._height = 0

    @property
    def width(self) -> int:
        """Get the total display width in pixels."""
        if self._width == 0:
            self._calculate_dimensions()
        return self._width

    @property
    def height(self) -> int:
        """Get the total display height in pixels."""
        if self._height == 0:
            self._calculate_dimensions()
        return self._height

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    @property
    def is_running(self) -> bool:
        """Check if display is running."""
        return self._running

    @property
    def brightness(self) -> int:
        """Get current brightness level."""
        config = get_config()
        return config.display.brightness

    def _calculate_dimensions(self) -> None:
        """Calculate total display dimensions based on config."""
        config = get_config()
        display = config.display

        # With U-mapper (vertical stacking):
        # - Width stays the same as panel width
        # - Height = panel height * chain length
        if "U-mapper" in display.pixel_mapper_config:
            self._width = display.cols
            self._height = display.rows * display.chain_length
        else:
            # Horizontal chaining
            self._width = display.cols * display.chain_length
            self._height = display.rows

        logger.debug("Display dimensions: %dx%d", self._width, self._height)

    def start(self) -> None:
        """Initialize and start the LED matrix.

        Raises:
            HardwareError: If matrix initialization fails
        """
        if self._running:
            logger.warning("Display already running")
            return

        if self._mock_mode:
            logger.info("Starting display in mock mode")
            self._calculate_dimensions()
            self._running = True
            return

        config = get_config()
        display = config.display

        logger.info(
            "Starting LED matrix: %dx%d, chain=%d, panel_type=%s",
            display.cols,
            display.rows,
            display.chain_length,
            display.panel_type,
        )

        try:
            options = RGBMatrixOptions()

            # Basic settings
            options.rows = display.rows
            options.cols = display.cols
            options.chain_length = display.chain_length
            options.parallel = display.parallel
            options.hardware_mapping = display.hardware_mapping
            options.gpio_slowdown = display.gpio_slowdown
            options.brightness = display.brightness

            # PWM settings
            options.pwm_bits = display.pwm_bits
            options.pwm_lsb_nanoseconds = display.pwm_lsb_nanoseconds
            options.scan_mode = display.scan_mode
            options.multiplexing = display.multiplexing

            # FM6126A specific settings
            options.row_address_type = display.row_address_type
            if display.panel_type:
                options.panel_type = display.panel_type

            # Pixel mapper for vertical stacking
            if display.pixel_mapper_config:
                options.pixel_mapper_config = display.pixel_mapper_config

            # Optional settings
            options.disable_hardware_pulsing = display.disable_hardware_pulsing
            options.show_refresh_rate = display.show_refresh_rate
            options.inverse_colors = display.inverse_colors
            options.led_rgb_sequence = display.led_rgb_sequence

            if display.limit_refresh_rate_hz > 0:
                options.limit_refresh_rate_hz = display.limit_refresh_rate_hz

            # Initialize matrix
            self._matrix = RGBMatrix(options=options)
            self._canvas = self._matrix.CreateFrameCanvas()
            self._calculate_dimensions()
            self._running = True

            logger.info("LED matrix started successfully")

        except Exception as e:
            logger.exception("Failed to initialize LED matrix")
            raise HardwareError(
                "Failed to initialize LED matrix",
                details={"error": str(e)},
                cause=e,
            )

    def stop(self) -> None:
        """Stop the display and clean up."""
        if not self._running:
            return

        logger.info("Stopping display")
        self._running = False

        with self._lock:
            if self._matrix:
                try:
                    self._matrix.Clear()
                except Exception as e:
                    logger.warning("Error clearing matrix: %s", e)
                self._matrix = None
                self._canvas = None

    def set_brightness(self, brightness: int) -> None:
        """Set the display brightness.

        Args:
            brightness: Brightness level (0-100)
        """
        brightness = max(0, min(100, brightness))
        logger.debug("Setting brightness to %d", brightness)

        with self._lock:
            if self._matrix:
                self._matrix.brightness = brightness

    def render_image(self, image: Image.Image) -> None:
        """Render a PIL Image to the display.

        The image will be resized if dimensions don't match.

        Args:
            image: PIL Image to render (RGB mode)
        """
        if not self._running:
            return

        # Ensure correct size
        if image.size != (self._width, self._height):
            image = image.resize((self._width, self._height), Image.Resampling.LANCZOS)

        # Ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        if self._mock_mode:
            # In mock mode, just log that we would render
            logger.debug("Mock render: %dx%d image", image.width, image.height)
            return

        with self._lock:
            if not self._canvas:
                return

            # Copy image pixels to canvas
            self._canvas.SetImage(image)

            # Swap canvas (vsync)
            self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def clear(self) -> None:
        """Clear the display to black."""
        if not self._running:
            return

        if self._mock_mode:
            logger.debug("Mock clear")
            return

        with self._lock:
            if self._canvas:
                self._canvas.Clear()
                self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def draw_test_pattern(self) -> None:
        """Draw a test pattern to verify the display is working."""
        logger.info("Drawing test pattern")

        if self._mock_mode:
            logger.info("Mock test pattern: %dx%d", self._width, self._height)
            return

        # Create test pattern image
        image = Image.new("RGB", (self._width, self._height), (0, 0, 0))
        pixels = image.load()

        bar_width = self._width // 4

        for y in range(self._height):
            for x in range(self._width):
                if x < bar_width:
                    pixels[x, y] = (255, 0, 0)  # Red
                elif x < bar_width * 2:
                    pixels[x, y] = (0, 255, 0)  # Green
                elif x < bar_width * 3:
                    pixels[x, y] = (0, 0, 255)  # Blue
                else:
                    pixels[x, y] = (255, 255, 255)  # White

        self.render_image(image)


# =============================================================================
# Singleton Instance
# =============================================================================

_display_manager: DisplayManager | None = None
_display_lock = threading.Lock()


def get_display_manager() -> DisplayManager:
    """Get the global display manager instance.

    Returns:
        DisplayManager singleton instance
    """
    global _display_manager
    with _display_lock:
        if _display_manager is None:
            _display_manager = DisplayManager()
        return _display_manager


def reset_display_manager() -> None:
    """Reset the display manager singleton (for testing)."""
    global _display_manager
    with _display_lock:
        if _display_manager is not None:
            _display_manager.stop()
            _display_manager = None
