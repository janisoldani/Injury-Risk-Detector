from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlannedSession(Base):
    __tablename__ = "planned_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # Planned session details
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)
    planned_start_time: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_intensity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gym_split: Mapped[str | None] = mapped_column(String(20), nullable=True)
    goal: Mapped[str] = mapped_column(String(50), default="endurance")
    priority: Mapped[int] = mapped_column(Integer, default=1)

    # Completion tracking
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_workout_id: Mapped[int | None] = mapped_column(ForeignKey("workouts.id"), nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="planned_sessions")
    completed_workout = relationship("Workout", back_populates="planned_session", foreign_keys=[completed_workout_id])
    predictions = relationship("Prediction", back_populates="planned_session", cascade="all, delete-orphan")
    labels = relationship("Label", back_populates="planned_session")
