"""Word Clock display application (QLOCKTWO style).

Displays time as illuminated words in a letter grid,
with smooth transitions and minute precision dots.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw

from ..display.graphics import Color, Colors, get_time_color
from .base import BaseApp, AppMetadata, ConfigFieldSchema, RenderResult

logger = logging.getLogger(__name__)


# The QLOCKTWO-style German letter grid (11 columns x 10 rows)
LETTER_GRID = [
    "ESKISTAFÜNF",   # Row 0: ES IST (A)FÜNF
    "ZEHNZWANZIG",   # Row 1: ZEHN ZWANZIG
    "DREIVIERTEL",   # Row 2: DREI VIERTEL
    "VORFUNKNACH",   # Row 3: VOR (FUNK) NACH
    "HALBAELFÜNF",   # Row 4: HALB (A) ELF FÜNF (hour)
    "EINSXAMZWEI",   # Row 5: EINS (X AM) ZWEI
    "DREIPMJVIER",   # Row 6: DREI (PMJ) VIER
    "SECHSNLACHT",   # Row 7: SECHS (NL) ACHT
    "SIEBENZWÖLF",   # Row 8: SIEBEN ZWÖLF
    "ZEHNEUNKUHR",   # Row 9: ZEHN NEUN (K) UHR
]

# Word positions as (row, start_col, end_col) - end_col is inclusive
@dataclass(frozen=True)
class WordPos:
    """Position of a word in the grid."""
    row: int
    start: int
    end: int  # inclusive


# Time-related words
WORDS = {
    # Always visible
    "ES": WordPos(0, 0, 1),
    "IST": WordPos(0, 3, 5),

    # Minute words
    "FÜNF_MIN": WordPos(0, 7, 10),      # FÜNF (for minutes)
    "ZEHN_MIN": WordPos(1, 0, 3),       # ZEHN (for minutes)
    "ZWANZIG": WordPos(1, 4, 10),       # ZWANZIG
    "DREIVIERTEL": WordPos(2, 0, 10),   # DREIVIERTEL (combined)
    "VIERTEL": WordPos(2, 4, 10),       # VIERTEL
    "VOR": WordPos(3, 0, 2),
    "NACH": WordPos(3, 7, 10),
    "HALB": WordPos(4, 0, 3),

    # Hour words
    "EIN": WordPos(5, 0, 2),            # EIN (for "EIN UHR")
    "EINS": WordPos(5, 0, 3),           # EINS (for other times)
    "ZWEI": WordPos(5, 7, 10),
    "DREI": WordPos(6, 0, 3),
    "VIER": WordPos(6, 7, 10),
    "FÜNF_HOUR": WordPos(4, 7, 10),     # FÜNF (for hours) - shares F with ELF
    "SECHS": WordPos(7, 0, 4),
    "SIEBEN": WordPos(8, 0, 5),
    "ACHT": WordPos(7, 7, 10),
    "NEUN": WordPos(9, 3, 6),           # Shares N with ZEHN
    "ZEHN_HOUR": WordPos(9, 0, 3),      # ZEHN (for hours)
    "ELF": WordPos(4, 5, 7),
    "ZWÖLF": WordPos(8, 6, 10),

    # UHR
    "UHR": WordPos(9, 8, 10),
}

# Hour word mapping (12-hour format, 0=12)
HOUR_WORDS = {
    0: "ZWÖLF",
    1: "EINS",
    2: "ZWEI",
    3: "DREI",
    4: "VIER",
    5: "FÜNF_HOUR",
    6: "SECHS",
    7: "SIEBEN",
    8: "ACHT",
    9: "NEUN",
    10: "ZEHN_HOUR",
    11: "ELF",
    12: "ZWÖLF",
}


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease in-out function for smooth transitions."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


class WordClockApp(BaseApp):
    """Word Clock display application.

    Shows time as illuminated German words in a QLOCKTWO-style grid.
    Features smooth transitions and minute precision corner dots.
    """

    @property
    def metadata(self) -> AppMetadata:
        return AppMetadata(
            name="wordclock",
            display_name="Word Clock",
            description="QLOCKTWO-style word clock display",
            version="1.0.0",
            requires_network=False,
            requires_credentials=False,
        )

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        return {
            "color_mode": ConfigFieldSchema(
                type="select",
                label="Color Mode",
                description="How to color the active words",
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
            "dim_factor": ConfigFieldSchema(
                type="int",
                label="Inactive Brightness",
                description="Brightness of inactive letters (0-30%)",
                default=8,
                min_value=0,
                max_value=30,
            ),
            "transition_speed": ConfigFieldSchema(
                type="select",
                label="Transition Speed",
                description="Speed of word transitions",
                default="normal",
                options=[
                    {"value": "instant", "label": "Instant"},
                    {"value": "fast", "label": "Fast"},
                    {"value": "normal", "label": "Normal"},
                    {"value": "slow", "label": "Slow"},
                ],
            ),
            "show_dots": ConfigFieldSchema(
                type="bool",
                label="Show Minute Dots",
                description="Show corner dots for minute precision",
                default=True,
            ),
            "dialect": ConfigFieldSchema(
                type="select",
                label="Dialect",
                description="Time expression variant",
                default="standard",
                options=[
                    {"value": "standard", "label": "Standard (VIERTEL NACH)"},
                    {"value": "regional", "label": "Regional (DREIVIERTEL)"},
                ],
            ),
        }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)

        # Animation state
        self._active_letters: set[tuple[int, int]] = set()
        self._target_letters: set[tuple[int, int]] = set()
        self._letter_brightness: dict[tuple[int, int], float] = {}
        self._last_update_time = 0.0
        self._transition_start = 0.0
        self._last_minute = -1

        # Precompute grid dimensions
        self._grid_rows = len(LETTER_GRID)
        self._grid_cols = len(LETTER_GRID[0])

    def get_render_interval(self) -> float:
        """Render at 30 FPS for smooth transitions."""
        return 1.0 / 30.0

    def _get_transition_duration(self) -> float:
        """Get transition duration based on config."""
        speed = self._config.get("transition_speed", "normal")
        return {
            "instant": 0.0,
            "fast": 0.3,
            "normal": 0.6,
            "slow": 1.2,
        }.get(speed, 0.6)

    def _get_time_words(self, hour: int, minute: int) -> list[str]:
        """Get list of words to illuminate for given time.

        Args:
            hour: Hour (0-23)
            minute: Minute (0-59)

        Returns:
            List of word keys to illuminate
        """
        words = ["ES", "IST"]  # Always shown

        # Convert to 12-hour format
        display_hour = hour % 12

        # Get the five-minute block
        five_min = minute // 5

        # Determine which hour word to use
        # For :25-:59, we reference the next hour
        if five_min >= 5:  # :25 and later
            next_hour = (display_hour + 1) % 12
            if next_hour == 0:
                next_hour = 12
            hour_word = HOUR_WORDS[next_hour]
        else:
            hour_word = HOUR_WORDS[display_hour if display_hour != 0 else 12]

        # Regional vs standard dialect
        use_dreiviertel = self._config.get("dialect", "standard") == "regional"

        # Build time phrase based on five-minute block
        if five_min == 0:  # :00
            words.append(hour_word)
            words.append("UHR")
            # Use "EIN UHR" instead of "EINS UHR"
            if hour_word == "EINS":
                words.remove("EINS")
                words.append("EIN")
        elif five_min == 1:  # :05
            words.extend(["FÜNF_MIN", "NACH", hour_word])
        elif five_min == 2:  # :10
            words.extend(["ZEHN_MIN", "NACH", hour_word])
        elif five_min == 3:  # :15
            if use_dreiviertel:
                words.extend(["VIERTEL", hour_word])
            else:
                words.extend(["VIERTEL", "NACH", hour_word])
        elif five_min == 4:  # :20
            words.extend(["ZWANZIG", "NACH", hour_word])
        elif five_min == 5:  # :25
            words.extend(["FÜNF_MIN", "VOR", "HALB", hour_word])
        elif five_min == 6:  # :30
            words.extend(["HALB", hour_word])
        elif five_min == 7:  # :35
            words.extend(["FÜNF_MIN", "NACH", "HALB", hour_word])
        elif five_min == 8:  # :40
            words.extend(["ZWANZIG", "VOR", hour_word])
        elif five_min == 9:  # :45
            if use_dreiviertel:
                words.extend(["DREIVIERTEL", hour_word])
            else:
                words.extend(["VIERTEL", "VOR", hour_word])
        elif five_min == 10:  # :50
            words.extend(["ZEHN_MIN", "VOR", hour_word])
        elif five_min == 11:  # :55
            words.extend(["FÜNF_MIN", "VOR", hour_word])

        return words

    def _words_to_letters(self, word_names: list[str]) -> set[tuple[int, int]]:
        """Convert word names to set of (row, col) letter positions."""
        letters = set()
        for name in word_names:
            if name in WORDS:
                pos = WORDS[name]
                for col in range(pos.start, pos.end + 1):
                    letters.add((pos.row, col))
        return letters

    def _get_minute_dots(self, minute: int) -> list[int]:
        """Get which corner dots should be lit (0-3)."""
        extra_minutes = minute % 5
        return list(range(extra_minutes))

    def render(self, width: int, height: int) -> RenderResult:
        """Render the word clock display."""
        now = datetime.now()
        current_time = time.time()

        # Check if minute changed
        if now.minute != self._last_minute:
            self._last_minute = now.minute
            self._transition_start = current_time

            # Update target letters
            words = self._get_time_words(now.hour, now.minute)
            self._target_letters = self._words_to_letters(words)

            # On first render, set active immediately
            if not self._active_letters:
                self._active_letters = self._target_letters.copy()

        # Calculate transition progress
        transition_duration = self._get_transition_duration()
        if transition_duration > 0:
            elapsed = current_time - self._transition_start
            progress = min(1.0, elapsed / transition_duration)
            progress = ease_in_out_cubic(progress)
        else:
            progress = 1.0

        # Update letter brightness with smooth transitions
        all_letters = self._active_letters | self._target_letters
        for pos in all_letters:
            current = self._letter_brightness.get(pos, 0.0)
            target = 1.0 if pos in self._target_letters else 0.0

            if transition_duration > 0:
                # Interpolate brightness
                new_brightness = current + (target - current) * progress
            else:
                new_brightness = target

            self._letter_brightness[pos] = new_brightness

        # After transition complete, update active letters
        if progress >= 1.0:
            self._active_letters = self._target_letters.copy()

        # Determine colors
        if self._config.get("color_mode", "auto") == "auto":
            active_color = get_time_color(now.hour)
        else:
            active_color = Color.from_hex(self._config.get("color", "#FFFFFF"))

        dim_factor = self._config.get("dim_factor", 8) / 100.0
        inactive_color = active_color.dim(dim_factor)

        # Create image
        image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())

        # Calculate grid layout
        # Leave space for corner dots (2 pixels margin)
        margin = 2
        available_width = width - 2 * margin
        available_height = height - 2 * margin

        cell_width = available_width / self._grid_cols
        cell_height = available_height / self._grid_rows

        # Use smaller dimension to keep letters square-ish
        cell_size = min(cell_width, cell_height)

        # Center the grid
        grid_width = cell_size * self._grid_cols
        grid_height = cell_size * self._grid_rows
        offset_x = (width - grid_width) / 2
        offset_y = (height - grid_height) / 2

        # Draw letters
        pixels = image.load()

        for row in range(self._grid_rows):
            for col in range(self._grid_cols):
                letter = LETTER_GRID[row][col]

                # Calculate letter center position
                cx = int(offset_x + col * cell_size + cell_size / 2)
                cy = int(offset_y + row * cell_size + cell_size / 2)

                # Get brightness for this letter
                brightness = self._letter_brightness.get((row, col), 0.0)

                # Interpolate between inactive and active color
                if brightness > 0:
                    color = inactive_color.blend(active_color, brightness)
                else:
                    color = inactive_color

                # Draw the letter as a small filled region (3x3 or 2x2 depending on size)
                letter_size = max(1, int(cell_size * 0.6))
                half = letter_size // 2

                for dy in range(-half, half + 1):
                    for dx in range(-half, half + 1):
                        px, py = cx + dx, cy + dy
                        if 0 <= px < width and 0 <= py < height:
                            # Simple anti-aliasing: dim corners slightly
                            if abs(dx) == half and abs(dy) == half:
                                pixels[px, py] = color.dim(0.7).to_tuple()
                            else:
                                pixels[px, py] = color.to_tuple()

        # Draw corner dots for minute precision
        if self._config.get("show_dots", True):
            dots = self._get_minute_dots(now.minute)
            dot_positions = [
                (1, 1),                  # Top-left
                (width - 2, 1),          # Top-right
                (1, height - 2),         # Bottom-left
                (width - 2, height - 2), # Bottom-right
            ]

            for i, (dx, dy) in enumerate(dot_positions):
                if i < len(dots):
                    # Active dot
                    pixels[dx, dy] = active_color.to_tuple()
                else:
                    # Inactive dot (very dim)
                    pixels[dx, dy] = active_color.dim(dim_factor * 0.5).to_tuple()

        # Determine next render time
        # During transitions, render at 30 FPS
        # When stable, render at 1 FPS
        if progress < 1.0:
            next_render = 1.0 / 30.0
        else:
            # Calculate seconds until next minute
            next_render = max(0.1, 60 - now.second - now.microsecond / 1_000_000)
            # But check more frequently (every second) to not miss minute changes
            next_render = min(next_render, 1.0)

        return RenderResult(image=image, next_render_in=next_render)

    def _on_activate(self) -> None:
        """Reset state on activation."""
        self._active_letters = set()
        self._target_letters = set()
        self._letter_brightness = {}
        self._last_minute = -1
        self._transition_start = 0.0

    def _on_deactivate(self) -> None:
        """Clean up on deactivation."""
        self._letter_brightness.clear()
