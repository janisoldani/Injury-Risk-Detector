from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Prediction(Base):
    """Stored predictions for planned sessions."""
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    planned_session_id: Mapped[int] = mapped_column(
        ForeignKey("planned_sessions.id"), index=True, nullable=False
    )

    # Prediction results
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)  # green, yellow, red

    # Explanation
    top_factors: Mapped[dict] = mapped_column(JSON, default=list)  # List of {name, contribution, description}
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_safety_rules: Mapped[dict] = mapped_column(JSON, default=list)

    # Recommendations
    recommendation_a: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation_b: Mapped[dict] = mapped_column(JSON, nullable=False)

    # SHAP data (optional, can be large)
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Model metadata
    model_version: Mapped[str] = mapped_column(String(50), default="heuristic_v1")
    feature_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    planned_session = relationship("PlannedSession", back_populates="predictions")
