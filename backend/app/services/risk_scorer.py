"""
Risk Scorer - Combines safety rules, features, and heuristics to calculate risk.

This is the main entry point for risk evaluation.
"""
import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ml.features import (
    FeatureBuilder,
    UserFeatures,
    get_intensity_score,
    get_soreness_in_target_muscles,
    get_sport_impact_score,
)
from app.models import PlannedSession
from app.schemas.enums import GymSplit, IntensityZone, RiskLevel, SportType
from app.services.recommender import RecommendationEngine
from app.services.safety_rules import SafetyEvaluation, evaluate_all_safety_rules
from app.services.scoring_config import ScoringConfig, get_scoring_config

settings = get_settings()
logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for threshold evaluation."""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class ThresholdResult:
    """Result of threshold evaluation."""
    contribution: float = 0.0
    severity: Severity = Severity.NONE
    triggered: bool = False


def evaluate_lower_threshold(
    value: Optional[float],
    severe_threshold: float,
    moderate_threshold: float,
    mild_threshold: float,
    severe_points: float,
    moderate_points: float,
    mild_points: float,
) -> ThresholdResult:
    """
    Evaluate a value against lower-is-worse thresholds (e.g., HRV, sleep).
    Returns contribution and severity level.
    """
    if value is None:
        return ThresholdResult()

    if value < severe_threshold:
        return ThresholdResult(severe_points, Severity.SEVERE, True)
    elif value < moderate_threshold:
        return ThresholdResult(moderate_points, Severity.MODERATE, True)
    elif value < mild_threshold:
        return ThresholdResult(mild_points, Severity.MILD, True)
    return ThresholdResult()


def evaluate_upper_threshold(
    value: Optional[float],
    severe_threshold: float,
    moderate_threshold: float,
    mild_threshold: float,
    severe_points: float,
    moderate_points: float,
    mild_points: float,
) -> ThresholdResult:
    """
    Evaluate a value against upper-is-worse thresholds (e.g., RHR, fatigue).
    Returns contribution and severity level.
    """
    if value is None:
        return ThresholdResult()

    if value > severe_threshold:
        return ThresholdResult(severe_points, Severity.SEVERE, True)
    elif value > moderate_threshold:
        return ThresholdResult(moderate_points, Severity.MODERATE, True)
    elif value > mild_threshold:
        return ThresholdResult(mild_points, Severity.MILD, True)
    return ThresholdResult()


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of how the risk score was calculated."""
    hrv_contribution: float = 0.0
    rhr_contribution: float = 0.0
    sleep_contribution: float = 0.0
    acwr_contribution: float = 0.0
    pain_contribution: float = 0.0
    pain_trend_contribution: float = 0.0
    target_soreness_contribution: float = 0.0
    general_soreness_contribution: float = 0.0
    readiness_contribution: float = 0.0
    fatigue_contribution: float = 0.0
    consecutive_days_contribution: float = 0.0
    missing_data_penalty: float = 0.0
    base_score: float = 0.0
    intensity_multiplier: float = 1.0
    final_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "hrv": self.hrv_contribution,
            "rhr": self.rhr_contribution,
            "sleep": self.sleep_contribution,
            "acwr": self.acwr_contribution,
            "pain": self.pain_contribution,
            "pain_trend": self.pain_trend_contribution,
            "target_soreness": self.target_soreness_contribution,
            "general_soreness": self.general_soreness_contribution,
            "readiness": self.readiness_contribution,
            "fatigue": self.fatigue_contribution,
            "consecutive_days": self.consecutive_days_contribution,
            "missing_data": self.missing_data_penalty,
            "base_score": self.base_score,
            "intensity_multiplier": self.intensity_multiplier,
            "final_score": self.final_score,
        }


