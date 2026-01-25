from enum import Enum


class SportType(str, Enum):
    RUN = "run"
    BIKE = "bike"
    SWIM = "swim"
    GYM = "gym"
    FOOTBALL = "football"
    PADEL = "padel"
    WALK = "walk"
    HYROX = "hyrox"
    OTHER = "other"


class IntensityZone(str, Enum):
    Z1 = "Z1"  # Recovery
    Z2 = "Z2"  # Endurance
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    VO2 = "VO2"
    MAX = "max"


class TrainingGoal(str, Enum):
    ENDURANCE = "endurance"
    STRENGTH = "strength"
    RECOVERY = "recovery"
    SPEED = "speed"
    COMPETITION = "competition"


class GymSplit(str, Enum):
    PUSH = "push"
    PULL = "pull"
    LEGS = "legs"
    UPPER = "upper"
    LOWER = "lower"
    FULL_BODY = "full_body"


class PainLocation(str, Enum):
    KNEE_LEFT = "knee_left"
    KNEE_RIGHT = "knee_right"
    ANKLE_LEFT = "ankle_left"
    ANKLE_RIGHT = "ankle_right"
    HIP_LEFT = "hip_left"
    HIP_RIGHT = "hip_right"
    LOWER_BACK = "lower_back"
    UPPER_BACK = "upper_back"
    SHOULDER_LEFT = "shoulder_left"
    SHOULDER_RIGHT = "shoulder_right"
    NECK = "neck"
    CALF_LEFT = "calf_left"
    CALF_RIGHT = "calf_right"
    SHIN_LEFT = "shin_left"
    SHIN_RIGHT = "shin_right"
    FOOT_LEFT = "foot_left"
    FOOT_RIGHT = "foot_right"
    WRIST_LEFT = "wrist_left"
    WRIST_RIGHT = "wrist_right"
    ELBOW_LEFT = "elbow_left"
    ELBOW_RIGHT = "elbow_right"
    OTHER = "other"


class MuscleRegion(str, Enum):
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    CALVES = "calves"
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    CORE = "core"
    FOREARMS = "forearms"


class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class LabelReason(str, Enum):
    PAIN = "pain"
    SORENESS = "soreness"
    FATIGUE = "fatigue"
    INJURY = "injury"
    ILLNESS = "illness"
    NO_TIME = "no_time"
    OTHER = "other"


class SportProfile(str, Enum):
    HIGH_TRAINING_LOAD = "high_training_load"
    MODERATE_TRAINING_LOAD = "moderate_training_load"
    RECREATIONAL = "recreational"


class ImpactLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# Sport to Impact Level Mapping
SPORT_IMPACT_MAP: dict[SportType, ImpactLevel] = {
    SportType.RUN: ImpactLevel.HIGH,
    SportType.BIKE: ImpactLevel.LOW,
    SportType.SWIM: ImpactLevel.LOW,
    SportType.GYM: ImpactLevel.MEDIUM,  # Varies by split
    SportType.FOOTBALL: ImpactLevel.VERY_HIGH,
    SportType.PADEL: ImpactLevel.MEDIUM,
    SportType.WALK: ImpactLevel.VERY_LOW,
    SportType.HYROX: ImpactLevel.VERY_HIGH,
    SportType.OTHER: ImpactLevel.MEDIUM,
}

# Sport to Primary Muscle Groups Mapping
SPORT_MUSCLE_MAP: dict[SportType, list[MuscleRegion]] = {
    SportType.RUN: [MuscleRegion.QUADS, MuscleRegion.HAMSTRINGS, MuscleRegion.CALVES, MuscleRegion.GLUTES],
    SportType.BIKE: [MuscleRegion.QUADS, MuscleRegion.GLUTES],
    SportType.SWIM: [MuscleRegion.BACK, MuscleRegion.SHOULDERS, MuscleRegion.CORE],
    SportType.GYM: [],  # Depends on split
    SportType.FOOTBALL: [MuscleRegion.QUADS, MuscleRegion.HAMSTRINGS, MuscleRegion.CALVES, MuscleRegion.CORE],
    SportType.PADEL: [MuscleRegion.SHOULDERS, MuscleRegion.CORE, MuscleRegion.CALVES],
    SportType.WALK: [],
    SportType.HYROX: [
        MuscleRegion.QUADS, MuscleRegion.HAMSTRINGS, MuscleRegion.GLUTES,
        MuscleRegion.BACK, MuscleRegion.SHOULDERS, MuscleRegion.CORE
    ],
    SportType.OTHER: [],
}

# Gym Split to Muscle Groups Mapping
GYM_SPLIT_MUSCLE_MAP: dict[GymSplit, list[MuscleRegion]] = {
    GymSplit.PUSH: [MuscleRegion.CHEST, MuscleRegion.SHOULDERS, MuscleRegion.TRICEPS],
    GymSplit.PULL: [MuscleRegion.BACK, MuscleRegion.BICEPS, MuscleRegion.FOREARMS],
    GymSplit.LEGS: [MuscleRegion.QUADS, MuscleRegion.HAMSTRINGS, MuscleRegion.GLUTES, MuscleRegion.CALVES],
    GymSplit.UPPER: [MuscleRegion.CHEST, MuscleRegion.BACK, MuscleRegion.SHOULDERS, MuscleRegion.BICEPS, MuscleRegion.TRICEPS],
    GymSplit.LOWER: [MuscleRegion.QUADS, MuscleRegion.HAMSTRINGS, MuscleRegion.GLUTES, MuscleRegion.CALVES],
    GymSplit.FULL_BODY: list(MuscleRegion),
}

# Intensity Zone to Numeric Mapping (for scoring)
INTENSITY_ZONE_NUMERIC: dict[IntensityZone, int] = {
    IntensityZone.Z1: 1,
    IntensityZone.Z2: 2,
    IntensityZone.TEMPO: 3,
    IntensityZone.THRESHOLD: 4,
    IntensityZone.VO2: 5,
    IntensityZone.MAX: 6,
}
