"""PIL-based rendering utilities for the LED display.

Provides helper functions for text rendering, image manipulation,
and common display operations.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Default font paths to search
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "/System/Library/Fonts/SFCompact.ttf",  # macOS
]


class Renderer:
    """Utility class for rendering to PIL images.

    Provides convenience methods for common rendering operations
    on LED matrix displays.
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize renderer with target dimensions.

        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self.width = width
        self.height = height

    def create_canvas(
        self,
        background: tuple[int, int, int] = (0, 0, 0),
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create a new canvas for drawing.

        Args:
            background: RGB background color

        Returns:
            Tuple of (PIL Image, ImageDraw object)
        """
        image = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(image)
        return image, draw

    def draw_centered_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        y: int | None = None,
        font: ImageFont.FreeTypeFont | None = None,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        """Draw text centered horizontally.

        Args:
            draw: ImageDraw object
            text: Text to draw
            y: Y position (None = vertically centered)
            font: Font to use (None = default)
            color: RGB text color
        """
        if font is None:
            font = get_default_font(10)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.width - text_width) // 2
        if y is None:
            y = (self.height - text_height) // 2

        draw.text((x, y), text, font=font, fill=color)

    def draw_multiline_centered(
        self,
        draw: ImageDraw.ImageDraw,
        lines: Sequence[str],
        font: ImageFont.FreeTypeFont | None = None,
        color: tuple[int, int, int] = (255, 255, 255),
        line_spacing: int = 2,
    ) -> None:
        """Draw multiple lines of text, centered.

        Args:
            draw: ImageDraw object
            lines: List of text lines
            font: Font to use
            color: RGB text color
            line_spacing: Pixels between lines
        """
        if font is None:
            font = get_default_font(10)

        # Calculate total height
        total_height = 0
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            height = bbox[3] - bbox[1]
            line_heights.append(height)
            total_height += height

        total_height += line_spacing * (len(lines) - 1)

        # Start position
        y = (self.height - total_height) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, y), line, font=font, fill=color)
            y += line_heights[i] + line_spacing

    def scale_image(
        self,
        image: Image.Image,
        max_width: int | None = None,
        max_height: int | None = None,
        keep_aspect: bool = True,
    ) -> Image.Image:
        """Scale an image to fit within bounds.

        Args:
            image: Source image
            max_width: Maximum width (None = display width)
            max_height: Maximum height (None = display height)
            keep_aspect: Maintain aspect ratio

        Returns:
            Scaled image
        """
        max_width = max_width or self.width
        max_height = max_height or self.height

        if keep_aspect:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            return image
        else:
            return image.resize((max_width, max_height), Image.Resampling.LANCZOS)

    def center_image(
        self,
        image: Image.Image,
        background: tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        """Center an image on the display canvas.

        Args:
            image: Image to center
            background: Background color

        Returns:
            New image with centered content
        """
        canvas = Image.new("RGB", (self.width, self.height), background)

        x = (self.width - image.width) // 2
        y = (self.height - image.height) // 2

        canvas.paste(image, (x, y))
        return canvas


@lru_cache(maxsize=32)
def get_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font from path with caching.

    Args:
        path: Path to font file
        size: Font size in pixels

    Returns:
        PIL Font object
    """
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError) as e:
        logger.warning("Failed to load font %s: %s", path, e)
        return ImageFont.load_default()


def get_default_font(size: int = 10) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get the default system font.

    Args:
        size: Font size in pixels

    Returns:
        PIL Font object
    """
    for font_path in FONT_PATHS:
        if Path(font_path).exists():
            return get_font(font_path, size)

    logger.warning("No system fonts found, using PIL default")
    return ImageFont.load_default()


def get_text_dimensions(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> tuple[int, int]:
    """Get the dimensions of rendered text.

    Args:
        text: Text to measure
        font: Font to use (None = default)

    Returns:
        Tuple of (width, height) in pixels
    """
    if font is None:
        font = get_default_font()

    # Use a temporary draw object to measure
    dummy_image = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_image)
    bbox = draw.textbbox((0, 0), text, font=font)

    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def resize_for_display(
    image: Image.Image,
    target_width: int,
    target_height: int,
    fit_mode: str = "contain",
) -> Image.Image:
    """Resize an image to fit the display.

    Args:
        image: Source image
        target_width: Target width
        target_height: Target height
        fit_mode: 'contain' (fit within) or 'cover' (fill, may crop)

    Returns:
        Resized image
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    src_ratio = image.width / image.height
    target_ratio = target_width / target_height

    if fit_mode == "contain":
        if src_ratio > target_ratio:
            # Image is wider than target
            new_width = target_width
            new_height = int(target_width / src_ratio)
        else:
            # Image is taller than target
            new_height = target_height
            new_width = int(target_height * src_ratio)
    else:  # cover
        if src_ratio > target_ratio:
            new_height = target_height
            new_width = int(target_height * src_ratio)
        else:
            new_width = target_width
            new_height = int(target_width / src_ratio)

    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    if fit_mode == "cover" and (new_width > target_width or new_height > target_height):
        # Crop to target size
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        resized = resized.crop((left, top, left + target_width, top + target_height))

    return resized
