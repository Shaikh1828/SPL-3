"""
Utility functions and constants.

Includes validators, helpers, and application constants.
"""

import re
from typing import Tuple
from datetime import datetime

# ============================================================================
# Constants
# ============================================================================

# Scoring constants
ARROW_ZONES = list(range(0, 11))  # 0-10
ARROW_POINTS = list(range(0, 11))  # 0-10 points
MIN_ROUND = 1
MAX_ROUND = 20
MAX_ARROWS_PER_ROUND = 6

# Camera constants
CAMERA_TYPES = ["USB", "RTSP", "HTTP"]
CAMERA_STATUSES = ["connected", "disconnected", "error"]

# Session constants
SESSION_STATUSES = ["active", "paused", "completed"]

# User constants
USER_ROLES = ["admin", "scorer", "spectator", "archer"]
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRES_UPPER = True
PASSWORD_REQUIRES_LOWER = True
PASSWORD_REQUIRES_DIGIT = True
PASSWORD_REQUIRES_SPECIAL = True

# Report formats
REPORT_FORMATS = ["pdf", "csv", "json"]

# Pagination
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 1000
DEFAULT_SKIP = 0

# Storage
STORAGE_QUOTA_GB = 10
STORAGE_QUOTA_BYTES = STORAGE_QUOTA_GB * 1024 * 1024 * 1024
IMAGE_JPEG_QUALITY = 70
IMAGE_MAX_WIDTH = 1024
IMAGE_MAX_HEIGHT = 1024

# Performance targets
WEBSOCKET_GRACE_PERIOD_SECONDS = 30
MESSAGE_BATCH_WINDOW_MS = 100
MESSAGE_BATCH_MAX_EVENTS = 10
EVENT_PUBLISH_TARGET_MS = 500

# API timeouts
DATABASE_TIMEOUT_SECONDS = 5
CACHE_TIMEOUT_SECONDS = 5
IMAGE_PROCESSING_TIMEOUT_SECONDS = 10

# ============================================================================
# Validators
# ============================================================================


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        (is_valid, error_message) tuple
    """
    # Simple email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format.

    Requirements:
    - 3-32 characters
    - Alphanumeric and underscore only
    - Must start with letter

    Args:
        username: Username to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if len(username) < 3 or len(username) > 32:
        return False, "Username must be 3-32 characters"
    
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", username):
        return False, "Username must start with letter, contain only letters, numbers, and underscore"
    
    return True, ""


def validate_zone(zone: int) -> Tuple[bool, str]:
    """
    Validate arrow zone (0-10).

    Args:
        zone: Zone value to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if zone not in ARROW_ZONES:
        return False, f"Zone must be between 0 and 10, got {zone}"
    
    return True, ""


def validate_points(points: int) -> Tuple[bool, str]:
    """
    Validate arrow points (0-10).

    Args:
        points: Points value to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if points not in ARROW_POINTS:
        return False, f"Points must be between 0 and 10, got {points}"
    
    return True, ""


def validate_round(round_num: int) -> Tuple[bool, str]:
    """
    Validate round number.

    Args:
        round_num: Round number to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if round_num < MIN_ROUND or round_num > MAX_ROUND:
        return False, f"Round must be between {MIN_ROUND} and {MAX_ROUND}"
    
    return True, ""


def validate_arrow_number(arrow_num: int) -> Tuple[bool, str]:
    """
    Validate arrow number in round.

    Args:
        arrow_num: Arrow number to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if arrow_num < 1 or arrow_num > MAX_ARROWS_PER_ROUND:
        return False, f"Arrow number must be between 1 and {MAX_ARROWS_PER_ROUND}"
    
    return True, ""


def validate_camera_type(camera_type: str) -> Tuple[bool, str]:
    """
    Validate camera type.

    Args:
        camera_type: Camera type to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if camera_type not in CAMERA_TYPES:
        return False, f"Camera type must be one of: {', '.join(CAMERA_TYPES)}"
    
    return True, ""


def validate_session_status(status: str) -> Tuple[bool, str]:
    """
    Validate session status.

    Args:
        status: Status to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if status not in SESSION_STATUSES:
        return False, f"Status must be one of: {', '.join(SESSION_STATUSES)}"
    
    return True, ""


def validate_user_role(role: str) -> Tuple[bool, str]:
    """
    Validate user role.

    Args:
        role: Role to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if role not in USER_ROLES:
        return False, f"Role must be one of: {', '.join(USER_ROLES)}"
    
    return True, ""


# ============================================================================
# Date/Time Helpers
# ============================================================================


def get_utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


def format_iso_timestamp(dt: datetime = None) -> str:
    """
    Format datetime as ISO 8601 string.

    Args:
        dt: Datetime to format (defaults to now)

    Returns:
        ISO 8601 formatted string
    """
    if dt is None:
        dt = datetime.utcnow()
    
    return dt.isoformat() + "Z"


# ============================================================================
# String Helpers
# ============================================================================


def truncate_string(text: str, max_length: int) -> str:
    """
    Truncate string to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text
