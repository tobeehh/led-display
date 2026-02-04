"""Stock Ticker application for 64x64 LED display.

Features:
- Real-time stock/crypto/forex prices via Yahoo Finance
- Live company logos from Clearbit / crypto logos from CoinGecko
- Price change with color indication (green/red)
- Mini sparkline chart
- Multiple ticker rotation

Inspired by: https://github.com/feram18/led-stock-ticker
"""

import io
import time
from typing import Any

import requests
from PIL import Image

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from display.fonts import small_font, medium_font
from display.graphics import Colors, Gradients, Drawing

from .base import BaseApp


# Domain mapping for Clearbit logos
STOCK_DOMAINS = {
    'AAPL': 'apple.com',
    'GOOGL': 'google.com',
    'GOOG': 'google.com',
    'MSFT': 'microsoft.com',
    'AMZN': 'amazon.com',
    'TSLA': 'tesla.com',
    'META': 'meta.com',
    'NFLX': 'netflix.com',
    'NVDA': 'nvidia.com',
    'AMD': 'amd.com',
    'INTC': 'intel.com',
    'DIS': 'disney.com',
    'PYPL': 'paypal.com',
    'ADBE': 'adobe.com',
    'CRM': 'salesforce.com',
    'ORCL': 'oracle.com',
    'CSCO': 'cisco.com',
    'IBM': 'ibm.com',
    'UBER': 'uber.com',
    'LYFT': 'lyft.com',
    'SPOT': 'spotify.com',
    'SQ': 'squareup.com',
    'SHOP': 'shopify.com',
    'ZM': 'zoom.us',
    'SNAP': 'snap.com',
    'TWTR': 'twitter.com',
    'PINS': 'pinterest.com',
    'RBLX': 'roblox.com',
    'COIN': 'coinbase.com',
    'HOOD': 'robinhood.com',
    'V': 'visa.com',
    'MA': 'mastercard.com',
    'JPM': 'jpmorganchase.com',
    'BAC': 'bankofamerica.com',
    'WMT': 'walmart.com',
    'TGT': 'target.com',
    'COST': 'costco.com',
    'HD': 'homedepot.com',
    'NKE': 'nike.com',
    'SBUX': 'starbucks.com',
    'MCD': 'mcdonalds.com',
    'KO': 'coca-cola.com',
    'PEP': 'pepsico.com',
}

# CoinGecko IDs for crypto
CRYPTO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'BNB': 'binancecoin',
    'XRP': 'ripple',
    'ADA': 'cardano',
    'SOL': 'solana',
    'DOGE': 'dogecoin',
    'DOT': 'polkadot',
    'MATIC': 'matic-network',
    'LTC': 'litecoin',
    'SHIB': 'shiba-inu',
    'AVAX': 'avalanche-2',
    'LINK': 'chainlink',
    'UNI': 'uniswap',
    'ATOM': 'cosmos',
    'XLM': 'stellar',
    'ALGO': 'algorand',
    'VET': 'vechain',
    'FIL': 'filecoin',
    'AAVE': 'aave',
}


