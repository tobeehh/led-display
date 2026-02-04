"""Weather display application.

Shows current weather conditions from OpenWeatherMap API.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any

import httpx
from PIL import Image, ImageDraw

from ..core.retry import async_retry, RetryConfig
from ..core.errors import APIError
from ..display.graphics import Color, Colors
from ..display.renderer import get_default_font
from .base import BaseApp, AppMetadata, ConfigFieldSchema, RenderResult

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather data from API."""

    temperature: float
    feels_like: float
    humidity: int
    description: str
    icon: str
    city: str


# Weather icon mappings (simplified pixel art)
WEATHER_ICONS = {
    "01": "clear",  # Clear sky
    "02": "partly_cloudy",
    "03": "cloudy",
    "04": "cloudy",
    "09": "rain",
    "10": "rain",
    "11": "storm",
    "13": "snow",
    "50": "mist",
}


class WeatherApp(BaseApp):
    """Weather display application.

    Shows current temperature, conditions, and weather icon.
    Requires OpenWeatherMap API key.
    """

    API_URL = "https://api.openweathermap.org/data/2.5/weather"

    @property
    def metadata(self) -> AppMetadata:
        return AppMetadata(
            name="weather",
            display_name="Weather",
            description="Current weather conditions",
            version="1.0.0",
            requires_network=True,
            requires_credentials=True,
        )

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        return {
            "api_key": ConfigFieldSchema(
                type="password",
                label="API Key",
                description="OpenWeatherMap API key",
                required=True,
            ),
            "city": ConfigFieldSchema(
                type="string",
                label="City",
                description="City name (e.g., Berlin, London)",
                default="Berlin",
                required=True,
            ),
            "units": ConfigFieldSchema(
                type="select",
                label="Units",
                description="Temperature units",
                default="metric",
                options=[
                    {"value": "metric", "label": "Celsius"},
                    {"value": "imperial", "label": "Fahrenheit"},
                ],
            ),
            "update_interval": ConfigFieldSchema(
                type="int",
                label="Update Interval",
                description="Seconds between updates",
                default=600,
                min_value=60,
                max_value=3600,
            ),
        }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._weather_data: WeatherData | None = None
        self._data_lock = threading.Lock()
        self._error_message: str | None = None

    def get_update_interval(self) -> float:
        """Update weather data every 10 minutes by default."""
        return float(self._config.get("update_interval", 600))

    def _on_activate(self) -> None:
        """Validate config on activation."""
        is_valid, error = self.validate_config()
        if not is_valid:
            raise ValueError(error)

        if not self._config.get("api_key"):
            raise ValueError("API key is required")

    def update_data(self) -> None:
        """Fetch weather data from API."""
        import asyncio

        try:
            asyncio.run(self._fetch_weather())
            self._error_message = None
        except Exception as e:
            logger.error("Weather update failed: %s", e)
            self._error_message = str(e)

    @async_retry(RetryConfig(max_attempts=2, base_delay=5.0))
    async def _fetch_weather(self) -> None:
        """Fetch weather from OpenWeatherMap API."""
        api_key = self._config.get("api_key", "")
        city = self._config.get("city", "Berlin")
        units = self._config.get("units", "metric")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.API_URL,
                params={
                    "q": city,
                    "appid": api_key,
                    "units": units,
                },
            )

            if response.status_code == 401:
                raise APIError("Invalid API key")
            if response.status_code == 404:
                raise APIError(f"City not found: {city}")

            response.raise_for_status()
            data = response.json()

            with self._data_lock:
                self._weather_data = WeatherData(
                    temperature=data["main"]["temp"],
                    feels_like=data["main"]["feels_like"],
                    humidity=data["main"]["humidity"],
                    description=data["weather"][0]["description"].title(),
                    icon=data["weather"][0]["icon"][:2],
                    city=data["name"],
                )

            logger.info("Weather updated: %s, %.1f°", city, self._weather_data.temperature)

    def render(self, width: int, height: int) -> RenderResult:
        """Render weather display."""
        image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())
        draw = ImageDraw.Draw(image)

        with self._data_lock:
            if self._error_message:
                return self._render_error(image, draw, width, height)

            if not self._weather_data:
                return self._render_loading(image, draw, width, height)

            return self._render_weather(image, draw, width, height)

    def _render_weather(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
    ) -> RenderResult:
        """Render weather data."""
        data = self._weather_data
        units = self._config.get("units", "metric")
        unit_symbol = "°C" if units == "metric" else "°F"

        # Temperature (large)
        temp_str = f"{data.temperature:.0f}{unit_symbol}"
        temp_font = get_default_font(18)
        bbox = draw.textbbox((0, 0), temp_str, font=temp_font)
        temp_width = bbox[2] - bbox[0]
        x = (width - temp_width) // 2
        draw.text((x, 5), temp_str, font=temp_font, fill=Colors.WHITE.to_tuple())

        # Weather icon (simplified)
        icon_type = WEATHER_ICONS.get(data.icon, "cloudy")
        self._draw_weather_icon(image, icon_type, 5, 30, 20)

        # Description
        desc_font = get_default_font(8)
        desc = data.description[:12]  # Truncate
        bbox = draw.textbbox((0, 0), desc, font=desc_font)
        desc_width = bbox[2] - bbox[0]
        x = (width - desc_width) // 2
        draw.text((x, 35), desc, font=desc_font, fill=Colors.GRAY_LIGHT.to_tuple())

        # City
        city_font = get_default_font(7)
        city = data.city[:10]
        bbox = draw.textbbox((0, 0), city, font=city_font)
        city_width = bbox[2] - bbox[0]
        x = (width - city_width) // 2
        draw.text((x, 50), city, font=city_font, fill=Colors.CYAN.dim(0.5).to_tuple())

        return RenderResult(image=image, next_render_in=1.0)

    def _render_loading(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
    ) -> RenderResult:
        """Render loading state."""
        font = get_default_font(10)
        text = "Loading..."
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        y = (height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, font=font, fill=Colors.GRAY.to_tuple())

        return RenderResult(image=image, next_render_in=0.5)

    def _render_error(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
    ) -> RenderResult:
        """Render error state."""
        # Error title
        font = get_default_font(10)
        draw.text((5, 10), "Weather", font=font, fill=Colors.ERROR.to_tuple())

        # Error message
        msg_font = get_default_font(7)
        msg = self._error_message[:20] if self._error_message else "Error"
        draw.text((5, 30), msg, font=msg_font, fill=Colors.GRAY.to_tuple())

        return RenderResult(image=image, next_render_in=5.0)

    def _draw_weather_icon(
        self,
        image: Image.Image,
        icon_type: str,
        x: int,
        y: int,
        size: int,
    ) -> None:
        """Draw a simplified weather icon."""
        pixels = image.load()
        center_x = x + size // 2
        center_y = y + size // 2

        if icon_type == "clear":
            # Sun
            color = Colors.YELLOW.to_tuple()
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    if dx * dx + dy * dy <= 16:
                        px, py = center_x + dx, center_y + dy
                        if 0 <= px < image.width and 0 <= py < image.height:
                            pixels[px, py] = color

        elif icon_type in ("cloudy", "partly_cloudy"):
            # Cloud
            color = Colors.GRAY_LIGHT.to_tuple()
            for dx in range(-5, 6):
                for dy in range(-2, 3):
                    px, py = center_x + dx, center_y + dy
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color

        elif icon_type == "rain":
            # Cloud with rain
            color = Colors.GRAY.to_tuple()
            rain_color = Colors.CYAN.to_tuple()
            for dx in range(-5, 6):
                for dy in range(-3, 1):
                    px, py = center_x + dx, center_y + dy
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color
            # Rain drops
            for i in range(-3, 4, 2):
                px, py = center_x + i, center_y + 4
                if 0 <= px < image.width and 0 <= py < image.height:
                    pixels[px, py] = rain_color

        elif icon_type == "snow":
            # Snowflake
            color = Colors.WHITE.to_tuple()
            for i in range(-3, 4):
                px, py = center_x + i, center_y
                if 0 <= px < image.width and 0 <= py < image.height:
                    pixels[px, py] = color
                px, py = center_x, center_y + i
                if 0 <= px < image.width and 0 <= py < image.height:
                    pixels[px, py] = color
