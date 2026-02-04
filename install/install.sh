#!/bin/bash
#
# LED Display System Installation Script
# For Raspberry Pi 3B with RGB Matrix Bonnet
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="/opt/led-display"
SERVICE_NAME="led-display"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LED Display System Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to check command success
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1 failed${NC}"
        exit 1
    fi
}

# Step 1: Update system packages
echo
echo -e "${YELLOW}Step 1: Updating system packages...${NC}"
apt-get update
check_status "System update"

# Step 2: Install system dependencies
echo
echo -e "${YELLOW}Step 2: Installing system dependencies...${NC}"
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    cython3 \
    libgraphicsmagick++-dev \
    libwebp-dev \
    hostapd \
    dnsmasq \
    wireless-tools \
    wpasupplicant
check_status "System dependencies"

# Step 3: Install RGB Matrix library
echo
echo -e "${YELLOW}Step 3: Installing RGB Matrix library...${NC}"
if [ ! -d "/tmp/rpi-rgb-led-matrix" ]; then
    cd /tmp
    git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
fi
cd /tmp/rpi-rgb-led-matrix
make build-python PYTHON=$(which python3)
make install-python PYTHON=$(which python3)
check_status "RGB Matrix library"

# Step 4: Create installation directory
echo
echo -e "${YELLOW}Step 4: Setting up installation directory...${NC}"
mkdir -p "$INSTALL_DIR"

# Copy files from current directory or parent directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$SOURCE_DIR/main.py" ]; then
    cp -r "$SOURCE_DIR"/* "$INSTALL_DIR/"
else
    echo -e "${RED}Error: Source files not found${NC}"
    echo "Please run this script from the install directory"
    exit 1
fi
check_status "Files copied"

# Step 5: Create Python virtual environment
echo
echo -e "${YELLOW}Step 5: Creating Python virtual environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
check_status "Virtual environment"

# Step 6: Install Python dependencies
echo
echo -e "${YELLOW}Step 6: Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
check_status "Python dependencies"

# Step 7: Configure hostapd and dnsmasq
echo
echo -e "${YELLOW}Step 7: Configuring network services...${NC}"

# Disable services by default (will be enabled by captive portal)
systemctl disable hostapd 2>/dev/null || true
systemctl disable dnsmasq 2>/dev/null || true
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true

# Allow hostapd to run without a config file initially
echo 'DAEMON_CONF=""' > /etc/default/hostapd
check_status "Network services configured"

# Step 8: Install systemd service
echo
echo -e "${YELLOW}Step 8: Installing systemd service...${NC}"
cp "$INSTALL_DIR/install/led-display.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
check_status "Systemd service"

# Step 9: Configure GPIO permissions
echo
echo -e "${YELLOW}Step 9: Configuring GPIO permissions...${NC}"
usermod -a -G gpio root 2>/dev/null || true
check_status "GPIO permissions"

# Step 10: Create default configuration
echo
echo -e "${YELLOW}Step 10: Creating default configuration...${NC}"
mkdir -p "$INSTALL_DIR/config"
if [ ! -f "$INSTALL_DIR/config/settings.json" ]; then
    cat > "$INSTALL_DIR/config/settings.json" << 'EOF'
{
  "display": {
    "rows": 32,
    "cols": 64,
    "chain_length": 2,
    "parallel": 1,
    "hardware_mapping": "adafruit-hat",
    "gpio_slowdown": 4,
    "brightness": 50
  },
  "button": {
    "pin": 17,
    "long_press_duration": 3.0
  },
  "network": {
    "ap_ssid": "LED-Display-Setup"
  },
  "web": {
    "host": "0.0.0.0",
    "port": 80
  },
  "apps": {
    "active_app": "clock",
    "rotation_enabled": false,
    "rotation_interval": 30
  }
}
EOF
fi
check_status "Default configuration"

# Step 11: Set permissions
echo
echo -e "${YELLOW}Step 11: Setting permissions...${NC}"
chown -R root:root "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/main.py"
check_status "Permissions set"

# Completion message
echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "The LED Display system has been installed to: $INSTALL_DIR"
echo
echo "To start the service:"
echo "  sudo systemctl start $SERVICE_NAME"
echo
echo "To view logs:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo
echo "To access the web interface:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo
echo "On first boot, if no WiFi is configured, the system will"
echo "create an access point named 'LED-Display-Setup' for configuration."
echo
echo -e "${YELLOW}NOTE: A reboot is recommended to ensure all changes take effect.${NC}"
echo
read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    reboot
fi
