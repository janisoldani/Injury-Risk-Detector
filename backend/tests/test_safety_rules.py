"""Tests for Safety Rules (R0-R4)."""
import pytest

from app.schemas.enums import GymSplit, IntensityZone, RiskLevel, SportType
from app.services.safety_rules import (
    evaluate_all_safety_rules,
    evaluate_r0_acute_pain,
    evaluate_r1_moderate_pain_impact,
    evaluate_r2_doms,
    evaluate_r3_recovery_markers,
    evaluate_r4_two_a_day,
)


class TestR0AcutePain:
    """Tests for R0 - Acute Red Flags."""

    def test_pain_score_7_triggers_red(self):
        result = evaluate_r0_acute_pain(pain_score=7, swelling=False)
        assert result.triggered is True
        assert result.override_risk_level == RiskLevel.RED
        assert SportType.RUN in result.blocked_sports
        assert SportType.WALK not in result.blocked_sports

    def test_pain_score_8_triggers_red(self):
        result = evaluate_r0_acute_pain(pain_score=8, swelling=False)
        assert result.triggered is True
        assert result.override_risk_level == RiskLevel.RED

    def test_swelling_triggers_red(self):
        result = evaluate_r0_acute_pain(pain_score=0, swelling=True)
        assert result.triggered is True
        assert result.override_risk_level == RiskLevel.RED
        assert "Schwellung" in result.description

    def test_pain_score_6_no_swelling_not_triggered(self):
        result = evaluate_r0_acute_pain(pain_score=6, swelling=False)
        assert result.triggered is False

    def test_no_pain_no_swelling_not_triggered(self):
        result = evaluate_r0_acute_pain(pain_score=0, swelling=False)
        assert result.triggered is False


class TestR1ModeratePainImpact:
    """Tests for R1 - Moderate Pain + Impact Sport."""

    def test_pain_5_with_football_triggers(self):
        result = evaluate_r1_moderate_pain_impact(
            pain_score=5, planned_sport=SportType.FOOTBALL
        )
        assert result.triggered is True
        assert SportType.FOOTBALL in result.blocked_sports
        assert result.override_risk_level == RiskLevel.YELLOW

    def test_pain_6_with_run_triggers(self):
        result = evaluate_r1_moderate_pain_impact(
            pain_score=6, planned_sport=SportType.RUN
        )
        assert result.triggered is True
        assert SportType.RUN in result.blocked_sports

    def test_pain_5_with_bike_triggers_but_bike_not_blocked(self):
        result = evaluate_r1_moderate_pain_impact(
            pain_score=5, planned_sport=SportType.BIKE
        )
        assert result.triggered is True
        # Bike should NOT be in blocked sports (low impact)
        assert SportType.BIKE not in result.blocked_sports
        # But high impact sports should be blocked
        assert SportType.FOOTBALL in result.blocked_sports

    def test_pain_4_not_triggered(self):
        result = evaluate_r1_moderate_pain_impact(
            pain_score=4, planned_sport=SportType.FOOTBALL
        )
        assert result.triggered is False


class TestR2DOMS:
    """Tests for R2 - DOMS in target muscle groups."""

    def test_high_quad_soreness_blocks_legs(self):
        soreness_map = {"quads": 8, "hamstrings": 3}
        result = evaluate_r2_doms(
            soreness_map=soreness_map,
            planned_sport=SportType.GYM,
            planned_gym_split=GymSplit.LEGS,
        )
        assert result.triggered is True
        assert result.override_risk_level == RiskLevel.YELLOW
        assert "quads" in result.description.lower()

    def test_high_quad_soreness_with_running(self):
        soreness_map = {"quads": 7}
        result = evaluate_r2_doms(
            soreness_map=soreness_map,
            planned_sport=SportType.RUN,
            planned_gym_split=None,
        )
        assert result.triggered is True

    def test_high_chest_soreness_ok_for_legs(self):
        soreness_map = {"chest": 9, "quads": 2}
        result = evaluate_r2_doms(
            soreness_map=soreness_map,
            planned_sport=SportType.GYM,
            planned_gym_split=GymSplit.LEGS,
        )
        assert result.triggered is False

    def test_moderate_soreness_not_triggered(self):
        soreness_map = {"quads": 5, "hamstrings": 4}
        result = evaluate_r2_doms(
            soreness_map=soreness_map,
            planned_sport=SportType.GYM,
            planned_gym_split=GymSplit.LEGS,
        )
        assert result.triggered is False


