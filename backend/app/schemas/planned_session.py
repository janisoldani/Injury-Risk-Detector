from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import GymSplit, IntensityZone, SportType, TrainingGoal


class PlannedSessionBase(BaseModel):
    sport_type: SportType
    planned_start_time: datetime
    planned_duration_minutes: int = Field(..., ge=1)
    planned_intensity: IntensityZone | None = None
    gym_split: GymSplit | None = None
    goal: TrainingGoal = TrainingGoal.ENDURANCE
    priority: int = Field(1, ge=1, le=5, description="1=highest priority")
    notes: str | None = None


class PlannedSessionCreate(PlannedSessionBase):
    pass


class PlannedSessionUpdate(BaseModel):
    sport_type: SportType | None = None
    planned_start_time: datetime | None = None
    planned_duration_minutes: int | None = Field(None, ge=1)
    planned_intensity: IntensityZone | None = None
    gym_split: GymSplit | None = None
    goal: TrainingGoal | None = None
    priority: int | None = Field(None, ge=1, le=5)
    notes: str | None = None


class PlannedSessionResponse(PlannedSessionBase):
    id: int
    user_id: int
    created_at: datetime
    is_completed: bool = False
    completed_workout_id: int | None = None

    class Config:
        from_attributes = True


class PlannedSessionListResponse(BaseModel):
    sessions: list[PlannedSessionResponse]
    total: int
