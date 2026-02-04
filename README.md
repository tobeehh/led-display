# LED Matrix Display System

A modern, robust IoT display system for Raspberry Pi with RGB LED matrix panels.

## Features

- **Display Apps**
  - Clock with date and time-based color transitions
  - Word Clock (QLOCKTWO-style German word display)
  - Weather (OpenWeatherMap integration)
  - Stock/Crypto ticker (Yahoo Finance)
  - Spotify Now Playing with album art
  - Custom scrolling text

- **Connectivity**
  - WiFi captive portal for easy setup
  - REST API for external control
  - Modern web interface

- **Hardware Support**
  - P4 64x32 panels with FM6126A/TC7258GN driver
  - Adafruit RGB Matrix Bonnet
  - Raspberry Pi 3/4
  - GPIO button for app switching

## Hardware Requirements

- Raspberry Pi 3 or 4
- Adafruit RGB Matrix Bonnet
- 2x P4 64x32 LED panels (FM6126A driver)
- 5V power supply (7A+ recommended)
- Optional: Push button on GPIO 17

## Panel Wiring

```
Panel 1 (Bottom) ← HUB75 from Bonnet
      ↓ Daisy chain
Panel 2 (Top)
```

Both panels should be powered separately via their screw terminals.

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/led-display.git
cd led-display

# Run installer (requires sudo)
sudo ./scripts/install.sh
```

### Manual Install

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git cython3

# Install RGB Matrix library
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)

# Install LED Display
cd /opt
sudo git clone https://github.com/yourusername/led-display.git
cd led-display
sudo python3 -m venv --system-site-packages venv
sudo ./venv/bin/pip install .

# Copy config
sudo cp config/config.example.yaml config/config.yaml

# Install service
sudo cp systemd/led-display.service /etc/systemd/system/
sudo systemctl enable led-display
sudo systemctl start led-display
```

## Configuration

Edit `/opt/led-display/config/config.yaml`:

```yaml
display:
  rows: 32
  cols: 64
  chain_length: 2
  panel_type: "FM6126A"      # Important for FM6126A panels
  row_address_type: 3        # ABC addressing
  pixel_mapper_config: "U-mapper"
  brightness: 50

apps:
  active_app: "clock"

  weather:
    enabled: true
    api_key: "your_openweathermap_api_key"
    city: "Berlin"
```

## Web Interface

Access the web interface at `http://<raspberry-pi-ip>/`

On first access, you'll be prompted to set an admin password.

## API

### Status
```bash
curl http://localhost/api/status
```

### Switch App
```bash
curl -X POST http://localhost/api/apps/clock/activate
```

### Set Brightness
```bash
curl -X POST http://localhost/api/display/brightness \
  -H "Content-Type: application/json" \
  -d '{"brightness": 75}'
```

## WiFi Setup

If no WiFi is configured:

1. The display creates an access point: `LED-Display-Setup`
2. Connect to the AP with your phone/laptop
3. A captive portal will open for WiFi configuration
4. Select your network and enter the password
5. The display will connect and the AP will close

You can also trigger the captive portal with a long press (3+ seconds) on the GPIO button.

## Troubleshooting

### Display shows nothing
- Check power connections (5V, adequate amperage)
- Verify `panel_type: "FM6126A"` in config
- Run test pattern: `sudo /opt/led-display/venv/bin/python -m ledmatrix --test-display`

### Display flickering
- Increase `gpio_slowdown` (try 4-5)
- Check power supply voltage

### Ghosting/artifacts
- Increase `pwm_lsb_nanoseconds` (try 200-300)
- Reduce `pwm_bits` (try 7-9)

### Can't connect to web interface
- Check if service is running: `sudo systemctl status led-display`
- View logs: `sudo journalctl -u led-display -f`

## Development

### Running locally (mock mode)

```bash
# Install in development mode
pip install -e ".[dev]"

# Run with mock hardware
python -m ledmatrix --mock --debug
```

### Running tests

```bash
pytest tests/
```

## Project Structure

```
src/ledmatrix/
├── __main__.py         # Entry point
├── core/               # Core infrastructure
│   ├── config.py       # Configuration management
│   ├── errors.py       # Exception hierarchy
│   ├── logging.py      # Structured logging
│   ├── retry.py        # Retry logic
│   └── threading.py    # Thread-safe primitives
├── display/            # Display management
│   ├── manager.py      # LED matrix control
│   ├── renderer.py     # PIL rendering
│   └── graphics.py     # Drawing utilities
├── apps/               # Display applications
│   ├── base.py         # Base app class
│   ├── scheduler.py    # App lifecycle
│   ├── clock.py
│   ├── weather.py
│   ├── stocks.py
│   ├── spotify.py
│   └── text.py
├── hardware/           # Hardware abstraction
│   ├── button.py       # GPIO button
│   └── mock.py         # Mock implementations
├── network/            # Network management
│   ├── wifi.py         # nmcli-based WiFi
│   ├── manager.py      # Connection monitoring
│   └── captive_portal.py
└── web/                # Web interface
    ├── app.py          # FastAPI application
    ├── auth.py         # Authentication
    ├── schemas.py      # Request/response models
    └── routes/         # API endpoints
```

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) - LED matrix driver
- [Adafruit](https://www.adafruit.com/) - RGB Matrix Bonnet
