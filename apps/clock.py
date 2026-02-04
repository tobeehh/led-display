"""Modern clock application for 64x64 LED display.

Features:
- Large pixel-perfect time display optimized for 64x64
- Smooth color transitions based on time of day
- Animated colon separator
- Clean date display
"""

import math
import time
from datetime import datetime
from typing import Any

from PIL import Image

from display.fonts import small_font, medium_font
from display.graphics import Colors, Gradients, Drawing, Animation

from .base import BaseApp

# Custom large digits optimized for 64x64 display (12x20 each)
CLOCK_DIGITS = {
    '0': [
        ".1111111111.",
        "111111111111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111111111111",
        ".1111111111.",
    ],
    '1': [
        "....111.....",
        "...1111.....",
        "..11111.....",
        ".111111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "....111.....",
        "111111111111",
        "111111111111",
    ],
    '2': [
        ".1111111111.",
        "111111111111",
        "111......111",
        "111......111",
        ".........111",
        ".........111",
        "........111.",
        ".......111..",
        "......111...",
        ".....111....",
        "....111.....",
        "...111......",
        "..111.......",
        ".111........",
        "111.........",
        "111.........",
        "111.........",
        "111.........",
        "111111111111",
        "111111111111",
    ],
    '3': [
        ".1111111111.",
        "111111111111",
        "111......111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        "...111111111",
        "...111111111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        "111......111",
        "111......111",
        "111111111111",
        ".1111111111.",
    ],
    '4': [
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111111111111",
        "111111111111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
    ],
    '5': [
        "111111111111",
        "111111111111",
        "111.........",
        "111.........",
        "111.........",
        "111.........",
        "111.........",
        "111.........",
        "1111111111..",
        "111111111111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        "111......111",
        "111......111",
        "111111111111",
        ".1111111111.",
    ],
    '6': [
        ".1111111111.",
        "111111111111",
        "111......111",
        "111.........",
        "111.........",
        "111.........",
        "111.........",
        "111.........",
        "1111111111..",
        "111111111111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111111111111",
        ".1111111111.",
    ],
    '7': [
        "111111111111",
        "111111111111",
        ".........111",
        ".........111",
        "........111.",
        ".......111..",
        "......111...",
        ".....111....",
        "....111.....",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
        "...111......",
    ],
    '8': [
        ".1111111111.",
        "111111111111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        ".1111111111.",
        ".1111111111.",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111111111111",
        ".1111111111.",
    ],
    '9': [
        ".1111111111.",
        "111111111111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111......111",
        "111111111111",
        ".111111111.1",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        ".........111",
        "111......111",
        "111......111",
        "111111111111",
        ".1111111111.",
    ],
}

CLOCK_COLON = [
    "....",
    "....",
    "....",
    "....",
    ".11.",
    ".11.",
    ".11.",
    "....",
    "....",
    "....",
    "....",
    "....",
    ".11.",
    ".11.",
    ".11.",
    "....",
    "....",
    "....",
    "....",
    "....",
]


