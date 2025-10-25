"""
Spam Protection Utilities
Basic spam filtering without external dependencies
"""

import re
from typing import Tuple

# Common spam keywords
SPAM_KEYWORDS = [
    'viagra', 'cialis', 'casino', 'poker', 'lottery', 'bitcoin',
    'crypto', 'investment', 'earn money', 'make money', 'click here',
    'buy now', 'limited time', 'act now', 'weight loss', 'diet pill'
]

def validate_comment_content(comment_text: str) -> Tuple[bool, str]:
    """
    Validate comment content for spam and quality

    Args:
        comment_text: The comment text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Strip whitespace
    text = comment_text.strip()

    # Check minimum length
    if len(text) < 10:
        return False, "Comment must be at least 10 characters long"

    # Check maximum length
    if len(text) > 2000:
        return False, "Comment must be less than 2000 characters"

    # Check for excessive URLs (more than 2)
    url_pattern = r'https?://|www\.'
    url_count = len(re.findall(url_pattern, text, re.IGNORECASE))
    if url_count > 2:
        return False, "Too many URLs in comment"

    # Check for spam keywords
    text_lower = text.lower()
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return False, "Comment contains prohibited content"

    # Check for excessive repetition (same character repeated more than 10 times)
    if re.search(r'(.)\1{10,}', text):
        return False, "Comment contains excessive repetition"

    # Check for all caps (more than 70% uppercase)
    alpha_chars = [c for c in text if c.isalpha()]
    if len(alpha_chars) > 10:
        upper_count = sum(1 for c in alpha_chars if c.isupper())
        upper_ratio = upper_count / len(alpha_chars)
        if upper_ratio > 0.7:
            return False, "Please don't use all caps"

    # Check for excessive special characters
    special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if len(text) > 0 and special_count / len(text) > 0.3:
        return False, "Comment contains too many special characters"

    return True, ""


def sanitize_comment(comment_text: str) -> str:
    """
    Sanitize comment text (basic cleanup)

    Args:
        comment_text: The comment text to sanitize

    Returns:
        Sanitized comment text
    """
    # Strip leading/trailing whitespace
    text = comment_text.strip()

    # Normalize whitespace (replace multiple spaces with single space)
    text = re.sub(r'\s+', ' ', text)

    # Remove null bytes
    text = text.replace('\x00', '')

    return text


def validate_author_info(name: str = None, email: str = None) -> Tuple[bool, str]:
    """
    Validate author name and email

    Args:
        name: Author name (optional)
        email: Author email (optional)

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Name validation (if provided)
    if name:
        name = name.strip()
        if len(name) > 100:
            return False, "Name must be less than 100 characters"

        # Check for spam patterns in name
        if re.search(r'https?://', name, re.IGNORECASE):
            return False, "Name cannot contain URLs"

    # Email validation (if provided)
    if email:
        email = email.strip()
        if len(email) > 255:
            return False, "Email must be less than 255 characters"

        # Basic email format check
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"

    return True, ""
