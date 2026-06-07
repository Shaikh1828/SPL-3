"""
Scoring models: SessionArcher and Score.

SessionArcher: Archer participation in a session
Score: Individual arrow score with validation
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Boolean, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class SessionArcher(Base):
    """Archer participation in a scoring session."""

    __tablename__ = "session_archers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    archer_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # References user but not FK for flexibility
    archer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lane_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Assigned lane for this archer
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="session_archers")
    scores: Mapped[list["Score"]] = relationship("Score", back_populates="session_archer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_session_archer_composite", "session_id", "archer_id"),
    )

    def __repr__(self) -> str:
        return f"<SessionArcher(id={self.id}, archer_name={self.archer_name}, total_score={self.total_score})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "archer_id": self.archer_id,
            "archer_name": self.archer_name,
            "lane_number": self.lane_number,
            "current_round": self.current_round,
            "total_score": self.total_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Score(Base):
    """Individual arrow score in a session."""

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    session_archer_id: Mapped[int] = mapped_column(ForeignKey("session_archers.id"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    arrow_num: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-10 zones
    points: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-10 points
    image_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # AI detection confidence
    validated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="scores")
    session_archer: Mapped["SessionArcher"] = relationship("SessionArcher", back_populates="scores")

    __table_args__ = (
        Index("idx_score_archer_round_arrow", "session_archer_id", "round", "arrow_num"),
        Index("idx_score_session_created", "session_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Score(id={self.id}, archer={self.session_archer_id}, zone={self.zone}, points={self.points})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "session_archer_id": self.session_archer_id,
            "round": self.round,
            "arrow_num": self.arrow_num,
            "zone": self.zone,
            "points": self.points,
            "image_id": self.image_id,
            "confidence": self.confidence,
            "validated_by_ai": self.validated_by_ai,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
