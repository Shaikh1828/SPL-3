"""
Cache module for Redis-based caching.

Handles:
- TTL-based caching (Pattern #11, #13)
- Cache invalidation
- Leaderboard caching
- Session data caching
- Camera status caching
"""

import json
import time
import fnmatch
from typing import Any, Optional

import redis
import structlog

from src.config import settings

logger = structlog.get_logger()


class CacheManager:
    """Redis-based cache manager with TTL support and graceful in-memory fallback."""

    def __init__(self):
        """Initialize Redis connection pool and in-memory fallback store."""
        self._memory_cache: dict[str, Any] = {}
        self._memory_expiry: dict[str, float] = {}
        self._redis_disabled_until: float = 0.0

        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                socket_connect_timeout=min(settings.redis_socket_connect_timeout, 1.0),
                socket_timeout=1.0,
                socket_keepalive=settings.redis_socket_keepalive,
                decode_responses=True,
            )
        except Exception:
            self.redis_client = None

    def _is_redis_ready(self) -> bool:
        """Check if Redis client is available and not in backoff period."""
        if not self.redis_client:
            return False
        if time.time() < self._redis_disabled_until:
            return False
        return True

    def _mark_redis_failed(self, error: Exception):
        """Back off Redis for 30 seconds when connection fails to prevent latency degradation."""
        self._redis_disabled_until = time.time() + 30.0
        logger.warning("redis_connection_failed_falling_back_to_memory", error=str(error))

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized) or None if not found
        """
        if self._is_redis_ready():
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                self._mark_redis_failed(e)

        # Fallback to in-memory cache
        now = time.time()
        if key in self._memory_cache:
            if now < self._memory_expiry.get(key, float("inf")):
                return self._memory_cache[key]
            else:
                self._memory_cache.pop(key, None)
                self._memory_expiry.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (default 1 hour)
        """
        # Always maintain memory cache
        self._memory_cache[key] = value
        self._memory_expiry[key] = time.time() + ttl_seconds

        if self._is_redis_ready():
            try:
                serialized = json.dumps(value)
                self.redis_client.setex(key, ttl_seconds, serialized)
                logger.debug("cache_set", key=key, ttl_seconds=ttl_seconds)
            except Exception as e:
                self._mark_redis_failed(e)

    def delete(self, key: str):
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        self._memory_cache.pop(key, None)
        self._memory_expiry.pop(key, None)

        if self._is_redis_ready():
            try:
                self.redis_client.delete(key)
                logger.debug("cache_deleted", key=key)
            except Exception as e:
                self._mark_redis_failed(e)

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "leaderboard:*")

        Returns:
            Number of keys deleted
        """
        deleted = 0
        matched_keys = [k for k in list(self._memory_cache.keys()) if fnmatch.fnmatch(k, pattern)]
        for k in matched_keys:
            self._memory_cache.pop(k, None)
            self._memory_expiry.pop(k, None)
            deleted += 1

        if self._is_redis_ready():
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    r_del = self.redis_client.delete(*keys)
                    logger.debug("cache_pattern_deleted", pattern=pattern, count=r_del)
                    return r_del
            except Exception as e:
                self._mark_redis_failed(e)

        return deleted

    def ping(self) -> bool:
        """
        Check Redis connectivity.

        Returns:
            True if connected, False otherwise
        """
        if self._is_redis_ready():
            try:
                return self.redis_client.ping()
            except Exception as e:
                self._mark_redis_failed(e)
        return False


# Global cache manager instance
cache_manager = CacheManager()


class TTLCache:
    """Simple TTL-based cache decorator."""

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize TTL cache decorator.

        Args:
            ttl_seconds: Cache time-to-live in seconds
        """
        self.ttl_seconds = ttl_seconds

    def __call__(self, func):
        """
        Cache decorator factory.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function with caching
        """

        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__module__}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug("cache_hit", cache_key=cache_key)
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, self.ttl_seconds)

            return result

        return wrapper


def get_leaderboard_cache_key(session_id: int) -> str:
    """Get cache key for leaderboard."""
    return f"leaderboard:{session_id}"


def get_session_cache_key(session_id: int) -> str:
    """Get cache key for session."""
    return f"session:{session_id}"


def get_camera_cache_key(camera_id: int) -> str:
    """Get cache key for camera."""
    return f"camera:{camera_id}"


def invalidate_leaderboard_cache(session_id: int):
    """Invalidate leaderboard cache for a session."""
    cache_manager.delete(get_leaderboard_cache_key(session_id))


def invalidate_session_cache(session_id: int):
    """Invalidate session cache."""
    cache_manager.delete(get_session_cache_key(session_id))


def invalidate_camera_cache(camera_id: int):
    """Invalidate camera cache."""
    cache_manager.delete(get_camera_cache_key(camera_id))
