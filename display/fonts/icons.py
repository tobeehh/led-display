"""Pixel art icons for LED display - optimized for 64x64."""

from PIL import Image


class IconRenderer:
    """Base class for rendering pixel art icons."""

    @staticmethod
    def render_bitmap(
        image: Image.Image,
        bitmap: list[str],
        x: int,
        y: int,
        color_map: dict[str, tuple[int, int, int]],
    ) -> None:
        """Render a bitmap icon to an image."""
        pixels = image.load()

        for row_idx, row in enumerate(bitmap):
            for col_idx, pixel in enumerate(row):
                if pixel in color_map and pixel != '.':
                    px = x + col_idx
                    py = y + row_idx
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color_map[pixel]


class WeatherIcons:
    """Weather condition pixel art icons (24x24 for 64x64 display)."""

    YELLOW = (255, 220, 50)
    ORANGE = (255, 180, 80)
    WHITE = (255, 255, 255)
    LIGHT_GRAY = (200, 200, 200)
    GRAY = (140, 140, 140)
    DARK_GRAY = (80, 80, 80)
    BLUE = (100, 180, 255)
    DARK_BLUE = (60, 120, 200)
    LIGHT_BLUE = (180, 220, 255)

    # Sun icon 24x24
    SUN = [
        "..........YY..........",
        "..........YY..........",
        "....Y.....YY.....Y....",
        ".....Y....YY....Y.....",
        "......Y..YYYY..Y......",
        ".......YYYYYYYY.......",
        "...YYYOOOOOOOOYYY.....",
        "...YYOOOOOOOOOOYYY....",
        "..YYYOOOOOOOOOOYYY....",
        "YYYYOOOOOOOOOOOOYYYYY.",
        "YYYYOOOOOOOOOOOOYYYYY.",
        "YYYYOOOOOOOOOOOOYYYYY.",
        "YYYYOOOOOOOOOOOOYYYYY.",
        "..YYYOOOOOOOOOOYYY....",
        "...YYOOOOOOOOOOYYY....",
        "...YYYOOOOOOOOYYY.....",
        ".......YYYYYYYY.......",
        "......Y..YYYY..Y......",
        ".....Y....YY....Y.....",
        "....Y.....YY.....Y....",
        "..........YY..........",
        "..........YY..........",
        "........................",
        "........................",
    ]

    # Cloud icon 24x24
    CLOUD = [
        "........................",
        "........................",
        "........WWWWWW..........",
        "......WWWWWWWWWW........",
        ".....WWWWWWWWWWWW.......",
        "....WWWWWWWWWWWWWW......",
        "...WWWWWWWWWWWWWWW......",
        "..WWWWWWWWWWWWWWWWW.....",
        ".WWWWWWWWWWWWWWWWWW.....",
        ".WWWWWWWWWWWWWWWWWWW....",
        "WWWWWWWWWWWWWWWWWWWWW...",
        "WWWWWWWWWWWWWWWWWWWWWW..",
        "WWWWWWWWWWWWWWWWWWWWWWW.",
        "WWWWWWWWWWWWWWWWWWWWWWW.",
        ".WWWWWWWWWWWWWWWWWWWWW..",
        "..WWWWWWWWWWWWWWWWWWW...",
        "...WWWWWWWWWWWWWWWWW....",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
    ]

    # Partly cloudy 24x24
    PARTLY_CLOUDY = [
        "....YY..................",
        ".....YY....YY...........",
        "......YYYYYY............",
        "..YYYOOOOOYY............",
        "..YYOOOOOOOYYWWW........",
        ".YYYOOOOOOOOWWWWWW......",
        ".YYOOOOOOOOWWWWWWWW.....",
        "YYYOOOOOOWWWWWWWWWWW....",
        ".YYOOOOOWWWWWWWWWWWWW...",
        ".YYYOOOWWWWWWWWWWWWWWW..",
        "...YYWWWWWWWWWWWWWWWWWW.",
        "....WWWWWWWWWWWWWWWWWWWW",
        "...WWWWWWWWWWWWWWWWWWWWW",
        "...WWWWWWWWWWWWWWWWWWWW.",
        "....WWWWWWWWWWWWWWWWWW..",
        ".....WWWWWWWWWWWWWWWW...",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
    ]

    # Rain icon 24x24
    RAIN = [
        "........................",
        "........GGGGGG..........",
        "......GGGGGGGGGG........",
        ".....GGGGGGGGGGGG.......",
        "....GGGGGGGGGGGGGG......",
        "...GGGGGGGGGGGGGGGG.....",
        "..GGGGGGGGGGGGGGGGGG....",
        ".GGGGGGGGGGGGGGGGGGGG...",
        "GGGGGGGGGGGGGGGGGGGGGG..",
        ".GGGGGGGGGGGGGGGGGGGG...",
        "..GGGGGGGGGGGGGGGGGG....",
        "....B...B...B...B.......",
        "....B...B...B...B.......",
        "...B...B...B...B........",
        "...B...B...B...B........",
        "..B...B...B...B.........",
        "..B...B...B...B.........",
        ".B...B...B...B..........",
        ".B...B...B...B..........",
        "B...B...B...B...........",
        "........................",
        "........................",
        "........................",
        "........................",
    ]

    # Thunderstorm 24x24
    THUNDER = [
        "........GGGGGG..........",
        "......GGGGGGGGGG........",
        ".....GGGGGGGGGGGG.......",
        "....GGGGGGGGGGGGGG......",
        "...GGGGGGGGGGGGGGGG.....",
        "..GGGGGGGGGGGGGGGGGG....",
        ".GGGGGGGGGGGGGGGGGGGG...",
        "GGGGGGGGGGGGGGGGGGGGGG..",
        ".GGGGGGGGGGGGGGGGGGGG...",
        "......YYYY..............",
        ".....YYYY...............",
        "....YYYY................",
        "...YYYYYYYY.............",
        "......YYYY..............",
        ".....YYYY...............",
        "....YYYY................",
        "...YYY..................",
        "..YY....................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
    ]

    # Snow icon 24x24
    SNOW = [
        "........................",
        "........LLLLLL..........",
        "......LLLLLLLLLL........",
        ".....LLLLLLLLLLLL.......",
        "....LLLLLLLLLLLLLL......",
        "...LLLLLLLLLLLLLLLL.....",
        "..LLLLLLLLLLLLLLLLLL....",
        ".LLLLLLLLLLLLLLLLLLLL...",
        "LLLLLLLLLLLLLLLLLLLLLL..",
        ".LLLLLLLLLLLLLLLLLLLL...",
        "..LLLLLLLLLLLLLLLLLL....",
        "....W...W...W...W.......",
        "...WWW.WWW.WWW.WWW......",
        "....W...W...W...W.......",
        "..W...W...W...W.........",
        ".WWW.WWW.WWW.WWW........",
        "..W...W...W...W.........",
        "....W...W...W...W.......",
        "...WWW.WWW.WWW.WWW......",
        "....W...W...W...W.......",
        "........................",
        "........................",
        "........................",
        "........................",
    ]

    # Fog/Mist 24x24
    FOG = [
        "........................",
        "........................",
        "........................",
        "........................",
        "GGGGGGGGGGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGGGGGGGGGG",
        "........................",
        "..GGGGGGGGGGGGGGGGGGGG..",
        "..GGGGGGGGGGGGGGGGGGGG..",
        "........................",
        "GGGGGGGGGGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGGGGGGGGGG",
        "........................",
        "..GGGGGGGGGGGGGGGGGGGG..",
        "..GGGGGGGGGGGGGGGGGGGG..",
        "........................",
        "GGGGGGGGGGGGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGGGGGGGGGG",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
    ]

    # Moon 24x24
    MOON = [
        "........................",
        ".......LLLLLLLL.........",
        ".....LLLLLLLLLL.........",
        "....LLLLLLLLLL..........",
        "...LLLLLLLLLL...........",
        "..LLLLLLLLL.............",
        "..LLLLLLLL..............",
        ".LLLLLLLL...............",
        ".LLLLLLLL...............",
        ".LLLLLLL................",
        ".LLLLLLL................",
        ".LLLLLLL................",
        ".LLLLLLL................",
        ".LLLLLLLL...............",
        ".LLLLLLLL...............",
        "..LLLLLLLL..............",
        "..LLLLLLLLL.............",
        "...LLLLLLLLLL...........",
        "....LLLLLLLLLL..........",
        ".....LLLLLLLLLL.........",
        ".......LLLLLLLL.........",
        "........................",
        "........................",
        "........................",
    ]

    COLOR_MAP = {
        'Y': YELLOW,
        'O': ORANGE,
        'W': WHITE,
        'G': GRAY,
        'B': BLUE,
        'D': DARK_BLUE,
        'L': LIGHT_BLUE,
        '.': (0, 0, 0),
    }

    @classmethod
    def get_icon(cls, condition: str) -> tuple[list[str], dict]:
        """Get icon bitmap and color map for a weather condition."""
        condition = condition.lower()

        if 'thunder' in condition or 'storm' in condition:
            return cls.THUNDER, cls.COLOR_MAP
        elif 'rain' in condition or 'drizzle' in condition or 'shower' in condition:
            return cls.RAIN, cls.COLOR_MAP
        elif 'snow' in condition or 'sleet' in condition or 'ice' in condition:
            return cls.SNOW, cls.COLOR_MAP
        elif 'fog' in condition or 'mist' in condition or 'haze' in condition:
            return cls.FOG, cls.COLOR_MAP
        elif 'cloud' in condition or 'overcast' in condition:
            if 'partly' in condition or 'few' in condition or 'scattered' in condition:
                return cls.PARTLY_CLOUDY, cls.COLOR_MAP
            return cls.CLOUD, cls.COLOR_MAP
        elif 'clear' in condition or 'sunny' in condition:
            return cls.SUN, cls.COLOR_MAP
        elif 'night' in condition or 'moon' in condition:
            return cls.MOON, cls.COLOR_MAP
        else:
            return cls.SUN, cls.COLOR_MAP

    @classmethod
    def render(cls, image: Image.Image, condition: str, x: int, y: int) -> None:
        """Render a weather icon to an image."""
        bitmap, color_map = cls.get_icon(condition)
        IconRenderer.render_bitmap(image, bitmap, x, y, color_map)


