from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False, default=datetime.utcnow)

    # Pain tracking
    pain_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-10
    pain_location: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pain_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    swelling: Mapped[bool] = mapped_column(Boolean, default=False)

    # Soreness map: {"quads": 5, "hamstrings": 3, ...}
    soreness_map: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Subjective metrics
    readiness: Mapped[int] = mapped_column(Integer, default=7)  # 0-10
    fatigue: Mapped[int] = mapped_column(Integer, default=3)  # 0-10

    # Medical tracking
    physio_visit: Mapped[bool] = mapped_column(Boolean, default=False)
    diagnosis_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="symptoms")