class ClockApp(BaseApp):
    """Displays the current time with modern aesthetic on 64x64."""

    name = "clock"
    display_name = "Clock"
    description = "Shows current time and date"
    requires_credentials = False

    config_schema = {
        "format_24h": {
            "type": "bool",
            "label": "24-hour format",
            "default": True,
        },
        "show_date": {
            "type": "bool",
            "label": "Show date",
            "default": True,
        },
        "show_seconds": {
            "type": "bool",
            "label": "Show seconds",
            "default": False,
        },
        "color_mode": {
            "type": "select",
            "label": "Color mode",
            "options": [
                {"value": "auto", "label": "Auto (time of day)"},
                {"value": "static", "label": "Static color"},
            ],
            "default": "auto",
        },
        "color": {
            "type": "color",
            "label": "Static color",
            "default": "#FFFFFF",
        },
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._last_second = -1
        self._colon_visible = True
        self._start_time = time.time()

    def _get_time_of_day_color(self, hour: float) -> tuple[int, int, int]:
        """Get color based on time of day with smooth transitions."""
        color_stops = [
            (0, (80, 100, 180)),     # Midnight - blue
            (5, (100, 120, 200)),    # Early morning
            (6, (255, 160, 100)),    # Dawn - orange
            (8, (255, 230, 200)),    # Morning - warm
            (12, (255, 255, 255)),   # Noon - white
            (17, (255, 220, 180)),   # Afternoon - warm
            (19, (255, 150, 80)),    # Sunset - orange
            (20, (200, 100, 150)),   # Dusk - purple
            (22, (100, 100, 180)),   # Night - blue
            (24, (80, 100, 180)),    # Midnight
        ]

        for i in range(len(color_stops) - 1):
            h1, c1 = color_stops[i]
            h2, c2 = color_stops[i + 1]
            if h1 <= hour < h2:
                t = (hour - h1) / (h2 - h1)
                return Colors.lerp_color(c1, c2, t)

        return color_stops[0][1]

    def _render_digit(self, image: Image.Image, digit: str, x: int, y: int, color: tuple[int, int, int]) -> int:
        """Render a large clock digit. Returns width."""
        if digit not in CLOCK_DIGITS:
            return 12

        bitmap = CLOCK_DIGITS[digit]
        pixels = image.load()

        for row_idx, row in enumerate(bitmap):
            for col_idx, pixel in enumerate(row):
                if pixel == '1':
                    px = x + col_idx
                    py = y + row_idx
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color

        return len(bitmap[0])

    def _render_colon(self, image: Image.Image, x: int, y: int, color: tuple[int, int, int]) -> int:
        """Render the colon separator."""
        pixels = image.load()

        for row_idx, row in enumerate(CLOCK_COLON):
            for col_idx, pixel in enumerate(row):
                if pixel == '1':
                    px = x + col_idx
                    py = y + row_idx
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color

        return len(CLOCK_COLON[0])

    def render(self, width: int, height: int) -> Image.Image:
        """Render the clock display for 64x64."""
        image = Image.new("RGB", (width, height), (0, 0, 0))
        now = datetime.now()
        current_time = time.time()

        # Config
        format_24h = self._config.get("format_24h", True)
        show_date = self._config.get("show_date", True)
        show_seconds = self._config.get("show_seconds", False)
        color_mode = self._config.get("color_mode", "auto")

        # Determine color
        if color_mode == "auto":
            hour_float = now.hour + now.minute / 60.0
            main_color = self._get_time_of_day_color(hour_float)
        else:
            main_color = Colors.hex_to_rgb(self._config.get("color", "#FFFFFF"))

        # Colon blink animation
        elapsed = current_time - self._start_time
        self._colon_visible = Animation.blink(elapsed, on_duration=0.5)

        # Get time values
        if format_24h:
            hour = now.hour
        else:
            hour = now.hour % 12
            if hour == 0:
                hour = 12

        hour_str = f"{hour:02d}"
        minute_str = f"{now.minute:02d}"

        # Layout calculation for 64x64
        # Digit: 12px wide, Colon: 4px, Spacing: 1px
        # Total: 12 + 1 + 12 + 1 + 4 + 1 + 12 + 1 + 12 = 56px (centered in 64)
        digit_height = 20

        if show_seconds:
            # Compact layout with seconds
            time_y = 4 if show_date else 12

            # Hours and minutes (medium size)
            x = 4
            medium_font.render_text(image, hour_str, x, time_y, main_color)
            x += medium_font.get_text_width(hour_str) + 1

            colon_color = main_color if self._colon_visible else Colors.dim(main_color, 0.15)
            medium_font.render_text(image, ":", x, time_y, colon_color)
            x += medium_font.get_text_width(":") + 1

            medium_font.render_text(image, minute_str, x, time_y, main_color)
            x += medium_font.get_text_width(minute_str) + 2

            # Seconds (smaller)
            second_str = f"{now.second:02d}"
            small_font.render_text(image, second_str, x, time_y + 3, Colors.dim(main_color, 0.5))

        else:
            # Large time display
            time_y = 8 if show_date else 22

            # Calculate total width
            total_width = 12 * 4 + 4 + 3  # 4 digits + colon + spacing
            start_x = (width - total_width) // 2

            x = start_x

            # Hour digit 1
            x += self._render_digit(image, hour_str[0], x, time_y, main_color) + 1
            # Hour digit 2
            x += self._render_digit(image, hour_str[1], x, time_y, main_color) + 1

            # Colon (animated)
            colon_color = main_color if self._colon_visible else Colors.dim(main_color, 0.1)
            x += self._render_colon(image, x, time_y, colon_color) + 1

            # Minute digit 1
            x += self._render_digit(image, minute_str[0], x, time_y, main_color) + 1
            # Minute digit 2
            self._render_digit(image, minute_str[1], x, time_y, main_color)

            # AM/PM indicator for 12h format
            if not format_24h:
                ampm = "AM" if now.hour < 12 else "PM"
                ampm_color = Colors.dim(main_color, 0.4)
                small_font.render_text(image, ampm, width - 14, time_y, ampm_color)

        # Date display at bottom
        if show_date:
            # Separator line
            line_y = height - 20
            Drawing.line(image, 8, line_y, width - 8, line_y, Colors.dim(main_color, 0.15))

            # Date text
            date_y = height - 14
            day_name = now.strftime("%a")
            day_num = now.strftime("%d")
            month_name = now.strftime("%b")
            date_str = f"{day_name} {day_num} {month_name}"

            date_color = Colors.dim(main_color, 0.5)
            small_font.render_text_centered(image, date_str, date_y, date_color)

        return image

    def get_render_interval(self) -> float:
        """Update frequently for smooth colon animation."""
        return 0.5
