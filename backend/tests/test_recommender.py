"""Tests for Recommendation Engine."""
import pytest

from app.schemas.enums import GymSplit, IntensityZone, MuscleRegion, RiskLevel, SportType
from app.services.recommender import RecommendationEngine
from app.services.safety_rules import SafetyEvaluation, SafetyRuleResult


def create_empty_safety_eval() -> SafetyEvaluation:
    """Create an empty safety evaluation (no rules triggered)."""
    return SafetyEvaluation(
        triggered_rules=[],
        max_allowed_intensity=None,
        blocked_sports=[],
        blocked_muscle_regions=[],
        override_risk_level=None,
    )


def create_safety_eval_with_blocked(
    blocked_sports: list[SportType] = None,
    blocked_muscles: list[MuscleRegion] = None,
) -> SafetyEvaluation:
    """Create a safety evaluation with blocked items."""
    return SafetyEvaluation(
        triggered_rules=[],
        max_allowed_intensity=IntensityZone.Z2,
        blocked_sports=blocked_sports or [],
        blocked_muscle_regions=blocked_muscles or [],
        override_risk_level=RiskLevel.YELLOW,
    )


class TestGreenRecommendations:
    """Tests for green risk level recommendations."""

    def test_green_keeps_original_plan(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.GREEN,
            safety_eval=create_empty_safety_eval(),
        )

        rec_a, rec_b = engine.generate_recommendations(
            planned_sport=SportType.RUN,
            planned_duration=60,
            planned_intensity=IntensityZone.THRESHOLD,
            planned_gym_split=None,
        )

        # Rec A should be the original plan
        assert rec_a.sport_type == SportType.RUN
        assert rec_a.duration_minutes == 60
        assert rec_a.intensity == IntensityZone.THRESHOLD
        assert rec_a.is_original_plan_modified is False

        # Rec B should be an alternative
        assert rec_b.sport_type != SportType.RUN

    def test_green_with_gym_provides_alternative_split(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.GREEN,
            safety_eval=create_empty_safety_eval(),
        )

        rec_a, rec_b = engine.generate_recommendations(
            planned_sport=SportType.GYM,
            planned_duration=50,
            planned_intensity=None,
            planned_gym_split=GymSplit.PUSH,
        )

        assert rec_a.sport_type == SportType.GYM
        assert rec_a.gym_split == GymSplit.PUSH


class TestYellowRecommendations:
    """Tests for yellow risk level recommendations."""

    def test_yellow_modifies_plan(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.YELLOW,
            safety_eval=create_empty_safety_eval(),
        )

        rec_a, rec_b = engine.generate_recommendations(
            planned_sport=SportType.RUN,
            planned_duration=60,
            planned_intensity=IntensityZone.VO2,
            planned_gym_split=None,
        )

        # Rec A should be modified (lower intensity/duration)
        assert rec_a.is_original_plan_modified is True
        assert rec_a.duration_minutes < 60  # Should be reduced
        assert rec_a.intensity != IntensityZone.VO2  # Should be reduced

        # Rec B should be low impact
        assert rec_b.sport_type in [SportType.BIKE, SportType.SWIM, SportType.WALK, SportType.GYM]

    def test_yellow_with_blocked_sport_substitutes(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.YELLOW,
            safety_eval=create_safety_eval_with_blocked(
                blocked_sports=[SportType.RUN, SportType.FOOTBALL]
            ),
        )

        rec_a, rec_b = engine.generate_recommendations(
            planned_sport=SportType.RUN,
            planned_duration=45,
            planned_intensity=IntensityZone.TEMPO,
            planned_gym_split=None,
        )

        # Rec A should substitute the blocked sport
        assert rec_a.sport_type != SportType.RUN
        assert rec_a.is_original_plan_modified is True

    def test_yellow_avoids_blocked_muscles_for_gym(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.YELLOW,
            safety_eval=create_empty_safety_eval(),
            blocked_muscle_regions=[MuscleRegion.QUADS, MuscleRegion.HAMSTRINGS],
        )

        rec_a, rec_b = engine.generate_recommendations(
            planned_sport=SportType.GYM,
            planned_duration=50,
            planned_intensity=None,
            planned_gym_split=GymSplit.LEGS,  # Uses blocked muscles
        )

        # Should switch to a split that doesn't use legs
        assert rec_a.gym_split != GymSplit.LEGS


class TestRedRecommendations:
    """Tests for red risk level recommendations."""

    def test_red_recommends_recovery_only(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.RED,
            safety_eval=create_empty_safety_eval(),
        )

        rec_a, rec_b = engine.generate_recommendations(
            planned_sport=SportType.HYROX,  # Very intense
            planned_duration=90,
            planned_intensity=IntensityZone.MAX,
            planned_gym_split=None,
        )

        # Both should be recovery activities
        assert rec_a.sport_type == SportType.WALK
        assert rec_a.intensity == IntensityZone.Z1
        assert rec_a.duration_minutes <= 30

        assert rec_b.sport_type == SportType.SWIM
        assert rec_b.intensity == IntensityZone.Z1


class TestIntensityReduction:
    """Tests for intensity reduction logic."""

    def test_max_reduces_to_vo2(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.YELLOW,
            safety_eval=create_empty_safety_eval(),
        )
        result = engine._reduce_intensity(IntensityZone.MAX)
        assert result == IntensityZone.VO2

    def test_vo2_reduces_to_threshold(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.YELLOW,
            safety_eval=create_empty_safety_eval(),
        )
        result = engine._reduce_intensity(IntensityZone.VO2)
        assert result == IntensityZone.THRESHOLD

    def test_z1_stays_z1(self):
        engine = RecommendationEngine(
            risk_level=RiskLevel.YELLOW,
            safety_eval=create_empty_safety_eval(),
        )
        result = engine._reduce_intensity(IntensityZone.Z1)
        assert result == IntensityZone.Z1
