"""LED Matrix Display Manager.

Handles the rpi-rgb-led-matrix library for controlling the LED panels.
"""

import threading
from typing import Any

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    # Mock classes for development on non-Pi systems
    RGBMatrix = None
    RGBMatrixOptions = None

from config import get_config


class DisplayManager:
    """Manages the LED matrix display."""

    def __init__(self):
        """Initialize the display manager."""
        self._config = get_config()
        self._matrix: Any = None
        self._canvas: Any = None
        self._lock = threading.Lock()
        self._running = False
        self._mock_mode = RGBMatrix is None

    def start(self) -> None:
        """Initialize and start the LED matrix."""
        if self._running:
            return

        if self._mock_mode:
            print("[DisplayManager] Running in mock mode (no LED matrix hardware)")
            self._running = True
            return

        display_config = self._config.get("display")

        options = RGBMatrixOptions()
        options.rows = display_config.get("rows", 32)
        options.cols = display_config.get("cols", 64)
        options.chain_length = display_config.get("chain_length", 2)
        options.parallel = display_config.get("parallel", 1)
        options.hardware_mapping = display_config.get("hardware_mapping", "adafruit-hat")
        options.gpio_slowdown = display_config.get("gpio_slowdown", 4)
        options.brightness = display_config.get("brightness", 50)
        options.pwm_bits = display_config.get("pwm_bits", 11)
        options.pwm_lsb_nanoseconds = display_config.get("pwm_lsb_nanoseconds", 130)
        options.scan_mode = display_config.get("scan_mode", 1)
        options.row_address_type = display_config.get("row_address_type", 0)
        options.multiplexing = display_config.get("multiplexing", 0)
        options.disable_hardware_pulsing = display_config.get(
            "disable_hardware_pulsing", False
        )
        options.show_refresh_rate = display_config.get("show_refresh_rate", False)
        options.inverse_colors = display_config.get("inverse_colors", False)
        options.led_rgb_sequence = display_config.get("led_rgb_sequence", "RGB")

        pixel_mapper = display_config.get("pixel_mapper_config", "")
        if pixel_mapper:
            options.pixel_mapper_config = pixel_mapper

        panel_type = display_config.get("panel_type", "")
        if panel_type:
            options.panel_type = panel_type

        limit_refresh = display_config.get("limit_refresh_rate_hz", 0)
        if limit_refresh > 0:
            options.limit_refresh_rate_hz = limit_refresh

        self._matrix = RGBMatrix(options=options)
        self._canvas = self._matrix.CreateFrameCanvas()
        self._running = True

    def stop(self) -> None:
        """Stop the display and clean up."""
        self._running = False
        if self._matrix:
            self._matrix.Clear()
            self._matrix = None
            self._canvas = None

    @property
    def width(self) -> int:
        """Get the total display width in pixels.

        With U-mapper (vertical stacking), width stays the same as panel width.
        """
        display_config = self._config.get("display")
        pixel_mapper = display_config.get("pixel_mapper_config", "")

        if "U-mapper" in pixel_mapper:
            # Vertical stacking: width = panel width
            return display_config.get("cols", 64)
        else:
            # Horizontal chaining: width = panel width * chain length
            return display_config.get("cols", 64) * display_config.get("chain_length", 2)

    @property
    def height(self) -> int:
        """Get the total display height in pixels.

        With U-mapper (vertical stacking), height = panel height * chain length.
        """
        display_config = self._config.get("display")
        pixel_mapper = display_config.get("pixel_mapper_config", "")

        if "U-mapper" in pixel_mapper:
            # Vertical stacking: height = panel height * chain length
            return display_config.get("rows", 32) * display_config.get("chain_length", 2)
        else:
            # Horizontal chaining: height = panel height
            return display_config.get("rows", 32)

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    def set_brightness(self, brightness: int) -> None:
        """Set the display brightness.

        Args:
            brightness: Brightness level (0-100).
        """
        brightness = max(0, min(100, brightness))
        self._config.set("display", "brightness", brightness)

        if self._matrix:
            self._matrix.brightness = brightness

    def get_brightness(self) -> int:
        """Get the current brightness level."""
        return self._config.get("display", "brightness", 50)

    def clear(self) -> None:
        """Clear the display."""
        with self._lock:
            if self._canvas:
                self._canvas.Clear()
                self._canvas = self._matrix.SwapOnVSync(self._canvas)
            elif self._mock_mode:
                print("[DisplayManager] Clear display")

    def set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        """Set a single pixel.

        Args:
            x: X coordinate.
            y: Y coordinate.
            r: Red component (0-255).
            g: Green component (0-255).
            b: Blue component (0-255).
        """
        with self._lock:
            if self._canvas:
                self._canvas.SetPixel(x, y, r, g, b)

    def get_canvas(self) -> Any:
        """Get the current canvas for direct drawing.

        Returns:
            The canvas object, or None in mock mode.
        """
        return self._canvas

    def swap_canvas(self) -> Any:
        """Swap the canvas to display the drawn content.

        Returns:
            The new canvas for the next frame.
        """
        with self._lock:
            if self._matrix and self._canvas:
                self._canvas = self._matrix.SwapOnVSync(self._canvas)
                return self._canvas
            elif self._mock_mode:
                print("[DisplayManager] Swap canvas (frame update)")
                return None
        return None

    def draw_test_pattern(self) -> None:
        """Draw a test pattern to verify the display is working."""
        if self._mock_mode:
            print("[DisplayManager] Drawing test pattern (mock mode)")
            return

        with self._lock:
            if not self._canvas:
                return

            # Clear first
            self._canvas.Clear()

            # Draw color bars
            width = self.width
            height = self.height
            bar_width = width // 4

            for y in range(height):
                for x in range(width):
                    if x < bar_width:
                        # Red
                        self._canvas.SetPixel(x, y, 255, 0, 0)
                    elif x < bar_width * 2:
                        # Green
                        self._canvas.SetPixel(x, y, 0, 255, 0)
                    elif x < bar_width * 3:
                        # Blue
                        self._canvas.SetPixel(x, y, 0, 0, 255)
                    else:
                        # White
                        self._canvas.SetPixel(x, y, 255, 255, 255)

            self._canvas = self._matrix.SwapOnVSync(self._canvas)


# Global display manager instance
_display_manager: DisplayManager | None = None


def get_display_manager() -> DisplayManager:
    """Get the global display manager instance."""
    global _display_manager
    if _display_manager is None:
        _display_manager = DisplayManager()
    return _display_manager
