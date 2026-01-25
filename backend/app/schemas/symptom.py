from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import MuscleRegion, PainLocation


class SymptomBase(BaseModel):
    pain_score: int = Field(0, ge=0, le=10)
    pain_location: PainLocation | None = None
    pain_description: str | None = None
    swelling: bool = False
    soreness_map: dict[MuscleRegion, int] = Field(
        default_factory=dict,
        description="Muscle soreness levels (0-10) per region"
    )
    readiness: int = Field(7, ge=0, le=10, description="Subjective readiness to train")
    fatigue: int = Field(3, ge=0, le=10, description="Subjective fatigue level")
    physio_visit: bool = False
    diagnosis_tag: str | None = None
    notes: str | None = None


class SymptomCreate(SymptomBase):
    pass


class SymptomUpdate(BaseModel):
    pain_score: int | None = Field(None, ge=0, le=10)
    pain_location: PainLocation | None = None
    pain_description: str | None = None
    swelling: bool | None = None
    soreness_map: dict[MuscleRegion, int] | None = None
    readiness: int | None = Field(None, ge=0, le=10)
    fatigue: int | None = Field(None, ge=0, le=10)
    physio_visit: bool | None = None
    diagnosis_tag: str | None = None
    notes: str | None = None


class SymptomResponse(SymptomBase):
    id: int
    user_id: int
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SymptomListResponse(BaseModel):
    symptoms: list[SymptomResponse]
    total: int
