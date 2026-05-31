"""
Database module for SQLAlchemy configuration and session management.

Handles:
- Database connection pool configuration (Pattern #14)
- Session factory creation
- Connection retry logic with exponential backoff (Pattern #1)
- Database health checks
"""

import asyncio
import time
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.config import settings

# Database engine configuration (Pattern #14: Connection Pool Tuning)
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_min_size,
    max_overflow=settings.database_pool_max_size - settings.database_pool_min_size,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=settings.database_pool_pre_ping,
    echo=settings.sqlalchemy_echo,
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
    },
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Configure connection parameters on connect."""
    dbapi_conn.isolation_level = None  # autocommit mode


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.

    Yields:
        SQLAlchemy Session instance

    Raises:
        Exception: If database connection fails after retries
    """
    db = None
    try:
        db = get_db_connection_with_retry(max_retries=3)
        yield db
    finally:
        if db:
            db.close()


def get_db_connection_with_retry(
    max_retries: int = 3, base_backoff: float = 1.0
) -> Session:
    """
    Get a database connection with exponential backoff retry logic.

    Implements Pattern #1: Database Connection Resilience

    Args:
        max_retries: Maximum number of retry attempts
        base_backoff: Base backoff time in seconds (2^n formula)

    Returns:
        SQLAlchemy Session instance

    Raises:
        OperationalError: If all retry attempts fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test connection
            db.execute(text("SELECT 1"))
            return db
        except OperationalError as e:
            last_error = e
            if attempt < max_retries - 1:
                backoff_time = base_backoff * (2 ** attempt)
                time.sleep(backoff_time)
            else:
                break
        except Exception as e:
            last_error = e
            break

    raise last_error or OperationalError("Failed to connect to database", None, None)


def verify_database_connectivity() -> bool:
    """
    Verify database connectivity for health checks.

    Returns:
        True if connected successfully, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False


def run_migrations():
    """Run Alembic database migrations."""
    from alembic.config import Config
    from alembic.command import upgrade

    alembic_cfg = Config("alembic.ini")
    upgrade(alembic_cfg, "head")


def init_db():
    """
    Initialize database.

    Creates all tables defined in models.
    """
    from src.models.base import Base  # Import after models are defined

    Base.metadata.create_all(bind=engine)


def dispose_engine():
    """Dispose database engine connections."""
    engine.dispose()
