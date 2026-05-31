"""
Tournament and Session models.

Tournament: Container for multiple scoring sessions
Session: Active scoring event within a tournament
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Tournament(Base):
    """Tournament model representing an archery competition."""

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship("User", back_populates="tournaments")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="tournament")

    def __repr__(self) -> str:
        return f"<Tournament(id={self.id}, name={self.name}, location={self.location})>"

    def to_dict(self) -> dict:
        """Convert tournament to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Session(Base):
    """Scoring session within a tournament."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, paused, completed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="sessions")
    session_archers: Mapped[list["SessionArcher"]] = relationship(
        "SessionArcher", back_populates="session"
    )
    scores: Mapped[list["Score"]] = relationship("Score", back_populates="session", cascade="all, delete-orphan")
    camera_assignments: Mapped[list["CameraLaneAssignment"]] = relationship(
        "CameraLaneAssignment", back_populates="session"
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, tournament_id={self.tournament_id}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "tournament_id": self.tournament_id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