class SpotifyIcons:
    """Spotify-related pixel art icons (16x16)."""

    GREEN = (30, 215, 96)
    WHITE = (255, 255, 255)

    # Play icon 16x16
    PLAY = [
        "................",
        ".GGG............",
        ".GGGGG..........",
        ".GGGGGGG........",
        ".GGGGGGGGG......",
        ".GGGGGGGGGGG....",
        ".GGGGGGGGGGGGG..",
        ".GGGGGGGGGGGGGG.",
        ".GGGGGGGGGGGGGG.",
        ".GGGGGGGGGGGGG..",
        ".GGGGGGGGGGG....",
        ".GGGGGGGGG......",
        ".GGGGGGG........",
        ".GGGGG..........",
        ".GGG............",
        "................",
    ]

    # Pause icon 16x16
    PAUSE = [
        "................",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        ".GGGG....GGGG...",
        "................",
        "................",
    ]

    # Music note 14x16
    NOTE = [
        ".....WWWWWWWWW",
        ".....WWWWWWWWW",
        ".....WWWWWWWWW",
        ".....W.......W",
        ".....W.......W",
        ".....W.......W",
        ".....W.......W",
        ".....W.......W",
        ".....W.......W",
        "..WWWW....WWWW",
        ".WWWWW...WWWWW",
        "WWWWWW..WWWWWW",
        "WWWWWW..WWWWWW",
        ".WWWW....WWWW.",
        "..............",
        "..............",
    ]

    COLOR_MAP = {
        'G': GREEN,
        'W': WHITE,
        '.': (0, 0, 0),
    }

    @classmethod
    def render_play(cls, image: Image.Image, x: int, y: int) -> None:
        """Render play icon."""
        IconRenderer.render_bitmap(image, cls.PLAY, x, y, cls.COLOR_MAP)

    @classmethod
    def render_pause(cls, image: Image.Image, x: int, y: int) -> None:
        """Render pause icon."""
        IconRenderer.render_bitmap(image, cls.PAUSE, x, y, cls.COLOR_MAP)

    @classmethod
    def render_note(cls, image: Image.Image, x: int, y: int) -> None:
        """Render music note icon."""
        IconRenderer.render_bitmap(image, cls.NOTE, x, y, cls.COLOR_MAP)


class UIIcons:
    """General UI icons."""

    WHITE = (255, 255, 255)
    GREEN = (100, 255, 100)
    RED = (255, 100, 100)
    BLUE = (100, 150, 255)

    # WiFi icon 16x12
    WIFI = [
        "....WWWWWWWW....",
        "..WWWWWWWWWWWW..",
        ".WW..........WW.",
        "WW....WWWW....WW",
        "....WWWWWWWW....",
        "...WW......WW...",
        "......WWWW......",
        ".....WWWWWW.....",
        ".......WW.......",
        "......WWWW......",
        ".......WW.......",
        ".......WW.......",
    ]

    COLOR_MAP = {
        'W': WHITE,
        'G': GREEN,
        'R': RED,
        'B': BLUE,
        '.': (0, 0, 0),
    }

    @classmethod
    def render_wifi(cls, image: Image.Image, x: int, y: int, connected: bool = True) -> None:
        """Render WiFi icon."""
        color_map = cls.COLOR_MAP.copy()
        if not connected:
            color_map['W'] = cls.RED
        IconRenderer.render_bitmap(image, cls.WIFI, x, y, color_map)
