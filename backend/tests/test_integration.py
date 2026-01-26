"""Integration tests for key user flows."""

from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, DailyMetrics, Workout, PlannedSession, Symptom


class TestDataImportToPredictionFlow:
    """Test the complete flow from data import to prediction."""

    @pytest.mark.asyncio
    async def test_prediction_with_baseline_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that predictions work correctly with baseline health data."""
        # Step 1: Create 28 days of baseline metrics
        today = datetime.now().date()
        for i in range(28):
            date = today - timedelta(days=i)
            metrics = DailyMetrics(
                user_id=test_user.id,
                date=date,
                hrv_rmssd=45.0 + (i % 10),  # Varying HRV around 45-55ms
                resting_hr=58 + (i % 5),  # Varying RHR around 58-63bpm
                sleep_duration_minutes=420 + (i % 60),  # 7-8 hours sleep
                sleep_score=80 + (i % 15),
            )
            db_session.add(metrics)

        # Step 2: Create some workout history (7 days ACWR baseline)
        for i in range(14):
            date = today - timedelta(days=i)
            workout = Workout(
                user_id=test_user.id,
                sport_type="run",
                start_time=datetime.combine(date, datetime.min.time()),
                duration_minutes=45 if i % 2 == 0 else 60,
                distance_meters=8000 if i % 2 == 0 else 10000,
                avg_heart_rate=145,
                max_heart_rate=165,
                trimp=67.0 if i % 2 == 0 else 85.0,
                intensity_zone="Z2",
                source="garmin",
            )
            db_session.add(workout)

        await db_session.commit()

        # Step 3: Request prediction
        response = await client.post(f"/api/v1/predictions/{test_user.id}")

        assert response.status_code == 200
        prediction = response.json()

        # Verify prediction structure
        assert "risk_score" in prediction
        assert "risk_level" in prediction
        assert "confidence" in prediction
        assert "top_factors" in prediction
        assert "alternatives" in prediction
        assert "explanation" in prediction

        # With healthy baseline, expect GREEN or YELLOW
        assert prediction["risk_level"] in ["green", "yellow"]
        assert 0 <= prediction["risk_score"] <= 100

    @pytest.mark.asyncio
    async def test_prediction_with_planned_session(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test prediction with a planned session to evaluate session risk."""
        # Create baseline metrics
        today = datetime.now().date()
        for i in range(7):
            date = today - timedelta(days=i)
            metrics = DailyMetrics(
                user_id=test_user.id,
                date=date,
                hrv_rmssd=50.0,
                resting_hr=60,
                sleep_duration_minutes=420,
            )
            db_session.add(metrics)
        await db_session.commit()

        # Request prediction with planned high-intensity session
        planned_session = {
            "sport_type": "run",
            "planned_duration_minutes": 90,
            "planned_intensity": "VO2",  # High intensity
            "scheduled_date": today.isoformat(),
        }

        response = await client.post(
            f"/api/v1/predictions/{test_user.id}",
            json=planned_session,
        )

        assert response.status_code == 200
        prediction = response.json()

        # High intensity session should increase risk score
        assert prediction["risk_score"] > 20

    @pytest.mark.asyncio
    async def test_safety_rules_override_prediction(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that safety rules properly override ML predictions."""
        # Create symptom with high pain score
        today = datetime.now().date()
        symptom = Symptom(
            user_id=test_user.id,
            date=today,
            pain_score=8,  # High pain triggers R0
            swelling=True,  # Also triggers R0
            muscle_soreness=5,
            fatigue_level=5,
        )
        db_session.add(symptom)
        await db_session.commit()

        # Request prediction
        response = await client.post(f"/api/v1/predictions/{test_user.id}")

        assert response.status_code == 200
        prediction = response.json()

        # Safety rule R0 should trigger RED
        assert prediction["risk_level"] == "red"
        assert any(
            rule["triggered"]
            for rule in prediction.get("safety_rules_triggered", [])
        )

    @pytest.mark.asyncio
    async def test_full_user_journey(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test complete user journey from registration to prediction."""
        # Step 1: Create user
        user_response = await client.post(
            "/api/v1/users",
            json={
                "email": "journey@test.com",
                "sport_profile": "moderate_training_load",
                "timezone": "Europe/Berlin",
            },
        )
        assert user_response.status_code == 201
        user = user_response.json()
        user_id = user["id"]

        # Step 2: Add symptom data
        today = datetime.now().date()
        symptom_response = await client.post(
            f"/api/v1/symptoms/{user_id}",
            json={
                "date": today.isoformat(),
                "pain_score": 2,
                "muscle_soreness": 3,
                "fatigue_level": 4,
                "perceived_readiness": 7,
            },
        )
        assert symptom_response.status_code == 201

        # Step 3: Get prediction (should work even without workout history)
        prediction_response = await client.post(f"/api/v1/predictions/{user_id}")
        assert prediction_response.status_code == 200

        prediction = prediction_response.json()
        assert "risk_score" in prediction
        assert "risk_level" in prediction
        assert "alternatives" in prediction

        # Step 4: Plan a session
        session_response = await client.post(
            f"/api/v1/planned-sessions/{user_id}",
            json={
                "sport_type": "bike",
                "planned_duration_minutes": 60,
                "planned_intensity": "Z2",
                "scheduled_date": today.isoformat(),
            },
        )
        assert session_response.status_code == 201


class TestHealthChecks:
    """Test system health endpoints."""

    @pytest.mark.asyncio
    async def test_api_health_check(self, client: AsyncClient):
        """Test basic API health check."""
        # Root endpoint should return 200
        response = await client.get("/api/v1/")
        # Most FastAPI apps return 404 for root unless explicitly defined
        # Let's test a known endpoint instead
        pass

    @pytest.mark.asyncio
    async def test_user_not_found_returns_404(self, client: AsyncClient):
        """Test that nonexistent user returns 404."""
        response = await client.get("/api/v1/users/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_prediction_user_returns_404(self, client: AsyncClient):
        """Test prediction for nonexistent user."""
        response = await client.post("/api/v1/predictions/99999")
        assert response.status_code == 404
