from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    sport_profile: Mapped[str] = mapped_column(String(50), default="high_training_load")
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Zurich")
    device_sources: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    daily_metrics = relationship("DailyMetrics", back_populates="user", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    planned_sessions = relationship("PlannedSession", back_populates="user", cascade="all, delete-orphan")
    symptoms = relationship("Symptom", back_populates="user", cascade="all, delete-orphan")
    labels = relationship("Label", back_populates="user", cascade="all, delete-orphan")
