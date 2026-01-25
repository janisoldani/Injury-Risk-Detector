from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.enums import SportProfile


class UserBase(BaseModel):
    email: EmailStr
    sport_profile: SportProfile = SportProfile.HIGH_TRAINING_LOAD
    timezone: str = "Europe/Zurich"


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    sport_profile: SportProfile | None = None
    timezone: str | None = None
    device_sources: list[str] | None = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    device_sources: list[str] = []

    class Config:
        from_attributes = True