class StocksApp(BaseApp):
    """Displays stock/crypto/forex prices with live logos."""

    name = "stocks"
    display_name = "Stocks"
    description = "Shows stock, crypto & forex prices"
    requires_credentials = False

    config_schema = {
        "tickers": {
            "type": "string",
            "label": "Tickers (comma separated)",
            "default": "AAPL,GOOGL,MSFT,BTC-USD,ETH-USD",
            "description": "Stock symbols, crypto (add -USD), forex (e.g., EURUSD=X)",
        },
        "rotation_interval": {
            "type": "int",
            "label": "Rotation interval (seconds)",
            "default": 10,
            "min": 5,
            "max": 60,
        },
        "update_interval": {
            "type": "int",
            "label": "Data update interval (seconds)",
            "default": 300,
            "min": 60,
            "max": 3600,
        },
        "display_mode": {
            "type": "select",
            "label": "Display mode",
            "options": [
                {"value": "logo", "label": "Logo + Price"},
                {"value": "chart", "label": "Chart + Price"},
                {"value": "both", "label": "Logo + Chart"},
            ],
            "default": "logo",
        },
        "currency": {
            "type": "select",
            "label": "Display currency",
            "options": [
                {"value": "USD", "label": "USD ($)"},
                {"value": "EUR", "label": "EUR (€)"},
                {"value": "GBP", "label": "GBP (£)"},
            ],
            "default": "USD",
        },
    }

    CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._ticker_data: dict[str, dict] = {}
        self._logos: dict[str, Image.Image] = {}
        self._current_ticker_index = 0
        self._last_rotation = time.time()
        self._last_update = 0.0
        self._update_error: str | None = None
        self._tickers: list[str] = []

    def setup(self) -> bool:
        if not YFINANCE_AVAILABLE:
            self._update_error = "yfinance missing"
            return False
        self._parse_tickers()
        self.update()
        return True

    def _parse_tickers(self) -> None:
        tickers_str = self._config.get("tickers", "AAPL,GOOGL,BTC-USD")
        self._tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]

    def _fetch_stock_logo(self, symbol: str) -> Image.Image | None:
        """Fetch company logo from Clearbit."""
        domain = STOCK_DOMAINS.get(symbol)
        if not domain:
            return None

        try:
            url = f"https://logo.clearbit.com/{domain}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content)).convert("RGBA")
                # Resize to 24x24 for display
                img = img.resize((24, 24), Image.Resampling.LANCZOS)
                # Convert to RGB with black background
                background = Image.new("RGB", img.size, (0, 0, 0))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                return background
        except Exception as e:
            print(f"[Stocks] Logo fetch error for {symbol}: {e}")
        return None

    def _fetch_crypto_logo(self, symbol: str) -> Image.Image | None:
        """Fetch crypto logo from CoinGecko."""
        # Remove -USD suffix
        clean_symbol = symbol.replace('-USD', '').replace('-EUR', '')
        coin_id = CRYPTO_IDS.get(clean_symbol)
        if not coin_id:
            return None

        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            response = requests.get(url, timeout=5, params={'localization': 'false', 'tickers': 'false', 'market_data': 'false', 'community_data': 'false', 'developer_data': 'false'})
            if response.status_code == 200:
                data = response.json()
                logo_url = data.get('image', {}).get('small')
                if logo_url:
                    logo_response = requests.get(logo_url, timeout=5)
                    if logo_response.status_code == 200:
                        img = Image.open(io.BytesIO(logo_response.content)).convert("RGBA")
                        img = img.resize((24, 24), Image.Resampling.LANCZOS)
                        background = Image.new("RGB", img.size, (0, 0, 0))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[3])
                        else:
                            background.paste(img)
                        return background
        except Exception as e:
            print(f"[Stocks] Crypto logo fetch error for {symbol}: {e}")
        return None

    def _fetch_logo(self, symbol: str, ticker_type: str) -> Image.Image | None:
        """Fetch logo based on ticker type."""
        if symbol in self._logos:
            return self._logos[symbol]

        logo = None
        if ticker_type == 'crypto':
            logo = self._fetch_crypto_logo(symbol)
        elif ticker_type == 'stock':
            logo = self._fetch_stock_logo(symbol)

        if logo:
            self._logos[symbol] = logo
        return logo

    def update(self) -> None:
        if not YFINANCE_AVAILABLE:
            return

        self._parse_tickers()

        for symbol in self._tickers:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1d", interval="5m")

                if hist.empty:
                    continue

                current_price = hist['Close'].iloc[-1]
                open_price = hist['Open'].iloc[0]
                change = current_price - open_price
                change_pct = (change / open_price) * 100 if open_price > 0 else 0
                prices = hist['Close'].tolist()

                if '-USD' in symbol or '-EUR' in symbol:
                    ticker_type = 'crypto'
                    name = symbol.split('-')[0]
                elif '=X' in symbol:
                    ticker_type = 'forex'
                    name = symbol.replace('=X', '')
                else:
                    ticker_type = 'stock'
                    name = info.get('shortName', symbol)[:12]

                self._ticker_data[symbol] = {
                    'symbol': symbol,
                    'name': name,
                    'price': current_price,
                    'change': change,
                    'change_pct': change_pct,
                    'prices': prices,
                    'type': ticker_type,
                    'currency': info.get('currency', 'USD'),
                }

                # Fetch logo in background
                self._fetch_logo(symbol, ticker_type)

            except Exception as e:
                print(f"[Stocks] Error fetching {symbol}: {e}")
                continue

        self._last_update = time.time()
        self._update_error = None if self._ticker_data else "No data"

    def get_update_interval(self) -> float:
        return float(self._config.get("update_interval", 300))

    def _format_price(self, price: float, currency: str = "USD") -> str:
        symbol = self.CURRENCY_SYMBOLS.get(currency, "$")
        if price >= 10000:
            return f"{symbol}{price/1000:.1f}K"
        elif price >= 1000:
            return f"{symbol}{price:.0f}"
        elif price >= 100:
            return f"{symbol}{price:.1f}"
        elif price >= 1:
            return f"{symbol}{price:.2f}"
        else:
            return f"{symbol}{price:.4f}"

    def _draw_sparkline(self, image: Image.Image, prices: list[float],
                        x: int, y: int, width: int, height: int,
                        up_color: tuple, down_color: tuple) -> None:
        if len(prices) < 2:
            return

        pixels = image.load()
        min_p, max_p = min(prices), max(prices)
        p_range = max_p - min_p if max_p > min_p else 1

        is_up = prices[-1] >= prices[0]
        line_color = up_color if is_up else down_color
        fill_color = Colors.dim(line_color, 0.15)

        points = []
        for i, price in enumerate(prices):
            px = x + int((i / (len(prices) - 1)) * (width - 1))
            py = y + height - 1 - int(((price - min_p) / p_range) * (height - 1))
            points.append((px, py))

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            for col_x in range(x1, x2 + 1):
                t = (col_x - x1) / max(1, x2 - x1) if col_x < x2 else 1
                col_y = int(y1 + (y2 - y1) * t)
                for fy in range(col_y, y + height):
                    if 0 <= col_x < image.width and 0 <= fy < image.height:
                        pixels[col_x, fy] = fill_color

        for i in range(len(points) - 1):
            Drawing.line(image, points[i][0], points[i][1], points[i+1][0], points[i+1][1], line_color)

    def _draw_arrow(self, image: Image.Image, x: int, y: int, up: bool, color: tuple) -> None:
        pixels = image.load()
        if up:
            arrow = ["...1...", "..111..", ".11111.", "1111111", "...1...", "...1..."]
        else:
            arrow = ["...1...", "...1...", "1111111", ".11111.", "..111..", "...1..."]

        for row_idx, row in enumerate(arrow):
            for col_idx, pixel in enumerate(row):
                if pixel == '1':
                    px, py = x + col_idx, y + row_idx
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color

    def render(self, width: int, height: int) -> Image.Image:
        image = Image.new("RGB", (width, height), (0, 0, 0))

        if self._update_error:
            Gradients.vertical(image, (30, 20, 20), (15, 10, 10))
            small_font.render_text_centered(image, "Stocks", 10, (255, 100, 100))
            small_font.render_text_centered(image, self._update_error, 28, (200, 80, 80))
            if not YFINANCE_AVAILABLE:
                small_font.render_text_centered(image, "pip install", 44, (100, 100, 100))
                small_font.render_text_centered(image, "yfinance", 52, (100, 100, 100))
            return image

        if not self._ticker_data or not self._tickers:
            Gradients.vertical(image, (20, 25, 30), (10, 12, 15))
            small_font.render_text_centered(image, "Loading...", 28, (100, 150, 200))
            return image

        # Rotation
        rotation_interval = self._config.get("rotation_interval", 10)
        current_time = time.time()
        if current_time - self._last_rotation > rotation_interval:
            self._current_ticker_index = (self._current_ticker_index + 1) % len(self._tickers)
            self._last_rotation = current_time

        current_symbol = self._tickers[self._current_ticker_index % len(self._tickers)]
        data = self._ticker_data.get(current_symbol)

        if not data:
            self._current_ticker_index = (self._current_ticker_index + 1) % len(self._tickers)
            small_font.render_text_centered(image, "No data", 28, (150, 150, 150))
            return image

        is_up = data['change'] >= 0
        accent = (50, 220, 100) if is_up else (255, 80, 80)

        Gradients.vertical(image, Colors.dim(accent, 0.08), (0, 0, 0))

        display_mode = self._config.get("display_mode", "logo")
        logo = self._logos.get(current_symbol)
        show_logo = display_mode in ("logo", "both") and logo is not None
        show_chart = display_mode in ("chart", "both") or (display_mode == "logo" and logo is None)

        # Symbol display
        symbol_display = data['symbol'].replace('-USD', '').replace('=X', '')[:6]

        if show_logo and not show_chart:
            # Logo centered layout
            if logo:
                logo_x = (width - 24) // 2
                image.paste(logo, (logo_x, 2))

            # Symbol below logo
            small_font.render_text_centered(image, symbol_display, 28, Colors.dim(Colors.WHITE, 0.7))

            # Price
            price_str = self._format_price(data['price'], data.get('currency', 'USD'))
            medium_font.render_text_centered(image, price_str, 38, Colors.WHITE)

            # Change with arrow
            change_y = 52
            self._draw_arrow(image, 10, change_y, is_up, accent)
            pct_str = f"{'+' if is_up else ''}{data['change_pct']:.1f}%"
            small_font.render_text(image, pct_str, 20, change_y, accent)

        elif show_logo and show_chart:
            # Logo + Chart layout
            if logo:
                image.paste(logo, (2, 2))

            # Symbol and price right of logo
            small_font.render_text(image, symbol_display, 30, 2, Colors.WHITE)
            price_str = self._format_price(data['price'], data.get('currency', 'USD'))
            small_font.render_text(image, price_str, 30, 12, Colors.dim(Colors.WHITE, 0.8))

            # Change
            self._draw_arrow(image, 30, 22, is_up, accent)
            pct_str = f"{'+' if is_up else ''}{data['change_pct']:.1f}%"
            small_font.render_text(image, pct_str, 40, 22, accent)

            # Chart bottom
            if data.get('prices'):
                self._draw_sparkline(image, data['prices'], 2, 36, width - 4, 24,
                                    (50, 220, 100), (255, 80, 80))

        else:
            # Chart only layout
            small_font.render_text(image, symbol_display, 2, 2, Colors.WHITE)

            type_colors = {'stock': (100, 150, 255), 'crypto': (255, 180, 50), 'forex': (150, 255, 150)}
            type_label = data['type'][:3].upper()
            small_font.render_text(image, type_label, width - small_font.get_text_width(type_label) - 2, 2,
                                  Colors.dim(type_colors.get(data['type'], Colors.WHITE), 0.6))

            price_str = self._format_price(data['price'], data.get('currency', 'USD'))
            medium_font.render_text_centered(image, price_str, 12, Colors.WHITE)

            change_y = 26
            self._draw_arrow(image, 6, change_y, is_up, accent)
            change_str = f"{'+' if is_up else ''}{data['change']:.2f}"
            pct_str = f"({'+' if is_up else ''}{data['change_pct']:.1f}%)"
            small_font.render_text(image, change_str, 16, change_y, accent)
            small_font.render_text(image, pct_str, 16 + small_font.get_text_width(change_str) + 2, change_y,
                                  Colors.dim(accent, 0.7))

            if data.get('prices'):
                self._draw_sparkline(image, data['prices'], 4, 40, width - 8, 20,
                                    (50, 220, 100), (255, 80, 80))

        # Pagination dots
        if len(self._tickers) > 1:
            dot_y = height - 3
            total_width = len(self._tickers) * 4 - 2
            dot_x = (width - total_width) // 2
            for i in range(len(self._tickers)):
                color = Colors.WHITE if i == self._current_ticker_index else Colors.dim(Colors.WHITE, 0.2)
                Drawing.rect(image, dot_x + i * 4, dot_y, 2, 2, color)

        return image

    def get_render_interval(self) -> float:
        return 1.0
