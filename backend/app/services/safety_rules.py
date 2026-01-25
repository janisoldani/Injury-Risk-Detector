"""
Safety Rules (R0-R4) - Deterministic rules that override ML predictions.

These rules are "non-negotiable" and override any ML-based risk score.
"""
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.enums import (
    GYM_SPLIT_MUSCLE_MAP,
    SPORT_IMPACT_MAP,
    SPORT_MUSCLE_MAP,
    GymSplit,
    ImpactLevel,
    IntensityZone,
    MuscleRegion,
    RiskLevel,
    SportType,
)


@dataclass
class SafetyRuleResult:
    rule_id: str
    rule_name: str
    description: str
    triggered: bool = False
    blocked_sports: list[SportType] = field(default_factory=list)
    max_allowed_intensity: Optional[IntensityZone] = None
    blocked_muscle_regions: list[MuscleRegion] = field(default_factory=list)
    override_risk_level: Optional[RiskLevel] = None


@dataclass
class SafetyEvaluation:
    triggered_rules: list[SafetyRuleResult]
    max_allowed_intensity: Optional[IntensityZone]
    blocked_sports: list[SportType]
    blocked_muscle_regions: list[MuscleRegion]
    override_risk_level: Optional[RiskLevel]

    @property
    def any_triggered(self) -> bool:
        return len(self.triggered_rules) > 0


# Sports considered "high impact"
HIGH_IMPACT_SPORTS = [
    SportType.FOOTBALL,
    SportType.RUN,
    SportType.HYROX,
]


def evaluate_r0_acute_pain(
    pain_score: int,
    swelling: bool,
) -> SafetyRuleResult:
    """
    R0 – Acute Red Flags
    Schmerz ≥ 7/10 ODER Schwellung = ja
    → ROT, Empfehlung: Rest / ärztlich abklären
    """
    result = SafetyRuleResult(
        rule_id="R0",
        rule_name="Acute Red Flags",
        description="",
    )

    if pain_score >= 7 or swelling:
        result.triggered = True
        result.override_risk_level = RiskLevel.RED
        result.max_allowed_intensity = IntensityZone.Z1
        # Block all sports except walk
        result.blocked_sports = [s for s in SportType if s != SportType.WALK]

        if swelling:
            result.description = "Schwellung festgestellt. Ärztliche Abklärung empfohlen. Nur leichte Bewegung (Spaziergang) falls schmerzfrei."
        else:
            result.description = f"Schmerz sehr hoch ({pain_score}/10). Ärztliche Abklärung empfohlen. Nur leichte Bewegung (Spaziergang) falls schmerzfrei."

    return result


def evaluate_r1_moderate_pain_impact(
    pain_score: int,
    planned_sport: SportType,
) -> SafetyRuleResult:
    """
    R1 – Schmerz moderat + Impact-Sport
    Schmerz 5–6/10 → kein Impact-/Kontakt-Sport
    """
    result = SafetyRuleResult(
        rule_id="R1",
        rule_name="Moderate Pain - No Impact Sports",
        description="",
    )

    if 5 <= pain_score <= 6:
        result.triggered = True
        result.blocked_sports = HIGH_IMPACT_SPORTS
        result.max_allowed_intensity = IntensityZone.Z2
        result.description = f"Moderater Schmerz ({pain_score}/10). Kein Impact-Sport empfohlen. Alternativen: Bike Z1-Z2, Schwimmen locker, Mobility."

        # If planned sport is high impact, suggest yellow
        if planned_sport in HIGH_IMPACT_SPORTS:
            result.override_risk_level = RiskLevel.YELLOW

    return result


def evaluate_r2_doms(
    soreness_map: dict[str, int],
    planned_sport: SportType,
    planned_gym_split: Optional[GymSplit],
) -> SafetyRuleResult:
    """
    R2 – Lokaler Muskelkater stark
    DOMS ≥ 7/10 in primärer Muskelgruppe der geplanten Session
    → keine harte Belastung dieser Gruppe
    """
    result = SafetyRuleResult(
        rule_id="R2",
        rule_name="DOMS - Muscle Group Protection",
        description="",
    )

    # Get target muscle groups for planned activity
    if planned_sport == SportType.GYM and planned_gym_split:
        target_muscles = GYM_SPLIT_MUSCLE_MAP.get(planned_gym_split, [])
    else:
        target_muscles = SPORT_MUSCLE_MAP.get(planned_sport, [])

    # Check if any target muscle has high soreness
    high_soreness_muscles = []
    for muscle in target_muscles:
        muscle_key = muscle.value if isinstance(muscle, MuscleRegion) else muscle
        soreness_level = soreness_map.get(muscle_key, 0)
        if soreness_level >= 7:
            high_soreness_muscles.append(muscle)
            result.blocked_muscle_regions.append(muscle)

    if high_soreness_muscles:
        result.triggered = True
        muscle_names = ", ".join([m.value for m in high_soreness_muscles])
        result.description = f"Starker Muskelkater in {muscle_names}. Keine harte Belastung dieser Muskelgruppen empfohlen."
        result.override_risk_level = RiskLevel.YELLOW

    return result


