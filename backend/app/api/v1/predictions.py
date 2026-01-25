from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Label, PlannedSession, Prediction
from app.schemas.prediction import (
    LabelCreate,
    LabelResponse,
    PredictionRequest,
    PredictionResponse,
    QuickEvaluateRequest,
    QuickEvaluateResponse,
)
from app.services.risk_scorer import RiskScorer

router = APIRouter()


@router.post("/evaluate", response_model=PredictionResponse)
async def evaluate_planned_session(
    request: PredictionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> PredictionResponse:
    """Evaluate risk for a planned session and get recommendations."""
    # Get the planned session
    result = await db.execute(
        select(PlannedSession).where(
            PlannedSession.id == request.planned_session_id,
            PlannedSession.user_id == current_user.id,
        )
    )
    planned_session = result.scalar_one_or_none()

    if not planned_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned session not found",
        )

    # Calculate risk using the risk scorer service
    scorer = RiskScorer(db, current_user.id)
    prediction_data = await scorer.evaluate_session(planned_session)

    # Store the prediction
    prediction = Prediction(
        planned_session_id=planned_session.id,
        risk_score=prediction_data["risk_score"],
        risk_level=prediction_data["risk_level"],
        top_factors=prediction_data["top_factors"],
        explanation_text=prediction_data["explanation_text"],
        triggered_safety_rules=prediction_data["triggered_safety_rules"],
        recommendation_a=prediction_data["recommendation_a"],
        recommendation_b=prediction_data["recommendation_b"],
        model_version=prediction_data["model_version"],
        feature_snapshot=prediction_data.get("feature_snapshot"),
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)

    return PredictionResponse(
        id=prediction.id,
        planned_session_id=prediction.planned_session_id,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        top_factors=prediction.top_factors,
        explanation_text=prediction.explanation_text,
        triggered_safety_rules=prediction.triggered_safety_rules,
        recommendation_a=prediction.recommendation_a,
        recommendation_b=prediction.recommendation_b,
        model_version=prediction.model_version,
        created_at=prediction.created_at,
    )


@router.post("/quick-evaluate", response_model=QuickEvaluateResponse)
async def quick_evaluate(
    request: QuickEvaluateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> QuickEvaluateResponse:
    """Quick evaluation without saving a planned session first."""
    # Create a temporary planned session object for evaluation
    temp_session = PlannedSession(
        user_id=current_user.id,
        sport_type=request.sport_type.value,
        planned_start_time=datetime.utcnow(),
        planned_duration_minutes=request.planned_duration_minutes,
        planned_intensity=request.planned_intensity.value if request.planned_intensity else None,
        gym_split=request.gym_split.value if request.gym_split else None,
        goal=request.goal or "endurance",
    )

    # Calculate risk
    scorer = RiskScorer(db, current_user.id)
    prediction_data = await scorer.evaluate_session(temp_session)

    return QuickEvaluateResponse(
        risk_score=prediction_data["risk_score"],
        risk_level=prediction_data["risk_level"],
        top_factors=prediction_data["top_factors"],
        explanation_text=prediction_data["explanation_text"],
        triggered_safety_rules=prediction_data["triggered_safety_rules"],
        recommendation_a=prediction_data["recommendation_a"],
        recommendation_b=prediction_data["recommendation_b"],
    )


@router.get("/{session_id}", response_model=PredictionResponse)
async def get_prediction(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> PredictionResponse:
    """Get the latest prediction for a planned session."""
    # First verify the session belongs to the user
    session_result = await db.execute(
        select(PlannedSession).where(
            PlannedSession.id == session_id,
            PlannedSession.user_id == current_user.id,
        )
    )
    if not session_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned session not found",
        )

    # Get the latest prediction
    result = await db.execute(
        select(Prediction)
        .where(Prediction.planned_session_id == session_id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No prediction found for this session",
        )

    return PredictionResponse(
        id=prediction.id,
        planned_session_id=prediction.planned_session_id,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        top_factors=prediction.top_factors,
        explanation_text=prediction.explanation_text,
        triggered_safety_rules=prediction.triggered_safety_rules,
        recommendation_a=prediction.recommendation_a,
        recommendation_b=prediction.recommendation_b,
        model_version=prediction.model_version,
        created_at=prediction.created_at,
    )


@router.post("/labels", response_model=LabelResponse, status_code=status.HTTP_201_CREATED)
async def create_label(
    label_in: LabelCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Label:
    """Create a label for ML training (missed training, pain event, etc.)."""
    # Verify planned session if provided
    if label_in.planned_session_id:
        result = await db.execute(
            select(PlannedSession).where(
                PlannedSession.id == label_in.planned_session_id,
                PlannedSession.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planned session not found",
            )

    label = Label(
        user_id=current_user.id,
        planned_session_id=label_in.planned_session_id,
        label_date=label_in.label_date,
        overload_event=label_in.overload_event,
        reason=label_in.reason,
        severity=label_in.severity,
        notes=label_in.notes,
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label
