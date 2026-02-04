"""Clock display application.

Displays time and date with a modern aesthetic and
optional color transitions based on time of day.
"""

import logging
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw

from ..display.graphics import Color, Colors, get_time_color
from ..display.renderer import get_default_font
from .base import BaseApp, AppMetadata, ConfigFieldSchema, RenderResult

logger = logging.getLogger(__name__)


# Custom large digit font (5x7 pixels per digit)
LARGE_DIGITS = {
    "0": [
        " ### ",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        " ### ",
    ],
    "1": [
        "  #  ",
        " ##  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        " ### ",
    ],
    "2": [
        " ### ",
        "#   #",
        "    #",
        "  ## ",
        " #   ",
        "#    ",
        "#####",
    ],
    "3": [
        " ### ",
        "#   #",
        "    #",
        "  ## ",
        "    #",
        "#   #",
        " ### ",
    ],
    "4": [
        "#   #",
        "#   #",
        "#   #",
        "#####",
        "    #",
        "    #",
        "    #",
    ],
    "5": [
        "#####",
        "#    ",
        "#    ",
        "#### ",
        "    #",
        "#   #",
        " ### ",
    ],
    "6": [
        " ### ",
        "#    ",
        "#    ",
        "#### ",
        "#   #",
        "#   #",
        " ### ",
    ],
    "7": [
        "#####",
        "    #",
        "   # ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
    ],
    "8": [
        " ### ",
        "#   #",
        "#   #",
        " ### ",
        "#   #",
        "#   #",
        " ### ",
    ],
    "9": [
        " ### ",
        "#   #",
        "#   #",
        " ####",
        "    #",
        "    #",
        " ### ",
    ],
    ":": [
        "     ",
        "  #  ",
        "  #  ",
        "     ",
        "  #  ",
        "  #  ",
        "     ",
    ],
}

