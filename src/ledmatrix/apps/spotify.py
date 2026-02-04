"""Spotify Now Playing application.

Displays currently playing track with album art.
"""

import io
import logging
import threading
from dataclasses import dataclass
from typing import Any

import httpx
from PIL import Image, ImageDraw

from ..display.graphics import Colors
from ..display.renderer import get_default_font, resize_for_display
from .base import BaseApp, AppMetadata, ConfigFieldSchema, RenderResult

logger = logging.getLogger(__name__)


@dataclass
class NowPlaying:
    """Currently playing track data."""

    track: str
    artist: str
    album: str
    album_art_url: str | None
    is_playing: bool
    progress_ms: int
    duration_ms: int


class SpotifyApp(BaseApp):
    """Spotify Now Playing application.

    Shows currently playing track with scrolling text and album art.
    Requires Spotify API credentials.
    """

    @property
    def metadata(self) -> AppMetadata:
        return AppMetadata(
            name="spotify",
            display_name="Spotify",
            description="Now playing from Spotify",
            version="1.0.0",
            requires_network=True,
            requires_credentials=True,
        )

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        return {
            "client_id": ConfigFieldSchema(
                type="string",
                label="Client ID",
                description="Spotify API client ID",
                required=True,
            ),
            "client_secret": ConfigFieldSchema(
                type="password",
                label="Client Secret",
                description="Spotify API client secret",
                required=True,
            ),
            "refresh_token": ConfigFieldSchema(
                type="password",
                label="Refresh Token",
                description="Spotify refresh token",
                required=True,
            ),
            "show_album_art": ConfigFieldSchema(
                type="bool",
                label="Show Album Art",
                description="Display album artwork",
                default=True,
            ),
        }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._now_playing: NowPlaying | None = None
        self._album_art: Image.Image | None = None
        self._data_lock = threading.Lock()
        self._access_token: str | None = None
        self._token_expires: float = 0
        self._scroll_offset = 0
        self._error_message: str | None = None

    def get_update_interval(self) -> float:
        """Update every 5 seconds to track progress."""
        return 5.0

    def get_render_interval(self) -> float:
        """Render at 5 FPS for smooth scrolling."""
        return 0.2

    def _on_activate(self) -> None:
        """Validate credentials on activation."""
        is_valid, error = self.validate_config()
        if not is_valid:
            raise ValueError(error)

        required = ["client_id", "client_secret", "refresh_token"]
        for field in required:
            if not self._config.get(field):
                raise ValueError(f"{field} is required")

    def update_data(self) -> None:
        """Fetch currently playing track."""
        import asyncio

        try:
            asyncio.run(self._fetch_now_playing())
            self._error_message = None
        except Exception as e:
            logger.error("Spotify update failed: %s", e)
            self._error_message = str(e)

    async def _refresh_access_token(self) -> None:
        """Refresh the Spotify access token."""
        import base64
        import time

        client_id = self._config.get("client_id", "")
        client_secret = self._config.get("client_secret", "")
        refresh_token = self._config.get("refresh_token", "")

        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://accounts.spotify.com/api/token",
                headers={"Authorization": f"Basic {auth}"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )

            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 3600) - 60

    async def _fetch_now_playing(self) -> None:
        """Fetch currently playing track from Spotify."""
        import time

        # Refresh token if needed
        if not self._access_token or time.time() >= self._token_expires:
            await self._refresh_access_token()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.spotify.com/v1/me/player/currently-playing",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )

            if response.status_code == 204:
                # Nothing playing
                with self._data_lock:
                    self._now_playing = None
                    self._album_art = None
                return

            response.raise_for_status()
            data = response.json()

            if not data or data.get("currently_playing_type") != "track":
                with self._data_lock:
                    self._now_playing = None
                return

            track = data["item"]

            # Get album art URL
            images = track.get("album", {}).get("images", [])
            art_url = images[-1]["url"] if images else None  # Smallest image

            with self._data_lock:
                old_art_url = self._now_playing.album_art_url if self._now_playing else None

                self._now_playing = NowPlaying(
                    track=track["name"],
                    artist=", ".join(a["name"] for a in track["artists"]),
                    album=track["album"]["name"],
                    album_art_url=art_url,
                    is_playing=data.get("is_playing", False),
                    progress_ms=data.get("progress_ms", 0),
                    duration_ms=track.get("duration_ms", 0),
                )

                # Fetch album art if changed
                if art_url and art_url != old_art_url:
                    await self._fetch_album_art(art_url)

            logger.debug("Now playing: %s - %s", self._now_playing.artist, self._now_playing.track)

    async def _fetch_album_art(self, url: str) -> None:
        """Fetch and resize album art."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                image = Image.open(io.BytesIO(response.content))
                image = image.convert("RGB")

                # Resize to fit display (square, left side)
                image = image.resize((30, 30), Image.Resampling.LANCZOS)

                with self._data_lock:
                    self._album_art = image

        except Exception as e:
            logger.warning("Failed to fetch album art: %s", e)

    def render(self, width: int, height: int) -> RenderResult:
        """Render now playing display."""
        image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())
        draw = ImageDraw.Draw(image)

        with self._data_lock:
            if self._error_message:
                return self._render_error(image, draw, width, height)

            if not self._now_playing:
                return self._render_idle(image, draw, width, height)

            return self._render_playing(image, draw, width, height)

    def _render_playing(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
    ) -> RenderResult:
        """Render now playing state."""
        data = self._now_playing
        show_art = self._config.get("show_album_art", True)

        # Album art
        text_x = 3
        if show_art and self._album_art:
            image.paste(self._album_art, (2, 2))
            text_x = 35

        # Track name (scrolling if long)
        track_font = get_default_font(10)
        track = data.track

        # Simple scrolling
        max_chars = (width - text_x) // 6
        if len(track) > max_chars:
            self._scroll_offset = (self._scroll_offset + 1) % (len(track) + 5)
            display_track = (track + "     " + track)[self._scroll_offset : self._scroll_offset + max_chars]
        else:
            display_track = track

        draw.text((text_x, 5), display_track, font=track_font, fill=Colors.WHITE.to_tuple())

        # Artist
        artist_font = get_default_font(8)
        artist = data.artist[:15]
        draw.text((text_x, 20), artist, font=artist_font, fill=Colors.GRAY_LIGHT.to_tuple())

        # Progress bar
        if data.duration_ms > 0:
            progress = data.progress_ms / data.duration_ms
            bar_width = width - text_x - 5
            bar_y = 35

            # Background
            draw.rectangle(
                [(text_x, bar_y), (text_x + bar_width, bar_y + 3)],
                fill=Colors.GRAY_DARK.to_tuple(),
            )

            # Progress
            progress_width = int(bar_width * progress)
            if progress_width > 0:
                draw.rectangle(
                    [(text_x, bar_y), (text_x + progress_width, bar_y + 3)],
                    fill=Colors.CYAN.to_tuple(),
                )

        # Playing indicator
        if data.is_playing:
            # Play icon
            draw.polygon(
                [(width - 12, height - 12), (width - 12, height - 4), (width - 4, height - 8)],
                fill=Colors.CYAN.to_tuple(),
            )
        else:
            # Pause icon
            draw.rectangle(
                [(width - 12, height - 12), (width - 10, height - 4)],
                fill=Colors.GRAY.to_tuple(),
            )
            draw.rectangle(
                [(width - 7, height - 12), (width - 5, height - 4)],
                fill=Colors.GRAY.to_tuple(),
            )

        return RenderResult(image=image, next_render_in=0.2 if len(data.track) > 10 else 1.0)

    def _render_idle(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
    ) -> RenderResult:
        """Render idle state (nothing playing)."""
        font = get_default_font(10)

        # Spotify icon (simplified)
        draw.ellipse([(width // 2 - 10, 10), (width // 2 + 10, 30)], fill=Colors.SUCCESS.to_tuple())

        text = "Not Playing"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 40), text, font=font, fill=Colors.GRAY.to_tuple())

        return RenderResult(image=image, next_render_in=2.0)

    def _render_error(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
    ) -> RenderResult:
        """Render error state."""
        font = get_default_font(10)
        draw.text((5, 10), "Spotify", font=font, fill=Colors.ERROR.to_tuple())

        msg_font = get_default_font(7)
        msg = self._error_message[:20] if self._error_message else "Error"
        draw.text((5, 30), msg, font=msg_font, fill=Colors.GRAY.to_tuple())

        return RenderResult(image=image, next_render_in=5.0)
