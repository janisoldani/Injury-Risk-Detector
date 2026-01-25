from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # Core workout data
    sport_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Heart rate data
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Performance data
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_effect: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Intensity
    intensity_zone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gym_split: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Calculated metrics
    trimp: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # garmin, manual, etc.
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ID from Garmin/etc.

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="workouts")
    planned_session = relationship("PlannedSession", back_populates="completed_workout", uselist=False)
