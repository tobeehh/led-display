"""Pixel art logos for stocks and cryptocurrencies (20x20)."""

from PIL import Image


class StockLogos:
    """Company and crypto logos as pixel art for LED display."""

    # Color definitions
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    APPLE_GRAY = (180, 180, 180)
    GOOGLE_BLUE = (66, 133, 244)
    GOOGLE_RED = (234, 67, 53)
    GOOGLE_YELLOW = (251, 188, 5)
    GOOGLE_GREEN = (52, 168, 83)
    AMAZON_ORANGE = (255, 153, 0)
    MICROSOFT_ORANGE = (242, 80, 34)
    MICROSOFT_GREEN = (127, 186, 0)
    MICROSOFT_BLUE = (0, 164, 239)
    MICROSOFT_YELLOW = (255, 185, 0)
    TESLA_RED = (232, 33, 39)
    META_BLUE = (24, 119, 242)
    NETFLIX_RED = (229, 9, 20)
    NVIDIA_GREEN = (118, 185, 0)
    BTC_ORANGE = (247, 147, 26)
    ETH_PURPLE = (98, 126, 234)
    ETH_GRAY = (141, 141, 141)

    # Apple logo 20x20
    AAPL = [
        ".........WW.........",
        "........WWW.........",
        ".......WWWW.........",
        "......WWWW..........",
        ".....WWWWWWWWWW.....",
        "...WWWWWWWWWWWWWW...",
        "..WWWWWWWWWWWWWWWW..",
        ".WWWWWWWWWWWWWWWWWW.",
        ".WWWWWWWWWWWWWWWWWW.",
        "WWWWWWWWWWWWWWWWWWWW",
        "WWWWWWWWWWWWWWWWWWWW",
        "WWWWWWWWWWWWWWWWWWWW",
        "WWWWWWWWWWWWWWWWWWWW",
        ".WWWWWWWWWWWWWWWWWW.",
        ".WWWWWWWWWWWWWWWWWW.",
        "..WWWWWWWWWWWWWWWW..",
        "...WWWWWWWWWWWWWW...",
        ".....WWWWWWWWWW.....",
        "........WWW.........",
        "....................",
    ]

    # Google G logo 20x20
    GOOGL = [
        "....................",
        ".....BBBBBBBB.......",
        "...BBBBBBBBBBBB.....",
        "..BBBBB....BBBBB....",
        ".BBBB........BBBB...",
        ".BBB..........BBB...",
        "BBB............BBB..",
        "BBB.................",
        "BBB......GGGGGGGGG..",
        "BBB......GGGGGGGGG..",
        "BBB............GGG..",
        "BBB............GGG..",
        ".BBB..........GGG...",
        ".BBBB........GGGG...",
        "..BBBBB....GGGGG....",
        "...BBBBBBBBBBBB.....",
        ".....BBBBBBBB.......",
        "....................",
        "....................",
        "....................",
    ]

    # Amazon smile logo 20x20
    AMZN = [
        "....................",
        "....................",
        "....................",
        "....................",
        "..WWWW...WWWWWWWW...",
        ".WWWWWW.WWWWWWWWWW..",
        "WWWWWWWWWWWWWWWWWWW.",
        "WWWWWWWWWWWWWWWWWWWW",
        ".WWWWWWWWWWWWWWWWW..",
        "..WWWWWWWWWWWWWWW...",
        "....................",
        "....................",
        "O...................",
        "OO................OO",
        ".OOO............OOO.",
        "..OOOO........OOOO..",
        "....OOOOOOOOOOOO....",
        "......OOOOOOOO......",
        "....................",
        "....................",
    ]

    # Microsoft 4 squares 20x20
    MSFT = [
        "....................",
        "....................",
        "..RRRRRRR.GGGGGGG...",
        "..RRRRRRR.GGGGGGG...",
        "..RRRRRRR.GGGGGGG...",
        "..RRRRRRR.GGGGGGG...",
        "..RRRRRRR.GGGGGGG...",
        "..RRRRRRR.GGGGGGG...",
        "..RRRRRRR.GGGGGGG...",
        "....................",
        "..BBBBBBB.YYYYYYY...",
        "..BBBBBBB.YYYYYYY...",
        "..BBBBBBB.YYYYYYY...",
        "..BBBBBBB.YYYYYYY...",
        "..BBBBBBB.YYYYYYY...",
        "..BBBBBBB.YYYYYYY...",
        "..BBBBBBB.YYYYYYY...",
        "....................",
        "....................",
        "....................",
    ]

    # Tesla T logo 20x20
    TSLA = [
        "....................",
        "TTTTTTTTTTTTTTTTTTTT",
        "TTTTTTTTTTTTTTTTTTTT",
        "TTTTTTTTTTTTTTTTTTTT",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        ".......TTTTTT.......",
        "....................",
        "....................",
    ]

    # Meta/Facebook logo 20x20
    META = [
        "....................",
        "....................",
        "..MM..........MM....",
        ".MMMM........MMMM...",
        ".MMMMM......MMMMM...",
        ".MM.MMM....MMM.MM...",
        ".MM..MMM..MMM..MM...",
        ".MM...MMMMMM...MM...",
        ".MM....MMMM....MM...",
        ".MM.....MM.....MM...",
        ".MM............MM...",
        ".MM............MM...",
        ".MM............MM...",
        ".MM............MM...",
        ".MM............MM...",
        "....................",
        "....................",
        "....................",
        "....................",
        "....................",
    ]

    # Netflix N logo 20x20
    NFLX = [
        "....................",
        "..NN...........NN...",
        "..NNN..........NN...",
        "..NNNN.........NN...",
        "..NNNNN........NN...",
        "..NN.NNN.......NN...",
        "..NN..NNN......NN...",
        "..NN...NNN.....NN...",
        "..NN....NNN....NN...",
        "..NN.....NNN...NN...",
        "..NN......NNN..NN...",
        "..NN.......NNN.NN...",
        "..NN........NNNNN...",
        "..NN.........NNNN...",
        "..NN..........NNN...",
        "..NN...........NN...",
        "....................",
        "....................",
        "....................",
        "....................",
    ]

    # Nvidia logo 20x20
    NVDA = [
        "....................",
        ".VVVVV..............",
        ".VVVVVVV............",
        ".VV..VVVV...........",
        ".VV...VVVV..........",
        ".VV....VVVV.........",
        ".VV.....VVVV........",
        ".VV......VVVVVVVVVV.",
        ".VV.......VVVVVVVVV.",
        ".VV........VVVVVVVV.",
        ".VV.........VVVVVVV.",
        ".VV..........VVVVVV.",
        ".VV...........VVVV..",
        ".VV............VVV..",
        ".VV.............V...",
        ".VV.................",
        ".VV.................",
        "....................",
        "....................",
        "....................",
    ]

    # Bitcoin logo 20x20
    BTC = [
        "....................",
        "......BBBBBB........",
        "....BBBBBBBBBB......",
        "...BBB......BBB.....",
        "..BBB..BBBB..BBB....",
        "..BB..BB..BB..BB....",
        "..BB..BB..BB..BB....",
        "..BB..BBBBB...BB....",
        "..BB..BB..BB..BB....",
        "..BB..BB..BB..BB....",
        "..BB..BBBBB...BB....",
        "..BB..BB..BB..BB....",
        "..BB..BB..BB..BB....",
        "..BBB..BBBB..BBB....",
        "...BBB......BBB.....",
        "....BBBBBBBBBB......",
        "......BBBBBB........",
        "....................",
        "....................",
        "....................",
    ]

    # Ethereum diamond logo 20x20
    ETH = [
        ".........PP.........",
        "........PPPP........",
        ".......PP..PP.......",
        "......PP....PP......",
        ".....PP......PP.....",
        "....PP........PP....",
        "...PP..........PP...",
        "..PP............PP..",
        ".PP..............PP.",
        "PPPPPPPPPPPPPPPPPPPP",
        ".PP..............PP.",
        "..PP............PP..",
        "...PP..........PP...",
        "....PP........PP....",
        ".....PP......PP.....",
        "......PP....PP......",
        ".......PP..PP.......",
        "........PPPP........",
        ".........PP.........",
        "....................",
    ]

    # Color maps for each logo
    COLOR_MAPS = {
        'AAPL': {'W': APPLE_GRAY, '.': BLACK},
        'GOOGL': {'B': GOOGLE_BLUE, 'R': GOOGLE_RED, 'G': GOOGLE_GREEN, 'Y': GOOGLE_YELLOW, '.': BLACK},
        'GOOG': {'B': GOOGLE_BLUE, 'R': GOOGLE_RED, 'G': GOOGLE_GREEN, 'Y': GOOGLE_YELLOW, '.': BLACK},
        'AMZN': {'W': WHITE, 'O': AMAZON_ORANGE, '.': BLACK},
        'MSFT': {'R': MICROSOFT_ORANGE, 'G': MICROSOFT_GREEN, 'B': MICROSOFT_BLUE, 'Y': MICROSOFT_YELLOW, '.': BLACK},
        'TSLA': {'T': TESLA_RED, '.': BLACK},
        'META': {'M': META_BLUE, '.': BLACK},
        'NFLX': {'N': NETFLIX_RED, '.': BLACK},
        'NVDA': {'V': NVIDIA_GREEN, '.': BLACK},
        'BTC': {'B': BTC_ORANGE, '.': BLACK},
        'BTC-USD': {'B': BTC_ORANGE, '.': BLACK},
        'ETH': {'P': ETH_PURPLE, '.': BLACK},
        'ETH-USD': {'P': ETH_PURPLE, '.': BLACK},
    }

    LOGOS = {
        'AAPL': AAPL,
        'GOOGL': GOOGL,
        'GOOG': GOOGL,
        'AMZN': AMZN,
        'MSFT': MSFT,
        'TSLA': TSLA,
        'META': META,
        'NFLX': NFLX,
        'NVDA': NVDA,
        'BTC': BTC,
        'BTC-USD': BTC,
        'ETH': ETH,
        'ETH-USD': ETH,
    }

    @classmethod
    def has_logo(cls, symbol: str) -> bool:
        """Check if a logo exists for this symbol."""
        symbol = symbol.upper().replace('-USD', '')
        return symbol in cls.LOGOS or f"{symbol}-USD" in cls.LOGOS

    @classmethod
    def render(cls, image: Image.Image, symbol: str, x: int, y: int) -> bool:
        """Render a logo to an image.

        Returns True if logo was rendered, False if no logo exists.
        """
        symbol_upper = symbol.upper()

        # Try exact match first, then without -USD
        if symbol_upper not in cls.LOGOS:
            symbol_upper = symbol_upper.replace('-USD', '')

        if symbol_upper not in cls.LOGOS:
            return False

        bitmap = cls.LOGOS[symbol_upper]
        color_map = cls.COLOR_MAPS.get(symbol_upper, {'W': cls.WHITE, '.': cls.BLACK})

        pixels = image.load()

        for row_idx, row in enumerate(bitmap):
            for col_idx, pixel in enumerate(row):
                if pixel in color_map and pixel != '.':
                    px = x + col_idx
                    py = y + row_idx
                    if 0 <= px < image.width and 0 <= py < image.height:
                        pixels[px, py] = color_map[pixel]

        return True

    @classmethod
    def get_available_logos(cls) -> list[str]:
        """Get list of symbols with available logos."""
        return list(cls.LOGOS.keys())
