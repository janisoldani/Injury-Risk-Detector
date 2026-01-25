"""
Scoring Configuration - Configurable weights and thresholds for risk calculation.

All "magic numbers" are centralized here for easy tuning without code changes.
"""
from dataclasses import dataclass, field
from typing import Optional

import yaml
from pathlib import Path


@dataclass
class HRVConfig:
    """HRV-based scoring configuration."""
    # Z-score thresholds (standard deviations below baseline)
    severe_threshold: float = -1.5  # Very poor recovery
    moderate_threshold: float = -1.0  # Moderate concern
    mild_threshold: float = -0.5  # Slight concern

    # Points added to risk score
    severe_points: int = 25
    moderate_points: int = 15
    mild_points: int = 8


@dataclass
class RHRConfig:
    """Resting Heart Rate scoring configuration."""
    # Delta thresholds (bpm above baseline)
    severe_threshold: float = 8.0
    moderate_threshold: float = 5.0
    mild_threshold: float = 3.0

    # Points added to risk score
    severe_points: int = 25
    moderate_points: int = 15
    mild_points: int = 8


@dataclass
class SleepConfig:
    """Sleep deficit scoring configuration."""
    # Delta thresholds (minutes below baseline)
    severe_threshold: float = -90.0  # 1.5 hours less
    moderate_threshold: float = -60.0  # 1 hour less
    mild_threshold: float = -30.0  # 30 min less

    # Points added to risk score
    severe_points: int = 20
    moderate_points: int = 12
    mild_points: int = 5


@dataclass
class ACWRConfig:
    """Acute:Chronic Workload Ratio scoring configuration."""
    # Ratio thresholds
    critical_threshold: float = 1.5  # High injury risk
    elevated_threshold: float = 1.3  # Elevated risk
    warning_threshold: float = 1.2  # Slight concern
    detraining_threshold: float = 0.8  # Too low (detraining)

    # Points added to risk score
    critical_points: int = 25
    elevated_points: int = 15
    warning_points: int = 8
    detraining_points: int = 3


@dataclass
class PainConfig:
    """Pain scoring configuration."""
    # Points per pain level (multiplier)
    points_per_level: int = 5  # pain_score * this value

    # Pain trend scoring
    worsening_severe_threshold: float = 2.0  # Pain increased by 2+ over 3 days
    worsening_moderate_threshold: float = 0.0  # Any increase
    worsening_severe_points: int = 10
    worsening_moderate_points: int = 5


@dataclass
class SorenessConfig:
    """Muscle soreness scoring configuration."""
    # Points for target muscle soreness (multiplier)
    target_muscle_points_per_level: int = 3

    # Points for general soreness (multiplier)
    general_points_per_level: float = 1.5


@dataclass
class ReadinessConfig:
    """Subjective readiness scoring configuration."""
    # Thresholds (lower = worse)
    poor_threshold: int = 4
    moderate_threshold: int = 6

    # Points added
    poor_points: int = 15
    moderate_points: int = 8


@dataclass
class FatigueConfig:
    """Subjective fatigue scoring configuration."""
    # Thresholds (higher = worse)
    severe_threshold: int = 7
    moderate_threshold: int = 5

    # Points added
    severe_points: int = 12
    moderate_points: int = 5


@dataclass
class TrainingLoadConfig:
    """Training load scoring configuration."""
    # Consecutive days thresholds
    consecutive_severe_threshold: int = 5
    consecutive_moderate_threshold: int = 4
    consecutive_mild_threshold: int = 3

    # Points added
    consecutive_severe_points: int = 15
    consecutive_moderate_points: int = 8
    consecutive_mild_points: int = 4


@dataclass
class MissingDataConfig:
    """Missing data penalty configuration."""
    # Points per missing data source
    points_per_missing: int = 3


@dataclass
class IntensityMultiplierConfig:
    """Configuration for sport impact and intensity multipliers."""
    # Base value for neutral multiplier
    neutral_base: int = 4  # (impact + intensity) - neutral_base

    # Multiplier scaling factor
    scaling_factor: float = 0.05


