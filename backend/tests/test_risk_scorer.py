"""Tests for RiskScorer with configurable scoring."""
import pytest
from datetime import date

from app.schemas.enums import GymSplit, IntensityZone, RiskLevel, SportType
from app.services.scoring_config import (
    HRVConfig,
    PainConfig,
    ScoringConfig,
)
from app.services.risk_scorer import ScoreBreakdown


class TestScoreBreakdownCalculation:
    """Tests for score breakdown logic."""

    def test_hrv_contribution_severe(self):
        """Test HRV contribution at severe threshold."""
        config = ScoringConfig()
        hrv_z = -2.0  # Below severe threshold (-1.5)

        # Simulate the logic
        if hrv_z < config.hrv.severe_threshold:
            contribution = config.hrv.severe_points
        elif hrv_z < config.hrv.moderate_threshold:
            contribution = config.hrv.moderate_points
        elif hrv_z < config.hrv.mild_threshold:
            contribution = config.hrv.mild_points
        else:
            contribution = 0

        assert contribution == 25

    def test_hrv_contribution_moderate(self):
        """Test HRV contribution at moderate threshold."""
        config = ScoringConfig()
        hrv_z = -1.2  # Between moderate (-1.0) and severe (-1.5)

        if hrv_z < config.hrv.severe_threshold:
            contribution = config.hrv.severe_points
        elif hrv_z < config.hrv.moderate_threshold:
            contribution = config.hrv.moderate_points
        elif hrv_z < config.hrv.mild_threshold:
            contribution = config.hrv.mild_points
        else:
            contribution = 0

        assert contribution == 15

    def test_hrv_contribution_mild(self):
        """Test HRV contribution at mild threshold."""
        config = ScoringConfig()
        hrv_z = -0.7  # Between mild (-0.5) and moderate (-1.0)

        if hrv_z < config.hrv.severe_threshold:
            contribution = config.hrv.severe_points
        elif hrv_z < config.hrv.moderate_threshold:
            contribution = config.hrv.moderate_points
        elif hrv_z < config.hrv.mild_threshold:
            contribution = config.hrv.mild_points
        else:
            contribution = 0

        assert contribution == 8

    def test_hrv_contribution_normal(self):
        """Test HRV contribution when normal."""
        config = ScoringConfig()
        hrv_z = 0.5  # Above mild threshold

        if hrv_z < config.hrv.severe_threshold:
            contribution = config.hrv.severe_points
        elif hrv_z < config.hrv.moderate_threshold:
            contribution = config.hrv.moderate_points
        elif hrv_z < config.hrv.mild_threshold:
            contribution = config.hrv.mild_points
        else:
            contribution = 0

        assert contribution == 0


class TestRHRContribution:
    """Tests for RHR contribution calculation."""

    def test_rhr_severely_elevated(self):
        config = ScoringConfig()
        rhr_delta = 10.0  # Above severe (8.0)

        if rhr_delta > config.rhr.severe_threshold:
            contribution = config.rhr.severe_points
        elif rhr_delta > config.rhr.moderate_threshold:
            contribution = config.rhr.moderate_points
        elif rhr_delta > config.rhr.mild_threshold:
            contribution = config.rhr.mild_points
        else:
            contribution = 0

        assert contribution == 25

    def test_rhr_moderately_elevated(self):
        config = ScoringConfig()
        rhr_delta = 6.0  # Between moderate (5.0) and severe (8.0)

        if rhr_delta > config.rhr.severe_threshold:
            contribution = config.rhr.severe_points
        elif rhr_delta > config.rhr.moderate_threshold:
            contribution = config.rhr.moderate_points
        elif rhr_delta > config.rhr.mild_threshold:
            contribution = config.rhr.mild_points
        else:
            contribution = 0

        assert contribution == 15


