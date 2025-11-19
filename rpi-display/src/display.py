"""
Main display application for Raspberry Pi 3.5" screen.
Displays system information and I2P router statistics.
"""

import pygame
import sys
import os
from datetime import datetime
from typing import Optional, List, Tuple
from PIL import Image
import io

from i2p_client import I2PControlClient, format_bytes, format_uptime
from system_info import SystemInfo


class I2PDisplay:
    """Main display class for I2P statistics monitor."""

    # Display dimensions for 3.5" RPi display
    WIDTH = 480
    HEIGHT = 320

    # Colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    BLUE = (66, 135, 245)
    GREEN = (76, 175, 80)
    ORANGE = (255, 152, 0)
    RED = (244, 67, 54)
    GRAY = (158, 158, 158)
    DARK_GRAY = (50, 50, 50)

    def __init__(self, config: dict):
        """
        Initialize display.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Initialize pygame
        pygame.init()

        # Set up display
        if config.get("fullscreen", True):
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))

        pygame.display.set_caption("I2P Monitor")
        pygame.mouse.set_visible(False)

        # Initialize fonts
        self.font_large = pygame.font.Font(None, 32)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        # Initialize I2P client
        self.i2p_client = I2PControlClient(
            host=config.get("i2p_host", "127.0.0.1"),
            port=config.get("i2p_port", 7650),
            password=config.get("i2p_password", "itoopie")
        )

        # Initialize system info
        self.system_info = SystemInfo()

        # Load mascot gif
        self.mascot_frames = []
        self.current_frame = 0
        self.frame_delay = 100  # milliseconds
        self.last_frame_time = pygame.time.get_ticks()
        self._load_mascot()

        # Authenticate with I2P
        self.i2p_connected = False
        self._authenticate_i2p()

        # Clock for FPS control
        self.clock = pygame.time.Clock()
        self.update_interval = config.get("update_interval", 2000)  # milliseconds
        self.last_update = pygame.time.get_ticks()

        # Data cache
        self.i2p_stats = {}
        self.system_stats = {}

    def _authenticate_i2p(self):
        """Authenticate with I2P router."""
        try:
            self.i2p_connected = self.i2p_client.authenticate()
            if self.i2p_connected:
                print("Successfully connected to I2P router")
            else:
                print("Failed to authenticate with I2P router")
        except Exception as e:
            print(f"Error connecting to I2P: {e}")
            self.i2p_connected = False

    def _load_mascot(self):
        """Load I2P mascot gif frames."""
        mascot_path = self.config.get("mascot_path", "assets/i2p_mascot.gif")
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), mascot_path)

        try:
            if os.path.exists(full_path):
                gif = Image.open(full_path)

                # Extract all frames from gif
                frame_index = 0
                while True:
                    try:
                        gif.seek(frame_index)
                        # Resize to fit display (small icon in corner)
                        frame = gif.copy().convert('RGBA')
                        frame = frame.resize((80, 80), Image.Resampling.LANCZOS)

                        # Convert PIL image to pygame surface
                        mode = frame.mode
                        size = frame.size
                        data = frame.tobytes()

                        py_image = pygame.image.fromstring(data, size, mode)
                        self.mascot_frames.append(py_image)

                        frame_index += 1
                    except EOFError:
                        break

                if self.mascot_frames:
                    print(f"Loaded {len(self.mascot_frames)} mascot frames")
                else:
                    print("No frames loaded from mascot gif")
            else:
                print(f"Mascot file not found: {full_path}")
        except Exception as e:
            print(f"Error loading mascot: {e}")

    def _update_data(self):
        """Update I2P and system statistics."""
        # Update I2P stats
        if self.i2p_connected:
            stats = self.i2p_client.get_all_stats()
            if stats:
                self.i2p_stats = stats

        # Update system stats
        self.system_stats = self.system_info.get_all_info()

    def _draw_header(self):
        """Draw header section."""
        # Title
        title = self.font_large.render("I2P Monitor", True, self.BLUE)
        self.screen.blit(title, (10, 10))

        # Time
        current_time = datetime.now().strftime("%H:%M:%S")
        time_text = self.font_small.render(current_time, True, self.WHITE)
        self.screen.blit(time_text, (self.WIDTH - 80, 15))

        # Draw mascot animation
        if self.mascot_frames:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_frame_time > self.frame_delay:
                self.current_frame = (self.current_frame + 1) % len(self.mascot_frames)
                self.last_frame_time = current_time

            self.screen.blit(self.mascot_frames[self.current_frame], (self.WIDTH - 90, 40))

        # Separator line
        pygame.draw.line(self.screen, self.GRAY, (10, 45), (self.WIDTH - 10, 45), 2)

    def _draw_i2p_stats(self, y_offset: int) -> int:
        """
        Draw I2P statistics section.

        Args:
            y_offset: Y position to start drawing

        Returns:
            New Y offset after drawing
        """
        # Section title
        title = self.font_medium.render("I2P Router", True, self.GREEN)
        self.screen.blit(title, (10, y_offset))
        y_offset += 30

        if not self.i2p_connected:
            text = self.font_small.render("Not connected", True, self.RED)
            self.screen.blit(text, (20, y_offset))
            return y_offset + 25

        # Status
        status = self.i2p_stats.get("i2p.router.status", "Unknown")
        net_status = self.i2p_stats.get("i2p.router.net.status", "Unknown")
        status_text = self.font_small.render(f"Status: {status} / {net_status}", True, self.WHITE)
        self.screen.blit(status_text, (20, y_offset))
        y_offset += 20

        # Uptime
        uptime_ms = self.i2p_stats.get("i2p.router.uptime", 0)
        uptime_str = format_uptime(uptime_ms) if uptime_ms else "N/A"
        uptime_text = self.font_small.render(f"Uptime: {uptime_str}", True, self.WHITE)
        self.screen.blit(uptime_text, (20, y_offset))
        y_offset += 20

        # Bandwidth
        bw_in = self.i2p_stats.get("i2p.router.net.bw.inbound.1s", 0)
        bw_out = self.i2p_stats.get("i2p.router.net.bw.outbound.1s", 0)

        if isinstance(bw_in, (int, float)) and isinstance(bw_out, (int, float)):
            bw_in_str = format_bytes(bw_in)
            bw_out_str = format_bytes(bw_out)
            bw_text = self.font_small.render(f"BW: ↓{bw_in_str} ↑{bw_out_str}", True, self.ORANGE)
            self.screen.blit(bw_text, (20, y_offset))
            y_offset += 20

        # Peers
        active_peers = self.i2p_stats.get("i2p.router.netdb.activepeers", "N/A")
        known_peers = self.i2p_stats.get("i2p.router.netdb.knownpeers", "N/A")
        peers_text = self.font_small.render(f"Peers: {active_peers} active / {known_peers} known", True, self.WHITE)
        self.screen.blit(peers_text, (20, y_offset))
        y_offset += 20

        # Tunnels
        participating = self.i2p_stats.get("i2p.router.net.tunnels.participating", "N/A")
        tunnels_text = self.font_small.render(f"Tunnels: {participating} participating", True, self.WHITE)
        self.screen.blit(tunnels_text, (20, y_offset))
        y_offset += 25

        return y_offset

    def _draw_system_stats(self, y_offset: int) -> int:
        """
        Draw system statistics section.

        Args:
            y_offset: Y position to start drawing

        Returns:
            New Y offset after drawing
        """
        # Section title
        title = self.font_medium.render("System", True, self.GREEN)
        self.screen.blit(title, (10, y_offset))
        y_offset += 30

        # CPU
        cpu_info = self.system_stats.get("cpu", {})
        cpu_usage = cpu_info.get("usage_percent", 0)
        cpu_temp = cpu_info.get("temperature", 0)

        cpu_color = self.WHITE
        if cpu_usage > 80 or cpu_temp > 70:
            cpu_color = self.RED
        elif cpu_usage > 60 or cpu_temp > 60:
            cpu_color = self.ORANGE

        cpu_text = self.font_small.render(f"CPU: {cpu_usage:.1f}% @ {cpu_temp:.1f}°C", True, cpu_color)
        self.screen.blit(cpu_text, (20, y_offset))
        y_offset += 20

        # Memory
        mem_info = self.system_stats.get("memory", {})
        mem_percent = mem_info.get("percent", 0)
        mem_used = self.system_info.format_bytes(mem_info.get("used", 0))
        mem_total = self.system_info.format_bytes(mem_info.get("total", 0))

        mem_color = self.WHITE
        if mem_percent > 90:
            mem_color = self.RED
        elif mem_percent > 75:
            mem_color = self.ORANGE

        mem_text = self.font_small.render(f"Memory: {mem_used} / {mem_total} ({mem_percent:.1f}%)", True, mem_color)
        self.screen.blit(mem_text, (20, y_offset))
        y_offset += 20

        # Disk
        disk_info = self.system_stats.get("disk", {})
        disk_percent = disk_info.get("percent", 0)
        disk_free = self.system_info.format_bytes(disk_info.get("free", 0))

        disk_color = self.WHITE
        if disk_percent > 90:
            disk_color = self.RED
        elif disk_percent > 75:
            disk_color = self.ORANGE

        disk_text = self.font_small.render(f"Disk: {disk_free} free ({disk_percent:.1f}% used)", True, disk_color)
        self.screen.blit(disk_text, (20, y_offset))
        y_offset += 20

        return y_offset

    def _draw_footer(self):
        """Draw footer section."""
        # Connection indicator
        if self.i2p_connected:
            pygame.draw.circle(self.screen, self.GREEN, (self.WIDTH - 20, self.HEIGHT - 15), 5)
        else:
            pygame.draw.circle(self.screen, self.RED, (self.WIDTH - 20, self.HEIGHT - 15), 5)

        # Version info
        version = self.i2p_stats.get("i2p.router.version", "")
        if version:
            version_text = self.font_small.render(f"I2P v{version}", True, self.GRAY)
            self.screen.blit(version_text, (10, self.HEIGHT - 25))

    def render(self):
        """Render the display."""
        # Clear screen
        self.screen.fill(self.BLACK)

        # Draw header
        self._draw_header()

        # Draw I2P statistics
        y_pos = 60
        y_pos = self._draw_i2p_stats(y_pos)

        # Draw system statistics
        y_pos = self._draw_system_stats(y_pos)

        # Draw footer
        self._draw_footer()

        # Update display
        pygame.display.flip()

    def run(self):
        """Main event loop."""
        running = True

        # Initial data update
        self._update_data()

        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False

            # Update data periodically
            current_time = pygame.time.get_ticks()
            if current_time - self.last_update > self.update_interval:
                self._update_data()
                self.last_update = current_time

            # Render
            self.render()

            # Control FPS
            self.clock.tick(30)

        # Cleanup
        pygame.quit()
        sys.exit()


def main():
    """Main entry point."""
    # Load configuration
    import json

    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        print("Using default configuration")
        config = {
            "fullscreen": True,
            "i2p_host": "127.0.0.1",
            "i2p_port": 7650,
            "i2p_password": "itoopie",
            "update_interval": 2000,
            "mascot_path": "assets/i2p_mascot.gif"
        }

    # Create and run display
    display = I2PDisplay(config)
    display.run()


if __name__ == "__main__":
    main()
