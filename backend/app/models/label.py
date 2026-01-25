from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Label(Base):
    """Labels for ML training - tracks overload/injury events."""
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    planned_session_id: Mapped[int | None] = mapped_column(ForeignKey("planned_sessions.id"), nullable=True)

    # Label data
    label_date: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    overload_event: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)  # pain, soreness, fatigue, injury, illness, no_time
    severity: Mapped[int] = mapped_column(Integer, default=0)  # 0-3
    target_horizon: Mapped[str] = mapped_column(String(20), default="next_session")

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="labels")
    planned_session = relationship("PlannedSession", back_populates="labels")
