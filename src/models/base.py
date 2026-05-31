"""
SQLAlchemy declarative base for all ORM models.
"""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass
