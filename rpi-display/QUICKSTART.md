# Quick Start Guide

Get your I2P monitor display running in minutes!

## Prerequisites

- Raspberry Pi with 3.5" LCD display connected
- I2P Router installed and running
- Internet connection (for initial setup)

## 5-Minute Setup

### 1. Install LCD Driver (First Time Only)

```bash
git clone https://github.com/goodtft/LCD-show.git
cd LCD-show
sudo ./LCD35-show
# System will reboot
```

### 2. Install I2P Monitor

```bash
cd rpi-display
./install.sh
```

### 3. Enable I2PControl

Open browser and navigate to: http://127.0.0.1:7657

1. Go to **Applications** → **Plugins**
2. Install **I2PControl**
3. Go to http://127.0.0.1:7657/configclients
4. Enable I2PControl, set password (or use default: itoopie)
5. Save settings

### 4. Add I2P Mascot (Optional)

```bash
# Download an I2P mascot gif and place it at:
# rpi-display/assets/i2p_mascot.gif
```

### 5. Configure

Edit `config/config.json` if you changed the I2PControl password:

```json
{
  "i2p_password": "your_password_here"
}
```

### 6. Test Connection

```bash
python3 test_connection.py
```

You should see all statistics displayed. If there are errors, follow the troubleshooting steps shown.

### 7. Run Display

```bash
python3 src/display.py
```

Press `ESC` or `Q` to exit.

## Auto-Start on Boot

If you want the display to start automatically:

```bash
sudo systemctl enable i2p-monitor
sudo systemctl start i2p-monitor
```

## Troubleshooting Quick Fixes

### Can't connect to I2P?
```bash
# Check I2P is running
sudo systemctl status i2p

# Restart I2P
sudo systemctl restart i2p
```

### Display not showing?
```bash
# Check LCD driver
ls /dev/fb1

# If missing, reinstall LCD driver
cd LCD-show
sudo ./LCD35-show
```

### Permission errors?
```bash
sudo usermod -a -G video $USER
sudo chmod 666 /dev/fb1
```

## What's Displayed?

### I2P Stats
- Router status and uptime
- Real-time bandwidth (download/upload)
- Connected peers
- Active tunnels

### System Stats
- CPU usage and temperature
- Memory usage
- Disk space
- Network activity

### Visual Indicators
- 🟢 Green: All good
- 🟠 Orange: Warning (high usage)
- 🔴 Red: Critical (very high usage)

## Next Steps

- See [README.md](README.md) for detailed documentation
- Customize `config/config.json` for your needs
- Add your own I2P mascot GIF
- Check logs: `sudo journalctl -u i2p-monitor -f`

## Need Help?

1. Run `python3 test_connection.py` to diagnose issues
2. Check the Troubleshooting section in README.md
3. Review I2P Router Console for I2PControl settings
4. Ensure LCD drivers are properly installed

Enjoy monitoring your I2P router! 🚀
