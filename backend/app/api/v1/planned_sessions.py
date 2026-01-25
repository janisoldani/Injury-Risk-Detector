from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import PlannedSession
from app.schemas.planned_session import (
    PlannedSessionCreate,
    PlannedSessionListResponse,
    PlannedSessionResponse,
    PlannedSessionUpdate,
)

router = APIRouter()


@router.post("", response_model=PlannedSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_planned_session(
    session_in: PlannedSessionCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PlannedSession:
    """Create a new planned training session."""
    session = PlannedSession(
        user_id=current_user.id,
        sport_type=session_in.sport_type.value,
        planned_start_time=session_in.planned_start_time,
        planned_duration_minutes=session_in.planned_duration_minutes,
        planned_intensity=session_in.planned_intensity.value if session_in.planned_intensity else None,
        gym_split=session_in.gym_split.value if session_in.gym_split else None,
        goal=session_in.goal.value,
        priority=session_in.priority,
        notes=session_in.notes,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=PlannedSessionListResponse)
async def list_planned_sessions(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_completed: bool = False,
    future_only: bool = True,
) -> PlannedSessionListResponse:
    """List planned sessions."""
    query = select(PlannedSession).where(PlannedSession.user_id == current_user.id)

    if not include_completed:
        query = query.where(PlannedSession.is_completed == False)

    if future_only:
        query = query.where(PlannedSession.planned_start_time >= datetime.utcnow())

    query = query.order_by(PlannedSession.planned_start_time.asc()).offset(offset).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Get total count
    count_query = select(PlannedSession).where(PlannedSession.user_id == current_user.id)
    if not include_completed:
        count_query = count_query.where(PlannedSession.is_completed == False)
    if future_only:
        count_query = count_query.where(PlannedSession.planned_start_time >= datetime.utcnow())

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return PlannedSessionListResponse(sessions=list(sessions), total=total)


@router.get("/upcoming", response_model=PlannedSessionResponse | None)
async def get_next_planned_session(
    current_user: CurrentUser,
    db: DbSession,
) -> PlannedSession | None:
    """Get the next upcoming planned session."""
    result = await db.execute(
        select(PlannedSession)
        .where(
            PlannedSession.user_id == current_user.id,
            PlannedSession.is_completed == False,
            PlannedSession.planned_start_time >= datetime.utcnow(),
        )
        .order_by(PlannedSession.planned_start_time.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/{session_id}", response_model=PlannedSessionResponse)
async def get_planned_session(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> PlannedSession:
    """Get a specific planned session."""
    result = await db.execute(
        select(PlannedSession).where(
            PlannedSession.id == session_id,
            PlannedSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned session not found",
        )
    return session


@router.patch("/{session_id}", response_model=PlannedSessionResponse)
async def update_planned_session(
    session_id: int,
    session_update: PlannedSessionUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PlannedSession:
    """Update a planned session."""
    result = await db.execute(
        select(PlannedSession).where(
            PlannedSession.id == session_id,
            PlannedSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned session not found",
        )

    update_data = session_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field in ("sport_type", "planned_intensity", "gym_split", "goal") and value is not None:
            setattr(session, field, value.value)
        else:
            setattr(session, field, value)

    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_planned_session(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a planned session."""
    result = await db.execute(
        select(PlannedSession).where(
            PlannedSession.id == session_id,
            PlannedSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned session not found",
        )

    await db.delete(session)
    await db.commit()


@router.post("/{session_id}/complete", response_model=PlannedSessionResponse)
async def mark_session_completed(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
    workout_id: int | None = None,
) -> PlannedSession:
    """Mark a planned session as completed."""
    result = await db.execute(
        select(PlannedSession).where(
            PlannedSession.id == session_id,
            PlannedSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned session not found",
        )

    session.is_completed = True
    session.completed_workout_id = workout_id
    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)
    return session
