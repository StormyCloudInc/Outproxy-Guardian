import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration management for the feedback system"""

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', '../database/feedback.db')

    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # CORS - Allow access from your website domains
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Admin Panel - Restrict to localhost by default
    ADMIN_ONLY_LOCALHOST = os.getenv('ADMIN_ONLY_LOCALHOST', 'True').lower() == 'true'

    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_STORAGE = os.getenv('RATE_LIMIT_STORAGE', 'memory')

    # Rate limits per action (requests per hour)
    RATE_LIMITS = {
        'feedback': int(os.getenv('RATE_LIMIT_FEEDBACK', 10)),  # 10 feedback submissions per hour
        'vote': int(os.getenv('RATE_LIMIT_VOTE', 20)),  # 20 votes per hour
        'feature_submit': int(os.getenv('RATE_LIMIT_FEATURE_SUBMIT', 5)),  # 5 feature submissions per hour
        'feature_upvote': int(os.getenv('RATE_LIMIT_FEATURE_UPVOTE', 50)),  # 50 upvotes per hour
        'comment': int(os.getenv('RATE_LIMIT_COMMENT', 10)),  # 10 comments per hour
    }

    # Email Configuration
    SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'False').lower() == 'true'
    SMTP_HOST = os.getenv('SMTP_HOST', 'localhost')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
    SMTP_FROM = os.getenv('SMTP_FROM', 'noreply@example.com')
    SMTP_TO = os.getenv('SMTP_TO', 'admin@example.com')  # Email for thumbs down notifications

    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Network accessibility (for documentation purposes)
    CLEARNET_URL = os.getenv('CLEARNET_URL', '')
    I2P_URL = os.getenv('I2P_URL', '')
    TOR_URL = os.getenv('TOR_URL', '')

    @classmethod
    def get_api_url(cls, network='clearnet'):
        """Get the appropriate API URL for the network"""
        urls = {
            'clearnet': cls.CLEARNET_URL,
            'i2p': cls.I2P_URL,
            'tor': cls.TOR_URL
        }
        return urls.get(network, f"http://{cls.HOST}:{cls.PORT}")

config = Config()