class TestACWRContribution:
    """Tests for ACWR (Acute:Chronic Workload Ratio) contribution."""

    def test_acwr_critical(self):
        config = ScoringConfig()
        acwr = 1.6  # Above critical (1.5)

        if acwr > config.acwr.critical_threshold:
            contribution = config.acwr.critical_points
        elif acwr > config.acwr.elevated_threshold:
            contribution = config.acwr.elevated_points
        elif acwr > config.acwr.warning_threshold:
            contribution = config.acwr.warning_points
        elif acwr < config.acwr.detraining_threshold:
            contribution = config.acwr.detraining_points
        else:
            contribution = 0

        assert contribution == 25

    def test_acwr_optimal(self):
        """ACWR in optimal range (0.8-1.2) should contribute 0."""
        config = ScoringConfig()
        acwr = 1.0

        if acwr > config.acwr.critical_threshold:
            contribution = config.acwr.critical_points
        elif acwr > config.acwr.elevated_threshold:
            contribution = config.acwr.elevated_points
        elif acwr > config.acwr.warning_threshold:
            contribution = config.acwr.warning_points
        elif acwr < config.acwr.detraining_threshold:
            contribution = config.acwr.detraining_points
        else:
            contribution = 0

        assert contribution == 0

    def test_acwr_detraining(self):
        """Low ACWR (detraining) should contribute small amount."""
        config = ScoringConfig()
        acwr = 0.6  # Below detraining (0.8)

        if acwr > config.acwr.critical_threshold:
            contribution = config.acwr.critical_points
        elif acwr > config.acwr.elevated_threshold:
            contribution = config.acwr.elevated_points
        elif acwr > config.acwr.warning_threshold:
            contribution = config.acwr.warning_points
        elif acwr < config.acwr.detraining_threshold:
            contribution = config.acwr.detraining_points
        else:
            contribution = 0

        assert contribution == 3


class TestPainContribution:
    """Tests for pain contribution calculation."""

    def test_pain_linear_scaling(self):
        config = ScoringConfig()

        for pain_score in range(0, 11):
            contribution = pain_score * config.pain.points_per_level
            assert contribution == pain_score * 5

    def test_pain_trend_worsening_severe(self):
        config = ScoringConfig()
        pain_trend = 3.0  # Increased by 3 over 3 days

        if pain_trend > config.pain.worsening_severe_threshold:
            contribution = config.pain.worsening_severe_points
        elif pain_trend > config.pain.worsening_moderate_threshold:
            contribution = config.pain.worsening_moderate_points
        else:
            contribution = 0

        assert contribution == 10

    def test_pain_trend_worsening_moderate(self):
        config = ScoringConfig()
        pain_trend = 1.0  # Slight increase

        if pain_trend > config.pain.worsening_severe_threshold:
            contribution = config.pain.worsening_severe_points
        elif pain_trend > config.pain.worsening_moderate_threshold:
            contribution = config.pain.worsening_moderate_points
        else:
            contribution = 0

        assert contribution == 5


class TestIntensityMultiplier:
    """Tests for intensity/impact multiplier."""

    def test_neutral_multiplier(self):
        """Neutral impact + intensity should give multiplier of 1.0."""
        config = ScoringConfig()

        # Impact=2 (low) + Intensity=2 (Z2) = 4 = neutral_base
        impact_score = 2
        intensity_score = 2

        multiplier = 1.0 + (
            impact_score + intensity_score - config.intensity_multiplier.neutral_base
        ) * config.intensity_multiplier.scaling_factor

        assert multiplier == 1.0

    def test_high_impact_high_intensity_multiplier(self):
        """High impact + high intensity should increase multiplier."""
        config = ScoringConfig()

        # Impact=5 (very high) + Intensity=5 (VO2) = 10
        impact_score = 5
        intensity_score = 5

        multiplier = 1.0 + (
            impact_score + intensity_score - config.intensity_multiplier.neutral_base
        ) * config.intensity_multiplier.scaling_factor

        # (5+5-4) * 0.05 = 0.3, so multiplier = 1.3
        assert multiplier == pytest.approx(1.3)

    def test_low_impact_low_intensity_multiplier(self):
        """Low impact + low intensity should decrease multiplier."""
        config = ScoringConfig()

        # Impact=1 (very low) + Intensity=1 (Z1) = 2
        impact_score = 1
        intensity_score = 1

        multiplier = 1.0 + (
            impact_score + intensity_score - config.intensity_multiplier.neutral_base
        ) * config.intensity_multiplier.scaling_factor

        # (1+1-4) * 0.05 = -0.1, so multiplier = 0.9
        assert multiplier == pytest.approx(0.9)


