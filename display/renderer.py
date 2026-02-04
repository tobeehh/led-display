"""Rendering utilities for the LED display.

Provides text rendering, image scaling, and other drawing utilities.
"""

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont


class Renderer:
    """Rendering utilities for the LED matrix display."""

    def __init__(self, width: int, height: int):
        """Initialize the renderer.

        Args:
            width: Display width in pixels.
            height: Display height in pixels.
        """
        self.width = width
        self.height = height
        self._font_cache: dict[tuple[str | None, int], ImageFont.FreeTypeFont] = {}

    def _get_font(
        self, font_path: str | None = None, size: int = 10
    ) -> ImageFont.FreeTypeFont:
        """Get a font, using cache if available.

        Args:
            font_path: Path to a TTF font file. None for default.
            size: Font size in pixels.

        Returns:
            The loaded font.
        """
        cache_key = (font_path, size)
        if cache_key not in self._font_cache:
            if font_path:
                try:
                    self._font_cache[cache_key] = ImageFont.truetype(font_path, size)
                except OSError:
                    # Fallback to default
                    self._font_cache[cache_key] = ImageFont.load_default()
            else:
                # Try to load a common system font
                for system_font in [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                ]:
                    try:
                        self._font_cache[cache_key] = ImageFont.truetype(
                            system_font, size
                        )
                        break
                    except OSError:
                        continue
                else:
                    self._font_cache[cache_key] = ImageFont.load_default()

        return self._font_cache[cache_key]

    def create_image(self) -> Image.Image:
        """Create a new blank image for the display.

        Returns:
            A new PIL Image with the display dimensions.
        """
        return Image.new("RGB", (self.width, self.height), (0, 0, 0))

    def render_text(
        self,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        font_path: str | None = None,
        font_size: int = 10,
        x: int = 0,
        y: int = 0,
        image: Image.Image | None = None,
    ) -> Image.Image:
        """Render text to an image.

        Args:
            text: The text to render.
            color: RGB color tuple.
            font_path: Path to a TTF font file.
            font_size: Font size in pixels.
            x: X position.
            y: Y position.
            image: Existing image to draw on, or None to create new.

        Returns:
            The image with rendered text.
        """
        if image is None:
            image = self.create_image()

        font = self._get_font(font_path, font_size)
        draw = ImageDraw.Draw(image)
        draw.text((x, y), text, fill=color, font=font)

        return image

    def render_centered_text(
        self,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        font_path: str | None = None,
        font_size: int = 10,
        image: Image.Image | None = None,
    ) -> Image.Image:
        """Render centered text to an image.

        Args:
            text: The text to render.
            color: RGB color tuple.
            font_path: Path to a TTF font file.
            font_size: Font size in pixels.
            image: Existing image to draw on, or None to create new.

        Returns:
            The image with centered text.
        """
        if image is None:
            image = self.create_image()

        font = self._get_font(font_path, font_size)
        draw = ImageDraw.Draw(image)

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate centered position
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2

        draw.text((x, y), text, fill=color, font=font)

        return image

    def get_text_width(
        self, text: str, font_path: str | None = None, font_size: int = 10
    ) -> int:
        """Get the width of rendered text.

        Args:
            text: The text to measure.
            font_path: Path to a TTF font file.
            font_size: Font size in pixels.

        Returns:
            The width in pixels.
        """
        font = self._get_font(font_path, font_size)
        dummy_image = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_image)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def scale_image(
        self,
        image: Image.Image,
        max_width: int | None = None,
        max_height: int | None = None,
        keep_aspect: bool = True,
    ) -> Image.Image:
        """Scale an image to fit within bounds.

        Args:
            image: The image to scale.
            max_width: Maximum width (defaults to display width).
            max_height: Maximum height (defaults to display height).
            keep_aspect: Whether to maintain aspect ratio.

        Returns:
            The scaled image.
        """
        if max_width is None:
            max_width = self.width
        if max_height is None:
            max_height = self.height

        if keep_aspect:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            return image
        else:
            return image.resize((max_width, max_height), Image.Resampling.LANCZOS)

    def load_image(
        self, path: str, max_width: int | None = None, max_height: int | None = None
    ) -> Image.Image:
        """Load and scale an image from a file.

        Args:
            path: Path to the image file.
            max_width: Maximum width.
            max_height: Maximum height.

        Returns:
            The loaded and scaled image.
        """
        image = Image.open(path).convert("RGB")
        return self.scale_image(image, max_width, max_height)

    def load_image_from_bytes(
        self,
        data: bytes,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> Image.Image:
        """Load and scale an image from bytes.

        Args:
            data: Image data as bytes.
            max_width: Maximum width.
            max_height: Maximum height.

        Returns:
            The loaded and scaled image.
        """
        image = Image.open(io.BytesIO(data)).convert("RGB")
        return self.scale_image(image, max_width, max_height)

    def image_to_canvas(self, image: Image.Image, canvas: Any) -> None:
        """Draw a PIL Image to the LED matrix canvas.

        Args:
            image: The PIL Image to draw.
            canvas: The rgbmatrix canvas.
        """
        if canvas is None:
            return

        # Ensure image is RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Set pixels from image
        pixels = image.load()
        for y in range(min(image.height, self.height)):
            for x in range(min(image.width, self.width)):
                r, g, b = pixels[x, y]
                canvas.SetPixel(x, y, r, g, b)

    def hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert a hex color string to RGB tuple.

        Args:
            hex_color: Hex color string (e.g., '#FFFFFF' or 'FFFFFF').

        Returns:
            RGB tuple (r, g, b).
        """
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB values to hex color string.

        Args:
            r: Red component (0-255).
            g: Green component (0-255).
            b: Blue component (0-255).

        Returns:
            Hex color string with '#' prefix.
        """
        return f"#{r:02X}{g:02X}{b:02X}"

    def draw_rectangle(
        self,
        image: Image.Image,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int],
        fill: bool = False,
    ) -> Image.Image:
        """Draw a rectangle on an image.

        Args:
            image: The image to draw on.
            x1: Top-left X coordinate.
            y1: Top-left Y coordinate.
            x2: Bottom-right X coordinate.
            y2: Bottom-right Y coordinate.
            color: RGB color tuple.
            fill: Whether to fill the rectangle.

        Returns:
            The image with the rectangle.
        """
        draw = ImageDraw.Draw(image)
        if fill:
            draw.rectangle((x1, y1, x2, y2), fill=color)
        else:
            draw.rectangle((x1, y1, x2, y2), outline=color)
        return image

    def draw_progress_bar(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        progress: float,
        fg_color: tuple[int, int, int] = (0, 255, 0),
        bg_color: tuple[int, int, int] = (50, 50, 50),
    ) -> Image.Image:
        """Draw a progress bar on an image.

        Args:
            image: The image to draw on.
            x: Top-left X coordinate.
            y: Top-left Y coordinate.
            width: Bar width.
            height: Bar height.
            progress: Progress value (0.0 to 1.0).
            fg_color: Foreground (filled) color.
            bg_color: Background color.

        Returns:
            The image with the progress bar.
        """
        # Draw background
        self.draw_rectangle(image, x, y, x + width - 1, y + height - 1, bg_color, True)

        # Draw progress
        progress = max(0.0, min(1.0, progress))
        fill_width = int(width * progress)
        if fill_width > 0:
            self.draw_rectangle(
                image, x, y, x + fill_width - 1, y + height - 1, fg_color, True
            )

        return image
