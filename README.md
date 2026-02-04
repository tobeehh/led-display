# LED Display System

A Raspberry Pi-based LED matrix display system with multiple apps, web configuration, and captive portal for WiFi setup.

## Hardware

- Raspberry Pi 3B (or newer)
- 2x 64x32 RGB LED Matrix Panels (HUB75)
- Adafruit RGB Matrix Bonnet
- Push button on GPIO 17

## Features

- **64x64 pixel display** (two 64x32 panels in daisy-chain with U-mapper)
- **5 Display Apps:**
  - Clock - Large digits with date
  - Text - Custom scrolling text
  - Weather - OpenWeatherMap integration with pixel art icons
  - Spotify - Now playing with album art
  - Stocks - Live stock/crypto prices with company logos
- **Web UI** for configuration (port 80)
- **Captive Portal** for WiFi setup
- **Button control** - Short press: next app, Long press: start captive portal

## Installation

```bash
# Clone the repository
git clone https://github.com/tobeehh/led-display.git
cd led-display

# Run the installer (on Raspberry Pi)
cd install
sudo ./install.sh
```

## Usage

```bash
# Start the service
sudo systemctl start led-display

# View logs
sudo journalctl -u led-display -f

# Access web UI
http://<raspberry-pi-ip>
```

## Configuration

The web UI allows configuration of:
- Display brightness
- App settings (API keys, preferences)
- WiFi credentials
- App rotation

## Project Structure

```
led/
├── main.py              # Entry point
├── config/              # Configuration
├── display/             # LED matrix control
├── apps/                # Display applications
├── network/             # WiFi & captive portal
├── web/                 # Flask web UI
├── hardware/            # Button handler
└── install/             # Installation scripts
```

## License

MIT
