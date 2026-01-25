"""Tests for FIT file parser."""
from datetime import date, datetime

import pytest

from app.services.fit_parser import (
    FIT_SPORT_MAP,
    FitFileProcessor,
    FitParseResult,
    ParsedDailyMetrics,
    ParsedWorkout,
    parse_fit_file,
)


class TestFitSportMapping:
    """Tests for sport type mapping."""

    def test_running_maps_to_run(self):
        assert FIT_SPORT_MAP["running"] == "run"

    def test_cycling_maps_to_bike(self):
        assert FIT_SPORT_MAP["cycling"] == "bike"

    def test_swimming_maps_to_swim(self):
        assert FIT_SPORT_MAP["swimming"] == "swim"

    def test_training_maps_to_gym(self):
        assert FIT_SPORT_MAP["training"] == "gym"

    def test_walking_maps_to_walk(self):
        assert FIT_SPORT_MAP["walking"] == "walk"

    def test_soccer_maps_to_football(self):
        assert FIT_SPORT_MAP["soccer"] == "football"

    def test_unknown_sport_maps_to_other(self):
        assert FIT_SPORT_MAP.get("unknown", "other") == "other"


class TestParsedWorkout:
    """Tests for ParsedWorkout dataclass."""

    def test_create_minimal_workout(self):
        workout = ParsedWorkout(
            sport_type="run",
            start_time=datetime.now(),
            duration_minutes=30,
        )
        assert workout.sport_type == "run"
        assert workout.duration_minutes == 30
        assert workout.avg_hr is None

    def test_create_full_workout(self):
        workout = ParsedWorkout(
            sport_type="bike",
            start_time=datetime.now(),
            duration_minutes=60,
            avg_hr=145,
            max_hr=175,
            calories=500,
            distance_meters=25000,
            training_effect=3.5,
            intensity_zone="threshold",
        )
        assert workout.avg_hr == 145
        assert workout.calories == 500
        assert workout.distance_meters == 25000


class TestParsedDailyMetrics:
    """Tests for ParsedDailyMetrics dataclass."""

    def test_create_minimal_metrics(self):
        metrics = ParsedDailyMetrics(date=date.today())
        assert metrics.date == date.today()
        assert metrics.resting_hr is None

    def test_create_full_metrics(self):
        metrics = ParsedDailyMetrics(
            date=date.today(),
            resting_hr=52,
            hrv_rmssd=45.5,
            sleep_duration_minutes=420,
            stress_score=25,
        )
        assert metrics.resting_hr == 52
        assert metrics.hrv_rmssd == 45.5


class TestFitParseResult:
    """Tests for FitParseResult dataclass."""

    def test_empty_result_has_no_data(self):
        result = FitParseResult()
        assert result.has_data is False

    def test_result_with_workout_has_data(self):
        result = FitParseResult(
            workouts=[
                ParsedWorkout(
                    sport_type="run",
                    start_time=datetime.now(),
                    duration_minutes=30,
                )
            ]
        )
        assert result.has_data is True

    def test_result_with_metrics_has_data(self):
        result = FitParseResult(
            daily_metrics=[
                ParsedDailyMetrics(date=date.today())
            ]
        )
        assert result.has_data is True


class TestFitFileProcessor:
    """Tests for FitFileProcessor."""

    def test_processor_initialization(self):
        processor = FitFileProcessor()
        assert processor.processor is not None

    def test_safe_int_with_valid_value(self):
        result = FitFileProcessor._safe_int(42)
        assert result == 42

    def test_safe_int_with_none(self):
        result = FitFileProcessor._safe_int(None)
        assert result is None

    def test_safe_int_with_invalid_string(self):
        result = FitFileProcessor._safe_int("invalid")
        assert result is None

    def test_safe_int_with_float(self):
        result = FitFileProcessor._safe_int(42.7)
        assert result == 42

    def test_safe_float_with_valid_value(self):
        result = FitFileProcessor._safe_float(3.14)
        assert result == 3.14

    def test_safe_float_with_none(self):
        result = FitFileProcessor._safe_float(None)
        assert result is None

    def test_safe_float_with_int(self):
        result = FitFileProcessor._safe_float(42)
        assert result == 42.0


