from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import GymSplit, IntensityZone, SportType


class WorkoutBase(BaseModel):
    sport_type: SportType
    start_time: datetime
    duration_minutes: int = Field(..., ge=1)
    avg_hr: int | None = Field(None, ge=30, le=250)
    max_hr: int | None = Field(None, ge=30, le=250)
    calories: int | None = Field(None, ge=0)
    distance_meters: float | None = Field(None, ge=0)
    training_effect: float | None = Field(None, ge=0, le=5)
    intensity_zone: IntensityZone | None = None
    gym_split: GymSplit | None = None
    notes: str | None = None


class WorkoutCreate(WorkoutBase):
    pass


class WorkoutResponse(WorkoutBase):
    id: int
    user_id: int
    trimp: float | None = None  # Calculated server-side
    created_at: datetime

    class Config:
        from_attributes = True


class WorkoutListResponse(BaseModel):
    workouts: list[WorkoutResponse]
    total: int
