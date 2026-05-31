"""
Camera models: Camera and CameraLaneAssignment.

Camera: Physical camera device
CameraLaneAssignment: Assignment of camera to lane in session
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Camera(Base):
    """Camera device for capturing archery images."""

    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    camera_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # USB, RTSP, HTTP
    url: Mapped[str] = mapped_column(String(500), nullable=False)  # Device path or stream URL
    status: Mapped[str] = mapped_column(
        String(20), default="disconnected", nullable=False
    )  # connected, disconnected, error
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    lane_assignments: Mapped[list["CameraLaneAssignment"]] = relationship(
        "CameraLaneAssignment", back_populates="camera"
    )

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, name={self.name}, type={self.camera_type}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "camera_type": self.camera_type,
            "url": self.url,
            "status": self.status,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CameraLaneAssignment(Base):
    """Assignment of camera to lane within a session."""

    __tablename__ = "camera_lane_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    lane: Mapped[int] = mapped_column(Integer, nullable=False)  # Lane number (1-N)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    camera: Mapped["Camera"] = relationship("Camera", back_populates="lane_assignments")
    session: Mapped["Session"] = relationship("Session", back_populates="camera_assignments")

    __table_args__ = (
        Index("idx_camera_lane_session_lane", "session_id", "lane"),
        Index("idx_camera_lane_camera_session", "camera_id", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<CameraLaneAssignment(camera_id={self.camera_id}, lane={self.lane}, session_id={self.session_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "session_id": self.session_id,
            "lane": self.lane,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
