from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import Workout
from app.schemas.workout import WorkoutCreate, WorkoutListResponse, WorkoutResponse

router = APIRouter()


def calculate_trimp(duration_minutes: int, avg_hr: int | None, max_hr: int | None = None) -> float | None:
    """
    Calculate Training Impulse (TRIMP) based on duration and heart rate.
    Simplified Banister TRIMP formula.
    """
    if avg_hr is None:
        return None

    # Simplified TRIMP: duration * avg_hr_fraction
    # Assuming max HR around 190 for simplification (will be personalized later)
    estimated_max_hr = max_hr or 190
    resting_hr = 60  # Default, will be personalized

    hr_reserve = (avg_hr - resting_hr) / (estimated_max_hr - resting_hr)
    hr_reserve = max(0, min(1, hr_reserve))  # Clamp between 0 and 1

    # TRIMP = duration * hr_reserve * intensity_factor
    intensity_factor = 0.64 * (2.718 ** (1.92 * hr_reserve))
    trimp = duration_minutes * hr_reserve * intensity_factor

    return round(trimp, 1)


@router.post("", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(
    workout_in: WorkoutCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Workout:
    """Log a new workout."""
    trimp = calculate_trimp(
        workout_in.duration_minutes,
        workout_in.avg_hr,
        workout_in.max_hr,
    )

    workout = Workout(
        user_id=current_user.id,
        sport_type=workout_in.sport_type.value,
        start_time=workout_in.start_time,
        duration_minutes=workout_in.duration_minutes,
        avg_hr=workout_in.avg_hr,
        max_hr=workout_in.max_hr,
        calories=workout_in.calories,
        distance_meters=workout_in.distance_meters,
        training_effect=workout_in.training_effect,
        intensity_zone=workout_in.intensity_zone.value if workout_in.intensity_zone else None,
        gym_split=workout_in.gym_split.value if workout_in.gym_split else None,
        trimp=trimp,
        notes=workout_in.notes,
        source="manual",
    )
    db.add(workout)
    await db.commit()
    await db.refresh(workout)
    return workout


@router.get("", response_model=WorkoutListResponse)
async def list_workouts(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> WorkoutListResponse:
    """List user's workouts with optional date filtering."""
    query = select(Workout).where(Workout.user_id == current_user.id)

    if start_date:
        query = query.where(Workout.start_time >= start_date)
    if end_date:
        query = query.where(Workout.start_time <= end_date)

    query = query.order_by(Workout.start_time.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    workouts = result.scalars().all()

    # Get total count
    count_query = select(Workout).where(Workout.user_id == current_user.id)
    if start_date:
        count_query = count_query.where(Workout.start_time >= start_date)
    if end_date:
        count_query = count_query.where(Workout.start_time <= end_date)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return WorkoutListResponse(workouts=list(workouts), total=total)


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(
    workout_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Workout:
    """Get a specific workout."""
    result = await db.execute(
        select(Workout).where(
            Workout.id == workout_id,
            Workout.user_id == current_user.id,
        )
    )
    workout = result.scalar_one_or_none()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )
    return workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a workout."""
    result = await db.execute(
        select(Workout).where(
            Workout.id == workout_id,
            Workout.user_id == current_user.id,
        )
    )
    workout = result.scalar_one_or_none()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found",
        )

    await db.delete(workout)
    await db.commit()