class TestR3RecoveryMarkers:
    """Tests for R3 - Poor Recovery Markers."""

    def test_both_markers_bad_triggers(self):
        result = evaluate_r3_recovery_markers(hrv_z=-2.0, rhr_delta=7.0)
        assert result.triggered is True
        assert result.max_allowed_intensity == IntensityZone.Z2
        assert result.override_risk_level == RiskLevel.YELLOW

    def test_only_hrv_bad_triggers_less_severe(self):
        result = evaluate_r3_recovery_markers(hrv_z=-2.0, rhr_delta=2.0)
        assert result.triggered is True
        assert result.max_allowed_intensity == IntensityZone.TEMPO

    def test_only_rhr_elevated_triggers_less_severe(self):
        result = evaluate_r3_recovery_markers(hrv_z=0.0, rhr_delta=7.0)
        assert result.triggered is True
        assert result.max_allowed_intensity == IntensityZone.TEMPO

    def test_good_markers_not_triggered(self):
        result = evaluate_r3_recovery_markers(hrv_z=0.5, rhr_delta=1.0)
        assert result.triggered is False

    def test_missing_data_not_triggered(self):
        result = evaluate_r3_recovery_markers(hrv_z=None, rhr_delta=None)
        assert result.triggered is False


class TestR4TwoADay:
    """Tests for R4 - Two-a-Day Limit."""

    def test_hard_session_today_with_hard_planned_triggers(self):
        result = evaluate_r4_two_a_day(
            hard_session_today=True, planned_intensity=IntensityZone.VO2
        )
        assert result.triggered is True
        assert result.max_allowed_intensity == IntensityZone.Z2
        assert result.override_risk_level == RiskLevel.YELLOW

    def test_hard_session_today_with_easy_planned_not_triggered(self):
        result = evaluate_r4_two_a_day(
            hard_session_today=True, planned_intensity=IntensityZone.Z2
        )
        assert result.triggered is False

    def test_no_hard_session_today_not_triggered(self):
        result = evaluate_r4_two_a_day(
            hard_session_today=False, planned_intensity=IntensityZone.VO2
        )
        assert result.triggered is False


class TestCombinedSafetyRules:
    """Tests for combined safety rule evaluation."""

    def test_multiple_rules_triggered(self):
        result = evaluate_all_safety_rules(
            pain_score=5,
            swelling=False,
            soreness_map={"quads": 8},
            planned_sport=SportType.RUN,
            planned_gym_split=None,
            planned_intensity=IntensityZone.THRESHOLD,
            hrv_z=-2.0,
            rhr_delta=6.0,
            hard_session_today=False,
        )
        # Should trigger R1, R2, R3
        assert result.any_triggered
        assert len(result.triggered_rules) >= 2

    def test_r0_takes_precedence(self):
        result = evaluate_all_safety_rules(
            pain_score=8,  # R0 trigger
            swelling=False,
            soreness_map={},
            planned_sport=SportType.RUN,
            planned_gym_split=None,
            planned_intensity=IntensityZone.Z2,
            hrv_z=0.0,
            rhr_delta=0.0,
            hard_session_today=False,
        )
        assert result.override_risk_level == RiskLevel.RED
        assert SportType.RUN in result.blocked_sports

    def test_no_rules_triggered(self):
        result = evaluate_all_safety_rules(
            pain_score=2,
            swelling=False,
            soreness_map={"quads": 3},
            planned_sport=SportType.BIKE,
            planned_gym_split=None,
            planned_intensity=IntensityZone.Z2,
            hrv_z=0.5,
            rhr_delta=1.0,
            hard_session_today=False,
        )
        assert not result.any_triggered
        assert result.override_risk_level is None
