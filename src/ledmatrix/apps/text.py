"""Scrolling text display application.

Shows customizable scrolling or static text with various styles.
"""

import logging
import time
from typing import Any

from PIL import Image, ImageDraw

from ..display.graphics import Color, Colors, create_gradient
from ..display.renderer import get_default_font
from .base import BaseApp, AppMetadata, ConfigFieldSchema, RenderResult

logger = logging.getLogger(__name__)


# Style definitions
STYLES = {
    "modern": {
        "text_color": Colors.CYAN,
        "bg_gradient": (Colors.BLACK, Colors.GRAY_DARK),
    },
    "neon": {
        "text_color": Colors.MAGENTA,
        "bg_gradient": (Colors.BLACK, Colors.PURPLE.dim(0.2)),
    },
    "minimal": {
        "text_color": Colors.WHITE,
        "bg_gradient": (Colors.BLACK, Colors.BLACK),
    },
    "retro": {
        "text_color": Colors.ORANGE,
        "bg_gradient": (Colors.BLACK, Colors.GRAY_DARK),
    },
    "matrix": {
        "text_color": Colors.SUCCESS,
        "bg_gradient": (Colors.BLACK, Colors.BLACK),
    },
}


class TextApp(BaseApp):
    """Scrolling text display application.

    Shows customizable text with various visual styles
    and optional scrolling animation.
    """

    @property
    def metadata(self) -> AppMetadata:
        return AppMetadata(
            name="text",
            display_name="Text",
            description="Custom scrolling text display",
            version="1.0.0",
            requires_network=False,
            requires_credentials=False,
        )

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        return {
            "message": ConfigFieldSchema(
                type="string",
                label="Message",
                description="Text to display",
                default="Hello World!",
            ),
            "scroll": ConfigFieldSchema(
                type="bool",
                label="Scroll",
                description="Enable scrolling animation",
                default=True,
            ),
            "scroll_speed": ConfigFieldSchema(
                type="int",
                label="Scroll Speed",
                description="Pixels per second",
                default=30,
                min_value=10,
                max_value=100,
            ),
            "style": ConfigFieldSchema(
                type="select",
                label="Style",
                description="Visual style",
                default="modern",
                options=[
                    {"value": "modern", "label": "Modern (Cyan)"},
                    {"value": "neon", "label": "Neon (Magenta)"},
                    {"value": "minimal", "label": "Minimal (White)"},
                    {"value": "retro", "label": "Retro (Orange)"},
                    {"value": "matrix", "label": "Matrix (Green)"},
                ],
            ),
            "color": ConfigFieldSchema(
                type="color",
                label="Custom Color",
                description="Override style color (leave empty for style default)",
                default="",
            ),
            "size": ConfigFieldSchema(
                type="select",
                label="Font Size",
                description="Text size",
                default="large",
                options=[
                    {"value": "small", "label": "Small"},
                    {"value": "large", "label": "Large"},
                ],
            ),
        }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._scroll_offset = 0.0
        self._last_render_time = 0.0
        self._text_width = 0

    def get_render_interval(self) -> float:
        """Render at 30 FPS for smooth scrolling."""
        if self._config.get("scroll", True):
            return 1.0 / 30.0
        return 1.0

    def render(self, width: int, height: int) -> RenderResult:
        """Render text display."""
        message = self._config.get("message", "Hello World!")
        scroll = self._config.get("scroll", True)
        scroll_speed = self._config.get("scroll_speed", 30)
        style_name = self._config.get("style", "modern")
        custom_color = self._config.get("color", "")
        size = self._config.get("size", "large")

        # Get style
        style = STYLES.get(style_name, STYLES["modern"])

        # Create background
        bg_start, bg_end = style["bg_gradient"]
        image = create_gradient(width, height, bg_start, bg_end, direction="vertical")
        draw = ImageDraw.Draw(image)

        # Get color
        if custom_color:
            try:
                text_color = Color.from_hex(custom_color)
            except ValueError:
                text_color = style["text_color"]
        else:
            text_color = style["text_color"]

        # Get font
        font_size = 16 if size == "large" else 10
        font = get_default_font(font_size)

        # Calculate text dimensions
        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        self._text_width = text_width

        # Calculate position
        y = (height - text_height) // 2

        if scroll and text_width > width:
            # Update scroll position
            now = time.time()
            if self._last_render_time > 0:
                dt = now - self._last_render_time
                self._scroll_offset += scroll_speed * dt
            self._last_render_time = now

            # Wrap scroll offset
            total_width = text_width + width
            if self._scroll_offset >= total_width:
                self._scroll_offset = 0

            # Draw scrolling text
            x = width - int(self._scroll_offset)

            # Draw text twice for seamless scroll
            draw.text((x, y), message, font=font, fill=text_color.to_tuple())
            draw.text((x + text_width + width // 2, y), message, font=font, fill=text_color.to_tuple())

            return RenderResult(image=image, next_render_in=1.0 / 30.0)

        else:
            # Static centered text
            x = (width - text_width) // 2
            draw.text((x, y), message, font=font, fill=text_color.to_tuple())

            return RenderResult(image=image, next_render_in=1.0)

    def _on_deactivate(self) -> None:
        """Reset scroll on deactivation."""
        self._scroll_offset = 0
        self._last_render_time = 0
