from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import (
    GymSplit,
    IntensityZone,
    MuscleRegion,
    RiskLevel,
    SportType,
)


class RiskFactor(BaseModel):
    name: str
    contribution: float = Field(..., description="Contribution to risk score")
    description: str
    value: float | None = None


class Recommendation(BaseModel):
    sport_type: SportType
    duration_minutes: int
    intensity: IntensityZone | None = None
    gym_split: GymSplit | None = None
    intensity_level: str | None = Field(None, description="light/moderate/hard for gym")
    reason: str
    is_original_plan_modified: bool = False


class SafetyRuleTriggered(BaseModel):
    rule_id: str  # e.g., "R0", "R1", "R2", "R3", "R4"
    rule_name: str
    description: str
    blocked_sports: list[SportType] = []
    max_allowed_intensity: IntensityZone | None = None
    blocked_muscle_regions: list[MuscleRegion] = []


class PredictionRequest(BaseModel):
    planned_session_id: int


class PredictionResponse(BaseModel):
    id: int
    planned_session_id: int
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    top_factors: list[RiskFactor]
    explanation_text: str
    triggered_safety_rules: list[SafetyRuleTriggered] = []
    recommendation_a: Recommendation
    recommendation_b: Recommendation
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuickEvaluateRequest(BaseModel):
    """For quick evaluation without saving a planned session first."""
    sport_type: SportType
    planned_duration_minutes: int = Field(..., ge=1)
    planned_intensity: IntensityZone | None = None
    gym_split: GymSplit | None = None
    goal: str | None = None


class QuickEvaluateResponse(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    top_factors: list[RiskFactor]
    explanation_text: str
    triggered_safety_rules: list[SafetyRuleTriggered] = []
    recommendation_a: Recommendation
    recommendation_b: Recommendation


class LabelCreate(BaseModel):
    planned_session_id: int | None = None
    label_date: datetime
    overload_event: bool
    reason: str
    severity: int = Field(0, ge=0, le=3)
    notes: str | None = None


class LabelResponse(BaseModel):
    id: int
    user_id: int
    planned_session_id: int | None
    label_date: datetime
    overload_event: bool
    reason: str
    severity: int
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