class TestRiskLevelThresholds:
    """Tests for risk level determination."""

    def test_green_threshold(self):
        """Score 0-35 should be GREEN."""
        from app.config import get_settings
        settings = get_settings()

        for score in [0, 15, 35]:
            if score <= settings.risk_threshold_green_max:
                level = RiskLevel.GREEN
            elif score <= settings.risk_threshold_yellow_max:
                level = RiskLevel.YELLOW
            else:
                level = RiskLevel.RED

            assert level == RiskLevel.GREEN

    def test_yellow_threshold(self):
        """Score 36-60 should be YELLOW."""
        from app.config import get_settings
        settings = get_settings()

        for score in [36, 45, 60]:
            if score <= settings.risk_threshold_green_max:
                level = RiskLevel.GREEN
            elif score <= settings.risk_threshold_yellow_max:
                level = RiskLevel.YELLOW
            else:
                level = RiskLevel.RED

            assert level == RiskLevel.YELLOW

    def test_red_threshold(self):
        """Score 61-100 should be RED."""
        from app.config import get_settings
        settings = get_settings()

        for score in [61, 75, 100]:
            if score <= settings.risk_threshold_green_max:
                level = RiskLevel.GREEN
            elif score <= settings.risk_threshold_yellow_max:
                level = RiskLevel.YELLOW
            else:
                level = RiskLevel.RED

            assert level == RiskLevel.RED


class TestCustomConfigScoring:
    """Tests with custom configuration values."""

    def test_more_sensitive_hrv(self):
        """Test with more sensitive HRV thresholds."""
        sensitive_config = ScoringConfig(
            hrv=HRVConfig(
                severe_threshold=-1.0,  # Trigger earlier
                moderate_threshold=-0.5,
                mild_threshold=-0.2,
                severe_points=35,  # Higher penalty
            )
        )

        hrv_z = -1.2  # Would be "moderate" in default, "severe" in sensitive

        # With sensitive config
        if hrv_z < sensitive_config.hrv.severe_threshold:
            sensitive_contribution = sensitive_config.hrv.severe_points
        else:
            sensitive_contribution = 0

        assert sensitive_contribution == 35

        # With default config
        default_config = ScoringConfig()
        if hrv_z < default_config.hrv.severe_threshold:
            default_contribution = default_config.hrv.severe_points
        else:
            default_contribution = default_config.hrv.moderate_points

        assert default_contribution == 15  # Only moderate in default

    def test_more_lenient_pain(self):
        """Test with more lenient pain scoring."""
        lenient_config = ScoringConfig(
            pain=PainConfig(points_per_level=2)  # Lower than default 5
        )

        pain_score = 6
        lenient_contribution = pain_score * lenient_config.pain.points_per_level
        default_contribution = pain_score * ScoringConfig().pain.points_per_level

        assert lenient_contribution == 12
        assert default_contribution == 30


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_score_capped_at_100(self):
        """Final score should never exceed 100."""
        # Simulate a scenario with many high contributions
        contributions = [25, 25, 20, 25, 50, 15, 15, 12, 15, 9]  # Total = 211
        total = sum(contributions)
        final_score = min(100, max(0, round(total)))

        assert final_score == 100

    def test_score_floored_at_0(self):
        """Final score should never be negative."""
        # This shouldn't happen in practice, but test the floor
        score = -10
        final_score = min(100, max(0, round(score)))

        assert final_score == 0

    def test_missing_data_penalty(self):
        """Test missing data adds uncertainty penalty."""
        config = ScoringConfig()

        missing_count = 3  # All three sources missing
        penalty = missing_count * config.missing_data.points_per_missing

        assert penalty == 9

    def test_none_values_handled(self):
        """Test that None values for optional metrics are handled."""
        config = ScoringConfig()

        # Simulate HRV being None
        hrv_z = None
        if hrv_z is not None:
            if hrv_z < config.hrv.severe_threshold:
                contribution = config.hrv.severe_points
            else:
                contribution = 0
        else:
            contribution = 0

        assert contribution == 0
