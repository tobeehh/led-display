"""Display helper functions for apps.

Provides common image generation utilities used across apps.
"""

from PIL import Image, ImageDraw

from .display.graphics import Colors, draw_text
from .display.renderer import get_default_font


def create_error_image(width: int, height: int, message: str) -> Image.Image:
    """Create an error display image.

    Args:
        width: Image width
        height: Image height
        message: Error message to display

    Returns:
        PIL Image showing the error
    """
    image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())
    draw = ImageDraw.Draw(image)

    # Red border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=Colors.ERROR.to_tuple())

    # Error text
    font = get_default_font(8)
    text = "ERROR"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, 5), text, font=font, fill=Colors.ERROR.to_tuple())

    # Message (truncated if needed)
    msg_font = get_default_font(7)
    max_chars = width // 5  # Approximate character width
    if len(message) > max_chars:
        message = message[: max_chars - 3] + "..."

    bbox = draw.textbbox((0, 0), message, font=msg_font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, height // 2), message, font=msg_font, fill=Colors.GRAY_LIGHT.to_tuple())

    return image


def create_loading_image(width: int, height: int) -> Image.Image:
    """Create a loading display image.

    Args:
        width: Image width
        height: Image height

    Returns:
        PIL Image showing loading state
    """
    image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())
    draw = ImageDraw.Draw(image)

    # Loading text
    font = get_default_font(10)
    text = "Loading..."
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    draw.text((x, y), text, font=font, fill=Colors.GRAY.to_tuple())

    return image


def create_message_image(
    width: int,
    height: int,
    title: str,
    message: str = "",
    color: tuple[int, int, int] = Colors.CYAN.to_tuple(),
) -> Image.Image:
    """Create a message display image.

    Args:
        width: Image width
        height: Image height
        title: Title text
        message: Optional message text
        color: Text color

    Returns:
        PIL Image with the message
    """
    image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())
    draw = ImageDraw.Draw(image)

    # Title
    title_font = get_default_font(12)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    text_width = bbox[2] - bbox[0]

    x = (width - text_width) // 2
    y = height // 3 if message else height // 2 - 6

    draw.text((x, y), title, font=title_font, fill=color)

    # Message
    if message:
        msg_font = get_default_font(8)
        bbox = draw.textbbox((0, 0), message, font=msg_font)
        text_width = bbox[2] - bbox[0]

        x = (width - text_width) // 2
        y = height * 2 // 3

        draw.text((x, y), message, font=msg_font, fill=Colors.GRAY_LIGHT.to_tuple())

    return image
