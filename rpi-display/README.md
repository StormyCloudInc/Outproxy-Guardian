# I2P Monitor Display for Raspberry Pi

A real-time monitoring display for I2P routers on Raspberry Pi with 3.5" LCD screen. Shows system information and I2P router statistics including bandwidth, tunnels, peers, and uptime.

## Features

- **I2P Router Statistics**
  - Real-time bandwidth monitoring (inbound/outbound)
  - Current tunnel count (participating tunnels)
  - Active and known peer counts
  - Router uptime and status
  - Network status

- **System Information**
  - CPU usage and temperature
  - Memory usage
  - Disk space
  - Network statistics

- **Display Features**
  - Animated I2P mascot GIF
  - Color-coded warnings (CPU/memory/disk thresholds)
  - Auto-refresh every 2 seconds
  - Full-screen display on 3.5" LCD

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- 3.5" SPI LCD Display (480x320 resolution)
  - Compatible with: Waveshare 3.5" RPi LCD, Kuman 3.5", ELEGOO 3.5", etc.
  - GPIO interface (SPI)
- I2P Router running on the same or network-accessible device

## Software Requirements

- Raspberry Pi OS (Raspbian)
- Python 3.7+
- I2P Router with I2PControl plugin enabled

## Installation

### 1. LCD Driver Installation

First, install the driver for your 3.5" LCD display:

```bash
# Clone LCD driver repository
git clone https://github.com/goodtft/LCD-show.git
cd LCD-show

# Install driver for 3.5" LCD (480x320)
sudo ./LCD35-show

# The system will reboot after installation
```

**Note**: Different LCD models may require different drivers. Refer to https://www.lcdwiki.com/3.5inch_RPi_Display for specific instructions for your display.

### 2. Install I2P Monitor Display

```bash
# Navigate to the project directory
cd rpi-display

# Run the installation script
chmod +x install.sh
./install.sh
```

The installation script will:
- Install system dependencies
- Install Python packages
- Optionally create a systemd service for auto-start
- Provide instructions for I2PControl setup

### 3. Enable I2PControl Plugin

1. Open I2P Router Console: http://127.0.0.1:7657
2. Navigate to **Applications** → **Plugins**
3. Find **I2PControl** and click **Install**
4. After installation, go to http://127.0.0.1:7657/configclients
5. Configure I2PControl:
   - Enable I2PControl: ✓
   - Listen Address: 127.0.0.1
   - Port: 7650
   - Password: Set your password (default: itoopie)
6. Click **Save**

### 4. Add I2P Mascot GIF

Download or create an I2P mascot GIF and place it at:

```bash
rpi-display/assets/i2p_mascot.gif
```

