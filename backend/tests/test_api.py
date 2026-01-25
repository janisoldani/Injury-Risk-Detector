"""Tests for API Endpoints."""
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models import User


@pytest.mark.asyncio
class TestUserAPI:
    """Tests for User endpoints."""

    async def test_create_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "newuser@example.com",
                "sport_profile": "high_training_load",
                "timezone": "Europe/Berlin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["sport_profile"] == "high_training_load"

    async def test_create_user_duplicate_email(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/users",
            json={
                "email": test_user.email,
                "sport_profile": "high_training_load",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_get_user(self, client: AsyncClient, test_user: User):
        response = await client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email


@pytest.mark.asyncio
class TestWorkoutAPI:
    """Tests for Workout endpoints."""

    async def test_create_workout(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/workouts",
            json={
                "sport_type": "run",
                "start_time": datetime.utcnow().isoformat(),
                "duration_minutes": 45,
                "avg_hr": 145,
                "max_hr": 165,
                "distance_meters": 8000,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sport_type"] == "run"
        assert data["duration_minutes"] == 45
        assert data["trimp"] is not None  # Should be calculated

    async def test_list_workouts(self, client: AsyncClient, test_user: User):
        # Create a workout first
        await client.post(
            "/api/v1/workouts",
            json={
                "sport_type": "bike",
                "start_time": datetime.utcnow().isoformat(),
                "duration_minutes": 60,
            },
        )

        response = await client.get("/api/v1/workouts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


@pytest.mark.asyncio
class TestSymptomAPI:
    """Tests for Symptom endpoints."""

    async def test_create_symptom(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/symptoms",
            json={
                "pain_score": 3,
                "pain_location": "knee_left",
                "soreness_map": {"quads": 5, "hamstrings": 3},
                "readiness": 7,
                "fatigue": 4,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["pain_score"] == 3
        assert data["soreness_map"]["quads"] == 5

    async def test_get_today_symptom(self, client: AsyncClient, test_user: User):
        # Create a symptom first
        await client.post(
            "/api/v1/symptoms",
            json={"pain_score": 2, "readiness": 8},
        )

        response = await client.get("/api/v1/symptoms/today")
        assert response.status_code == 200
        data = response.json()
        assert data["pain_score"] == 2


@pytest.mark.asyncio
class TestPlannedSessionAPI:
    """Tests for Planned Session endpoints."""

    async def test_create_planned_session(self, client: AsyncClient, test_user: User):
        start_time = datetime.utcnow() + timedelta(hours=2)
        response = await client.post(
            "/api/v1/planned-sessions",
            json={
                "sport_type": "run",
                "planned_start_time": start_time.isoformat(),
                "planned_duration_minutes": 45,
                "planned_intensity": "threshold",
                "goal": "speed",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sport_type"] == "run"
        assert data["planned_intensity"] == "threshold"

    async def test_get_upcoming_session(self, client: AsyncClient, test_user: User):
        # Create a session
        start_time = datetime.utcnow() + timedelta(hours=1)
        await client.post(
            "/api/v1/planned-sessions",
            json={
                "sport_type": "bike",
                "planned_start_time": start_time.isoformat(),
                "planned_duration_minutes": 60,
            },
        )

        response = await client.get("/api/v1/planned-sessions/upcoming")
        assert response.status_code == 200
        data = response.json()
        assert data["sport_type"] == "bike"

    async def test_mark_session_completed(self, client: AsyncClient, test_user: User):
        # Create a session
        start_time = datetime.utcnow() + timedelta(hours=1)
        create_response = await client.post(
            "/api/v1/planned-sessions",
            json={
                "sport_type": "gym",
                "planned_start_time": start_time.isoformat(),
                "planned_duration_minutes": 50,
                "gym_split": "push",
            },
        )
        session_id = create_response.json()["id"]

        # Mark as completed
        response = await client.post(f"/api/v1/planned-sessions/{session_id}/complete")
        assert response.status_code == 200
        assert response.json()["is_completed"] is True


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
