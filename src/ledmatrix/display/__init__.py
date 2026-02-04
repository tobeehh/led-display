"""Display subsystem for LED matrix control.

Provides:
- DisplayManager for hardware control
- Renderer for PIL image utilities
- Graphics primitives (colors, gradients, shapes)
"""

from .manager import DisplayManager, get_display_manager
from .renderer import Renderer
from .graphics import Colors, draw_text, draw_rect, create_gradient

__all__ = [
    "DisplayManager",
    "get_display_manager",
    "Renderer",
    "Colors",
    "draw_text",
    "draw_rect",
    "create_gradient",
]