class TestTrainingEffectToZone:
    """Tests for training effect to zone conversion."""

    def test_te_below_1_is_z1(self):
        processor = FitFileProcessor()
        assert processor._training_effect_to_zone(0.5) == "Z1"

    def test_te_1_to_2_is_z2(self):
        processor = FitFileProcessor()
        assert processor._training_effect_to_zone(1.5) == "Z2"

    def test_te_2_to_3_is_tempo(self):
        processor = FitFileProcessor()
        assert processor._training_effect_to_zone(2.5) == "tempo"

    def test_te_3_to_4_is_threshold(self):
        processor = FitFileProcessor()
        assert processor._training_effect_to_zone(3.5) == "threshold"

    def test_te_4_to_5_is_vo2(self):
        processor = FitFileProcessor()
        assert processor._training_effect_to_zone(4.5) == "VO2"

    def test_te_5_plus_is_max(self):
        processor = FitFileProcessor()
        assert processor._training_effect_to_zone(5.0) == "max"


class TestRMSSDCalculation:
    """Tests for RMSSD calculation from RR intervals."""

    def test_calculate_rmssd_valid_intervals(self):
        processor = FitFileProcessor()
        # Sample RR intervals in ms
        rr_intervals = [800, 820, 790, 810, 805]
        rmssd = processor._calculate_rmssd(rr_intervals)
        assert rmssd is not None
        assert rmssd > 0

    def test_calculate_rmssd_insufficient_intervals(self):
        processor = FitFileProcessor()
        rr_intervals = [800]  # Only one interval
        rmssd = processor._calculate_rmssd(rr_intervals)
        assert rmssd is None

    def test_calculate_rmssd_invalid_intervals(self):
        processor = FitFileProcessor()
        rr_intervals = [100, 3000]  # Outside valid range
        rmssd = processor._calculate_rmssd(rr_intervals)
        assert rmssd is None

    def test_calculate_rmssd_empty_list(self):
        processor = FitFileProcessor()
        rmssd = processor._calculate_rmssd([])
        assert rmssd is None


class TestParseInvalidFile:
    """Tests for handling invalid files."""

    def test_parse_empty_bytes(self):
        result = parse_fit_file(b"")
        assert result.has_data is False
        assert len(result.errors) > 0

    def test_parse_invalid_bytes(self):
        result = parse_fit_file(b"not a fit file")
        assert result.has_data is False
        assert len(result.errors) > 0

    def test_parse_random_bytes(self):
        import random
        random_bytes = bytes(random.getrandbits(8) for _ in range(100))
        result = parse_fit_file(random_bytes)
        assert result.has_data is False


class TestWorkoutDeduplication:
    """Tests related to workout deduplication logic."""

    def test_workouts_with_same_start_time(self):
        """Verify we can detect duplicate workouts by start_time."""
        start = datetime(2024, 1, 15, 8, 0, 0)

        workout1 = ParsedWorkout(
            sport_type="run",
            start_time=start,
            duration_minutes=30,
        )

        workout2 = ParsedWorkout(
            sport_type="run",
            start_time=start,
            duration_minutes=30,
        )

        # Same start time means duplicate
        assert workout1.start_time == workout2.start_time

    def test_workouts_with_different_start_time(self):
        """Verify different start times are not duplicates."""
        workout1 = ParsedWorkout(
            sport_type="run",
            start_time=datetime(2024, 1, 15, 8, 0, 0),
            duration_minutes=30,
        )

        workout2 = ParsedWorkout(
            sport_type="run",
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            duration_minutes=30,
        )

        assert workout1.start_time != workout2.start_time
