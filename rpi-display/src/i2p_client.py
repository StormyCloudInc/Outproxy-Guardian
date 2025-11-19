"""
I2PControl API client for retrieving I2P router statistics.
Uses JSON-RPC 2.0 protocol to communicate with I2P router.
"""

import json
import requests
import hmac
import hashlib
import time
from typing import Dict, Optional, Any


class I2PControlClient:
    """Client for I2PControl JSON-RPC API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7650, password: str = "itoopie"):
        """
        Initialize I2PControl client.

        Args:
            host: I2P router host address
            port: I2PControl API port (default: 7650)
            password: I2PControl password (default: itoopie)
        """
        self.url = f"http://{host}:{port}/jsonrpc"
        self.password = password
        self.token = None
        self.request_id = 0

    def _get_request_id(self) -> int:
        """Generate unique request ID."""
        self.request_id += 1
        return self.request_id

    def _make_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Make JSON-RPC request to I2PControl API.

        Args:
            method: API method name
            params: Method parameters

        Returns:
            Response data or None on error
        """
        if self.token:
            params["Token"] = self.token

        payload = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": method,
            "params": params
        }

        try:
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                print(f"I2PControl error: {result['error']}")
                return None

            return result.get("result", {})
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None

    def authenticate(self) -> bool:
        """
        Authenticate with I2PControl API.

        Returns:
            True if authentication successful
        """
        params = {
            "API": 1,
            "Password": self.password
        }

        result = self._make_request("Authenticate", params)
        if result and "Token" in result:
            self.token = result["Token"]
            return True
        return False

    def get_router_info(self) -> Optional[Dict]:
        """
        Get basic router information.

        Returns:
            Dictionary with router info or None
        """
        params = {
            "i2p.router.uptime": "",
            "i2p.router.version": "",
            "i2p.router.status": "",
            "i2p.router.net.status": ""
        }

        return self._make_request("RouterInfo", params)

    def get_bandwidth_stats(self) -> Optional[Dict]:
        """
        Get bandwidth statistics.

        Returns:
            Dictionary with bandwidth stats (1s and 15s averages)
        """
        params = {
            "i2p.router.net.bw.inbound.1s": "",
            "i2p.router.net.bw.inbound.15s": "",
            "i2p.router.net.bw.outbound.1s": "",
            "i2p.router.net.bw.outbound.15s": ""
        }

        return self._make_request("RouterInfo", params)

    def get_tunnel_stats(self) -> Optional[Dict]:
        """
        Get tunnel statistics.

        Returns:
            Dictionary with tunnel counts
        """
        params = {
            "i2p.router.net.tunnels.participating": "",
            "i2p.router.net.tunnels.inbound.count": "",
            "i2p.router.net.tunnels.outbound.count": ""
        }

        result = self._make_request("RouterInfo", params)
        return result

    def get_peer_stats(self) -> Optional[Dict]:
        """
        Get peer statistics.

        Returns:
            Dictionary with peer information
        """
        params = {
            "i2p.router.netdb.activepeers": "",
            "i2p.router.netdb.knownpeers": "",
            "i2p.router.netdb.fastpeers": "",
            "i2p.router.netdb.highcapacitypeers": ""
        }

        return self._make_request("RouterInfo", params)

    def get_all_stats(self) -> Optional[Dict]:
        """
        Get all statistics in a single request.

        Returns:
            Dictionary with all available statistics
        """
        params = {
            # Router info
            "i2p.router.uptime": "",
            "i2p.router.version": "",
            "i2p.router.status": "",
            "i2p.router.net.status": "",
            # Bandwidth
            "i2p.router.net.bw.inbound.1s": "",
            "i2p.router.net.bw.inbound.15s": "",
            "i2p.router.net.bw.outbound.1s": "",
            "i2p.router.net.bw.outbound.15s": "",
            # Tunnels
            "i2p.router.net.tunnels.participating": "",
            # Peers
            "i2p.router.netdb.activepeers": "",
            "i2p.router.netdb.knownpeers": "",
            "i2p.router.netdb.fastpeers": "",
            "i2p.router.netdb.highcapacitypeers": ""
        }

        return self._make_request("RouterInfo", params)


def format_bytes(bytes_per_sec: float) -> str:
    """
    Format bytes per second to human-readable format.

    Args:
        bytes_per_sec: Bandwidth in bytes per second

    Returns:
        Formatted string (e.g., "1.5 MB/s")
    """
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.1f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"


def format_uptime(milliseconds: int) -> str:
    """
    Format uptime from milliseconds to human-readable format.

    Args:
        milliseconds: Uptime in milliseconds

    Returns:
        Formatted string (e.g., "2d 5h 30m")
    """
    seconds = milliseconds / 1000
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
