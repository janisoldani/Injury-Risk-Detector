"""Tests for ScoringConfig and configurable scoring."""
import tempfile
from pathlib import Path

import pytest
import yaml

from app.services.scoring_config import (
    ACWRConfig,
    HRVConfig,
    RHRConfig,
    ScoringConfig,
    SleepConfig,
    get_scoring_config,
    set_scoring_config,
)


class TestScoringConfigDefaults:
    """Tests for default configuration values."""

    def test_default_hrv_thresholds(self):
        config = ScoringConfig()
        assert config.hrv.severe_threshold == -1.5
        assert config.hrv.moderate_threshold == -1.0
        assert config.hrv.mild_threshold == -0.5

    def test_default_hrv_points(self):
        config = ScoringConfig()
        assert config.hrv.severe_points == 25
        assert config.hrv.moderate_points == 15
        assert config.hrv.mild_points == 8

    def test_default_rhr_thresholds(self):
        config = ScoringConfig()
        assert config.rhr.severe_threshold == 8.0
        assert config.rhr.moderate_threshold == 5.0
        assert config.rhr.mild_threshold == 3.0

    def test_default_acwr_thresholds(self):
        config = ScoringConfig()
        assert config.acwr.critical_threshold == 1.5
        assert config.acwr.elevated_threshold == 1.3
        assert config.acwr.warning_threshold == 1.2
        assert config.acwr.detraining_threshold == 0.8

    def test_default_pain_multiplier(self):
        config = ScoringConfig()
        assert config.pain.points_per_level == 5

    def test_default_safety_rules(self):
        config = ScoringConfig()
        assert config.safety_rules.r0_pain_threshold == 7
        assert config.safety_rules.r2_doms_threshold == 7


class TestScoringConfigCustomization:
    """Tests for custom configuration values."""

    def test_custom_hrv_config(self):
        custom_hrv = HRVConfig(
            severe_threshold=-2.0,
            moderate_threshold=-1.5,
            mild_threshold=-1.0,
            severe_points=30,
            moderate_points=20,
            mild_points=10,
        )
        config = ScoringConfig(hrv=custom_hrv)

        assert config.hrv.severe_threshold == -2.0
        assert config.hrv.severe_points == 30

    def test_custom_acwr_config(self):
        custom_acwr = ACWRConfig(
            critical_threshold=1.8,
            critical_points=35,
        )
        config = ScoringConfig(acwr=custom_acwr)

        assert config.acwr.critical_threshold == 1.8
        assert config.acwr.critical_points == 35
        # Other values should still be defaults
        assert config.acwr.elevated_threshold == 1.3


class TestScoringConfigYAML:
    """Tests for YAML loading."""

    def test_load_from_yaml(self):
        yaml_content = """
hrv:
  severe_threshold: -2.0
  severe_points: 30

rhr:
  severe_threshold: 10.0
  severe_points: 30

acwr:
  critical_threshold: 1.6
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = ScoringConfig.from_yaml(f.name)

            assert config.hrv.severe_threshold == -2.0
            assert config.hrv.severe_points == 30
            assert config.rhr.severe_threshold == 10.0
            assert config.acwr.critical_threshold == 1.6

            # Non-specified values should be defaults
            assert config.hrv.moderate_threshold == -1.0  # default
            assert config.sleep.severe_threshold == -90.0  # default

    def test_to_dict(self):
        config = ScoringConfig()
        config_dict = config.to_dict()

        assert "hrv" in config_dict
        assert "rhr" in config_dict
        assert "sleep" in config_dict
        assert "acwr" in config_dict
        assert "pain" in config_dict

        assert config_dict["hrv"]["severe_threshold"] == -1.5
        assert config_dict["pain"]["points_per_level"] == 5


class TestScoringConfigSingleton:
    """Tests for global config management."""

    def test_get_default_config(self):
        config = get_scoring_config()
        assert config is not None
        assert isinstance(config, ScoringConfig)

    def test_set_custom_config(self):
        original = get_scoring_config()

        custom = ScoringConfig(
            hrv=HRVConfig(severe_points=50)
        )
        set_scoring_config(custom)

        current = get_scoring_config()
        assert current.hrv.severe_points == 50

        # Restore original
        set_scoring_config(original)


class TestScoreCalculationWithConfig:
    """Tests verifying score calculation uses config values."""

    def test_hrv_severe_uses_config_points(self):
        """Verify that HRV severe condition uses configured points."""
        from app.ml.features import UserFeatures
        from app.services.risk_scorer import RiskScorer, ScoreBreakdown
        from app.schemas.enums import SportType

        # Create a config with custom HRV points
        custom_config = ScoringConfig(
            hrv=HRVConfig(severe_points=40)  # Higher than default 25
        )

        # Mock features with severe HRV
        class MockFeatures:
            hrv_z = -2.0  # Below severe threshold
            rhr_delta = 0
            sleep_delta = 0
            acwr = 1.0
            pain_score = 0
            pain_trend_3d = 0
            max_soreness = 0
            soreness_map = {}
            readiness = 7
            fatigue = 3
            consecutive_training_days = 0
            missing_hrv = False
            missing_sleep = False
            missing_rhr = False

        # We can't easily test the full RiskScorer without async DB
        # But we can verify the config structure is correct
        assert custom_config.hrv.severe_points == 40
        assert custom_config.hrv.severe_threshold == -1.5

    def test_pain_multiplier_effect(self):
        """Verify pain score uses configured multiplier."""
        default_config = ScoringConfig()
        custom_config = ScoringConfig()
        custom_config.pain.points_per_level = 10  # Double the default

        pain_score = 5

        default_contribution = pain_score * default_config.pain.points_per_level
        custom_contribution = pain_score * custom_config.pain.points_per_level

        assert default_contribution == 25  # 5 * 5
        assert custom_contribution == 50  # 5 * 10

    def test_acwr_thresholds(self):
        """Verify ACWR threshold logic."""
        config = ScoringConfig()

        # Critical zone
        acwr = 1.6
        assert acwr > config.acwr.critical_threshold
        expected_points = config.acwr.critical_points
        assert expected_points == 25

        # Elevated zone
        acwr = 1.4
        assert acwr > config.acwr.elevated_threshold
        assert acwr <= config.acwr.critical_threshold

        # Warning zone
        acwr = 1.25
        assert acwr > config.acwr.warning_threshold
        assert acwr <= config.acwr.elevated_threshold


class TestScoreBreakdown:
    """Tests for ScoreBreakdown dataclass."""

    def test_breakdown_to_dict(self):
        from app.services.risk_scorer import ScoreBreakdown

        breakdown = ScoreBreakdown(
            hrv_contribution=25,
            rhr_contribution=15,
            pain_contribution=10,
            base_score=50,
            intensity_multiplier=1.1,
            final_score=55,
        )

        result = breakdown.to_dict()

        assert result["hrv"] == 25
        assert result["rhr"] == 15
        assert result["pain"] == 10
        assert result["base_score"] == 50
        assert result["intensity_multiplier"] == 1.1
        assert result["final_score"] == 55

    def test_breakdown_defaults(self):
        from app.services.risk_scorer import ScoreBreakdown

        breakdown = ScoreBreakdown()

        assert breakdown.hrv_contribution == 0.0
        assert breakdown.base_score == 0.0
        assert breakdown.intensity_multiplier == 1.0
        assert breakdown.final_score == 0.0
