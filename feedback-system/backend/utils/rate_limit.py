import sqlite3
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Custom rate limiter using database storage"""

    def __init__(self, db_path):
        self.db_path = db_path

    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def check_rate_limit(self, ip_address, action_type, action_key='', limit_per_hour=10):
        """
        Check if an IP address has exceeded the rate limit for an action

        Args:
            ip_address: IP address to check
            action_type: Type of action (e.g., 'feedback', 'vote', 'feature_submit')
            action_key: Optional additional key (e.g., document_id, poll_id)
            limit_per_hour: Maximum allowed actions per hour

        Returns:
            tuple: (is_allowed: bool, remaining: int, reset_time: datetime)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Calculate time window (1 hour ago)
            time_window = datetime.now() - timedelta(hours=1)

            # Count recent actions
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM rate_limits
                WHERE ip_address = ?
                  AND action_type = ?
                  AND action_key = ?
                  AND created_at > ?
            """, (ip_address, action_type, action_key, time_window))

            result = cursor.fetchone()
            current_count = result['count'] if result else 0

            # Clean up old entries (older than 2 hours)
            cleanup_time = datetime.now() - timedelta(hours=2)
            cursor.execute("""
                DELETE FROM rate_limits
                WHERE created_at < ?
            """, (cleanup_time,))

            conn.commit()
            conn.close()

            is_allowed = current_count < limit_per_hour
            remaining = max(0, limit_per_hour - current_count - 1)
            reset_time = datetime.now() + timedelta(hours=1)

            return is_allowed, remaining, reset_time

        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            # On error, allow the request (fail open)
            return True, limit_per_hour, datetime.now() + timedelta(hours=1)

    def record_action(self, ip_address, action_type, action_key=''):
        """
        Record an action for rate limiting

        Args:
            ip_address: IP address performing the action
            action_type: Type of action
            action_key: Optional additional key
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO rate_limits (ip_address, action_type, action_key, created_at)
                VALUES (?, ?, ?, ?)
            """, (ip_address, action_type, action_key, datetime.now()))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to record rate limit action: {str(e)}")

    def generate_session_token(self, ip_address, user_agent=''):
        """Generate a session token for vote tracking"""
        data = f"{ip_address}:{user_agent}:{datetime.now().date()}"
        return hashlib.sha256(data.encode()).hexdigest()
