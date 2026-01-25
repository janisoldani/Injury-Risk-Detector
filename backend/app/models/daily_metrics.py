from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DailyMetrics(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # Garmin/Health metrics
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_rmssd: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Calculated load metrics (updated by feature pipeline)
    training_load_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    acute_load_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    chronic_load_28d: Mapped[float | None] = mapped_column(Float, nullable=True)
    acwr: Mapped[float | None] = mapped_column(Float, nullable=True)  # Acute:Chronic ratio
    monotony: Mapped[float | None] = mapped_column(Float, nullable=True)
    strain: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Baseline references (rolling 28d)
    hrv_baseline_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv_baseline_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    rhr_baseline_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_baseline_mean: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Data quality flags
    missing_fields_mask: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="daily_metrics")
