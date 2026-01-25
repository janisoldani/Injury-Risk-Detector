from fastapi import APIRouter

from app.api.v1 import (
    users,
    workouts,
    symptoms,
    planned_sessions,
    predictions,
)

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(symptoms.router, prefix="/symptoms", tags=["symptoms"])
api_router.include_router(planned_sessions.router, prefix="/planned-sessions", tags=["planned-sessions"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
