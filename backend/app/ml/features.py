"""
Feature Engineering for Risk Prediction.

Builds features from daily metrics, workouts, and symptoms.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyMetrics, Symptom, Workout
from app.schemas.enums import (
    GYM_SPLIT_MUSCLE_MAP,
    INTENSITY_ZONE_NUMERIC,
    SPORT_IMPACT_MAP,
    SPORT_MUSCLE_MAP,
    GymSplit,
    IntensityZone,
    MuscleRegion,
    SportType,
)


@dataclass
class UserFeatures:
    """Features for risk prediction."""

    # Date
    date: date

    # Baseline-normalized metrics
    hrv_z: Optional[float] = None  # (hrv - mean) / std
    rhr_delta: Optional[float] = None  # rhr - baseline
    sleep_delta: Optional[float] = None  # sleep_duration - baseline (minutes)

    # Raw metrics
    hrv_rmssd: Optional[float] = None
    resting_hr: Optional[int] = None
    sleep_duration_minutes: Optional[int] = None
    sleep_score: Optional[int] = None
    body_battery: Optional[int] = None
    stress_score: Optional[int] = None

    # Load features
    acute_load_7d: Optional[float] = None
    chronic_load_28d: Optional[float] = None
    acwr: Optional[float] = None  # Acute:Chronic Work Ratio
    monotony: Optional[float] = None
    strain: Optional[float] = None
    consecutive_training_days: int = 0
    hours_since_hard_session: Optional[float] = None
    hard_session_today: bool = False

    # Symptom features
    pain_score: int = 0
    pain_trend_3d: float = 0.0  # Trend over last 3 days
    max_soreness: int = 0
    soreness_map: dict = None
    readiness: int = 7
    fatigue: int = 3
    swelling: bool = False

    # Missing data flags
    missing_hrv: bool = True
    missing_sleep: bool = True
    missing_rhr: bool = True

    def __post_init__(self):
        if self.soreness_map is None:
            self.soreness_map = {}


class FeatureBuilder:
    """Builds features for a user on a specific date."""

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def build_features(self, target_date: date = None) -> UserFeatures:
        """Build all features for the target date."""
        if target_date is None:
            target_date = date.today()

        features = UserFeatures(date=target_date)

        # Get daily metrics
        await self._add_daily_metrics(features, target_date)

        # Get symptom features
        await self._add_symptom_features(features, target_date)

        # Get load features
        await self._add_load_features(features, target_date)

        return features

    async def _add_daily_metrics(self, features: UserFeatures, target_date: date) -> None:
        """Add features from daily_metrics table."""
        result = await self.db.execute(
            select(DailyMetrics).where(
                DailyMetrics.user_id == self.user_id,
                DailyMetrics.date == target_date,
            )
        )
        metrics = result.scalar_one_or_none()

        if not metrics:
            return

        # Raw values
        features.hrv_rmssd = metrics.hrv_rmssd
        features.resting_hr = metrics.resting_hr
        features.sleep_duration_minutes = metrics.sleep_duration_minutes
        features.sleep_score = metrics.sleep_score
        features.body_battery = metrics.body_battery
        features.stress_score = metrics.stress_score

        # Pre-calculated load metrics
        features.acute_load_7d = metrics.acute_load_7d
        features.chronic_load_28d = metrics.chronic_load_28d
        features.acwr = metrics.acwr
        features.monotony = metrics.monotony
        features.strain = metrics.strain

        # Calculate normalized features using baselines
        if metrics.hrv_rmssd is not None and metrics.hrv_baseline_mean is not None:
            features.missing_hrv = False
            if metrics.hrv_baseline_std and metrics.hrv_baseline_std > 0:
                features.hrv_z = (metrics.hrv_rmssd - metrics.hrv_baseline_mean) / metrics.hrv_baseline_std
            else:
                features.hrv_z = 0.0

        if metrics.resting_hr is not None and metrics.rhr_baseline_mean is not None:
            features.missing_rhr = False
            features.rhr_delta = metrics.resting_hr - metrics.rhr_baseline_mean

        if metrics.sleep_duration_minutes is not None and metrics.sleep_baseline_mean is not None:
            features.missing_sleep = False
            features.sleep_delta = metrics.sleep_duration_minutes - metrics.sleep_baseline_mean

    async def _add_symptom_features(self, features: UserFeatures, target_date: date) -> None:
        """Add features from symptoms table."""
        # Get most recent symptom entry for target date
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)

        result = await self.db.execute(
            select(Symptom)
            .where(
                Symptom.user_id == self.user_id,
                Symptom.timestamp >= start_of_day,
                Symptom.timestamp < end_of_day,
            )
            .order_by(Symptom.timestamp.desc())
            .limit(1)
        )
        symptom = result.scalar_one_or_none()

        if symptom:
            features.pain_score = symptom.pain_score
            features.readiness = symptom.readiness
            features.fatigue = symptom.fatigue
            features.swelling = symptom.swelling
            features.soreness_map = symptom.soreness_map or {}

            if features.soreness_map:
                features.max_soreness = max(features.soreness_map.values())

        # Calculate pain trend (last 3 days)
        three_days_ago = start_of_day - timedelta(days=3)
        result = await self.db.execute(
            select(Symptom)
            .where(
                Symptom.user_id == self.user_id,
                Symptom.timestamp >= three_days_ago,
                Symptom.timestamp < end_of_day,
            )
            .order_by(Symptom.timestamp.asc())
        )
        recent_symptoms = result.scalars().all()

        if len(recent_symptoms) >= 2:
            pain_values = [s.pain_score for s in recent_symptoms]
            # Simple trend: difference between most recent and oldest
            features.pain_trend_3d = pain_values[-1] - pain_values[0]

    async def _add_load_features(self, features: UserFeatures, target_date: date) -> None:
        """Add training load features from workouts."""
        # Get workouts from last 28 days
        start_date = datetime.combine(target_date - timedelta(days=28), datetime.min.time())
        end_date = datetime.combine(target_date, datetime.max.time())

        result = await self.db.execute(
            select(Workout)
            .where(
                Workout.user_id == self.user_id,
                Workout.start_time >= start_date,
                Workout.start_time <= end_date,
            )
            .order_by(Workout.start_time.desc())
        )
        workouts = result.scalars().all()

        if not workouts:
            return

        # Consecutive training days
        features.consecutive_training_days = self._count_consecutive_days(workouts, target_date)

        # Hours since last hard session
        hard_intensities = ["threshold", "VO2", "max"]
        for workout in workouts:
            if workout.intensity_zone in hard_intensities:
                delta = datetime.combine(target_date, datetime.min.time()) - workout.start_time
                features.hours_since_hard_session = delta.total_seconds() / 3600
                break

        # Check for hard session today
        today_start = datetime.combine(target_date, datetime.min.time())
        for workout in workouts:
            if workout.start_time >= today_start and workout.intensity_zone in hard_intensities:
                features.hard_session_today = True
                break

        # If load metrics not in daily_metrics, calculate them
        if features.acute_load_7d is None:
            features.acute_load_7d = self._calculate_load(workouts, target_date, 7)
        if features.chronic_load_28d is None:
            features.chronic_load_28d = self._calculate_load(workouts, target_date, 28)
        if features.acwr is None and features.chronic_load_28d and features.chronic_load_28d > 0:
            features.acwr = features.acute_load_7d / features.chronic_load_28d

    def _count_consecutive_days(self, workouts: list[Workout], target_date: date) -> int:
        """Count consecutive training days leading up to target date."""
        workout_dates = set(w.start_time.date() for w in workouts)
        count = 0
        check_date = target_date - timedelta(days=1)  # Start from yesterday

        while check_date in workout_dates:
            count += 1
            check_date -= timedelta(days=1)

        return count

    def _calculate_load(self, workouts: list[Workout], target_date: date, days: int) -> float:
        """Calculate TRIMP-based load for specified period."""
        start = target_date - timedelta(days=days)
        total = 0.0

        for workout in workouts:
            if start <= workout.start_time.date() <= target_date:
                total += workout.trimp or 0.0

        return total


def get_soreness_in_target_muscles(
    soreness_map: dict,
    sport_type: SportType,
    gym_split: Optional[GymSplit] = None,
) -> int:
    """Get maximum soreness level in muscles targeted by planned activity."""
    if sport_type == SportType.GYM and gym_split:
        target_muscles = GYM_SPLIT_MUSCLE_MAP.get(gym_split, [])
    else:
        target_muscles = SPORT_MUSCLE_MAP.get(sport_type, [])

    max_soreness = 0
    for muscle in target_muscles:
        muscle_key = muscle.value if isinstance(muscle, MuscleRegion) else muscle
        soreness = soreness_map.get(muscle_key, 0)
        max_soreness = max(max_soreness, soreness)

    return max_soreness


def get_sport_impact_score(sport_type: SportType) -> int:
    """Get numeric impact score for sport (1-5)."""
    from app.schemas.enums import ImpactLevel

    impact = SPORT_IMPACT_MAP.get(sport_type, ImpactLevel.MEDIUM)
    scores = {
        ImpactLevel.VERY_LOW: 1,
        ImpactLevel.LOW: 2,
        ImpactLevel.MEDIUM: 3,
        ImpactLevel.HIGH: 4,
        ImpactLevel.VERY_HIGH: 5,
    }
    return scores.get(impact, 3)


def get_intensity_score(intensity: Optional[IntensityZone]) -> int:
    """Get numeric intensity score (1-6)."""
    if intensity is None:
        return 3  # Default to moderate
    return INTENSITY_ZONE_NUMERIC.get(intensity, 3)