def evaluate_r3_recovery_markers(
    hrv_z: Optional[float],
    rhr_delta: Optional[float],
) -> SafetyRuleResult:
    """
    R3 – Recovery-Marker massiv schlecht
    HRV deutlich reduziert UND Ruhepuls erhöht
    → Intensität runterstufen, max Z2
    """
    result = SafetyRuleResult(
        rule_id="R3",
        rule_name="Poor Recovery Markers",
        description="",
    )

    # Check if both markers indicate poor recovery
    hrv_poor = hrv_z is not None and hrv_z < -1.5  # 1.5 std below baseline
    rhr_elevated = rhr_delta is not None and rhr_delta > 5  # 5 bpm above baseline

    if hrv_poor and rhr_elevated:
        result.triggered = True
        result.max_allowed_intensity = IntensityZone.Z2
        result.description = "HRV deutlich unter Baseline und Ruhepuls erhöht. Keine hochintensive Belastung empfohlen. Max. Zone 2."
        result.override_risk_level = RiskLevel.YELLOW
    elif hrv_poor or rhr_elevated:
        # Single marker warning (less severe)
        if hrv_poor:
            result.triggered = True
            result.max_allowed_intensity = IntensityZone.TEMPO
            result.description = "HRV deutlich unter Baseline. Hochintensive Belastung mit Vorsicht."
        elif rhr_elevated:
            result.triggered = True
            result.max_allowed_intensity = IntensityZone.TEMPO
            result.description = "Ruhepuls erhöht. Hochintensive Belastung mit Vorsicht."

    return result


def evaluate_r4_two_a_day(
    hard_session_today: bool,
    planned_intensity: Optional[IntensityZone],
) -> SafetyRuleResult:
    """
    R4 – Two-a-days Limit
    Bereits harte Einheit am selben Tag + geplante harte Einheit
    → zweite Einheit automatisch "easy" oder sportartwechselnd
    """
    result = SafetyRuleResult(
        rule_id="R4",
        rule_name="Two-a-Day Limit",
        description="",
    )

    # Define what counts as "hard" intensity
    hard_intensities = [IntensityZone.THRESHOLD, IntensityZone.VO2, IntensityZone.MAX]

    if hard_session_today and planned_intensity in hard_intensities:
        result.triggered = True
        result.max_allowed_intensity = IntensityZone.Z2
        result.description = "Bereits eine harte Einheit heute absolviert. Zweite Einheit sollte leicht sein (max. Zone 2) oder eine andere Sportart."
        result.override_risk_level = RiskLevel.YELLOW

    return result


def evaluate_all_safety_rules(
    pain_score: int,
    swelling: bool,
    soreness_map: dict[str, int],
    planned_sport: SportType,
    planned_gym_split: Optional[GymSplit],
    planned_intensity: Optional[IntensityZone],
    hrv_z: Optional[float],
    rhr_delta: Optional[float],
    hard_session_today: bool,
) -> SafetyEvaluation:
    """Evaluate all safety rules and return combined result."""

    results = []

    # R0 - Acute pain/swelling
    r0 = evaluate_r0_acute_pain(pain_score, swelling)
    if r0.triggered:
        results.append(r0)

    # R1 - Moderate pain + impact sport
    r1 = evaluate_r1_moderate_pain_impact(pain_score, planned_sport)
    if r1.triggered:
        results.append(r1)

    # R2 - DOMS
    r2 = evaluate_r2_doms(soreness_map, planned_sport, planned_gym_split)
    if r2.triggered:
        results.append(r2)

    # R3 - Recovery markers
    r3 = evaluate_r3_recovery_markers(hrv_z, rhr_delta)
    if r3.triggered:
        results.append(r3)

    # R4 - Two-a-day
    r4 = evaluate_r4_two_a_day(hard_session_today, planned_intensity)
    if r4.triggered:
        results.append(r4)

    # Combine results
    blocked_sports: list[SportType] = []
    blocked_muscles: list[MuscleRegion] = []
    max_intensity: Optional[IntensityZone] = None
    override_level: Optional[RiskLevel] = None

    for rule in results:
        blocked_sports.extend(rule.blocked_sports)
        blocked_muscles.extend(rule.blocked_muscle_regions)

        # Take the most restrictive intensity
        if rule.max_allowed_intensity:
            if max_intensity is None:
                max_intensity = rule.max_allowed_intensity
            elif _intensity_order(rule.max_allowed_intensity) < _intensity_order(max_intensity):
                max_intensity = rule.max_allowed_intensity

        # Take the highest risk level
        if rule.override_risk_level:
            if override_level is None:
                override_level = rule.override_risk_level
            elif _risk_order(rule.override_risk_level) > _risk_order(override_level):
                override_level = rule.override_risk_level

    return SafetyEvaluation(
        triggered_rules=results,
        max_allowed_intensity=max_intensity,
        blocked_sports=list(set(blocked_sports)),
        blocked_muscle_regions=list(set(blocked_muscles)),
        override_risk_level=override_level,
    )


def _intensity_order(intensity: IntensityZone) -> int:
    """Return order of intensity (lower = easier)."""
    order = {
        IntensityZone.Z1: 1,
        IntensityZone.Z2: 2,
        IntensityZone.TEMPO: 3,
        IntensityZone.THRESHOLD: 4,
        IntensityZone.VO2: 5,
        IntensityZone.MAX: 6,
    }
    return order.get(intensity, 3)


def _risk_order(risk: RiskLevel) -> int:
    """Return order of risk level (higher = worse)."""
    order = {
        RiskLevel.GREEN: 1,
        RiskLevel.YELLOW: 2,
        RiskLevel.RED: 3,
    }
    return order.get(risk, 1)
