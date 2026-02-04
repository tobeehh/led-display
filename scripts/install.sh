#!/bin/bash
#
# LED Display System Installation Script
# For Raspberry Pi with RGB Matrix Bonnet
#
# Tested on: Raspbian Trixie Lite
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Installation paths
INSTALL_DIR="/opt/led-display"
SERVICE_NAME="led-display"
VENV_DIR="$INSTALL_DIR/venv"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║     LED Display System Installer          ║"
    echo "║     For Raspberry Pi + RGB Matrix         ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Error: This script must be run as root${NC}"
        echo "Please run: sudo $0"
        exit 1
    fi
}

check_platform() {
    if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

install_system_deps() {
    echo -e "${CYAN}[1/7] Installing system dependencies...${NC}"

    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        python3-pil \
        git \
        cython3 \
        libgraphicsmagick++-dev \
        libwebp-dev \
        network-manager

    echo -e "${GREEN}✓ System dependencies installed${NC}"
}

install_rgb_matrix() {
    echo -e "${CYAN}[2/7] Installing RGB Matrix library...${NC}"

    RGB_DIR="/tmp/rpi-rgb-led-matrix"

    if [ ! -d "$RGB_DIR" ]; then
        git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "$RGB_DIR"
    fi

    cd "$RGB_DIR"

    # Build the library
    make build-python PYTHON=$(which python3)
    make install-python PYTHON=$(which python3)

    echo -e "${GREEN}✓ RGB Matrix library installed${NC}"
}

setup_install_dir() {
    echo -e "${CYAN}[3/7] Setting up installation directory...${NC}"

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/config"

    # Copy source files
    if [ -f "$SOURCE_DIR/pyproject.toml" ]; then
        cp -r "$SOURCE_DIR/src" "$INSTALL_DIR/"
        cp "$SOURCE_DIR/pyproject.toml" "$INSTALL_DIR/"

        # Copy example config if no config exists
        if [ ! -f "$INSTALL_DIR/config/config.yaml" ]; then
            if [ -f "$SOURCE_DIR/config/config.example.yaml" ]; then
                cp "$SOURCE_DIR/config/config.example.yaml" "$INSTALL_DIR/config/config.yaml"
            fi
        fi
    else
        echo -e "${RED}Error: Source files not found in $SOURCE_DIR${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Files installed to $INSTALL_DIR${NC}"
}

setup_venv() {
    echo -e "${CYAN}[4/7] Creating Python virtual environment...${NC}"

    python3 -m venv --system-site-packages "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    pip install --upgrade pip
    pip install "$INSTALL_DIR"

    echo -e "${GREEN}✓ Virtual environment created${NC}"
}

setup_network_manager() {
    echo -e "${CYAN}[5/7] Configuring NetworkManager...${NC}"

    # Enable NetworkManager
    systemctl enable NetworkManager
    systemctl start NetworkManager

    # Disable wpa_supplicant if present (NetworkManager will manage WiFi)
    systemctl disable wpa_supplicant 2>/dev/null || true

    echo -e "${GREEN}✓ NetworkManager configured${NC}"
}

install_service() {
    echo -e "${CYAN}[6/7] Installing systemd service...${NC}"

    cp "$SOURCE_DIR/systemd/led-display.service" /etc/systemd/system/

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"

    echo -e "${GREEN}✓ Systemd service installed${NC}"
}

set_permissions() {
    echo -e "${CYAN}[7/7] Setting permissions...${NC}"

    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    chmod 600 "$INSTALL_DIR/config/config.yaml" 2>/dev/null || true

    echo -e "${GREEN}✓ Permissions set${NC}"
}

print_success() {
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Installation Complete!                ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo
    echo "Installation directory: $INSTALL_DIR"
    echo
    echo "Commands:"
    echo "  Start service:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
    echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
    echo "  Test display:    sudo $VENV_DIR/bin/python -m ledmatrix --test-display"
    echo
    echo "Web interface will be available at:"
    echo "  http://$(hostname -I | awk '{print $1}')"
    echo
    echo "On first boot without WiFi, connect to:"
    echo "  SSID: LED-Display-Setup"
    echo
    echo -e "${YELLOW}A reboot is recommended to ensure all changes take effect.${NC}"
    echo
    read -p "Start the service now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start "$SERVICE_NAME"
        echo -e "${GREEN}Service started!${NC}"
    fi
    echo
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        reboot
    fi
}

# Main installation flow
main() {
    print_header
    check_root
    check_platform

    echo "This script will install the LED Display System."
    echo "Installation directory: $INSTALL_DIR"
    echo
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi

    install_system_deps
    install_rgb_matrix
    setup_install_dir
    setup_venv
    setup_network_manager
    install_service
    set_permissions
    print_success
}

main "$@"