class RiskScorer:
    """Calculates risk score for a planned training session."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: int,
        config: Optional[ScoringConfig] = None,
    ):
        self.db = db
        self.user_id = user_id
        self.feature_builder = FeatureBuilder(db, user_id)
        self.config = config or get_scoring_config()
        self._last_breakdown: Optional[ScoreBreakdown] = None

    async def evaluate_session(self, planned_session: PlannedSession) -> dict[str, Any]:
        """
        Evaluate risk for a planned session.

        Returns dict with all prediction data ready for storage.
        """
        logger.info(
            "Evaluating session",
            extra={
                "user_id": self.user_id,
                "session_id": getattr(planned_session, "id", None),
                "sport_type": planned_session.sport_type,
                "planned_intensity": planned_session.planned_intensity,
            }
        )

        # Build features
        features = await self.feature_builder.build_features(date.today())
        logger.debug(
            "Features built",
            extra={
                "user_id": self.user_id,
                "hrv_z": features.hrv_z,
                "rhr_delta": features.rhr_delta,
                "pain_score": features.pain_score,
                "acwr": features.acwr,
            }
        )

        # Parse planned session details
        planned_sport = SportType(planned_session.sport_type)
        planned_intensity = (
            IntensityZone(planned_session.planned_intensity)
            if planned_session.planned_intensity
            else None
        )
        planned_gym_split = (
            GymSplit(planned_session.gym_split)
            if planned_session.gym_split
            else None
        )

        # Evaluate safety rules
        safety_eval = evaluate_all_safety_rules(
            pain_score=features.pain_score,
            swelling=features.swelling,
            soreness_map=features.soreness_map,
            planned_sport=planned_sport,
            planned_gym_split=planned_gym_split,
            planned_intensity=planned_intensity,
            hrv_z=features.hrv_z,
            rhr_delta=features.rhr_delta,
            hard_session_today=features.hard_session_today,
        )

        if safety_eval.any_triggered:
            logger.info(
                "Safety rules triggered",
                extra={
                    "user_id": self.user_id,
                    "triggered_rules": [r.rule_id for r in safety_eval.triggered_rules],
                    "override_level": safety_eval.override_risk_level.value if safety_eval.override_risk_level else None,
                }
            )

        # Calculate heuristic score with breakdown
        heuristic_score, breakdown = self._calculate_heuristic_score(
            features, planned_sport, planned_intensity, planned_gym_split
        )
        self._last_breakdown = breakdown

        logger.info(
            "Heuristic score calculated",
            extra={
                "user_id": self.user_id,
                "base_score": breakdown.base_score,
                "multiplier": breakdown.intensity_multiplier,
                "final_score": heuristic_score,
                "breakdown": breakdown.to_dict(),
            }
        )

        # Determine final risk score and level
        risk_score, risk_level = self._determine_risk(heuristic_score, safety_eval)

        logger.info(
            "Risk evaluation complete",
            extra={
                "user_id": self.user_id,
                "risk_score": risk_score,
                "risk_level": risk_level.value,
            }
        )

        # Generate explanations
        top_factors = self._get_top_factors(features, planned_sport, planned_gym_split)
        explanation_text = self._generate_explanation(risk_level, safety_eval, top_factors)

        # Generate recommendations
        recommender = RecommendationEngine(
            risk_level=risk_level,
            safety_eval=safety_eval,
            blocked_muscle_regions=safety_eval.blocked_muscle_regions,
        )
        rec_a, rec_b = recommender.generate_recommendations(
            planned_sport=planned_sport,
            planned_duration=planned_session.planned_duration_minutes,
            planned_intensity=planned_intensity,
            planned_gym_split=planned_gym_split,
        )

        # Format triggered safety rules
        triggered_rules = [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "description": r.description,
                "blocked_sports": [s.value for s in r.blocked_sports],
                "max_allowed_intensity": r.max_allowed_intensity.value if r.max_allowed_intensity else None,
                "blocked_muscle_regions": [m.value for m in r.blocked_muscle_regions],
            }
            for r in safety_eval.triggered_rules
        ]

        return {
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "top_factors": [
                {"name": f["name"], "contribution": f["contribution"], "description": f["description"]}
                for f in top_factors
            ],
            "explanation_text": explanation_text,
            "triggered_safety_rules": triggered_rules,
            "recommendation_a": {
                "sport_type": rec_a.sport_type.value,
                "duration_minutes": rec_a.duration_minutes,
                "intensity": rec_a.intensity.value if rec_a.intensity else None,
                "gym_split": rec_a.gym_split.value if rec_a.gym_split else None,
                "intensity_level": rec_a.intensity_level,
                "reason": rec_a.reason,
                "is_original_plan_modified": rec_a.is_original_plan_modified,
            },
            "recommendation_b": {
                "sport_type": rec_b.sport_type.value,
                "duration_minutes": rec_b.duration_minutes,
                "intensity": rec_b.intensity.value if rec_b.intensity else None,
                "gym_split": rec_b.gym_split.value if rec_b.gym_split else None,
                "intensity_level": rec_b.intensity_level,
                "reason": rec_b.reason,
                "is_original_plan_modified": rec_b.is_original_plan_modified,
            },
            "model_version": "heuristic_v1",
            "feature_snapshot": self._features_to_dict(features),
            "score_breakdown": breakdown.to_dict(),
        }

    def _calculate_heuristic_score(
        self,
        features: UserFeatures,
        planned_sport: SportType,
        planned_intensity: Optional[IntensityZone],
        planned_gym_split: Optional[GymSplit],
    ) -> tuple[float, ScoreBreakdown]:
        """
        Calculate heuristic risk score (0-100) with detailed breakdown.

        Uses configurable thresholds and weights from ScoringConfig.
        """
        cfg = self.config
        breakdown = ScoreBreakdown()
        score = 0.0

        # HRV under baseline (more negative = worse)
        hrv_result = evaluate_lower_threshold(
            features.hrv_z,
            cfg.hrv.severe_threshold, cfg.hrv.moderate_threshold, cfg.hrv.mild_threshold,
            cfg.hrv.severe_points, cfg.hrv.moderate_points, cfg.hrv.mild_points,
        )
        breakdown.hrv_contribution = hrv_result.contribution
        score += breakdown.hrv_contribution

        # RHR elevated (higher = worse)
        rhr_result = evaluate_upper_threshold(
            features.rhr_delta,
            cfg.rhr.severe_threshold, cfg.rhr.moderate_threshold, cfg.rhr.mild_threshold,
            cfg.rhr.severe_points, cfg.rhr.moderate_points, cfg.rhr.mild_points,
        )
        breakdown.rhr_contribution = rhr_result.contribution
        score += breakdown.rhr_contribution

        # Sleep deficit (more negative = worse)
        sleep_result = evaluate_lower_threshold(
            features.sleep_delta,
            cfg.sleep.severe_threshold, cfg.sleep.moderate_threshold, cfg.sleep.mild_threshold,
            cfg.sleep.severe_points, cfg.sleep.moderate_points, cfg.sleep.mild_points,
        )
        breakdown.sleep_contribution = sleep_result.contribution
        score += breakdown.sleep_contribution

        # ACWR (Acute:Chronic Work Ratio) - special case with 4 thresholds
        if features.acwr is not None:
            if features.acwr > cfg.acwr.critical_threshold:
                breakdown.acwr_contribution = cfg.acwr.critical_points
            elif features.acwr > cfg.acwr.elevated_threshold:
                breakdown.acwr_contribution = cfg.acwr.elevated_points
            elif features.acwr > cfg.acwr.warning_threshold:
                breakdown.acwr_contribution = cfg.acwr.warning_points
            elif features.acwr < cfg.acwr.detraining_threshold:
                breakdown.acwr_contribution = cfg.acwr.detraining_points
        score += breakdown.acwr_contribution

        # Pain (linear scaling)
        breakdown.pain_contribution = features.pain_score * cfg.pain.points_per_level
        score += breakdown.pain_contribution

        # Pain trend (worsening)
        pain_trend_result = evaluate_upper_threshold(
            features.pain_trend_3d,
            cfg.pain.worsening_severe_threshold, cfg.pain.worsening_moderate_threshold, 0.0,
            cfg.pain.worsening_severe_points, cfg.pain.worsening_moderate_points, 0.0,
        )
        breakdown.pain_trend_contribution = pain_trend_result.contribution
        score += breakdown.pain_trend_contribution

        # Soreness in target muscles (linear scaling)
        target_soreness = get_soreness_in_target_muscles(
            features.soreness_map, planned_sport, planned_gym_split
        )
        breakdown.target_soreness_contribution = target_soreness * cfg.soreness.target_muscle_points_per_level
        score += breakdown.target_soreness_contribution

        # General soreness (linear scaling)
        breakdown.general_soreness_contribution = features.max_soreness * cfg.soreness.general_points_per_level
        score += breakdown.general_soreness_contribution

        # Readiness (low = higher risk)
        readiness_result = evaluate_lower_threshold(
            features.readiness,
            cfg.readiness.poor_threshold, cfg.readiness.moderate_threshold, 0.0,
            cfg.readiness.poor_points, cfg.readiness.moderate_points, 0.0,
        )
        breakdown.readiness_contribution = readiness_result.contribution
        score += breakdown.readiness_contribution

        # Fatigue (high = higher risk)
        fatigue_result = evaluate_upper_threshold(
            features.fatigue,
            cfg.fatigue.severe_threshold, cfg.fatigue.moderate_threshold, 0.0,
            cfg.fatigue.severe_points, cfg.fatigue.moderate_points, 0.0,
        )
        breakdown.fatigue_contribution = fatigue_result.contribution
        score += breakdown.fatigue_contribution

        # Consecutive training days
        consecutive_result = evaluate_upper_threshold(
            float(features.consecutive_training_days),
            cfg.training_load.consecutive_severe_threshold,
            cfg.training_load.consecutive_moderate_threshold,
            cfg.training_load.consecutive_mild_threshold,
            cfg.training_load.consecutive_severe_points,
            cfg.training_load.consecutive_moderate_points,
            cfg.training_load.consecutive_mild_points,
        )
        breakdown.consecutive_days_contribution = consecutive_result.contribution
        score += breakdown.consecutive_days_contribution

        # Store base score before multiplier
        breakdown.base_score = score

        # Sport impact and intensity multiplier
        impact_score = get_sport_impact_score(planned_sport)
        intensity_score = get_intensity_score(planned_intensity)
        breakdown.intensity_multiplier = 1.0 + (
            impact_score + intensity_score - cfg.intensity_multiplier.neutral_base
        ) * cfg.intensity_multiplier.scaling_factor
        score *= breakdown.intensity_multiplier

        # Missing data penalty (uncertainty)
        missing_count = sum([features.missing_hrv, features.missing_sleep, features.missing_rhr])
        breakdown.missing_data_penalty = missing_count * cfg.missing_data.points_per_missing
        score += breakdown.missing_data_penalty

        breakdown.final_score = min(100, max(0, round(score)))
        return breakdown.final_score, breakdown

    def _determine_risk(
        self, heuristic_score: float, safety_eval: SafetyEvaluation
    ) -> tuple[int, RiskLevel]:
        """Determine final risk score and level, applying safety rule overrides."""
        risk_score = int(heuristic_score)

        # Apply safety rule override if present
        if safety_eval.override_risk_level == RiskLevel.RED:
            risk_score = max(risk_score, settings.risk_threshold_yellow_max + 1)
        elif safety_eval.override_risk_level == RiskLevel.YELLOW:
            risk_score = max(risk_score, settings.risk_threshold_green_max + 1)

        # Determine level from score
        if risk_score <= settings.risk_threshold_green_max:
            risk_level = RiskLevel.GREEN
        elif risk_score <= settings.risk_threshold_yellow_max:
            risk_level = RiskLevel.YELLOW
        else:
            risk_level = RiskLevel.RED

        return risk_score, risk_level

    def _get_top_factors(
        self,
        features: UserFeatures,
        planned_sport: SportType,
        planned_gym_split: Optional[GymSplit],
    ) -> list[dict]:
        """Get top contributing factors to the risk score."""
        cfg = self.config
        factors = []

        # HRV
        hrv_result = evaluate_lower_threshold(
            features.hrv_z,
            cfg.hrv.severe_threshold, cfg.hrv.moderate_threshold, cfg.hrv.mild_threshold,
            cfg.hrv.severe_points, cfg.hrv.moderate_points, cfg.hrv.mild_points,
        )
        if hrv_result.triggered:
            factors.append({
                "name": "HRV below baseline",
                "contribution": hrv_result.contribution,
                "description": f"HRV {features.hrv_z:.1f} standard deviations below your 28-day average",
                "value": features.hrv_z,
            })

        # RHR
        rhr_result = evaluate_upper_threshold(
            features.rhr_delta,
            cfg.rhr.severe_threshold, cfg.rhr.moderate_threshold, cfg.rhr.mild_threshold,
            cfg.rhr.severe_points, cfg.rhr.moderate_points, cfg.rhr.mild_points,
        )
        if rhr_result.triggered:
            factors.append({
                "name": "Elevated resting heart rate",
                "contribution": rhr_result.contribution,
                "description": f"Resting heart rate {features.rhr_delta:.0f} bpm above your average",
                "value": features.rhr_delta,
            })

        # Sleep
        sleep_result = evaluate_lower_threshold(
            features.sleep_delta,
            cfg.sleep.severe_threshold, cfg.sleep.moderate_threshold, cfg.sleep.mild_threshold,
            cfg.sleep.severe_points, cfg.sleep.moderate_points, cfg.sleep.mild_points,
        )
        if sleep_result.triggered:
            factors.append({
                "name": "Sleep deficit",
                "contribution": sleep_result.contribution,
                "description": f"{abs(features.sleep_delta):.0f} minutes less sleep than usual",
                "value": features.sleep_delta,
            })

        # ACWR
        if features.acwr is not None and features.acwr > cfg.acwr.warning_threshold:
            if features.acwr > cfg.acwr.critical_threshold:
                contribution = cfg.acwr.critical_points
            elif features.acwr > cfg.acwr.elevated_threshold:
                contribution = cfg.acwr.elevated_points
            else:
                contribution = cfg.acwr.warning_points
            factors.append({
                "name": "High acute workload",
                "contribution": contribution,
                "description": f"ACWR of {features.acwr:.2f} - acute load higher than chronic",
                "value": features.acwr,
            })

        # Pain
        if features.pain_score > 0:
            contribution = features.pain_score * cfg.pain.points_per_level
            factors.append({
                "name": "Pain",
                "contribution": contribution,
                "description": f"Pain score of {features.pain_score}/10",
                "value": features.pain_score,
            })

        # Target muscle soreness
        target_soreness = get_soreness_in_target_muscles(
            features.soreness_map, planned_sport, planned_gym_split
        )
        if target_soreness >= 5:
            contribution = target_soreness * cfg.soreness.target_muscle_points_per_level
            factors.append({
                "name": "Soreness in target muscles",
                "contribution": contribution,
                "description": f"Muscle soreness {target_soreness}/10 in muscles used for this activity",
                "value": target_soreness,
            })

        # Consecutive days
        consecutive_result = evaluate_upper_threshold(
            float(features.consecutive_training_days),
            cfg.training_load.consecutive_severe_threshold,
            cfg.training_load.consecutive_moderate_threshold,
            cfg.training_load.consecutive_mild_threshold,
            cfg.training_load.consecutive_severe_points,
            cfg.training_load.consecutive_moderate_points,
            cfg.training_load.consecutive_mild_points,
        )
        if consecutive_result.triggered:
            factors.append({
                "name": "Consecutive training days",
                "contribution": consecutive_result.contribution,
                "description": f"{features.consecutive_training_days} days of training in a row",
                "value": features.consecutive_training_days,
            })

        # Fatigue
        fatigue_result = evaluate_upper_threshold(
            features.fatigue,
            cfg.fatigue.severe_threshold, cfg.fatigue.moderate_threshold, 0.0,
            cfg.fatigue.severe_points, cfg.fatigue.moderate_points, 0.0,
        )
        if fatigue_result.triggered:
            factors.append({
                "name": "Subjective fatigue",
                "contribution": fatigue_result.contribution,
                "description": f"Fatigue level of {features.fatigue}/10",
                "value": features.fatigue,
            })

        # Sort by contribution and return top 5
        factors.sort(key=lambda x: x["contribution"], reverse=True)
        return factors[:5]

    def _generate_explanation(
        self,
        risk_level: RiskLevel,
        safety_eval: SafetyEvaluation,
        top_factors: list[dict],
    ) -> str:
        """Generate human-readable explanation text."""
        if risk_level == RiskLevel.GREEN:
            base = "Your body shows good recovery signs. Training as planned is possible."
        elif risk_level == RiskLevel.YELLOW:
            base = "Some stress indicators are elevated. Training modification is recommended."
        else:
            base = "Multiple critical indicators suggest high stress or impaired recovery. Rest is recommended."

        # Add safety rule warnings
        if safety_eval.any_triggered:
            rule_texts = [r.description for r in safety_eval.triggered_rules if r.description]
            if rule_texts:
                base += " " + " ".join(rule_texts)

        # Add top factor summary
        if top_factors and len(top_factors) > 0:
            factor_names = [f["name"] for f in top_factors[:3]]
            base += f" Main factors: {', '.join(factor_names)}."

        return base

    def _features_to_dict(self, features: UserFeatures) -> dict:
        """Convert features to dictionary for storage."""
        return {
            "date": features.date.isoformat(),
            "hrv_z": features.hrv_z,
            "rhr_delta": features.rhr_delta,
            "sleep_delta": features.sleep_delta,
            "hrv_rmssd": features.hrv_rmssd,
            "resting_hr": features.resting_hr,
            "sleep_duration_minutes": features.sleep_duration_minutes,
            "acute_load_7d": features.acute_load_7d,
            "chronic_load_28d": features.chronic_load_28d,
            "acwr": features.acwr,
            "consecutive_training_days": features.consecutive_training_days,
            "pain_score": features.pain_score,
            "max_soreness": features.max_soreness,
            "readiness": features.readiness,
            "fatigue": features.fatigue,
            "swelling": features.swelling,
        }

    @property
    def last_breakdown(self) -> Optional[ScoreBreakdown]:
        """Get the breakdown from the last score calculation."""
        return self._last_breakdown
