"""Modern text display application for LED display.

Features:
- Smooth pixel-perfect scrolling
- Gradient text option
- Fade in/out at edges
- Multiple animation styles
"""

import math
import time
from typing import Any

from PIL import Image

from display.fonts import small_font, large_font, PixelFont, FONT_5X7
from display.graphics import Colors, Gradients, Drawing, Animation

from .base import BaseApp


class TextApp(BaseApp):
    """Displays custom text with modern styling."""

    name = "text"
    display_name = "Text"
    description = "Shows custom text message"
    requires_credentials = False

    config_schema = {
        "message": {
            "type": "string",
            "label": "Message",
            "default": "Hello World!",
        },
        "scroll": {
            "type": "bool",
            "label": "Scroll text",
            "default": True,
        },
        "scroll_speed": {
            "type": "int",
            "label": "Scroll speed",
            "default": 30,
            "min": 10,
            "max": 100,
        },
        "style": {
            "type": "select",
            "label": "Style",
            "options": [
                {"value": "modern", "label": "Modern (gradient)"},
                {"value": "neon", "label": "Neon glow"},
                {"value": "minimal", "label": "Minimal"},
                {"value": "retro", "label": "Retro"},
            ],
            "default": "modern",
        },
        "color": {
            "type": "color",
            "label": "Primary color",
            "default": "#00D4FF",
        },
        "size": {
            "type": "select",
            "label": "Text size",
            "options": [
                {"value": "small", "label": "Small"},
                {"value": "large", "label": "Large"},
            ],
            "default": "large",
        },
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._scroll_offset = 0.0
        self._last_render_time = time.time()
        self._text_width = 0

    def setup(self) -> bool:
        """Reset scroll position when app becomes active."""
        self._scroll_offset = 0.0
        self._last_render_time = time.time()
        return True

    def _apply_edge_fade(
        self,
        image: Image.Image,
        fade_width: int = 8,
    ) -> None:
        """Apply fade effect at left and right edges."""
        pixels = image.load()

        for y in range(image.height):
            for x in range(fade_width):
                # Left fade
                factor = x / fade_width
                r, g, b = pixels[x, y]
                pixels[x, y] = (int(r * factor), int(g * factor), int(b * factor))

                # Right fade
                rx = image.width - 1 - x
                r, g, b = pixels[rx, y]
                pixels[rx, y] = (int(r * factor), int(g * factor), int(b * factor))

    def _draw_neon_glow(
        self,
        image: Image.Image,
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int],
        font: PixelFont,
    ) -> None:
        """Draw text with neon glow effect."""
        # Draw glow layers (dimmer, offset copies)
        glow_color = Colors.dim(color, 0.2)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            font.render_text(image, text, x + dx, y + dy, glow_color)

        # Draw outer glow
        outer_glow = Colors.dim(color, 0.1)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            font.render_text(image, text, x + dx, y + dy, outer_glow)

        # Draw main text
        font.render_text(image, text, x, y, color)

    def _draw_gradient_text(
        self,
        image: Image.Image,
        text: str,
        x: int,
        y: int,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        font: PixelFont,
    ) -> None:
        """Draw text with vertical gradient."""
        # Create a temporary image for the text
        text_width = font.get_text_width(text)
        temp = Image.new("RGB", (max(1, text_width), font.char_height), (0, 0, 0))

        # Render text in white
        font.render_text(temp, text, 0, 0, (255, 255, 255))

        # Apply gradient based on y position
        temp_pixels = temp.load()
        for py in range(temp.height):
            t = py / max(1, temp.height - 1)
            grad_color = Colors.lerp_color(color1, color2, t)

            for px in range(temp.width):
                r, g, b = temp_pixels[px, py]
                if r > 0:  # If pixel is lit
                    # Apply gradient color
                    temp_pixels[px, py] = grad_color

        # Paste onto main image
        image.paste(temp, (x, y))

    def render(self, width: int, height: int) -> Image.Image:
        """Render the text display."""
        image = Image.new("RGB", (width, height), (0, 0, 0))

        message = self._config.get("message", "Hello World!")
        scroll = self._config.get("scroll", True)
        scroll_speed = self._config.get("scroll_speed", 30)
        style = self._config.get("style", "modern")
        primary_color = Colors.hex_to_rgb(self._config.get("color", "#00D4FF"))
        size = self._config.get("size", "large")

        # Select font
        font = large_font if size == "large" else small_font

        # Calculate text dimensions
        text_width = font.get_text_width(message)
        text_height = font.char_height
        self._text_width = text_width

        # Calculate vertical center
        y = (height - text_height) // 2

        # Update scroll position
        current_time = time.time()
        delta_time = current_time - self._last_render_time
        self._last_render_time = current_time

        if scroll and text_width > width:
            self._scroll_offset += scroll_speed * delta_time

            # Reset when text fully scrolled
            total_scroll = text_width + width
            if self._scroll_offset > total_scroll:
                self._scroll_offset = 0.0

            x = int(width - self._scroll_offset)
        else:
            # Center static text
            x = (width - text_width) // 2

        # Draw based on style
        if style == "modern":
            # Draw subtle background gradient
            Gradients.vertical(
                image,
                Colors.dim(primary_color, 0.05),
                (0, 0, 0),
                height=height // 2,
            )

            # Gradient text from primary color to white
            secondary_color = Colors.brighten(primary_color, 0.5)
            self._draw_gradient_text(image, message, x, y, primary_color, secondary_color, font)

        elif style == "neon":
            # Neon glow effect
            self._draw_neon_glow(image, message, x, y, primary_color, font)

        elif style == "retro":
            # Retro style with shadow
            shadow_color = Colors.dim(primary_color, 0.3)
            font.render_text(image, message, x + 1, y + 1, shadow_color)
            font.render_text(image, message, x, y, primary_color)

            # Add scanlines
            pixels = image.load()
            for sy in range(0, height, 2):
                for sx in range(width):
                    r, g, b = pixels[sx, sy]
                    pixels[sx, sy] = (int(r * 0.7), int(g * 0.7), int(b * 0.7))

        else:  # minimal
            font.render_text(image, message, x, y, primary_color)

        # Apply edge fade for scrolling text
        if scroll and text_width > width:
            self._apply_edge_fade(image, fade_width=6)

        # Draw subtle top and bottom borders
        border_color = Colors.dim(primary_color, 0.2)
        Drawing.line(image, 0, 0, width - 1, 0, border_color)
        Drawing.line(image, 0, height - 1, width - 1, height - 1, border_color)

        return image

    def get_render_interval(self) -> float:
        """Fast updates for smooth scrolling."""
        if self._config.get("scroll", True) and self._text_width > 64:
            return 0.033  # ~30 FPS
        return 0.5
