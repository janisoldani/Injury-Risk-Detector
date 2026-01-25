"""
Recommendation Engine - Generates alternative training suggestions.

Based on risk level and safety rules, provides two recommendations:
- Recommendation A: Close to original plan (modified if needed)
- Recommendation B: Alternative activity
"""
from dataclasses import dataclass
from typing import Optional

from app.schemas.enums import (
    GYM_SPLIT_MUSCLE_MAP,
    SPORT_MUSCLE_MAP,
    GymSplit,
    IntensityZone,
    MuscleRegion,
    RiskLevel,
    SportType,
)
from app.services.safety_rules import SafetyEvaluation


@dataclass
class Recommendation:
    sport_type: SportType
    duration_minutes: int
    intensity: Optional[IntensityZone] = None
    gym_split: Optional[GymSplit] = None
    intensity_level: Optional[str] = None  # light, moderate, hard
    reason: str = ""
    is_original_plan_modified: bool = False


class RecommendationEngine:
    """Generates training recommendations based on risk and safety evaluation."""

    def __init__(
        self,
        risk_level: RiskLevel,
        safety_eval: SafetyEvaluation,
        blocked_muscle_regions: list[MuscleRegion] = None,
    ):
        self.risk_level = risk_level
        self.safety_eval = safety_eval
        self.blocked_muscles = blocked_muscle_regions or []

    def generate_recommendations(
        self,
        planned_sport: SportType,
        planned_duration: int,
        planned_intensity: Optional[IntensityZone],
        planned_gym_split: Optional[GymSplit],
    ) -> tuple[Recommendation, Recommendation]:
        """Generate two recommendations based on current state."""

        if self.risk_level == RiskLevel.GREEN:
            return self._green_recommendations(
                planned_sport, planned_duration, planned_intensity, planned_gym_split
            )
        elif self.risk_level == RiskLevel.YELLOW:
            return self._yellow_recommendations(
                planned_sport, planned_duration, planned_intensity, planned_gym_split
            )
        else:  # RED
            return self._red_recommendations(planned_duration)

    def _green_recommendations(
        self,
        planned_sport: SportType,
        planned_duration: int,
        planned_intensity: Optional[IntensityZone],
        planned_gym_split: Optional[GymSplit],
    ) -> tuple[Recommendation, Recommendation]:
        """Green: Plan OK + provide alternative option."""

        # Check if planned sport is blocked
        if planned_sport in self.safety_eval.blocked_sports:
            return self._yellow_recommendations(
                planned_sport, planned_duration, planned_intensity, planned_gym_split
            )

        # Recommendation A: Original plan
        rec_a = Recommendation(
            sport_type=planned_sport,
            duration_minutes=planned_duration,
            intensity=planned_intensity,
            gym_split=planned_gym_split,
            reason="Training wie geplant möglich. Gute Erholung und niedrige Belastungsindikatoren.",
        )

        # Recommendation B: Alternative (different sport, same intensity)
        alt_sport = self._get_alternative_sport(planned_sport)
        rec_b = Recommendation(
            sport_type=alt_sport,
            duration_minutes=planned_duration,
            intensity=planned_intensity if alt_sport != SportType.GYM else None,
            gym_split=self._get_alternative_gym_split(planned_gym_split) if alt_sport == SportType.GYM else None,
            reason=f"Alternative: {alt_sport.value.title()} als Abwechslung.",
        )

        return rec_a, rec_b

    def _yellow_recommendations(
        self,
        planned_sport: SportType,
        planned_duration: int,
        planned_intensity: Optional[IntensityZone],
        planned_gym_split: Optional[GymSplit],
    ) -> tuple[Recommendation, Recommendation]:
        """Yellow: Modify plan + provide low-impact alternative."""

        # Recommendation A: Modified version of original plan
        modified_duration = int(planned_duration * 0.8)  # -20%
        modified_intensity = self._reduce_intensity(planned_intensity)

        # Check if sport is blocked
        if planned_sport in self.safety_eval.blocked_sports:
            alt_sport = self._get_low_impact_sport()
            rec_a = Recommendation(
                sport_type=alt_sport,
                duration_minutes=modified_duration,
                intensity=modified_intensity,
                reason=f"Originalplan angepasst: {alt_sport.value.title()} statt {planned_sport.value.title()} aufgrund erhöhter Belastungsindikatoren.",
                is_original_plan_modified=True,
            )
        else:
            # Check gym split for blocked muscles
            final_gym_split = planned_gym_split
            if planned_sport == SportType.GYM and planned_gym_split:
                if self._gym_split_uses_blocked_muscles(planned_gym_split):
                    final_gym_split = self._get_safe_gym_split()

            rec_a = Recommendation(
                sport_type=planned_sport,
                duration_minutes=modified_duration,
                intensity=modified_intensity,
                gym_split=final_gym_split,
                reason="Originalplan angepasst: Reduzierte Dauer und Intensität aufgrund erhöhter Belastungsindikatoren.",
                is_original_plan_modified=True,
            )

        # Recommendation B: Low-impact alternative
        low_impact = self._get_low_impact_sport()
        rec_b = Recommendation(
            sport_type=low_impact,
            duration_minutes=45,
            intensity=IntensityZone.Z2 if low_impact != SportType.GYM else None,
            gym_split=self._get_safe_gym_split() if low_impact == SportType.GYM else None,
            intensity_level="light" if low_impact == SportType.GYM else None,
            reason=f"Schonende Alternative: {low_impact.value.title()} mit niedriger Intensität.",
        )

        return rec_a, rec_b

    def _red_recommendations(
        self,
        planned_duration: int,
    ) -> tuple[Recommendation, Recommendation]:
        """Red: Recovery recommendations only."""

        # Recommendation A: Rest/Walk
        rec_a = Recommendation(
            sport_type=SportType.WALK,
            duration_minutes=30,
            intensity=IntensityZone.Z1,
            reason="Erholung empfohlen. Leichter Spaziergang falls schmerzfrei möglich.",
        )

        # Recommendation B: Mobility/Swim easy
        rec_b = Recommendation(
            sport_type=SportType.SWIM,
            duration_minutes=20,
            intensity=IntensityZone.Z1,
            reason="Alternative: Lockeres Schwimmen oder Mobility-Übungen zur aktiven Erholung.",
        )

        return rec_a, rec_b

    def _reduce_intensity(self, intensity: Optional[IntensityZone]) -> Optional[IntensityZone]:
        """Reduce intensity by one level."""
        if intensity is None:
            return IntensityZone.Z2

        reductions = {
            IntensityZone.MAX: IntensityZone.VO2,
            IntensityZone.VO2: IntensityZone.THRESHOLD,
            IntensityZone.THRESHOLD: IntensityZone.TEMPO,
            IntensityZone.TEMPO: IntensityZone.Z2,
            IntensityZone.Z2: IntensityZone.Z1,
            IntensityZone.Z1: IntensityZone.Z1,
        }
        return reductions.get(intensity, IntensityZone.Z2)

    def _get_alternative_sport(self, current: SportType) -> SportType:
        """Get an alternative sport (different from current)."""
        alternatives = {
            SportType.RUN: SportType.BIKE,
            SportType.BIKE: SportType.SWIM,
            SportType.SWIM: SportType.BIKE,
            SportType.GYM: SportType.BIKE,
            SportType.FOOTBALL: SportType.BIKE,
            SportType.PADEL: SportType.SWIM,
            SportType.HYROX: SportType.BIKE,
            SportType.WALK: SportType.SWIM,
        }
        alt = alternatives.get(current, SportType.BIKE)

        # Make sure alternative is not blocked
        if alt in self.safety_eval.blocked_sports:
            for sport in [SportType.BIKE, SportType.SWIM, SportType.WALK]:
                if sport not in self.safety_eval.blocked_sports:
                    return sport

        return alt

    def _get_low_impact_sport(self) -> SportType:
        """Get a low-impact sport that's not blocked."""
        low_impact = [SportType.BIKE, SportType.SWIM, SportType.WALK, SportType.GYM]

        for sport in low_impact:
            if sport not in self.safety_eval.blocked_sports:
                return sport

        return SportType.WALK  # Always available

    def _get_alternative_gym_split(self, current: Optional[GymSplit]) -> Optional[GymSplit]:
        """Get alternative gym split."""
        if current is None:
            return GymSplit.UPPER

        alternatives = {
            GymSplit.PUSH: GymSplit.PULL,
            GymSplit.PULL: GymSplit.PUSH,
            GymSplit.LEGS: GymSplit.UPPER,
            GymSplit.UPPER: GymSplit.LOWER,
            GymSplit.LOWER: GymSplit.UPPER,
            GymSplit.FULL_BODY: GymSplit.UPPER,
        }
        return alternatives.get(current, GymSplit.UPPER)

    def _get_safe_gym_split(self) -> GymSplit:
        """Get a gym split that doesn't use blocked muscles."""
        for split in [GymSplit.PUSH, GymSplit.PULL, GymSplit.UPPER, GymSplit.LEGS]:
            if not self._gym_split_uses_blocked_muscles(split):
                return split
        return GymSplit.UPPER  # Default

    def _gym_split_uses_blocked_muscles(self, split: GymSplit) -> bool:
        """Check if gym split uses any blocked muscle regions."""
        split_muscles = GYM_SPLIT_MUSCLE_MAP.get(split, [])
        for muscle in split_muscles:
            if muscle in self.blocked_muscles:
                return True
        return False
