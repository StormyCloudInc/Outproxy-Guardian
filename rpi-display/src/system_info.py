"""
System information module for Raspberry Pi.
Collects CPU, memory, disk, and network statistics.
"""

import psutil
import platform
from typing import Dict


class SystemInfo:
    """Collect and format system information."""

    @staticmethod
    def get_cpu_info() -> Dict[str, any]:
        """
        Get CPU information.

        Returns:
            Dictionary with CPU stats
        """
        return {
            "usage_percent": psutil.cpu_percent(interval=1),
            "temperature": SystemInfo._get_cpu_temperature(),
            "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0
        }

    @staticmethod
    def _get_cpu_temperature() -> float:
        """
        Get CPU temperature (Raspberry Pi specific).

        Returns:
            Temperature in Celsius or 0 if unavailable
        """
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except (FileNotFoundError, ValueError):
            # Fallback for non-RPi systems or if sensor not available
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return entries[0].current
            return 0.0

    @staticmethod
    def get_memory_info() -> Dict[str, any]:
        """
        Get memory information.

        Returns:
            Dictionary with memory stats
        """
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "used": mem.used,
            "available": mem.available,
            "percent": mem.percent
        }

    @staticmethod
    def get_disk_info() -> Dict[str, any]:
        """
        Get disk information.

        Returns:
            Dictionary with disk stats
        """
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }

    @staticmethod
    def get_network_info() -> Dict[str, any]:
        """
        Get network information.

        Returns:
            Dictionary with network stats
        """
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }

    @staticmethod
    def get_all_info() -> Dict[str, any]:
        """
        Get all system information.

        Returns:
            Dictionary with all system stats
        """
        return {
            "hostname": platform.node(),
            "cpu": SystemInfo.get_cpu_info(),
            "memory": SystemInfo.get_memory_info(),
            "disk": SystemInfo.get_disk_info(),
            "network": SystemInfo.get_network_info()
        }

    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """
        Format bytes to human-readable format.

        Args:
            bytes_value: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 GB")
        """
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.1f} MB"
        else:
            return f"{bytes_value / (1024 ** 3):.2f} GB"
