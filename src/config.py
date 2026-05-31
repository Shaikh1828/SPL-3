"""
Configuration module for the Archery Scoring System backend.

Loads environment variables and provides configuration for:
- Database connection pool
- Redis cache
- JWT authentication
- CORS
- Logging
- Storage
- Rate limiting
"""

import os
from typing import List, Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_title: str = "Archery Scoring System"
    api_version: str = "0.1.0"
    api_workers: int = 4

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/archery"
    sqlalchemy_echo: bool = False
    database_pool_min_size: int = 5
    database_pool_max_size: int = 20
    database_pool_recycle: int = 3600
    database_pool_pre_ping: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    redis_socket_connect_timeout: int = 5
    redis_socket_keepalive: bool = True
    redis_socket_keepalive_options: dict = {
        1: (9, 3),  # TCP_KEEPIDLE: 3 seconds, TCP_KEEPINTVL: 3 seconds
        2: (9, 3),
    }
    redis_memory_limit_mb: int = 512

    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 8
    refresh_token_expiration_days: int = 30

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "*"

    # Storage
    storage_path: str = "/storage"
    storage_quota_gb: int = 10

    # Rate Limiting
    rate_limit_requests_per_minute: int = 1000

    # Image Processing
    image_jpeg_quality: int = 70
    image_resize_width: int = 1024
    image_resize_height: int = 1024

    # WebSocket
    websocket_disconnect_grace_period_seconds: int = 30
    websocket_message_batch_window_ms: int = 100
    websocket_message_batch_max_events: int = 10

    # ThreadPool
    threadpool_base_workers: int = 4
    threadpool_max_workers: int = 8
    threadpool_cpu_threshold_percent: int = 80

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL from settings."""
    return settings.database_url


def get_redis_url() -> str:
    """Get Redis URL from settings."""
    return settings.redis_url


def get_jwt_secret() -> str:
    """Get JWT secret from settings."""
    return settings.jwt_secret


def get_jwt_algorithm() -> str:
    """Get JWT algorithm from settings."""
    return settings.jwt_algorithm


def get_jwt_expiration_hours() -> int:
    """Get JWT expiration hours from settings."""
    return settings.jwt_expiration_hours


def get_storage_path() -> str:
    """Get storage path, creating directories if needed."""
    path = settings.storage_path
    for subdir in ["raw", "annotated", "archives", "reports"]:
        subpath = os.path.join(path, subdir)
        os.makedirs(subpath, exist_ok=True)
    return path


def get_cors_origins() -> List[str]:
    """Get CORS origins from settings."""
    if isinstance(settings.cors_origins, str):
        return [origin.strip() for origin in settings.cors_origins.split(",")]
    return settings.cors_origins


def get_cors_allow_methods() -> List[str]:
    """Get CORS allow methods from settings."""
    if isinstance(settings.cors_allow_methods, str):
        return [method.strip() for method in settings.cors_allow_methods.split(",")]
    return settings.cors_allow_methods


def get_cors_allow_headers() -> List[str]:
    """Get CORS allow headers from settings."""
    if isinstance(settings.cors_allow_headers, str):
        headers = settings.cors_allow_headers
        if headers == "*":
            return ["*"]
        return [header.strip() for header in headers.split(",")]
    return settings.cors_allow_headers
