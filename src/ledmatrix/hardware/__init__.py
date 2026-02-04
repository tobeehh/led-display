"""Hardware abstraction module.

Provides:
- ButtonHandler for GPIO button input
- Mock implementations for development
"""

from .button import ButtonHandler, get_button_handler
from .mock import MockMatrix, MockGPIO

__all__ = [
    "ButtonHandler",
    "get_button_handler",
    "MockMatrix",
    "MockGPIO",
]
