"""Modern weather application for 64x64 LED display.

Features:
- Large 24x24 pixel art weather icons
- Dynamic color scheme based on conditions
- Clean layout optimized for 64x64
- Temperature with feels-like
"""

import time
from typing import Any

import requests
from PIL import Image

from display.fonts import small_font, medium_font, WeatherIcons
from display.graphics import Colors, Gradients, Drawing

from .base import BaseApp


class WeatherApp(BaseApp):
    """Displays current weather with modern aesthetic on 64x64."""

    name = "weather"
    display_name = "Weather"
    description = "Shows current weather from OpenWeatherMap"
    requires_credentials = True

    config_schema = {
        "api_key": {
            "type": "password",
            "label": "OpenWeatherMap API Key",
            "required": True,
        },
        "city": {
            "type": "string",
            "label": "City name",
            "default": "Berlin",
            "required": True,
        },
        "units": {
            "type": "select",
            "label": "Units",
            "options": [
                {"value": "metric", "label": "Celsius"},
                {"value": "imperial", "label": "Fahrenheit"},
            ],
            "default": "metric",
        },
        "update_interval": {
            "type": "int",
            "label": "Update interval (seconds)",
            "default": 600,
            "min": 60,
            "max": 3600,
        },
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._weather_data: dict[str, Any] | None = None
        self._last_update = 0.0
        self._update_error: str | None = None

    def setup(self) -> bool:
        """Set up the weather app."""
        is_valid, error = self.validate_config()
        if not is_valid:
            self._update_error = error
            return False
        self.update()
        return True

    def update(self) -> None:
        """Fetch weather data from OpenWeatherMap."""
        api_key = self._config.get("api_key", "")
        city = self._config.get("city", "Berlin")
        units = self._config.get("units", "metric")

        if not api_key or not city:
            self._update_error = "Missing config"
            return

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": api_key, "units": units}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            self._weather_data = {
                "temp": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "city": data["name"],
            }
            self._update_error = None
            self._last_update = time.time()

        except requests.RequestException:
            self._update_error = "Network error"
        except (KeyError, ValueError):
            self._update_error = "Data error"

    def get_update_interval(self) -> float:
        return float(self._config.get("update_interval", 600))

    def _get_condition_colors(self, condition: str) -> tuple:
        """Get colors based on weather condition."""
        c = condition.lower()
        if "thunder" in c or "storm" in c:
            return ((40, 35, 60), (20, 18, 35), (150, 120, 255))
        elif "rain" in c or "drizzle" in c:
            return ((35, 45, 65), (18, 25, 40), (100, 160, 255))
        elif "snow" in c:
            return ((55, 60, 75), (35, 40, 55), (200, 220, 255))
        elif "cloud" in c:
            return ((45, 50, 60), (25, 30, 40), (180, 190, 210))
        elif "clear" in c:
            return ((45, 55, 90), (20, 28, 55), (255, 210, 100))
        elif "fog" in c or "mist" in c:
            return ((50, 55, 60), (30, 35, 40), (160, 170, 180))
        else:
            return ((35, 45, 65), (18, 25, 40), (255, 255, 255))

    def render(self, width: int, height: int) -> Image.Image:
        """Render weather for 64x64."""
        image = Image.new("RGB", (width, height), (0, 0, 0))

        if self._update_error:
            Gradients.vertical(image, (40, 25, 25), (20, 12, 12))
            small_font.render_text_centered(image, "Weather", 12, (255, 120, 120))
            small_font.render_text_centered(image, self._update_error, 28, (200, 100, 100))
            small_font.render_text_centered(image, "Check config", 44, (120, 80, 80))
            return image

        if not self._weather_data:
            Gradients.vertical(image, (30, 35, 50), (15, 18, 30))
            small_font.render_text_centered(image, "Loading...", 28, (100, 130, 180))
            return image

        condition = self._weather_data.get("condition", "Clear")
        temp = self._weather_data.get("temp", 0)
        feels_like = self._weather_data.get("feels_like", 0)
        city = self._weather_data.get("city", "")
        description = self._weather_data.get("description", "").title()
        humidity = self._weather_data.get("humidity", 0)
        units = self._config.get("units", "metric")
        unit = "C" if units == "metric" else "F"

        bg_top, bg_bottom, accent = self._get_condition_colors(condition)
        Gradients.vertical(image, bg_top, bg_bottom)

        # === 64x64 Layout ===

        # Weather icon (24x24) - top left area
        WeatherIcons.render(image, condition, 2, 2)

        # Temperature - large, right of icon
        temp_str = f"{temp}°"
        temp_x = 30
        temp_y = 4
        medium_font.render_text(image, temp_str, temp_x, temp_y, accent)

        # Unit indicator
        temp_width = medium_font.get_text_width(temp_str)
        small_font.render_text(image, unit, temp_x + temp_width + 1, temp_y + 3, Colors.dim(accent, 0.6))

        # Feels like - smaller, below temperature
        feels_str = f"Feels {feels_like}°"
        small_font.render_text(image, feels_str, temp_x, temp_y + 14, Colors.dim(Colors.WHITE, 0.5))

        # Description - center area
        desc_y = 32
        desc_short = description[:14]
        small_font.render_text_centered(image, desc_short, desc_y, Colors.dim(Colors.WHITE, 0.7))

        # Separator
        Drawing.line(image, 6, 42, width - 6, 42, Colors.dim(accent, 0.2))

        # City name - bottom left
        city_short = city[:10]
        small_font.render_text(image, city_short, 4, 48, Colors.dim(accent, 0.7))

        # Humidity - bottom right
        humidity_str = f"{humidity}%"
        humidity_width = small_font.get_text_width(humidity_str)
        small_font.render_text(image, humidity_str, width - humidity_width - 4, 48, Colors.dim(Colors.BLUE, 0.7))

        # Small humidity icon
        drop_x = width - humidity_width - 11
        pixels = image.load()
        drop_color = Colors.dim(Colors.BLUE, 0.5)
        for dy, row in enumerate(["...", ".X.", ".X.", "XXX", ".X."]):
            for dx, c in enumerate(row):
                if c == 'X':
                    px, py = drop_x + dx, 48 + dy
                    if 0 <= px < width and 0 <= py < height:
                        pixels[px, py] = drop_color

        return image

    def get_render_interval(self) -> float:
        return 5.0