# Smaller digits for seconds (3x5 pixels)
SMALL_DIGITS = {
    "0": ["###", "# #", "# #", "# #", "###"],
    "1": [" # ", "## ", " # ", " # ", "###"],
    "2": ["###", "  #", "###", "#  ", "###"],
    "3": ["###", "  #", "###", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"],
    "5": ["###", "#  ", "###", "  #", "###"],
    "6": ["###", "#  ", "###", "# #", "###"],
    "7": ["###", "  #", "  #", "  #", "  #"],
    "8": ["###", "# #", "###", "# #", "###"],
    "9": ["###", "# #", "###", "  #", "###"],
}


class ClockApp(BaseApp):
    """Clock display application.

    Shows time and optional date with modern styling.
    Supports 12/24 hour format and auto color transitions.
    """

    @property
    def metadata(self) -> AppMetadata:
        return AppMetadata(
            name="clock",
            display_name="Clock",
            description="Digital clock with date display",
            version="1.0.0",
            requires_network=False,
            requires_credentials=False,
        )

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        return {
            "format_24h": ConfigFieldSchema(
                type="bool",
                label="24-Hour Format",
                description="Use 24-hour time format",
                default=True,
            ),
            "show_date": ConfigFieldSchema(
                type="bool",
                label="Show Date",
                description="Display date below time",
                default=True,
            ),
            "show_seconds": ConfigFieldSchema(
                type="bool",
                label="Show Seconds",
                description="Display seconds",
                default=False,
            ),
            "color_mode": ConfigFieldSchema(
                type="select",
                label="Color Mode",
                description="Time-based or static color",
                default="auto",
                options=[
                    {"value": "auto", "label": "Auto (time-based)"},
                    {"value": "static", "label": "Static color"},
                ],
            ),
            "color": ConfigFieldSchema(
                type="color",
                label="Static Color",
                description="Color when using static mode",
                default="#FFFFFF",
            ),
        }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._last_second = -1
        self._colon_visible = True

    def get_render_interval(self) -> float:
        """Render at 2 FPS for colon blinking."""
        return 0.5

    def render(self, width: int, height: int) -> RenderResult:
        """Render the clock display."""
        now = datetime.now()

        # Determine color
        if self._config.get("color_mode", "auto") == "auto":
            color = get_time_color(now.hour)
        else:
            color = Color.from_hex(self._config.get("color", "#FFFFFF"))

        # Create image
        image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())

        # Format time
        format_24h = self._config.get("format_24h", True)
        show_seconds = self._config.get("show_seconds", False)
        show_date = self._config.get("show_date", True)

        if format_24h:
            hour_str = f"{now.hour:02d}"
        else:
            hour = now.hour % 12
            if hour == 0:
                hour = 12
            hour_str = f"{hour:2d}"

        minute_str = f"{now.minute:02d}"

        # Toggle colon
        self._colon_visible = now.second % 2 == 0

        # Calculate layout
        if show_date:
            time_y = 8
            date_y = 45
        else:
            time_y = (height - 20) // 2

        # Draw time using large digits
        self._draw_large_time(image, hour_str, minute_str, time_y, color, width)

        # Draw seconds if enabled
        if show_seconds:
            second_str = f"{now.second:02d}"
            self._draw_small_digits(image, second_str, width - 12, time_y + 2, color.dim(0.6))

        # Draw date
        if show_date:
            date_str = now.strftime("%d.%m.%Y")
            self._draw_date(image, date_str, date_y, color.dim(0.5), width)

        # Draw AM/PM indicator for 12-hour format
        if not format_24h:
            ampm = "PM" if now.hour >= 12 else "AM"
            self._draw_ampm(image, ampm, width - 12, time_y + 14, color.dim(0.4))

        return RenderResult(image=image, next_render_in=0.5)

    def _draw_large_time(
        self,
        image: Image.Image,
        hour: str,
        minute: str,
        y: int,
        color: Color,
        width: int,
    ) -> None:
        """Draw time using large custom digits."""
        # Calculate total width: 2 digits + colon + 2 digits
        digit_width = 6
        colon_width = 5
        total_width = digit_width * 4 + colon_width + 4  # spacing

        x = (width - total_width) // 2

        # Draw hour
        for char in hour.strip():
            self._draw_large_digit(image, char, x, y, color)
            x += digit_width + 1

        # Draw colon
        if self._colon_visible:
            self._draw_large_digit(image, ":", x, y, color)
        x += colon_width

        # Draw minute
        for char in minute:
            self._draw_large_digit(image, char, x, y, color)
            x += digit_width + 1

    def _draw_large_digit(
        self,
        image: Image.Image,
        digit: str,
        x: int,
        y: int,
        color: Color,
    ) -> None:
        """Draw a single large digit."""
        if digit not in LARGE_DIGITS:
            return

        pixels = image.load()
        pattern = LARGE_DIGITS[digit]

        for row_idx, row in enumerate(pattern):
            for col_idx, char in enumerate(row):
                if char == "#":
                    px = x + col_idx
                    py = y + row_idx * 2  # Scale vertically
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color.to_tuple()
                    # Double height for better visibility
                    if 0 <= px < image.width and 0 <= py + 1 < image.height:
                        pixels[px, py + 1] = color.to_tuple()

    def _draw_small_digits(
        self,
        image: Image.Image,
        text: str,
        x: int,
        y: int,
        color: Color,
    ) -> None:
        """Draw small digits for seconds."""
        pixels = image.load()

        for char_idx, char in enumerate(text):
            if char not in SMALL_DIGITS:
                continue

            pattern = SMALL_DIGITS[char]
            char_x = x + char_idx * 4

            for row_idx, row in enumerate(pattern):
                for col_idx, c in enumerate(row):
                    if c == "#":
                        px = char_x + col_idx
                        py = y + row_idx
                        if 0 <= px < image.width and 0 <= py < image.height:
                            pixels[px, py] = color.to_tuple()

    def _draw_date(
        self,
        image: Image.Image,
        text: str,
        y: int,
        color: Color,
        width: int,
    ) -> None:
        """Draw date text."""
        draw = ImageDraw.Draw(image)
        font = get_default_font(9)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2

        draw.text((x, y), text, font=font, fill=color.to_tuple())

    def _draw_ampm(
        self,
        image: Image.Image,
        text: str,
        x: int,
        y: int,
        color: Color,
    ) -> None:
        """Draw AM/PM indicator."""
        draw = ImageDraw.Draw(image)
        font = get_default_font(7)
        draw.text((x, y), text, font=font, fill=color.to_tuple())
