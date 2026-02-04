"""Graphics utilities for LED matrix display.

Provides colors, gradients, and drawing primitives with a modern aesthetic.
"""

from dataclasses import dataclass
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from .renderer import get_default_font


@dataclass(frozen=True)
class Color:
    """RGB color with utility methods."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        # Clamp values
        object.__setattr__(self, "r", max(0, min(255, self.r)))
        object.__setattr__(self, "g", max(0, min(255, self.g)))
        object.__setattr__(self, "b", max(0, min(255, self.b)))

    @classmethod
    def from_hex(cls, hex_color: str) -> "Color":
        """Create color from hex string (e.g., '#FF5500' or 'FF5500')."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        return cls(
            r=int(hex_color[0:2], 16),
            g=int(hex_color[2:4], 16),
            b=int(hex_color[4:6], 16),
        )

    def to_tuple(self) -> tuple[int, int, int]:
        """Convert to RGB tuple."""
        return (self.r, self.g, self.b)

    def to_hex(self) -> str:
        """Convert to hex string."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def blend(self, other: "Color", factor: float) -> "Color":
        """Blend with another color.

        Args:
            other: Color to blend with
            factor: Blend factor (0.0 = self, 1.0 = other)

        Returns:
            Blended color
        """
        factor = max(0.0, min(1.0, factor))
        return Color(
            r=int(self.r + (other.r - self.r) * factor),
            g=int(self.g + (other.g - self.g) * factor),
            b=int(self.b + (other.b - self.b) * factor),
        )

    def dim(self, factor: float) -> "Color":
        """Dim the color by a factor.

        Args:
            factor: Dim factor (0.0 = black, 1.0 = original)

        Returns:
            Dimmed color
        """
        factor = max(0.0, min(1.0, factor))
        return Color(
            r=int(self.r * factor),
            g=int(self.g * factor),
            b=int(self.b * factor),
        )


class Colors:
    """Predefined color palette for modern aesthetic."""

    # Basic colors
    BLACK = Color(0, 0, 0)
    WHITE = Color(255, 255, 255)
    RED = Color(255, 0, 0)
    GREEN = Color(0, 255, 0)
    BLUE = Color(0, 0, 255)

    # Modern accent colors
    CYAN = Color(0, 212, 255)
    MAGENTA = Color(255, 0, 128)
    YELLOW = Color(255, 200, 0)
    ORANGE = Color(255, 100, 0)
    PURPLE = Color(128, 0, 255)
    PINK = Color(255, 100, 150)
    TEAL = Color(0, 180, 180)

    # Neutral tones
    GRAY_DARK = Color(30, 30, 35)
    GRAY = Color(80, 80, 90)
    GRAY_LIGHT = Color(150, 150, 160)

    # Status colors
    SUCCESS = Color(0, 200, 100)
    WARNING = Color(255, 180, 0)
    ERROR = Color(255, 60, 60)
    INFO = Color(0, 150, 255)

    # Stock colors
    STOCK_UP = Color(0, 200, 100)
    STOCK_DOWN = Color(255, 60, 60)

    # Time-based colors (for clock)
    MORNING = Color(255, 200, 100)  # Warm yellow
    DAY = Color(255, 255, 255)  # White
    EVENING = Color(255, 150, 100)  # Orange
    NIGHT = Color(100, 150, 255)  # Cool blue


def create_gradient(
    width: int,
    height: int,
    color_start: Color,
    color_end: Color,
    direction: str = "vertical",
) -> Image.Image:
    """Create a gradient image.

    Args:
        width: Image width
        height: Image height
        color_start: Starting color
        color_end: Ending color
        direction: 'vertical', 'horizontal', or 'diagonal'

    Returns:
        PIL Image with gradient
    """
    image = Image.new("RGB", (width, height))
    pixels = image.load()

    for y in range(height):
        for x in range(width):
            if direction == "vertical":
                factor = y / (height - 1) if height > 1 else 0
            elif direction == "horizontal":
                factor = x / (width - 1) if width > 1 else 0
            else:  # diagonal
                factor = (x + y) / (width + height - 2) if width + height > 2 else 0

            color = color_start.blend(color_end, factor)
            pixels[x, y] = color.to_tuple()

    return image


def create_radial_gradient(
    width: int,
    height: int,
    color_center: Color,
    color_edge: Color,
) -> Image.Image:
    """Create a radial gradient image.

    Args:
        width: Image width
        height: Image height
        color_center: Center color
        color_edge: Edge color

    Returns:
        PIL Image with radial gradient
    """
    image = Image.new("RGB", (width, height))
    pixels = image.load()

    center_x = width / 2
    center_y = height / 2
    max_dist = ((center_x) ** 2 + (center_y) ** 2) ** 0.5

    for y in range(height):
        for x in range(width):
            dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            factor = min(1.0, dist / max_dist)
            color = color_center.blend(color_edge, factor)
            pixels[x, y] = color.to_tuple()

    return image


def draw_text(
    image: Image.Image,
    text: str,
    x: int,
    y: int,
    color: Color = Colors.WHITE,
    font_size: int = 10,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> None:
    """Draw text on an image.

    Args:
        image: Target image
        text: Text to draw
        x: X position
        y: Y position
        color: Text color
        font_size: Font size (ignored if font provided)
        font: Optional font override
    """
    draw = ImageDraw.Draw(image)
    if font is None:
        font = get_default_font(font_size)
    draw.text((x, y), text, font=font, fill=color.to_tuple())


def draw_rect(
    image: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    color: Color = Colors.WHITE,
    filled: bool = True,
    border_radius: int = 0,
) -> None:
    """Draw a rectangle on an image.

    Args:
        image: Target image
        x: X position
        y: Y position
        width: Rectangle width
        height: Rectangle height
        color: Fill/outline color
        filled: Whether to fill the rectangle
        border_radius: Corner radius for rounded rectangles
    """
    draw = ImageDraw.Draw(image)

    if border_radius > 0:
        # Draw rounded rectangle
        draw.rounded_rectangle(
            [(x, y), (x + width - 1, y + height - 1)],
            radius=border_radius,
            fill=color.to_tuple() if filled else None,
            outline=color.to_tuple() if not filled else None,
        )
    else:
        if filled:
            draw.rectangle([(x, y), (x + width - 1, y + height - 1)], fill=color.to_tuple())
        else:
            draw.rectangle([(x, y), (x + width - 1, y + height - 1)], outline=color.to_tuple())


def draw_line(
    image: Image.Image,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: Color = Colors.WHITE,
    width: int = 1,
) -> None:
    """Draw a line on an image.

    Args:
        image: Target image
        x1, y1: Start point
        x2, y2: End point
        color: Line color
        width: Line width
    """
    draw = ImageDraw.Draw(image)
    draw.line([(x1, y1), (x2, y2)], fill=color.to_tuple(), width=width)


def draw_circle(
    image: Image.Image,
    center_x: int,
    center_y: int,
    radius: int,
    color: Color = Colors.WHITE,
    filled: bool = True,
) -> None:
    """Draw a circle on an image.

    Args:
        image: Target image
        center_x: Center X
        center_y: Center Y
        radius: Circle radius
        color: Fill/outline color
        filled: Whether to fill the circle
    """
    draw = ImageDraw.Draw(image)
    bbox = [
        center_x - radius,
        center_y - radius,
        center_x + radius,
        center_y + radius,
    ]

    if filled:
        draw.ellipse(bbox, fill=color.to_tuple())
    else:
        draw.ellipse(bbox, outline=color.to_tuple())


def draw_progress_bar(
    image: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    progress: float,
    color_fg: Color = Colors.CYAN,
    color_bg: Color = Colors.GRAY_DARK,
    border_radius: int = 0,
) -> None:
    """Draw a progress bar on an image.

    Args:
        image: Target image
        x: X position
        y: Y position
        width: Total width
        height: Bar height
        progress: Progress value (0.0 to 1.0)
        color_fg: Foreground (filled) color
        color_bg: Background color
        border_radius: Corner radius
    """
    progress = max(0.0, min(1.0, progress))

    # Background
    draw_rect(image, x, y, width, height, color_bg, filled=True, border_radius=border_radius)

    # Foreground
    fill_width = int(width * progress)
    if fill_width > 0:
        draw_rect(
            image, x, y, fill_width, height, color_fg, filled=True, border_radius=border_radius
        )


def draw_sparkline(
    image: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    values: Sequence[float],
    color: Color = Colors.CYAN,
) -> None:
    """Draw a sparkline chart.

    Args:
        image: Target image
        x: X position
        y: Y position
        width: Chart width
        height: Chart height
        values: Data values
        color: Line color
    """
    if len(values) < 2:
        return

    draw = ImageDraw.Draw(image)

    min_val = min(values)
    max_val = max(values)
    value_range = max_val - min_val if max_val != min_val else 1

    points = []
    for i, val in enumerate(values):
        px = x + int(i * width / (len(values) - 1))
        normalized = (val - min_val) / value_range
        py = y + height - int(normalized * height)
        points.append((px, py))

    # Draw line
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=color.to_tuple(), width=1)


def get_time_color(hour: int) -> Color:
    """Get a color based on time of day.

    Args:
        hour: Hour of day (0-23)

    Returns:
        Appropriate color for that time
    """
    if 6 <= hour < 10:
        return Colors.MORNING
    elif 10 <= hour < 17:
        return Colors.DAY
    elif 17 <= hour < 21:
        return Colors.EVENING
    else:
        return Colors.NIGHT
