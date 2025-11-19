#!/bin/bash

# Installation script for I2P Monitor Display on Raspberry Pi
# This script installs drivers for 3.5" LCD and required dependencies

set -e

echo "=========================================="
echo "I2P Monitor Display Installation Script"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt-get update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y python3-pip python3-dev python3-setuptools
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
sudo apt-get install -y libfreetype6-dev libjpeg-dev libportmidi-dev
sudo apt-get install -y git cmake

# Install LCD driver (for 3.5" RPi Display)
echo ""
echo "=========================================="
echo "LCD Driver Installation"
echo "=========================================="
echo "The 3.5\" RPi Display requires a specific driver."
echo "Please follow these steps:"
echo ""
echo "1. Clone the LCD driver repository:"
echo "   git clone https://github.com/goodtft/LCD-show.git"
echo "   cd LCD-show"
echo ""
echo "2. Run the appropriate installation script:"
echo "   For 3.5\" LCD (480x320): sudo ./LCD35-show"
echo "   For 3.5\" LCD (320x480): sudo ./LCD35-show 90"
echo ""
echo "3. The system will reboot after driver installation"
echo ""
echo "For detailed instructions, visit:"
echo "https://www.lcdwiki.com/3.5inch_RPi_Display"
echo ""
read -p "Have you already installed the LCD driver? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please install the LCD driver first, then run this script again."
    exit 0
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create systemd service (optional)
echo ""
read -p "Do you want to create a systemd service to auto-start the display? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    SERVICE_FILE="/etc/systemd/system/i2p-monitor.service"

    echo "Creating systemd service..."
    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=I2P Monitor Display
After=network.target i2p.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
Environment=DISPLAY=:0
Environment=SDL_VIDEODRIVER=fbcon
Environment=SDL_FBDEV=/dev/fb1
ExecStart=/usr/bin/python3 $SCRIPT_DIR/src/display.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable i2p-monitor.service

    echo "Service created and enabled."
    echo "Start with: sudo systemctl start i2p-monitor"
    echo "Check status: sudo systemctl status i2p-monitor"
fi

# Enable I2PControl plugin
echo ""
echo "=========================================="
echo "I2PControl Configuration"
echo "=========================================="
echo "To use this monitor, you need to enable the I2PControl plugin in your I2P router:"
echo ""
echo "1. Open I2P Router Console (http://127.0.0.1:7657)"
echo "2. Go to Applications -> Plugins"
echo "3. Find 'I2PControl' and click 'Install'"
echo "4. After installation, go to http://127.0.0.1:7657/configclients"
echo "5. Configure I2PControl settings:"
echo "   - Enable I2PControl"
echo "   - Port: 7650 (default)"
echo "   - Password: Set a password (default is 'itoopie')"
echo "6. Update config/config.json with your I2PControl settings"
echo ""

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Place an I2P mascot GIF in assets/i2p_mascot.gif"
echo "2. Configure settings in config/config.json"
echo "3. Ensure I2P router is running with I2PControl enabled"
echo "4. Run the display: python3 src/display.py"
echo ""
echo "For more information, see README.md"
echo ""