You can find I2P mascot images at:
- [I2P Website](https://geti2p.net)
- [I2P Graphics Repository](https://github.com/i2p/i2p.www/tree/master/www/static/images)

### 5. Configure Settings

Edit `config/config.json` to match your setup:

```json
{
  "fullscreen": true,
  "i2p_host": "127.0.0.1",
  "i2p_port": 7650,
  "i2p_password": "itoopie",
  "update_interval": 2000,
  "mascot_path": "assets/i2p_mascot.gif"
}
```

**Configuration Options**:
- `fullscreen`: Run in fullscreen mode (recommended for dedicated display)
- `i2p_host`: I2P router hostname or IP address
- `i2p_port`: I2PControl API port (default: 7650)
- `i2p_password`: I2PControl password
- `update_interval`: Data refresh interval in milliseconds (default: 2000)
- `mascot_path`: Path to I2P mascot GIF file

## Usage

### Manual Start

```bash
cd rpi-display
python3 src/display.py
```

Press `ESC` or `Q` to exit.

### Auto-Start with Systemd

If you created the systemd service during installation:

```bash
# Start the service
sudo systemctl start i2p-monitor

# Check status
sudo systemctl status i2p-monitor

# View logs
sudo journalctl -u i2p-monitor -f

# Stop the service
sudo systemctl stop i2p-monitor

# Disable auto-start
sudo systemctl disable i2p-monitor
```

## Displayed Statistics

### I2P Router Section

- **Status**: Router and network status
- **Uptime**: How long the router has been running
- **BW**: Current bandwidth (↓ inbound / ↑ outbound)
- **Peers**: Active peers / Total known peers
- **Tunnels**: Number of participating tunnels

### System Section

- **CPU**: Usage percentage and temperature
- **Memory**: Used / Total memory
- **Disk**: Free space and usage percentage

### Color Indicators

- **Green**: Normal operation
- **Orange**: Warning threshold (CPU > 60%, Memory > 75%, Disk > 75%, Temp > 60°C)
- **Red**: Critical threshold (CPU > 80%, Memory > 90%, Disk > 90%, Temp > 70°C)
- **Connection Indicator**: Green dot (connected) / Red dot (disconnected)

## Troubleshooting

### Display Not Working

1. Verify LCD driver is installed:
   ```bash
   ls /dev/fb1
   ```

2. Test LCD with fbi:
   ```bash
   sudo apt-get install fbi
   sudo fbi -d /dev/fb1 -T 1 test_image.png
   ```

3. Check environment variables in systemd service:
   ```bash
   SDL_VIDEODRIVER=fbcon
   SDL_FBDEV=/dev/fb1
   ```

### Cannot Connect to I2P

1. Verify I2P router is running:
   ```bash
   sudo systemctl status i2p
   ```

2. Check I2PControl plugin is installed and enabled in Router Console

3. Verify I2PControl settings:
   - Port 7650 is accessible
   - Password matches config.json
   - Firewall allows connections

4. Test I2PControl connection:
   ```bash
   curl -X POST http://127.0.0.1:7650/jsonrpc \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"Authenticate","params":{"API":1,"Password":"itoopie"}}'
   ```

### High CPU Usage

- Increase `update_interval` in config.json (e.g., 5000 for 5 seconds)
- Reduce mascot GIF frame count or size
- Lower display refresh rate in code (clock.tick value)

### Permission Errors

If you get framebuffer permission errors:

```bash
sudo usermod -a -G video $USER
sudo chmod 666 /dev/fb1
```

## File Structure

```
rpi-display/
├── src/
│   ├── display.py          # Main display application
│   ├── i2p_client.py       # I2PControl API client
│   └── system_info.py      # System information collector
├── config/
│   └── config.json         # Configuration file
├── assets/
│   └── i2p_mascot.gif      # I2P mascot animation
├── requirements.txt        # Python dependencies
├── install.sh             # Installation script
└── README.md              # This file
```

## I2PControl API Reference

The application uses the I2PControl JSON-RPC API to retrieve statistics:

- **Authentication**: `Authenticate` method with password
- **Router Info**: `RouterInfo` method with requested parameters
- **Statistics Retrieved**:
  - `i2p.router.uptime`: Router uptime in milliseconds
  - `i2p.router.version`: I2P version
  - `i2p.router.status`: Router status
  - `i2p.router.net.status`: Network status
  - `i2p.router.net.bw.inbound.1s`: Inbound bandwidth (1s avg)
  - `i2p.router.net.bw.outbound.1s`: Outbound bandwidth (1s avg)
  - `i2p.router.net.tunnels.participating`: Participating tunnel count
  - `i2p.router.netdb.activepeers`: Active peer count
  - `i2p.router.netdb.knownpeers`: Known peer count

For more information, see: https://geti2p.net/en/docs/api/i2pcontrol

## Future Enhancements

Planned features for future versions:

- Historical bandwidth graphs
- Peer connection map
- Tunnel activity visualization
- Multiple display pages (swipe/button navigation)
- Alert notifications for issues
- Configuration web interface
- Support for multiple I2P routers
- Export statistics to file/database

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is part of the Outproxy-Guardian suite.

## Resources

- [I2P Project](https://geti2p.net)
- [I2PControl API Documentation](https://geti2p.net/en/docs/api/i2pcontrol)
- [3.5" RPi LCD Wiki](https://www.lcdwiki.com/3.5inch_RPi_Display)
- [Pygame Documentation](https://www.pygame.org/docs/)

## Support

For issues or questions:
- Check the troubleshooting section above
- Review I2P documentation
- Check LCD display documentation
- Submit an issue on GitHub
