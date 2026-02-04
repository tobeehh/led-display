"""Graphics utilities for LED display - colors, gradients, animations."""

import math
import time
from typing import Callable

from PIL import Image


class Colors:
    """Color palette for modern aesthetic."""

    # Primary colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    # Grays
    GRAY_100 = (240, 240, 240)
    GRAY_200 = (200, 200, 200)
    GRAY_300 = (160, 160, 160)
    GRAY_400 = (120, 120, 120)
    GRAY_500 = (80, 80, 80)
    GRAY_600 = (50, 50, 50)
    GRAY_700 = (30, 30, 30)

    # Accent colors
    SPOTIFY_GREEN = (30, 215, 96)
    BLUE = (66, 133, 244)
    CYAN = (0, 200, 255)
    PURPLE = (150, 100, 255)
    PINK = (255, 100, 150)
    RED = (255, 80, 80)
    ORANGE = (255, 160, 50)
    YELLOW = (255, 220, 50)
    GREEN = (80, 220, 100)

    # Weather themed
    SUNNY = (255, 200, 50)
    CLOUDY = (180, 190, 200)
    RAINY = (100, 150, 200)
    STORMY = (80, 80, 120)
    SNOWY = (220, 230, 255)

    # Time of day
    DAWN = (255, 180, 120)
    DAY = (255, 255, 255)
    DUSK = (255, 140, 100)
    NIGHT = (100, 120, 180)

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex string."""
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def lerp_color(
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        t: float,
    ) -> tuple[int, int, int]:
        """Linear interpolation between two colors.

        Args:
            color1: Start color.
            color2: End color.
            t: Interpolation factor (0.0 to 1.0).
        """
        t = max(0.0, min(1.0, t))
        return (
            int(color1[0] + (color2[0] - color1[0]) * t),
            int(color1[1] + (color2[1] - color1[1]) * t),
            int(color1[2] + (color2[2] - color1[2]) * t),
        )

    @staticmethod
    def dim(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
        """Dim a color by a factor (0.0 to 1.0)."""
        factor = max(0.0, min(1.0, factor))
        return (
            int(color[0] * factor),
            int(color[1] * factor),
            int(color[2] * factor),
        )

    @staticmethod
    def brighten(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
        """Brighten a color by a factor (0.0 = original, 1.0 = white)."""
        factor = max(0.0, min(1.0, factor))
        return (
            int(color[0] + (255 - color[0]) * factor),
            int(color[1] + (255 - color[1]) * factor),
            int(color[2] + (255 - color[2]) * factor),
        )


class Gradients:
    """Gradient rendering utilities."""

    @staticmethod
    def vertical(
        image: Image.Image,
        color_top: tuple[int, int, int],
        color_bottom: tuple[int, int, int],
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Draw a vertical gradient on an image."""
        if width is None:
            width = image.width - x
        if height is None:
            height = image.height - y

        pixels = image.load()

        for row in range(height):
            t = row / max(1, height - 1)
            color = Colors.lerp_color(color_top, color_bottom, t)

            for col in range(width):
                px, py = x + col, y + row
                if 0 <= px < image.width and 0 <= py < image.height:
                    pixels[px, py] = color

    @staticmethod
    def horizontal(
        image: Image.Image,
        color_left: tuple[int, int, int],
        color_right: tuple[int, int, int],
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Draw a horizontal gradient on an image."""
        if width is None:
            width = image.width - x
        if height is None:
            height = image.height - y

        pixels = image.load()

        for col in range(width):
            t = col / max(1, width - 1)
            color = Colors.lerp_color(color_left, color_right, t)

            for row in range(height):
                px, py = x + col, y + row
                if 0 <= px < image.width and 0 <= py < image.height:
                    pixels[px, py] = color

    @staticmethod
    def radial(
        image: Image.Image,
        color_center: tuple[int, int, int],
        color_edge: tuple[int, int, int],
        center_x: int | None = None,
        center_y: int | None = None,
        radius: int | None = None,
    ) -> None:
        """Draw a radial gradient on an image."""
        if center_x is None:
            center_x = image.width // 2
        if center_y is None:
            center_y = image.height // 2
        if radius is None:
            radius = max(image.width, image.height) // 2

        pixels = image.load()

        for y in range(image.height):
            for x in range(image.width):
                dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                t = min(1.0, dist / radius)
                color = Colors.lerp_color(color_center, color_edge, t)
                pixels[x, y] = color


class Animation:
    """Animation timing utilities."""

    @staticmethod
    def ease_in_out(t: float) -> float:
        """Smooth ease-in-out interpolation."""
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def ease_out(t: float) -> float:
        """Ease-out (decelerate) interpolation."""
        return 1.0 - (1.0 - t) ** 2

    @staticmethod
    def ease_in(t: float) -> float:
        """Ease-in (accelerate) interpolation."""
        return t * t

    @staticmethod
    def bounce(t: float) -> float:
        """Bouncy interpolation."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    @staticmethod
    def pulse(t: float, frequency: float = 1.0) -> float:
        """Generate a smooth pulse value (0 to 1 to 0).

        Args:
            t: Time value.
            frequency: Pulse frequency.
        """
        return (math.sin(t * frequency * 2 * math.pi) + 1) / 2

    @staticmethod
    def blink(t: float, on_duration: float = 0.7) -> bool:
        """Generate a blink state.

        Args:
            t: Time value (0 to 1 per cycle).
            on_duration: Fraction of time spent "on".
        """
        return (t % 1.0) < on_duration


class Drawing:
    """Drawing primitives for LED display."""

    @staticmethod
    def rect(
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int],
        filled: bool = True,
    ) -> None:
        """Draw a rectangle."""
        pixels = image.load()

        if filled:
            for row in range(height):
                for col in range(width):
                    px, py = x + col, y + row
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color
        else:
            # Top and bottom edges
            for col in range(width):
                px = x + col
                if 0 <= px < image.width:
                    if 0 <= y < image.height:
                        pixels[px, y] = color
                    if 0 <= y + height - 1 < image.height:
                        pixels[px, y + height - 1] = color
            # Left and right edges
            for row in range(height):
                py = y + row
                if 0 <= py < image.height:
                    if 0 <= x < image.width:
                        pixels[x, py] = color
                    if 0 <= x + width - 1 < image.width:
                        pixels[x + width - 1, py] = color

    @staticmethod
    def rounded_rect(
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int],
        radius: int = 2,
    ) -> None:
        """Draw a rounded rectangle."""
        pixels = image.load()

        for row in range(height):
            for col in range(width):
                px, py = x + col, y + row
                if 0 <= px < image.width and 0 <= py < image.height:
                    # Check if in corner region
                    in_corner = False
                    corner_dist = 0

                    # Top-left
                    if col < radius and row < radius:
                        corner_dist = math.sqrt((radius - col - 0.5) ** 2 + (radius - row - 0.5) ** 2)
                        in_corner = corner_dist > radius
                    # Top-right
                    elif col >= width - radius and row < radius:
                        corner_dist = math.sqrt((col - (width - radius) + 0.5) ** 2 + (radius - row - 0.5) ** 2)
                        in_corner = corner_dist > radius
                    # Bottom-left
                    elif col < radius and row >= height - radius:
                        corner_dist = math.sqrt((radius - col - 0.5) ** 2 + (row - (height - radius) + 0.5) ** 2)
                        in_corner = corner_dist > radius
                    # Bottom-right
                    elif col >= width - radius and row >= height - radius:
                        corner_dist = math.sqrt((col - (width - radius) + 0.5) ** 2 + (row - (height - radius) + 0.5) ** 2)
                        in_corner = corner_dist > radius

                    if not in_corner:
                        pixels[px, py] = color

    @staticmethod
    def progress_bar(
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        progress: float,
        fg_color: tuple[int, int, int],
        bg_color: tuple[int, int, int] = (40, 40, 40),
        rounded: bool = True,
    ) -> None:
        """Draw a progress bar."""
        progress = max(0.0, min(1.0, progress))

        # Background
        if rounded:
            Drawing.rounded_rect(image, x, y, width, height, bg_color, radius=height // 2)
        else:
            Drawing.rect(image, x, y, width, height, bg_color)

        # Foreground
        fill_width = max(1, int(width * progress))
        if fill_width > 0:
            if rounded:
                Drawing.rounded_rect(image, x, y, fill_width, height, fg_color, radius=height // 2)
            else:
                Drawing.rect(image, x, y, fill_width, height, fg_color)

    @staticmethod
    def line(
        image: Image.Image,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a line using Bresenham's algorithm."""
        pixels = image.load()

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if 0 <= x1 < image.width and 0 <= y1 < image.height:
                pixels[x1, y1] = color

            if x1 == x2 and y1 == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    @staticmethod
    def circle(
        image: Image.Image,
        cx: int,
        cy: int,
        radius: int,
        color: tuple[int, int, int],
        filled: bool = True,
    ) -> None:
        """Draw a circle."""
        pixels = image.load()

        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if filled:
                    if dist <= radius and 0 <= x < image.width and 0 <= y < image.height:
                        pixels[x, y] = color
                else:
                    if abs(dist - radius) < 0.8 and 0 <= x < image.width and 0 <= y < image.height:
                        pixels[x, y] = color
