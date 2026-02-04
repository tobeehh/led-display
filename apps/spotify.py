"""Modern Spotify Now Playing for 64x64 LED display.

Features:
- Large album art (40x40)
- Dynamic color extraction
- Smooth progress bar
- Clean typography
"""

import io
import time
from typing import Any

import requests
from PIL import Image

from display.fonts import small_font, medium_font, SpotifyIcons
from display.graphics import Colors, Gradients, Drawing

from .base import BaseApp

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False


class SpotifyApp(BaseApp):
    """Displays Spotify now playing on 64x64."""

    name = "spotify"
    display_name = "Spotify"
    description = "Shows currently playing Spotify track"
    requires_credentials = True

    config_schema = {
        "client_id": {
            "type": "string",
            "label": "Client ID",
            "required": True,
        },
        "client_secret": {
            "type": "password",
            "label": "Client Secret",
            "required": True,
        },
        "refresh_token": {
            "type": "password",
            "label": "Refresh Token",
            "required": True,
        },
        "show_album_art": {
            "type": "bool",
            "label": "Show album art",
            "default": True,
        },
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._spotify: Any = None
        self._current_track: dict[str, Any] | None = None
        self._album_art: Image.Image | None = None
        self._dominant_color: tuple[int, int, int] = Colors.SPOTIFY_GREEN
        self._last_update = 0.0
        self._update_error: str | None = None
        self._scroll_offset = 0.0
        self._last_render_time = time.time()
        self._last_album_url = ""

    def setup(self) -> bool:
        """Set up Spotify authentication."""
        if not SPOTIPY_AVAILABLE:
            self._update_error = "spotipy missing"
            return False

        is_valid, error = self.validate_config()
        if not is_valid:
            self._update_error = error
            return False

        try:
            client_id = self._config.get("client_id", "")
            client_secret = self._config.get("client_secret", "")
            refresh_token = self._config.get("refresh_token", "")

            auth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost:8888/callback",
                scope="user-read-currently-playing user-read-playback-state",
            )

            token_info = auth.refresh_access_token(refresh_token)
            self._spotify = spotipy.Spotify(auth=token_info["access_token"])
            self._update_error = None
            self.update()
            return True

        except Exception:
            self._update_error = "Auth failed"
            return False

    def update(self) -> None:
        """Fetch currently playing track."""
        if not self._spotify:
            return

        try:
            playback = self._spotify.current_playback()

            if playback and playback.get("is_playing"):
                track = playback.get("item", {})
                progress = playback.get("progress_ms", 0)
                duration = track.get("duration_ms", 1)

                self._current_track = {
                    "name": track.get("name", "Unknown"),
                    "artist": ", ".join(a.get("name", "") for a in track.get("artists", [])),
                    "album": track.get("album", {}).get("name", ""),
                    "progress": progress / duration if duration > 0 else 0,
                    "progress_ms": progress,
                    "duration_ms": duration,
                    "is_playing": True,
                }

                if self._config.get("show_album_art", True):
                    images = track.get("album", {}).get("images", [])
                    if images:
                        url = images[-1].get("url", "")  # Smallest
                        if url != self._last_album_url:
                            self._fetch_album_art(url)
                            self._last_album_url = url
            else:
                self._current_track = {
                    "name": "Not playing",
                    "artist": "",
                    "is_playing": False,
                }
                self._album_art = None
                self._dominant_color = Colors.SPOTIFY_GREEN

            self._update_error = None
            self._last_update = time.time()

        except Exception:
            self._update_error = "API error"

    def _fetch_album_art(self, url: str) -> None:
        """Fetch album art and extract dominant color."""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            self._album_art = img.resize((40, 40), Image.Resampling.LANCZOS)
            self._dominant_color = self._extract_color(img)
        except Exception:
            self._album_art = None
            self._dominant_color = Colors.SPOTIFY_GREEN

    def _extract_color(self, img: Image.Image) -> tuple[int, int, int]:
        """Extract vibrant color from image."""
        small = img.resize((16, 16), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())

        best = Colors.SPOTIFY_GREEN
        best_score = 0

        for r, g, b in pixels:
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            if max_c == 0:
                continue

            sat = (max_c - min_c) / max_c
            bright = max_c / 255
            score = sat * 0.7 + bright * 0.3

            if score > best_score and bright > 0.2 and sat > 0.2:
                best_score = score
                best = (r, g, b)

        # Ensure brightness
        r, g, b = best
        if max(r, g, b) < 100:
            f = 100 / max(1, max(r, g, b))
            best = (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))

        return best

    def get_update_interval(self) -> float:
        return 3.0

    def _format_time(self, ms: int) -> str:
        secs = ms // 1000
        return f"{secs // 60}:{secs % 60:02d}"

    def render(self, width: int, height: int) -> Image.Image:
        """Render Spotify for 64x64."""
        image = Image.new("RGB", (width, height), (0, 0, 0))

        if self._update_error:
            Gradients.vertical(image, (25, 35, 25), (12, 18, 12))
            small_font.render_text_centered(image, "Spotify", 12, Colors.SPOTIFY_GREEN)
            small_font.render_text_centered(image, self._update_error, 28, (200, 100, 100))
            small_font.render_text_centered(image, "Check config", 44, (100, 100, 100))
            return image

        if not self._current_track:
            Gradients.vertical(image, (20, 30, 20), (10, 15, 10))
            SpotifyIcons.render_note(image, 25, 18)
            small_font.render_text_centered(image, "Loading...", 42, Colors.SPOTIFY_GREEN)
            return image

        accent = self._dominant_color
        is_playing = self._current_track.get("is_playing", False)

        # Background
        bg_top = Colors.dim(accent, 0.12)
        Gradients.vertical(image, bg_top, (0, 0, 0))

        if is_playing and self._config.get("show_album_art", True) and self._album_art:
            # === Layout with album art (40x40) ===

            # Album art centered at top
            art_size = 40
            art_x = (width - art_size) // 2
            art_y = 2

            art = self._album_art.resize((art_size, art_size), Image.Resampling.LANCZOS)
            image.paste(art, (art_x, art_y))

            # Subtle border
            Drawing.rect(image, art_x - 1, art_y - 1, art_size + 2, art_size + 2,
                        Colors.dim(accent, 0.3), filled=False)

            # Track name below art (scrolling if needed)
            track_name = self._current_track.get("name", "")
            name_y = 46
            name_width = small_font.get_text_width(track_name)

            if name_width > width - 4:
                # Scroll
                now = time.time()
                delta = now - self._last_render_time
                self._last_render_time = now
                self._scroll_offset += 30 * delta
                if self._scroll_offset > name_width + width:
                    self._scroll_offset = 0
                x = int(width - self._scroll_offset)
                small_font.render_text(image, track_name, x, name_y, Colors.WHITE)
            else:
                small_font.render_text_centered(image, track_name[:14], name_y, Colors.WHITE)

            # Progress bar at bottom
            progress = self._current_track.get("progress", 0)
            bar_y = 57
            Drawing.progress_bar(image, 4, bar_y, width - 8, 4, progress,
                                fg_color=accent, bg_color=Colors.dim(accent, 0.2), rounded=True)

            # Spotify dot indicator
            Drawing.circle(image, width - 4, 4, 2, Colors.SPOTIFY_GREEN, filled=True)

        elif is_playing:
            # === Layout without album art ===
            SpotifyIcons.render_play(image, 4, 8)

            # Track info
            track_name = self._current_track.get("name", "")[:16]
            artist = self._current_track.get("artist", "")[:16]

            small_font.render_text(image, track_name, 24, 8, Colors.WHITE)
            small_font.render_text(image, artist, 24, 20, Colors.dim(Colors.WHITE, 0.6))

            # Progress
            progress = self._current_track.get("progress", 0)
            Drawing.progress_bar(image, 4, 36, width - 8, 5, progress,
                                fg_color=accent, bg_color=Colors.dim(accent, 0.2), rounded=True)

            # Time
            progress_ms = self._current_track.get("progress_ms", 0)
            duration_ms = self._current_track.get("duration_ms", 1)
            time_str = f"{self._format_time(progress_ms)}/{self._format_time(duration_ms)}"
            small_font.render_text_centered(image, time_str, 48, Colors.dim(accent, 0.6))

        else:
            # Paused
            SpotifyIcons.render_pause(image, (width - 16) // 2, 18)
            small_font.render_text_centered(image, "Paused", 42, Colors.dim(Colors.WHITE, 0.5))

        return image

    def get_render_interval(self) -> float:
        if self._current_track and self._current_track.get("is_playing"):
            return 0.1
        return 1.0
