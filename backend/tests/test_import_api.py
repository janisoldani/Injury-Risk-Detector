"""Tests for Import API endpoints."""
from datetime import date, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models import User, Workout, DailyMetrics
from app.services.fit_parser import FitParseResult, ParsedDailyMetrics, ParsedWorkout


@pytest.mark.asyncio
class TestFitUploadEndpoint:
    """Tests for FIT file upload endpoint."""

    async def test_upload_rejects_non_fit_file(self, client: AsyncClient, test_user: User):
        """Non-.fit files should be rejected."""
        response = await client.post(
            "/api/v1/imports/fit",
            files={"file": ("workout.gpx", b"some content", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Only .fit files" in response.json()["detail"]

    async def test_upload_rejects_empty_file(self, client: AsyncClient, test_user: User):
        """Empty files should be rejected."""
        response = await client.post(
            "/api/v1/imports/fit",
            files={"file": ("workout.fit", b"", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    async def test_upload_handles_invalid_fit_file(self, client: AsyncClient, test_user: User):
        """Invalid FIT files should be handled gracefully."""
        response = await client.post(
            "/api/v1/imports/fit",
            files={"file": ("workout.fit", b"not a valid fit file", "application/octet-stream")},
        )
        # Should return 200 with success=false
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0 or "No data" in data["message"]

    @patch("app.api.v1.imports.FitFileProcessor")
    async def test_upload_processes_valid_workout(
        self, mock_processor_class, client: AsyncClient, test_user: User
    ):
        """Valid FIT file with workout should be processed."""
        # Mock the parser to return a workout
        mock_processor = MagicMock()
        mock_processor.parse_file.return_value = FitParseResult(
            workouts=[
                ParsedWorkout(
                    sport_type="run",
                    start_time=datetime(2024, 1, 15, 8, 0, 0),
                    duration_minutes=30,
                    avg_hr=145,
                    max_hr=165,
                    calories=300,
                )
            ],
            file_type="activity",
            device_info="Garmin Forerunner",
        )
        mock_processor_class.return_value = mock_processor

        response = await client.post(
            "/api/v1/imports/fit",
            files={"file": ("workout.fit", b"fake fit content", "application/octet-stream")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["workouts_created"] == 1
        assert data["file_type"] == "activity"

    @patch("app.api.v1.imports.FitFileProcessor")
    async def test_upload_processes_daily_metrics(
        self, mock_processor_class, client: AsyncClient, test_user: User
    ):
        """Valid FIT file with daily metrics should be processed."""
        mock_processor = MagicMock()
        mock_processor.parse_file.return_value = FitParseResult(
            daily_metrics=[
                ParsedDailyMetrics(
                    date=date(2024, 1, 15),
                    resting_hr=52,
                    hrv_rmssd=45.5,
                )
            ],
            file_type="monitoring",
        )
        mock_processor_class.return_value = mock_processor

        response = await client.post(
            "/api/v1/imports/fit",
            files={"file": ("daily.fit", b"fake fit content", "application/octet-stream")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metrics_created"] == 1

    @patch("app.api.v1.imports.FitFileProcessor")
    async def test_upload_skips_duplicate_workouts(
        self, mock_processor_class, client: AsyncClient, test_user: User, db_session
    ):
        """Duplicate workouts (same start time) should be skipped."""
        workout_time = datetime(2024, 1, 15, 8, 0, 0)

        # Create existing workout
        existing = Workout(
            user_id=test_user.id,
            sport_type="run",
            start_time=workout_time,
            duration_minutes=30,
            source="garmin_fit",
        )
        db_session.add(existing)
        await db_session.commit()

        # Mock parser to return same workout
        mock_processor = MagicMock()
        mock_processor.parse_file.return_value = FitParseResult(
            workouts=[
                ParsedWorkout(
                    sport_type="run",
                    start_time=workout_time,
                    duration_minutes=30,
                )
            ],
            file_type="activity",
        )
        mock_processor_class.return_value = mock_processor

        response = await client.post(
            "/api/v1/imports/fit",
            files={"file": ("workout.fit", b"fake", "application/octet-stream")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workouts_created"] == 0
        assert data["workouts_skipped"] == 1


@pytest.mark.asyncio
class TestImportStatsEndpoint:
    """Tests for import stats endpoint."""

    async def test_empty_stats(self, client: AsyncClient, test_user: User):
        """Stats should be empty for new user."""
        response = await client.get("/api/v1/imports/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_workouts"] == 0
        assert data["total_metrics_days"] == 0
        assert data["earliest_date"] is None

    async def test_stats_with_workouts(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Stats should reflect imported workouts."""
        # Create some workouts
        workout1 = Workout(
            user_id=test_user.id,
            sport_type="run",
            start_time=datetime(2024, 1, 10, 8, 0, 0),
            duration_minutes=30,
        )
        workout2 = Workout(
            user_id=test_user.id,
            sport_type="bike",
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            duration_minutes=60,
        )
        db_session.add_all([workout1, workout2])
        await db_session.commit()

        response = await client.get("/api/v1/imports/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_workouts"] == 2
        assert data["earliest_date"] == "2024-01-10"
        assert data["latest_date"] == "2024-01-15"

    async def test_stats_with_metrics(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Stats should reflect imported daily metrics."""
        metrics = DailyMetrics(
            user_id=test_user.id,
            date=date(2024, 1, 12),
            resting_hr=52,
        )
        db_session.add(metrics)
        await db_session.commit()

        response = await client.get("/api/v1/imports/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_metrics_days"] == 1


class TestImportResultMessage:
    """Tests for import result message building."""

    def test_message_with_workouts_only(self):
        from app.api.v1.imports import _build_success_message, ImportResult

        result = ImportResult(
            success=True,
            message="",
            workouts_created=3,
        )
        message = _build_success_message(result)
        assert "3 workout(s) imported" in message

    def test_message_with_skipped(self):
        from app.api.v1.imports import _build_success_message, ImportResult

        result = ImportResult(
            success=True,
            message="",
            workouts_created=2,
            workouts_skipped=1,
        )
        message = _build_success_message(result)
        assert "2 workout(s) imported" in message
        assert "1 duplicate(s) skipped" in message

    def test_message_with_metrics(self):
        from app.api.v1.imports import _build_success_message, ImportResult

        result = ImportResult(
            success=True,
            message="",
            metrics_created=5,
        )
        message = _build_success_message(result)
        assert "5 day(s) of health data imported" in message

    def test_message_with_all(self):
        from app.api.v1.imports import _build_success_message, ImportResult

        result = ImportResult(
            success=True,
            message="",
            workouts_created=2,
            workouts_skipped=1,
            metrics_created=3,
            metrics_updated=2,
        )
        message = _build_success_message(result)
        assert "2 workout(s) imported" in message
        assert "1 duplicate(s) skipped" in message
        assert "3 day(s) of health data imported" in message
        assert "2 day(s) of health data updated" in message

    def test_message_empty_result(self):
        from app.api.v1.imports import _build_success_message, ImportResult

        result = ImportResult(success=True, message="")
        message = _build_success_message(result)
        assert "no new data" in message.lower()
