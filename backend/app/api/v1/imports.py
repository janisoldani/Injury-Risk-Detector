"""
Import API - Handles file uploads for workout and health data.

Supports:
- FIT files (Garmin, Wahoo, etc.)
- Future: TCX, GPX, CSV
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import DailyMetrics, Workout
from app.services.fit_parser import FitFileProcessor, FitParseResult

logger = logging.getLogger(__name__)
router = APIRouter()


class ImportResult(BaseModel):
    """Result of a file import."""
    success: bool
    message: str
    workouts_created: int = 0
    workouts_skipped: int = 0
    metrics_created: int = 0
    metrics_updated: int = 0
    errors: list[str] = []
    file_type: Optional[str] = None
    device_info: Optional[str] = None


class ImportStats(BaseModel):
    """Statistics about imported data."""
    total_workouts: int
    total_metrics_days: int
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None


@router.post("/fit", response_model=ImportResult)
async def upload_fit_file(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> ImportResult:
    """
    Upload and process a FIT file.

    Extracts workouts and daily health metrics (HRV, RHR, sleep, etc.)
    and saves them to the database.

    Supported FIT file types:
    - Activity files (workouts)
    - Monitoring files (daily health data)
    """
    result = ImportResult(success=False, message="")

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not file.filename.lower().endswith(".fit"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .fit files are supported",
        )

    logger.info(
        "Processing FIT file upload",
        extra={
            "user_id": current_user.id,
            "filename": file.filename,
            "content_type": file.content_type,
        }
    )

    try:
        # Read file content
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file",
            )

        # Parse FIT file
        processor = FitFileProcessor()
        parse_result = processor.parse_file(content)

        result.file_type = parse_result.file_type
        result.device_info = parse_result.device_info
        result.errors = parse_result.errors

        if not parse_result.has_data:
            result.message = "No data could be extracted from the file"
            if parse_result.errors:
                result.message += f": {parse_result.errors[0]}"
            return result

        # Save workouts
        for parsed_workout in parse_result.workouts:
            created = await _save_workout(db, current_user.id, parsed_workout)
            if created:
                result.workouts_created += 1
            else:
                result.workouts_skipped += 1

        # Save daily metrics
        for parsed_metrics in parse_result.daily_metrics:
            created, updated = await _save_daily_metrics(db, current_user.id, parsed_metrics)
            if created:
                result.metrics_created += 1
            elif updated:
                result.metrics_updated += 1

        await db.commit()

        result.success = True
        result.message = _build_success_message(result)

        logger.info(
            "FIT file processed successfully",
            extra={
                "user_id": current_user.id,
                "workouts_created": result.workouts_created,
                "metrics_created": result.metrics_created,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing FIT file: {e}", exc_info=True)
        result.errors.append(str(e))
        result.message = f"Error processing file: {str(e)}"
        await db.rollback()

    return result


@router.get("/stats", response_model=ImportStats)
async def get_import_stats(
    current_user: CurrentUser,
    db: DbSession,
) -> ImportStats:
    """Get statistics about imported data for the current user."""
    # Count workouts
    workout_result = await db.execute(
        select(Workout).where(Workout.user_id == current_user.id)
    )
    workouts = workout_result.scalars().all()

    # Count metrics days
    metrics_result = await db.execute(
        select(DailyMetrics).where(DailyMetrics.user_id == current_user.id)
    )
    metrics = metrics_result.scalars().all()

    # Get date range
    earliest = None
    latest = None

    if workouts:
        workout_dates = [w.start_time.date() for w in workouts]
        earliest = min(workout_dates)
        latest = max(workout_dates)

    if metrics:
        metric_dates = [m.date for m in metrics]
        if earliest:
            earliest = min(earliest, min(metric_dates))
            latest = max(latest, max(metric_dates))
        else:
            earliest = min(metric_dates)
            latest = max(metric_dates)

    return ImportStats(
        total_workouts=len(workouts),
        total_metrics_days=len(metrics),
        earliest_date=earliest.isoformat() if earliest else None,
        latest_date=latest.isoformat() if latest else None,
    )


async def _save_workout(db: DbSession, user_id: int, parsed) -> bool:
    """Save a parsed workout to the database. Returns True if created."""
    from app.api.v1.workouts import calculate_trimp

    # Check for duplicate (same user, same start time)
    existing = await db.execute(
        select(Workout).where(
            Workout.user_id == user_id,
            Workout.start_time == parsed.start_time,
        )
    )
    if existing.scalar_one_or_none():
        logger.debug(f"Skipping duplicate workout at {parsed.start_time}")
        return False

    # Calculate TRIMP
    trimp = calculate_trimp(parsed.duration_minutes, parsed.avg_hr, parsed.max_hr)

    workout = Workout(
        user_id=user_id,
        sport_type=parsed.sport_type,
        start_time=parsed.start_time,
        duration_minutes=parsed.duration_minutes,
        avg_hr=parsed.avg_hr,
        max_hr=parsed.max_hr,
        calories=parsed.calories,
        distance_meters=parsed.distance_meters,
        training_effect=parsed.training_effect,
        intensity_zone=parsed.intensity_zone,
        trimp=trimp,
        source="garmin_fit",
        external_id=parsed.external_id,
    )
    db.add(workout)
    return True


async def _save_daily_metrics(db: DbSession, user_id: int, parsed) -> tuple[bool, bool]:
    """
    Save or update daily metrics.

    Returns (created, updated) tuple.
    """
    # Check for existing metrics on this date
    existing = await db.execute(
        select(DailyMetrics).where(
            DailyMetrics.user_id == user_id,
            DailyMetrics.date == parsed.date,
        )
    )
    metrics = existing.scalar_one_or_none()

    if metrics:
        # Update existing with non-None values from parsed
        updated = False

        if parsed.resting_hr is not None and (
            metrics.resting_hr is None or parsed.resting_hr < metrics.resting_hr
        ):
            metrics.resting_hr = parsed.resting_hr
            updated = True

        if parsed.hrv_rmssd is not None and metrics.hrv_rmssd is None:
            metrics.hrv_rmssd = parsed.hrv_rmssd
            updated = True

        if parsed.sleep_duration_minutes is not None and metrics.sleep_duration_minutes is None:
            metrics.sleep_duration_minutes = parsed.sleep_duration_minutes
            updated = True

        if parsed.sleep_score is not None and metrics.sleep_score is None:
            metrics.sleep_score = parsed.sleep_score
            updated = True

        if parsed.body_battery is not None and metrics.body_battery is None:
            metrics.body_battery = parsed.body_battery
            updated = True

        if parsed.stress_score is not None and metrics.stress_score is None:
            metrics.stress_score = parsed.stress_score
            updated = True

        metrics.updated_at = datetime.utcnow()
        return False, updated

    else:
        # Create new metrics
        metrics = DailyMetrics(
            user_id=user_id,
            date=parsed.date,
            resting_hr=parsed.resting_hr,
            hrv_rmssd=parsed.hrv_rmssd,
            sleep_duration_minutes=parsed.sleep_duration_minutes,
            sleep_score=parsed.sleep_score,
            body_battery=parsed.body_battery,
            stress_score=parsed.stress_score,
        )
        db.add(metrics)
        return True, False


def _build_success_message(result: ImportResult) -> str:
    """Build a human-readable success message."""
    parts = []

    if result.workouts_created > 0:
        parts.append(f"{result.workouts_created} workout(s) imported")

    if result.workouts_skipped > 0:
        parts.append(f"{result.workouts_skipped} duplicate(s) skipped")

    if result.metrics_created > 0:
        parts.append(f"{result.metrics_created} day(s) of health data imported")

    if result.metrics_updated > 0:
        parts.append(f"{result.metrics_updated} day(s) of health data updated")

    if not parts:
        return "File processed but no new data found"

    return ", ".join(parts)
