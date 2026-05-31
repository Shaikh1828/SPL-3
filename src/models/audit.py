"""
Audit log model for compliance and investigation.

Records all important system events for audit trails.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class AuditLog(Base):
    """Audit log for system actions and compliance."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # login, logout, score_recorded, etc.
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # user, tournament, session, score, camera
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for additional details
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type}:{self.resource_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
