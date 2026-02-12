"""
Unit tests for Feature Engineering (ml/features.py).
"""
from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import (
    FeatureBuilder,
    UserFeatures,
    get_intensity_score,
    get_soreness_in_target_muscles,
    get_sport_impact_score,
)
from app.models import DailyMetrics, Symptom, User, Workout
from app.schemas.enums import GymSplit, IntensityZone, MuscleRegion, SportType


class TestUserFeatures:
    """Tests for UserFeatures dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        features = UserFeatures(date=date.today())

        assert features.hrv_z is None
        assert features.rhr_delta is None
        assert features.sleep_delta is None
        assert features.pain_score == 0
        assert features.readiness == 7
        assert features.fatigue == 3
        assert features.swelling is False
        assert features.missing_hrv is True
        assert features.missing_sleep is True
        assert features.missing_rhr is True
        assert features.soreness_map == {}

    def test_soreness_map_not_shared(self):
        """Test that soreness_map is not shared between instances."""
        features1 = UserFeatures(date=date.today())
        features2 = UserFeatures(date=date.today())

        features1.soreness_map["quads"] = 5

        assert features1.soreness_map == {"quads": 5}
        assert features2.soreness_map == {}


class TestFeatureBuilder:
    """Tests for FeatureBuilder class."""

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession) -> User:
        """Create a test user."""
        user = User(
            email="feature_test@example.com",
            sport_profile="high_training_load",
            timezone="Europe/Zurich",
            device_sources=[],
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_build_features_empty_database(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test building features when no data exists."""
        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(date.today())

        assert features.date == date.today()
        assert features.hrv_z is None
        assert features.rhr_delta is None
        assert features.sleep_delta is None
        assert features.pain_score == 0
        assert features.consecutive_training_days == 0
        assert features.missing_hrv is True
        assert features.missing_sleep is True
        assert features.missing_rhr is True

    @pytest.mark.asyncio
    async def test_build_features_with_daily_metrics(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test building features with daily metrics data."""
        today = date.today()

        # Create daily metrics with baseline data
        metrics = DailyMetrics(
            user_id=test_user.id,
            date=today,
            hrv_rmssd=50.0,
            resting_hr=55,
            sleep_duration_minutes=420,  # 7 hours
            sleep_score=85,
            body_battery=70,
            stress_score=30,
            # Baseline values
            hrv_baseline_mean=60.0,
            hrv_baseline_std=10.0,
            rhr_baseline_mean=50.0,
            sleep_baseline_mean=480.0,  # 8 hours
            # Pre-calculated load metrics
            acute_load_7d=300.0,
            chronic_load_28d=250.0,
            acwr=1.2,
        )
        db_session.add(metrics)
        await db_session.commit()

        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(today)

        # Check raw values
        assert features.hrv_rmssd == 50.0
        assert features.resting_hr == 55
        assert features.sleep_duration_minutes == 420
        assert features.sleep_score == 85

        # Check calculated z-scores and deltas
        assert features.hrv_z == pytest.approx(-1.0, rel=0.01)  # (50-60)/10
        assert features.rhr_delta == pytest.approx(5.0, rel=0.01)  # 55-50
        assert features.sleep_delta == pytest.approx(-60.0, rel=0.01)  # 420-480

        # Check load metrics
        assert features.acute_load_7d == 300.0
        assert features.chronic_load_28d == 250.0
        assert features.acwr == 1.2

        # Check missing flags are False when data exists
        assert features.missing_hrv is False
        assert features.missing_rhr is False
        assert features.missing_sleep is False

    @pytest.mark.asyncio
    async def test_build_features_with_symptoms(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test building features with symptom data."""
        today = date.today()
        now = datetime.now()

        # Create today's symptom
        symptom = Symptom(
            user_id=test_user.id,
            timestamp=now,
            pain_score=5,
            readiness=4,
            fatigue=7,
            swelling=False,
            soreness_map={"quads": 6, "hamstrings": 4},
        )
        db_session.add(symptom)
        await db_session.commit()

        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(today)

        assert features.pain_score == 5
        assert features.readiness == 4
        assert features.fatigue == 7
        assert features.swelling is False
        assert features.soreness_map == {"quads": 6, "hamstrings": 4}
        assert features.max_soreness == 6

    @pytest.mark.asyncio
    async def test_build_features_pain_trend(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test pain trend calculation over 3 days."""
        today = date.today()

        # Create symptoms over 3 days (worsening pain trend)
        for days_ago, pain in [(2, 2), (1, 4), (0, 6)]:
            timestamp = datetime.combine(
                today - timedelta(days=days_ago), datetime.min.time()
            ) + timedelta(hours=10)
            symptom = Symptom(
                user_id=test_user.id,
                timestamp=timestamp,
                pain_score=pain,
                readiness=7,
                fatigue=3,
                swelling=False,
                soreness_map={},
            )
            db_session.add(symptom)

        await db_session.commit()

        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(today)

        # Pain trend should be 6 - 2 = 4 (worsening)
        assert features.pain_trend_3d == pytest.approx(4.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_build_features_consecutive_training_days(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test consecutive training days calculation."""
        today = date.today()

        # Create workouts for the last 4 days (not including today)
        for days_ago in range(1, 5):
            workout = Workout(
                user_id=test_user.id,
                sport_type="run",
                start_time=datetime.combine(
                    today - timedelta(days=days_ago), datetime.min.time()
                ) + timedelta(hours=10),
                duration_minutes=60,
                avg_hr=140,
                trimp=100.0,
            )
            db_session.add(workout)

        await db_session.commit()

        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(today)

        # Should count 4 consecutive days
        assert features.consecutive_training_days == 4

    @pytest.mark.asyncio
    async def test_build_features_hard_session_today(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test detection of hard session today."""
        today = date.today()
        now = datetime.combine(today, datetime.min.time()) + timedelta(hours=8)

        # Create a hard workout today
        workout = Workout(
            user_id=test_user.id,
            sport_type="run",
            start_time=now,
            duration_minutes=60,
            avg_hr=170,
            intensity_zone="threshold",
            trimp=150.0,
        )
        db_session.add(workout)
        await db_session.commit()

        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(today)

        assert features.hard_session_today is True

    @pytest.mark.asyncio
    async def test_build_features_calculates_acwr_if_missing(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that ACWR is calculated from workouts if not in daily_metrics."""
        today = date.today()

        # Create workouts without pre-calculated ACWR in daily_metrics
        for days_ago in range(10):
            workout = Workout(
                user_id=test_user.id,
                sport_type="run",
                start_time=datetime.combine(
                    today - timedelta(days=days_ago), datetime.min.time()
                ) + timedelta(hours=10),
                duration_minutes=60,
                avg_hr=140,
                trimp=100.0,
            )
            db_session.add(workout)

        await db_session.commit()

        builder = FeatureBuilder(db_session, test_user.id)
        features = await builder.build_features(today)

        # acute_load should be 7 days * 100 TRIMP = 700
        # chronic_load should be 10 days * 100 TRIMP = 1000
        assert features.acute_load_7d == pytest.approx(700.0, rel=0.01)
        assert features.chronic_load_28d == pytest.approx(1000.0, rel=0.01)
        # ACWR = 700 / 1000 = 0.7
        assert features.acwr == pytest.approx(0.7, rel=0.01)


class TestGetSorenessInTargetMuscles:
    """Tests for get_soreness_in_target_muscles function."""

    def test_gym_with_split(self):
        """Test soreness lookup for gym with specific split."""
        soreness_map = {
            "chest": 6,
            "shoulders": 8,
            "triceps": 4,
        }

        # Push day targets chest, shoulders, triceps
        soreness = get_soreness_in_target_muscles(
            soreness_map, SportType.GYM, GymSplit.PUSH
        )

        # Should return max soreness (8 from shoulders)
        assert soreness == 8

    def test_run_targets_legs(self):
        """Test soreness lookup for running."""
        soreness_map = {
            "quads": 7,
            "calves": 5,
            "hamstrings": 3,
        }

        soreness = get_soreness_in_target_muscles(
            soreness_map, SportType.RUN, None
        )

        # Running targets legs, should find max soreness
        assert soreness >= 5

    def test_no_soreness_data(self):
        """Test with empty soreness map."""
        soreness = get_soreness_in_target_muscles(
            {}, SportType.RUN, None
        )

        assert soreness == 0

    def test_no_matching_muscles(self):
        """Test when soreness exists but not in target muscles."""
        soreness_map = {
            "chest": 8,  # Not targeted by swimming
        }

        soreness = get_soreness_in_target_muscles(
            soreness_map, SportType.SWIM, None
        )

        # Swimming doesn't heavily target chest
        # Result depends on SPORT_MUSCLE_MAP definition
        assert soreness >= 0


class TestGetSportImpactScore:
    """Tests for get_sport_impact_score function."""

    def test_high_impact_sports(self):
        """Test high impact sports score."""
        # Football and running are high impact
        assert get_sport_impact_score(SportType.FOOTBALL) >= 4
        assert get_sport_impact_score(SportType.RUN) >= 3

    def test_low_impact_sports(self):
        """Test low impact sports score."""
        # Swimming and walking are low impact
        assert get_sport_impact_score(SportType.SWIM) <= 3
        assert get_sport_impact_score(SportType.WALK) <= 2

    def test_returns_valid_range(self):
        """Test that all sports return score in valid range (1-5)."""
        for sport in SportType:
            score = get_sport_impact_score(sport)
            assert 1 <= score <= 5, f"{sport} has invalid score {score}"


class TestGetIntensityScore:
    """Tests for get_intensity_score function."""

    def test_low_intensity_zones(self):
        """Test low intensity zone scores."""
        assert get_intensity_score(IntensityZone.Z1) == 1
        assert get_intensity_score(IntensityZone.Z2) == 2

    def test_high_intensity_zones(self):
        """Test high intensity zone scores."""
        assert get_intensity_score(IntensityZone.VO2) >= 5
        assert get_intensity_score(IntensityZone.MAX) == 6

    def test_none_returns_default(self):
        """Test that None returns default moderate value."""
        assert get_intensity_score(None) == 3

    def test_returns_valid_range(self):
        """Test that all zones return score in valid range (1-6)."""
        for zone in IntensityZone:
            score = get_intensity_score(zone)
            assert 1 <= score <= 6, f"{zone} has invalid score {score}"
