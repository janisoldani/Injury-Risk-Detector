"""
FIT File Parser - Extracts workout and health data from Garmin/Ant+ FIT files.

Supports extraction of:
- Workout sessions (duration, HR, calories, distance)
- Daily health metrics (HRV, RHR, sleep)
- Activity monitoring data
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from io import BytesIO
from typing import Optional, BinaryIO

from fitparse import FitFile
from fitparse.processors import StandardUnitsDataProcessor

logger = logging.getLogger(__name__)


@dataclass
class ParsedWorkout:
    """Extracted workout data from FIT file."""
    sport_type: str
    start_time: datetime
    duration_minutes: int
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    calories: Optional[int] = None
    distance_meters: Optional[float] = None
    training_effect: Optional[float] = None
    intensity_zone: Optional[str] = None
    avg_power: Optional[int] = None
    normalized_power: Optional[int] = None
    avg_cadence: Optional[int] = None
    total_ascent: Optional[float] = None
    external_id: Optional[str] = None


@dataclass
class ParsedDailyMetrics:
    """Extracted daily health metrics from FIT file."""
    date: date
    resting_hr: Optional[int] = None
    hrv_rmssd: Optional[float] = None
    sleep_duration_minutes: Optional[int] = None
    sleep_score: Optional[int] = None
    body_battery: Optional[int] = None
    stress_score: Optional[int] = None
    steps: Optional[int] = None
    active_calories: Optional[int] = None


@dataclass
class FitParseResult:
    """Result of parsing a FIT file."""
    workouts: list[ParsedWorkout] = field(default_factory=list)
    daily_metrics: list[ParsedDailyMetrics] = field(default_factory=list)
    file_type: Optional[str] = None
    device_info: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return len(self.workouts) > 0 or len(self.daily_metrics) > 0


# FIT sport type to our sport type mapping
FIT_SPORT_MAP = {
    "running": "run",
    "cycling": "bike",
    "swimming": "swim",
    "training": "gym",
    "fitness_equipment": "gym",
    "walking": "walk",
    "hiking": "walk",
    "soccer": "football",
    "paddling": "padel",
    "other": "other",
    "generic": "other",
    "all": "other",
}


class FitFileProcessor:
    """Processes FIT files and extracts workout/health data."""

    def __init__(self):
        self.processor = StandardUnitsDataProcessor()

    def parse_file(self, file_content: bytes | BinaryIO) -> FitParseResult:
        """
        Parse a FIT file and extract all relevant data.

        Args:
            file_content: Raw bytes or file-like object of the FIT file

        Returns:
            FitParseResult with extracted workouts and metrics
        """
        result = FitParseResult()

        try:
            if isinstance(file_content, bytes):
                file_obj = BytesIO(file_content)
            else:
                file_obj = file_content

            fitfile = FitFile(file_obj, data_processor=self.processor)

            # Get file type
            result.file_type = self._get_file_type(fitfile)
            result.device_info = self._get_device_info(fitfile)

            logger.info(
                "Parsing FIT file",
                extra={
                    "file_type": result.file_type,
                    "device": result.device_info,
                }
            )

            # Extract data based on file type
            if result.file_type in ["activity", "workout"]:
                workouts = self._extract_activity_data(fitfile)
                result.workouts.extend(workouts)

            if result.file_type in ["monitoring", "monitoring_a", "monitoring_b"]:
                metrics = self._extract_monitoring_data(fitfile)
                result.daily_metrics.extend(metrics)

            # Also try to extract HRV data from activity files
            hrv_data = self._extract_hrv_data(fitfile)
            if hrv_data:
                result.daily_metrics.extend(hrv_data)

            logger.info(
                "FIT file parsed successfully",
                extra={
                    "workouts_found": len(result.workouts),
                    "metrics_found": len(result.daily_metrics),
                }
            )

        except Exception as e:
            error_msg = f"Error parsing FIT file: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)

        return result

    def _get_file_type(self, fitfile: FitFile) -> Optional[str]:
        """Extract file type from FIT file."""
        for record in fitfile.get_messages("file_id"):
            for field in record.fields:
                if field.name == "type":
                    return str(field.value)
        return None

    def _get_device_info(self, fitfile: FitFile) -> Optional[str]:
        """Extract device info from FIT file."""
        for record in fitfile.get_messages("device_info"):
            manufacturer = None
            product = None
            for field in record.fields:
                if field.name == "manufacturer":
                    manufacturer = str(field.value)
                elif field.name == "product_name":
                    product = str(field.value)
            if manufacturer:
                return f"{manufacturer} {product or ''}".strip()
        return None

    def _extract_activity_data(self, fitfile: FitFile) -> list[ParsedWorkout]:
        """Extract workout/activity data from FIT file."""
        workouts = []

        for record in fitfile.get_messages("session"):
            workout = self._parse_session_record(record)
            if workout:
                workouts.append(workout)
                logger.debug(
                    "Extracted workout",
                    extra={
                        "sport": workout.sport_type,
                        "duration": workout.duration_minutes,
                        "avg_hr": workout.avg_hr,
                    }
                )

        return workouts

    def _parse_session_record(self, record) -> Optional[ParsedWorkout]:
        """Parse a session record into a ParsedWorkout."""
        data = {}
        for field in record.fields:
            data[field.name] = field.value

        # Required fields
        start_time = data.get("start_time")
        if not start_time:
            return None

        # Duration in seconds
        total_elapsed_time = data.get("total_elapsed_time", 0)
        if not total_elapsed_time:
            total_timer_time = data.get("total_timer_time", 0)
            total_elapsed_time = total_timer_time

        duration_minutes = int(total_elapsed_time / 60) if total_elapsed_time else 0
        if duration_minutes < 1:
            return None

        # Sport type
        sport = str(data.get("sport", "other")).lower()
        sport_type = FIT_SPORT_MAP.get(sport, "other")

        # Sub-sport for more specific categorization
        sub_sport = str(data.get("sub_sport", "")).lower()
        if "indoor" in sub_sport and sport_type == "bike":
            sport_type = "bike"  # Indoor cycling

        workout = ParsedWorkout(
            sport_type=sport_type,
            start_time=start_time,
            duration_minutes=duration_minutes,
            avg_hr=self._safe_int(data.get("avg_heart_rate")),
            max_hr=self._safe_int(data.get("max_heart_rate")),
            calories=self._safe_int(data.get("total_calories")),
            distance_meters=self._safe_float(data.get("total_distance")),
            training_effect=self._safe_float(data.get("total_training_effect")),
            avg_power=self._safe_int(data.get("avg_power")),
            normalized_power=self._safe_int(data.get("normalized_power")),
            avg_cadence=self._safe_int(data.get("avg_cadence")),
            total_ascent=self._safe_float(data.get("total_ascent")),
        )

        # Determine intensity zone from training effect
        if workout.training_effect:
            workout.intensity_zone = self._training_effect_to_zone(workout.training_effect)

        return workout

    def _extract_monitoring_data(self, fitfile: FitFile) -> list[ParsedDailyMetrics]:
        """Extract daily health metrics from monitoring files."""
        metrics_by_date: dict[date, ParsedDailyMetrics] = {}

        # Process monitoring records
        for record in fitfile.get_messages("monitoring"):
            data = {}
            for field in record.fields:
                data[field.name] = field.value

            timestamp = data.get("timestamp")
            if not timestamp:
                continue

            record_date = timestamp.date()

            if record_date not in metrics_by_date:
                metrics_by_date[record_date] = ParsedDailyMetrics(date=record_date)

            metrics = metrics_by_date[record_date]

            # Resting heart rate
            rhr = data.get("resting_heart_rate")
            if rhr and (metrics.resting_hr is None or rhr < metrics.resting_hr):
                metrics.resting_hr = self._safe_int(rhr)

            # Steps
            steps = data.get("steps")
            if steps:
                current = metrics.steps or 0
                metrics.steps = max(current, self._safe_int(steps) or 0)

            # Active calories
            active_cal = data.get("active_calories")
            if active_cal:
                current = metrics.active_calories or 0
                metrics.active_calories = max(current, self._safe_int(active_cal) or 0)

        # Process stress records
        for record in fitfile.get_messages("stress_level"):
            data = {}
            for field in record.fields:
                data[field.name] = field.value

            timestamp = data.get("stress_level_time")
            if not timestamp:
                continue

            record_date = timestamp.date()
            if record_date not in metrics_by_date:
                metrics_by_date[record_date] = ParsedDailyMetrics(date=record_date)

            stress = data.get("stress_level_value")
            if stress and stress > 0:
                metrics_by_date[record_date].stress_score = self._safe_int(stress)

        return list(metrics_by_date.values())

    def _extract_hrv_data(self, fitfile: FitFile) -> list[ParsedDailyMetrics]:
        """Extract HRV data from activity or HRV-specific files."""
        hrv_values: dict[date, list[float]] = {}

        # Try different HRV message types
        for msg_type in ["hrv", "hrv_summary", "hrv_status"]:
            for record in fitfile.get_messages(msg_type):
                data = {}
                for field in record.fields:
                    data[field.name] = field.value

                # Get timestamp
                timestamp = data.get("timestamp") or data.get("time")
                if not timestamp:
                    continue

                record_date = timestamp.date() if hasattr(timestamp, 'date') else date.today()

                # Get HRV value (RMSSD)
                rmssd = (
                    data.get("weekly_average") or
                    data.get("rmssd") or
                    data.get("hrv")
                )

                if rmssd:
                    if record_date not in hrv_values:
                        hrv_values[record_date] = []
                    hrv_values[record_date].append(float(rmssd))

        # Also try beat-to-beat intervals
        for record in fitfile.get_messages("hrv"):
            data = {}
            for field in record.fields:
                if field.name == "time" and field.value:
                    # RR intervals - calculate RMSSD
                    rr_intervals = field.value if isinstance(field.value, (list, tuple)) else [field.value]
                    rmssd = self._calculate_rmssd(rr_intervals)
                    if rmssd:
                        record_date = date.today()  # HRV messages often don't have timestamp
                        if record_date not in hrv_values:
                            hrv_values[record_date] = []
                        hrv_values[record_date].append(rmssd)

        # Create metrics from HRV data
        result = []
        for record_date, values in hrv_values.items():
            if values:
                avg_rmssd = sum(values) / len(values)
                result.append(ParsedDailyMetrics(
                    date=record_date,
                    hrv_rmssd=round(avg_rmssd, 2),
                ))

        return result

    def _calculate_rmssd(self, rr_intervals: list) -> Optional[float]:
        """Calculate RMSSD from RR intervals."""
        try:
            # Filter valid intervals (typically 300-2000ms)
            valid = [rr for rr in rr_intervals if rr and 300 < rr < 2000]
            if len(valid) < 2:
                return None

            # Calculate successive differences
            diffs = [valid[i+1] - valid[i] for i in range(len(valid)-1)]

            # Calculate RMSSD
            squared_diffs = [d**2 for d in diffs]
            mean_squared = sum(squared_diffs) / len(squared_diffs)
            rmssd = mean_squared ** 0.5

            return round(rmssd, 2)
        except Exception:
            return None

    def _training_effect_to_zone(self, te: float) -> str:
        """Convert Garmin Training Effect to intensity zone."""
        if te < 1.0:
            return "Z1"
        elif te < 2.0:
            return "Z2"
        elif te < 3.0:
            return "tempo"
        elif te < 4.0:
            return "threshold"
        elif te < 5.0:
            return "VO2"
        else:
            return "max"

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


def parse_fit_file(file_content: bytes | BinaryIO) -> FitParseResult:
    """Convenience function to parse a FIT file."""
    processor = FitFileProcessor()
    return processor.parse_file(file_content)
