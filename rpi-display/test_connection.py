#!/usr/bin/env python3
"""
Test script to verify I2PControl connection and display available statistics.
Run this before starting the main display to ensure everything is configured correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from i2p_client import I2PControlClient, format_bytes, format_uptime
from system_info import SystemInfo
import json


def test_i2p_connection(config):
    """Test I2P connection and display stats."""
    print("=" * 60)
    print("I2P CONNECTION TEST")
    print("=" * 60)
    print()

    print(f"Connecting to I2P at {config['i2p_host']}:{config['i2p_port']}...")

    client = I2PControlClient(
        host=config['i2p_host'],
        port=config['i2p_port'],
        password=config['i2p_password']
    )

    # Authenticate
    print("Authenticating...")
    if not client.authenticate():
        print("❌ Authentication failed!")
        print()
        print("Troubleshooting:")
        print("1. Check that I2P router is running")
        print("2. Verify I2PControl plugin is installed and enabled")
        print("3. Check that the password in config.json matches I2PControl settings")
        print("4. Verify port 7650 is accessible")
        return False

    print("✓ Authentication successful!")
    print()

    # Get all stats
    print("Retrieving statistics...")
    stats = client.get_all_stats()

    if not stats:
        print("❌ Failed to retrieve statistics!")
        return False

    print("✓ Statistics retrieved successfully!")
    print()

    # Display stats
    print("=" * 60)
    print("I2P ROUTER STATISTICS")
    print("=" * 60)
    print()

    # Router info
    version = stats.get("i2p.router.version", "Unknown")
    status = stats.get("i2p.router.status", "Unknown")
    net_status = stats.get("i2p.router.net.status", "Unknown")
    uptime_ms = stats.get("i2p.router.uptime", 0)

    print(f"Version:        {version}")
    print(f"Status:         {status}")
    print(f"Network Status: {net_status}")
    print(f"Uptime:         {format_uptime(uptime_ms)}")
    print()

    # Bandwidth
    print("BANDWIDTH")
    print("-" * 60)
    bw_in_1s = stats.get("i2p.router.net.bw.inbound.1s", 0)
    bw_out_1s = stats.get("i2p.router.net.bw.outbound.1s", 0)
    bw_in_15s = stats.get("i2p.router.net.bw.inbound.15s", 0)
    bw_out_15s = stats.get("i2p.router.net.bw.outbound.15s", 0)

    print(f"Inbound (1s):   {format_bytes(bw_in_1s)}")
    print(f"Outbound (1s):  {format_bytes(bw_out_1s)}")
    print(f"Inbound (15s):  {format_bytes(bw_in_15s)}")
    print(f"Outbound (15s): {format_bytes(bw_out_15s)}")
    print()

    # Peers
    print("PEERS")
    print("-" * 60)
    active_peers = stats.get("i2p.router.netdb.activepeers", "N/A")
    known_peers = stats.get("i2p.router.netdb.knownpeers", "N/A")
    fast_peers = stats.get("i2p.router.netdb.fastpeers", "N/A")
    high_cap_peers = stats.get("i2p.router.netdb.highcapacitypeers", "N/A")

    print(f"Active Peers:        {active_peers}")
    print(f"Known Peers:         {known_peers}")
    print(f"Fast Peers:          {fast_peers}")
    print(f"High Capacity Peers: {high_cap_peers}")
    print()

    # Tunnels
    print("TUNNELS")
    print("-" * 60)
    participating = stats.get("i2p.router.net.tunnels.participating", "N/A")
    print(f"Participating Tunnels: {participating}")
    print()

    # All available fields
    print("ALL AVAILABLE FIELDS")
    print("-" * 60)
    for key, value in sorted(stats.items()):
        if key != "Token":  # Don't display token
            print(f"{key}: {value}")

    print()
    return True


def test_system_info():
    """Test system information retrieval."""
    print()
    print("=" * 60)
    print("SYSTEM INFORMATION TEST")
    print("=" * 60)
    print()

    sys_info = SystemInfo()
    stats = sys_info.get_all_info()

    # CPU
    print("CPU")
    print("-" * 60)
    cpu = stats['cpu']
    print(f"Usage:       {cpu['usage_percent']:.1f}%")
    print(f"Temperature: {cpu['temperature']:.1f}°C")
    print(f"Frequency:   {cpu['frequency']:.1f} MHz")
    print()

    # Memory
    print("MEMORY")
    print("-" * 60)
    mem = stats['memory']
    print(f"Total:     {SystemInfo.format_bytes(mem['total'])}")
    print(f"Used:      {SystemInfo.format_bytes(mem['used'])}")
    print(f"Available: {SystemInfo.format_bytes(mem['available'])}")
    print(f"Usage:     {mem['percent']:.1f}%")
    print()

    # Disk
    print("DISK")
    print("-" * 60)
    disk = stats['disk']
    print(f"Total: {SystemInfo.format_bytes(disk['total'])}")
    print(f"Used:  {SystemInfo.format_bytes(disk['used'])}")
    print(f"Free:  {SystemInfo.format_bytes(disk['free'])}")
    print(f"Usage: {disk['percent']:.1f}%")
    print()

    # Network
    print("NETWORK")
    print("-" * 60)
    net = stats['network']
    print(f"Bytes Sent:     {SystemInfo.format_bytes(net['bytes_sent'])}")
    print(f"Bytes Received: {SystemInfo.format_bytes(net['bytes_recv'])}")
    print(f"Packets Sent:   {net['packets_sent']}")
    print(f"Packets Recv:   {net['packets_recv']}")
    print()


def main():
    """Main entry point."""
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        print("Please create config/config.json")
        return

    # Test I2P connection
    i2p_ok = test_i2p_connection(config)

    # Test system info
    test_system_info()

    # Summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print()

    if i2p_ok:
        print("✓ I2P Connection: OK")
    else:
        print("❌ I2P Connection: FAILED")

    print("✓ System Information: OK")

    # Check mascot
    mascot_path = os.path.join(os.path.dirname(__file__), config.get("mascot_path", "assets/i2p_mascot.gif"))
    if os.path.exists(mascot_path):
        print(f"✓ Mascot GIF: Found ({mascot_path})")
    else:
        print(f"⚠ Mascot GIF: Not found ({mascot_path})")
        print("  Display will work but without animated mascot")

    print()

    if i2p_ok:
        print("🎉 All tests passed! You can now run: python3 src/display.py")
    else:
        print("⚠ Some tests failed. Please fix the issues above before running the display.")

    print()


if __name__ == "__main__":
    main()
