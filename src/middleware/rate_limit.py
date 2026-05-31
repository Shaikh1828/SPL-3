"""
Rate limiting middleware and utilities.

Pattern #17: Rate Limiting

Implements per-IP rate limiting at 1000 requests/minute.
"""

from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

logger = structlog.get_logger()

# In-memory rate limit store: {ip_address: [(timestamp, count), ...]}
rate_limit_store = defaultdict(list)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 1000


class RateLimitMiddleware:
    """
    Middleware for per-IP rate limiting.

    Pattern #17: Rate Limiting
    
    Limits: 1000 requests per minute per IP address.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get client IP
        client = scope.get("client")
        if not client:
            await self.app(scope, receive, send)
            return

        ip_address = client[0]

        # Check rate limit
        is_allowed, remaining = self._check_rate_limit(ip_address)

        if not is_allowed:
            logger.warning("rate_limit_exceeded", ip_address=ip_address)
            
            # Send 429 Too Many Requests
            await send({
                "type": "http.response.start",
                "status": status.HTTP_429_TOO_MANY_REQUESTS,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"retry-after", b"60"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Rate limit exceeded", "retry_after": 60}',
            })
            return

        # Add rate limit info to scope for logging
        scope["rate_limit_remaining"] = remaining

        await self.app(scope, receive, send)

    @staticmethod
    def _check_rate_limit(ip_address: str) -> tuple[bool, int]:
        """
        Check if IP address is within rate limit.

        Args:
            ip_address: Client IP address

        Returns:
            (is_allowed, remaining_requests) tuple
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)

        # Get existing requests for this IP in current window
        requests = rate_limit_store[ip_address]

        # Remove old requests outside the window
        requests[:] = [req_time for req_time in requests if req_time > window_start]

        # Check if limit exceeded
        current_count = len(requests)
        remaining = RATE_LIMIT_MAX_REQUESTS - current_count

        if current_count >= RATE_LIMIT_MAX_REQUESTS:
            return False, 0

        # Add current request
        requests.append(now)

        return True, remaining - 1


def reset_rate_limits():
    """
    Reset all rate limit counters.
    
    Useful for testing and administrative operations.
    """
    rate_limit_store.clear()
    logger.info("rate_limits_reset")


def get_rate_limit_stats(ip_address: str) -> dict:
    """
    Get rate limit statistics for an IP address.

    Args:
        ip_address: Client IP address

    Returns:
        Dictionary with current request count and remaining quota
    """
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)

    requests = rate_limit_store.get(ip_address, [])
    current_count = len([req for req in requests if req > window_start])

    return {
        "ip_address": ip_address,
        "current_requests": current_count,
        "limit": RATE_LIMIT_MAX_REQUESTS,
        "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
        "remaining": max(0, RATE_LIMIT_MAX_REQUESTS - current_count),
    }
