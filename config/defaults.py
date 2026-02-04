"""Default configuration settings for the LED Display system."""

# Display settings
# 2x 64x32 panels stacked vertically = 64x64 total
DISPLAY_DEFAULTS = {
    "rows": 32,
    "cols": 64,
    "chain_length": 2,
    "parallel": 1,
    "hardware_mapping": "adafruit-hat",
    "gpio_slowdown": 4,
    "brightness": 50,
    "pwm_bits": 11,
    "pwm_lsb_nanoseconds": 130,
    "scan_mode": 1,
    "row_address_type": 0,
    "multiplexing": 0,
    "disable_hardware_pulsing": False,
    "show_refresh_rate": False,
    "inverse_colors": False,
    "led_rgb_sequence": "RGB",
    "pixel_mapper_config": "U-mapper",  # Stack panels vertically
    "panel_type": "",
    "limit_refresh_rate_hz": 0,
}

# Button settings
BUTTON_DEFAULTS = {
    "pin": 17,
    "long_press_duration": 3.0,  # seconds
    "debounce_time": 0.05,  # seconds
}

# Network settings
NETWORK_DEFAULTS = {
    "ap_ssid": "LED-Display-Setup",
    "ap_password": "",  # Open network for easy setup
    "ap_channel": 6,
    "ap_ip": "192.168.4.1",
    "ap_netmask": "255.255.255.0",
    "dns_port": 53,
    "captive_portal_port": 80,
}

# Web UI settings
WEB_DEFAULTS = {
    "host": "0.0.0.0",
    "port": 80,
    "debug": False,
}

# App settings
APP_DEFAULTS = {
    "active_app": "clock",
    "rotation_enabled": False,
    "rotation_interval": 30,  # seconds
    "apps": {
        "clock": {
            "enabled": True,
            "format_24h": True,
            "show_date": True,
            "show_seconds": False,
            "color": "#FFFFFF",
        },
        "weather": {
            "enabled": False,
            "api_key": "",
            "city": "",
            "units": "metric",
            "update_interval": 600,  # seconds
        },
        "spotify": {
            "enabled": False,
            "client_id": "",
            "client_secret": "",
            "refresh_token": "",
            "show_album_art": True,
        },
        "stocks": {
            "enabled": True,
            "tickers": "AAPL,GOOGL,BTC-USD,ETH-USD",
            "rotation_interval": 10,
            "update_interval": 300,
            "display_mode": "logo",  # logo, chart, both
            "currency": "USD",
        },
        "text": {
            "enabled": True,
            "message": "Hello World!",
            "scroll": True,
            "scroll_speed": 50,
            "color": "#FFFFFF",
        },
    },
}

# Default config file path
CONFIG_FILE = "config/settings.json"