@dataclass
class SafetyRulesConfig:
    """Safety rules thresholds configuration."""
    # R0: Acute pain thresholds
    r0_pain_threshold: int = 7
    r0_swelling_triggers: bool = True

    # R1: Moderate pain thresholds
    r1_pain_min: int = 5
    r1_pain_max: int = 6

    # R2: DOMS threshold
    r2_doms_threshold: int = 7

    # R3: Recovery markers
    r3_hrv_z_threshold: float = -1.5
    r3_rhr_delta_threshold: float = 5.0


@dataclass
class ScoringConfig:
    """Master configuration for all risk scoring parameters."""
    hrv: HRVConfig = field(default_factory=HRVConfig)
    rhr: RHRConfig = field(default_factory=RHRConfig)
    sleep: SleepConfig = field(default_factory=SleepConfig)
    acwr: ACWRConfig = field(default_factory=ACWRConfig)
    pain: PainConfig = field(default_factory=PainConfig)
    soreness: SorenessConfig = field(default_factory=SorenessConfig)
    readiness: ReadinessConfig = field(default_factory=ReadinessConfig)
    fatigue: FatigueConfig = field(default_factory=FatigueConfig)
    training_load: TrainingLoadConfig = field(default_factory=TrainingLoadConfig)
    missing_data: MissingDataConfig = field(default_factory=MissingDataConfig)
    intensity_multiplier: IntensityMultiplierConfig = field(default_factory=IntensityMultiplierConfig)
    safety_rules: SafetyRulesConfig = field(default_factory=SafetyRulesConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ScoringConfig":
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        config = cls()

        if "hrv" in data:
            config.hrv = HRVConfig(**data["hrv"])
        if "rhr" in data:
            config.rhr = RHRConfig(**data["rhr"])
        if "sleep" in data:
            config.sleep = SleepConfig(**data["sleep"])
        if "acwr" in data:
            config.acwr = ACWRConfig(**data["acwr"])
        if "pain" in data:
            config.pain = PainConfig(**data["pain"])
        if "soreness" in data:
            config.soreness = SorenessConfig(**data["soreness"])
        if "readiness" in data:
            config.readiness = ReadinessConfig(**data["readiness"])
        if "fatigue" in data:
            config.fatigue = FatigueConfig(**data["fatigue"])
        if "training_load" in data:
            config.training_load = TrainingLoadConfig(**data["training_load"])
        if "missing_data" in data:
            config.missing_data = MissingDataConfig(**data["missing_data"])
        if "intensity_multiplier" in data:
            config.intensity_multiplier = IntensityMultiplierConfig(**data["intensity_multiplier"])
        if "safety_rules" in data:
            config.safety_rules = SafetyRulesConfig(**data["safety_rules"])

        return config

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "hrv": self.hrv.__dict__,
            "rhr": self.rhr.__dict__,
            "sleep": self.sleep.__dict__,
            "acwr": self.acwr.__dict__,
            "pain": self.pain.__dict__,
            "soreness": self.soreness.__dict__,
            "readiness": self.readiness.__dict__,
            "fatigue": self.fatigue.__dict__,
            "training_load": self.training_load.__dict__,
            "missing_data": self.missing_data.__dict__,
            "intensity_multiplier": self.intensity_multiplier.__dict__,
            "safety_rules": self.safety_rules.__dict__,
        }


# Global default configuration instance
_default_config: Optional[ScoringConfig] = None


def get_scoring_config() -> ScoringConfig:
    """Get the current scoring configuration (singleton pattern)."""
    global _default_config
    if _default_config is None:
        _default_config = ScoringConfig()
    return _default_config


def set_scoring_config(config: ScoringConfig) -> None:
    """Set a custom scoring configuration."""
    global _default_config
    _default_config = config


def load_scoring_config_from_yaml(path: str | Path) -> ScoringConfig:
    """Load and set scoring configuration from YAML file."""
    config = ScoringConfig.from_yaml(path)
    set_scoring_config(config)
    return config
