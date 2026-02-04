"""Stock and cryptocurrency ticker application.

Displays live prices from Yahoo Finance with sparkline charts.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from ..display.graphics import Color, Colors, draw_sparkline
from ..display.renderer import get_default_font
from .base import BaseApp, AppMetadata, ConfigFieldSchema, RenderResult

logger = logging.getLogger(__name__)


@dataclass
class TickerData:
    """Stock/crypto ticker data."""

    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    currency: str
    history: list[float]


class StocksApp(BaseApp):
    """Stock and cryptocurrency display application.

    Shows live prices with change indicators and mini charts.
    Rotates through multiple tickers.
    """

    @property
    def metadata(self) -> AppMetadata:
        return AppMetadata(
            name="stocks",
            display_name="Stocks",
            description="Live stock and crypto prices",
            version="1.0.0",
            requires_network=True,
            requires_credentials=False,
        )

    @property
    def config_schema(self) -> dict[str, ConfigFieldSchema]:
        return {
            "tickers": ConfigFieldSchema(
                type="string",
                label="Tickers",
                description="Comma-separated symbols (e.g., AAPL,GOOGL,BTC-USD)",
                default="AAPL,GOOGL,BTC-USD,ETH-USD",
            ),
            "rotation_interval": ConfigFieldSchema(
                type="int",
                label="Rotation Interval",
                description="Seconds per ticker",
                default=10,
                min_value=3,
                max_value=60,
            ),
            "update_interval": ConfigFieldSchema(
                type="int",
                label="Update Interval",
                description="Seconds between data updates",
                default=300,
                min_value=60,
                max_value=3600,
            ),
            "display_mode": ConfigFieldSchema(
                type="select",
                label="Display Mode",
                description="What to show",
                default="price",
                options=[
                    {"value": "price", "label": "Price Only"},
                    {"value": "chart", "label": "With Chart"},
                ],
            ),
        }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._ticker_data: dict[str, TickerData] = {}
        self._data_lock = threading.Lock()
        self._current_index = 0
        self._last_rotation = 0.0
        self._error_message: str | None = None

    def get_update_interval(self) -> float:
        """Update prices every 5 minutes by default."""
        return float(self._config.get("update_interval", 300))

    def get_render_interval(self) -> float:
        """Render at 1 FPS."""
        return 1.0

    def update_data(self) -> None:
        """Fetch ticker data from Yahoo Finance."""
        try:
            import yfinance as yf

            tickers_str = self._config.get("tickers", "AAPL")
            symbols = [s.strip().upper() for s in tickers_str.split(",") if s.strip()]

            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    # Get current price
                    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                    prev_close = info.get("previousClose", price)
                    change = price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0

                    # Get history for sparkline
                    hist = ticker.history(period="5d", interval="1h")
                    history = list(hist["Close"].dropna().values[-24:]) if len(hist) > 0 else []

                    # Get name
                    name = info.get("shortName", symbol)[:15]

                    with self._data_lock:
                        self._ticker_data[symbol] = TickerData(
                            symbol=symbol,
                            name=name,
                            price=price,
                            change=change,
                            change_percent=change_pct,
                            currency=info.get("currency", "USD"),
                            history=history,
                        )

                    logger.debug("Updated %s: %.2f", symbol, price)

                except Exception as e:
                    logger.warning("Failed to fetch %s: %s", symbol, e)

            self._error_message = None
            logger.info("Updated %d tickers", len(self._ticker_data))

        except ImportError:
            self._error_message = "yfinance not installed"
            logger.error("yfinance not installed")
        except Exception as e:
            self._error_message = str(e)
            logger.error("Stocks update failed: %s", e)

    def render(self, width: int, height: int) -> RenderResult:
        """Render stock ticker display."""
        import time

        image = Image.new("RGB", (width, height), Colors.BLACK.to_tuple())
        draw = ImageDraw.Draw(image)

        # Handle rotation
        now = time.time()
        rotation_interval = self._config.get("rotation_interval", 10)

        if now - self._last_rotation >= rotation_interval:
            self._current_index += 1
            self._last_rotation = now

        with self._data_lock:
            if self._error_message:
                return self._render_error(image, draw, width, height)

            if not self._ticker_data:
                return self._render_loading(image, draw, width, height)

            # Get current ticker
            symbols = list(self._ticker_data.keys())
            if not symbols:
                return self._render_loading(image, draw, width, height)

            self._current_index = self._current_index % len(symbols)
            current_symbol = symbols[self._current_index]
            data = self._ticker_data[current_symbol]

            return self._render_ticker(image, draw, width, height, data)

    def _render_ticker(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        data: TickerData,
    ) -> RenderResult:
        """Render a single ticker."""
        display_mode = self._config.get("display_mode", "price")

        # Symbol
        symbol_font = get_default_font(10)
        draw.text((3, 3), data.symbol, font=symbol_font, fill=Colors.CYAN.to_tuple())

        # Price
        price_font = get_default_font(14)
        if data.price >= 1000:
            price_str = f"${data.price:,.0f}"
        elif data.price >= 1:
            price_str = f"${data.price:.2f}"
        else:
            price_str = f"${data.price:.4f}"

        draw.text((3, 18), price_str, font=price_font, fill=Colors.WHITE.to_tuple())

        # Change
        change_color = Colors.STOCK_UP if data.change >= 0 else Colors.STOCK_DOWN
        change_symbol = "+" if data.change >= 0 else ""
        change_str = f"{change_symbol}{data.change_percent:.1f}%"

        change_font = get_default_font(9)
        draw.text((3, 38), change_str, font=change_font, fill=change_color.to_tuple())

        # Sparkline chart
        if display_mode == "chart" and data.history:
            chart_color = Colors.STOCK_UP if data.change >= 0 else Colors.STOCK_DOWN
            draw_sparkline(
                image,
                x=width - 25,
                y=5,
                width=20,
                height=15,
                values=data.history,
                color=chart_color,
            )

        # Ticker indicator dots
        with self._data_lock:
            num_tickers = len(self._ticker_data)

        if num_tickers > 1:
            dot_y = height - 5
            dot_start_x = (width - (num_tickers * 4)) // 2

            for i in range(num_tickers):
                dot_color = Colors.CYAN if i == self._current_index else Colors.GRAY_DARK
                draw.ellipse(
                    [dot_start_x + i * 4, dot_y, dot_start_x + i * 4 + 2, dot_y + 2],
                    fill=dot_color.to_tuple(),
                )

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
        font = get_default_font(10)
        draw.text((5, 10), "Stocks", font=font, fill=Colors.ERROR.to_tuple())

        msg_font = get_default_font(7)
        msg = self._error_message[:20] if self._error_message else "Error"
        draw.text((5, 30), msg, font=msg_font, fill=Colors.GRAY.to_tuple())

        return RenderResult(image=image, next_render_in=5.0)
