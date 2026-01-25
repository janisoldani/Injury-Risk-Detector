"""
Risk Scorer - Combines safety rules, features, and heuristics to calculate risk.

This is the main entry point for risk evaluation.
"""
from datetime import date
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

settings = get_settings()


class RiskScorer:
    """Calculates risk score for a planned training session."""

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.feature_builder = FeatureBuilder(db, user_id)

    async def evaluate_session(self, planned_session: PlannedSession) -> dict[str, Any]:
        """
        Evaluate risk for a planned session.

        Returns dict with all prediction data ready for storage.
        """
        # Build features
        features = await self.feature_builder.build_features(date.today())

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

        # Calculate heuristic score
        heuristic_score = self._calculate_heuristic_score(
            features, planned_sport, planned_intensity, planned_gym_split
        )

        # Determine final risk score and level
        risk_score, risk_level = self._determine_risk(heuristic_score, safety_eval)

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
        }

    def _calculate_heuristic_score(
        self,
        features: UserFeatures,
        planned_sport: SportType,
        planned_intensity: Optional[IntensityZone],
        planned_gym_split: Optional[GymSplit],
    ) -> float:
        """
        Calculate heuristic risk score (0-100).

        This is used until ML model is trained with enough data.
        """
        score = 0.0

        # HRV under baseline (more negative = worse)
        if features.hrv_z is not None:
            if features.hrv_z < -1.5:
                score += 25
            elif features.hrv_z < -1.0:
                score += 15
            elif features.hrv_z < -0.5:
                score += 8

        # RHR elevated
        if features.rhr_delta is not None:
            if features.rhr_delta > 8:
                score += 25
            elif features.rhr_delta > 5:
                score += 15
            elif features.rhr_delta > 3:
                score += 8

        # Sleep deficit
        if features.sleep_delta is not None:
            if features.sleep_delta < -90:  # 1.5 hours less
                score += 20
            elif features.sleep_delta < -60:
                score += 12
            elif features.sleep_delta < -30:
                score += 5

        # ACWR (Acute:Chronic Work Ratio)
        if features.acwr is not None:
            if features.acwr > 1.5:
                score += 25
            elif features.acwr > 1.3:
                score += 15
            elif features.acwr > 1.2:
                score += 8
            elif features.acwr < 0.8:  # Detraining risk (less relevant for injury)
                score += 3

        # Pain
        score += features.pain_score * 5

        # Pain trend (worsening)
        if features.pain_trend_3d > 2:
            score += 10
        elif features.pain_trend_3d > 0:
            score += 5

        # Soreness in target muscles
        target_soreness = get_soreness_in_target_muscles(
            features.soreness_map, planned_sport, planned_gym_split
        )
        score += target_soreness * 3

        # General soreness
        score += features.max_soreness * 1.5

        # Readiness (low = higher risk)
        if features.readiness < 4:
            score += 15
        elif features.readiness < 6:
            score += 8

        # Fatigue (high = higher risk)
        if features.fatigue > 7:
            score += 12
        elif features.fatigue > 5:
            score += 5

        # Consecutive training days
        if features.consecutive_training_days >= 5:
            score += 15
        elif features.consecutive_training_days >= 4:
            score += 8
        elif features.consecutive_training_days >= 3:
            score += 4

        # Sport impact and intensity multiplier
        impact_score = get_sport_impact_score(planned_sport)
        intensity_score = get_intensity_score(planned_intensity)
        # Higher impact/intensity slightly amplifies the score
        multiplier = 1.0 + (impact_score + intensity_score - 4) * 0.05
        score *= multiplier

        # Missing data penalty (uncertainty)
        missing_count = sum([features.missing_hrv, features.missing_sleep, features.missing_rhr])
        score += missing_count * 3

        return min(100, max(0, round(score)))

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
        factors = []

        # HRV
        if features.hrv_z is not None and features.hrv_z < -0.5:
            contribution = 25 if features.hrv_z < -1.5 else (15 if features.hrv_z < -1.0 else 8)
            factors.append({
                "name": "HRV unter Baseline",
                "contribution": contribution,
                "description": f"HRV {features.hrv_z:.1f} Standardabweichungen unter deinem 28-Tage-Durchschnitt",
                "value": features.hrv_z,
            })

        # RHR
        if features.rhr_delta is not None and features.rhr_delta > 3:
            contribution = 25 if features.rhr_delta > 8 else (15 if features.rhr_delta > 5 else 8)
            factors.append({
                "name": "Ruhepuls erhöht",
                "contribution": contribution,
                "description": f"Ruhepuls {features.rhr_delta:.0f} bpm über deinem Durchschnitt",
                "value": features.rhr_delta,
            })

        # Sleep
        if features.sleep_delta is not None and features.sleep_delta < -30:
            contribution = 20 if features.sleep_delta < -90 else (12 if features.sleep_delta < -60 else 5)
            factors.append({
                "name": "Schlafdefizit",
                "contribution": contribution,
                "description": f"{abs(features.sleep_delta):.0f} Minuten weniger Schlaf als üblich",
                "value": features.sleep_delta,
            })

        # ACWR
        if features.acwr is not None and features.acwr > 1.2:
            contribution = 25 if features.acwr > 1.5 else (15 if features.acwr > 1.3 else 8)
            factors.append({
                "name": "Hohe akute Belastung",
                "contribution": contribution,
                "description": f"ACWR von {features.acwr:.2f} - akute Belastung höher als chronisch",
                "value": features.acwr,
            })

        # Pain
        if features.pain_score > 0:
            contribution = features.pain_score * 5
            factors.append({
                "name": "Schmerz",
                "contribution": contribution,
                "description": f"Schmerz-Score von {features.pain_score}/10",
                "value": features.pain_score,
            })

        # Target muscle soreness
        target_soreness = get_soreness_in_target_muscles(
            features.soreness_map, planned_sport, planned_gym_split
        )
        if target_soreness >= 5:
            contribution = target_soreness * 3
            factors.append({
                "name": "Muskelkater in Zielmuskulatur",
                "contribution": contribution,
                "description": f"Muskelkater {target_soreness}/10 in der für diese Aktivität beanspruchten Muskulatur",
                "value": target_soreness,
            })

        # Consecutive days
        if features.consecutive_training_days >= 3:
            contribution = 15 if features.consecutive_training_days >= 5 else (8 if features.consecutive_training_days >= 4 else 4)
            factors.append({
                "name": "Aufeinanderfolgende Trainingstage",
                "contribution": contribution,
                "description": f"{features.consecutive_training_days} Tage Training am Stück",
                "value": features.consecutive_training_days,
            })

        # Fatigue
        if features.fatigue > 5:
            contribution = 12 if features.fatigue > 7 else 5
            factors.append({
                "name": "Subjektive Ermüdung",
                "contribution": contribution,
                "description": f"Ermüdungs-Level von {features.fatigue}/10",
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
            base = "Dein Körper zeigt gute Erholungszeichen. Training wie geplant ist möglich."
        elif risk_level == RiskLevel.YELLOW:
            base = "Einige Belastungsindikatoren sind erhöht. Eine Anpassung des Trainings wird empfohlen."
        else:
            base = "Mehrere kritische Indikatoren deuten auf hohe Belastung oder eingeschränkte Erholung hin. Erholung wird empfohlen."

        # Add safety rule warnings
        if safety_eval.any_triggered:
            rule_texts = [r.description for r in safety_eval.triggered_rules if r.description]
            if rule_texts:
                base += " " + " ".join(rule_texts)

        # Add top factor summary
        if top_factors and len(top_factors) > 0:
            factor_names = [f["name"] for f in top_factors[:3]]
            base += f" Hauptfaktoren: {', '.join(factor_names)}."

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
