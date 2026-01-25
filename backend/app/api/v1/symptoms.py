from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Symptom
from app.schemas.symptom import SymptomCreate, SymptomListResponse, SymptomResponse, SymptomUpdate

router = APIRouter()


@router.post("", response_model=SymptomResponse, status_code=status.HTTP_201_CREATED)
async def create_symptom(
    symptom_in: SymptomCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Symptom:
    """Log symptoms and subjective metrics."""
    # Convert soreness_map enum keys to strings
    soreness_map_str = {k.value: v for k, v in symptom_in.soreness_map.items()}

    symptom = Symptom(
        user_id=current_user.id,
        timestamp=datetime.utcnow(),
        pain_score=symptom_in.pain_score,
        pain_location=symptom_in.pain_location.value if symptom_in.pain_location else None,
        pain_description=symptom_in.pain_description,
        swelling=symptom_in.swelling,
        soreness_map=soreness_map_str,
        readiness=symptom_in.readiness,
        fatigue=symptom_in.fatigue,
        physio_visit=symptom_in.physio_visit,
        diagnosis_tag=symptom_in.diagnosis_tag,
        notes=symptom_in.notes,
    )
    db.add(symptom)
    await db.commit()
    await db.refresh(symptom)
    return symptom


@router.get("/today", response_model=SymptomResponse | None)
async def get_today_symptom(
    current_user: CurrentUser,
    db: DbSession,
) -> Symptom | None:
    """Get today's symptom entry (most recent)."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    result = await db.execute(
        select(Symptom)
        .where(
            Symptom.user_id == current_user.id,
            Symptom.timestamp >= today_start,
            Symptom.timestamp < today_end,
        )
        .order_by(Symptom.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("", response_model=SymptomListResponse)
async def list_symptoms(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> SymptomListResponse:
    """List user's symptom entries."""
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Symptom)
        .where(
            Symptom.user_id == current_user.id,
            Symptom.timestamp >= start_date,
        )
        .order_by(Symptom.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    symptoms = result.scalars().all()

    # Get total count
    count_query = select(Symptom).where(
        Symptom.user_id == current_user.id,
        Symptom.timestamp >= start_date,
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return SymptomListResponse(symptoms=list(symptoms), total=total)


@router.get("/{symptom_id}", response_model=SymptomResponse)
async def get_symptom(
    symptom_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Symptom:
    """Get a specific symptom entry."""
    result = await db.execute(
        select(Symptom).where(
            Symptom.id == symptom_id,
            Symptom.user_id == current_user.id,
        )
    )
    symptom = result.scalar_one_or_none()

    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symptom entry not found",
        )
    return symptom


@router.patch("/{symptom_id}", response_model=SymptomResponse)
async def update_symptom(
    symptom_id: int,
    symptom_update: SymptomUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Symptom:
    """Update a symptom entry."""
    result = await db.execute(
        select(Symptom).where(
            Symptom.id == symptom_id,
            Symptom.user_id == current_user.id,
        )
    )
    symptom = result.scalar_one_or_none()

    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symptom entry not found",
        )

    update_data = symptom_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "pain_location" and value is not None:
            setattr(symptom, field, value.value)
        elif field == "soreness_map" and value is not None:
            setattr(symptom, field, {k.value: v for k, v in value.items()})
        else:
            setattr(symptom, field, value)

    await db.commit()
    await db.refresh(symptom)
    return symptom
