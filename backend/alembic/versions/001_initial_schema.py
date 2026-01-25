"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("sport_profile", sa.String(50), nullable=True, server_default="high_training_load"),
        sa.Column("timezone", sa.String(50), nullable=True, server_default="Europe/Zurich"),
        sa.Column("device_sources", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # Daily Metrics table
    op.create_table(
        "daily_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("sleep_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("hrv_rmssd", sa.Float(), nullable=True),
        sa.Column("resting_hr", sa.Integer(), nullable=True),
        sa.Column("body_battery", sa.Integer(), nullable=True),
        sa.Column("stress_score", sa.Integer(), nullable=True),
        sa.Column("training_load_7d", sa.Float(), nullable=True),
        sa.Column("acute_load_7d", sa.Float(), nullable=True),
        sa.Column("chronic_load_28d", sa.Float(), nullable=True),
        sa.Column("acwr", sa.Float(), nullable=True),
        sa.Column("monotony", sa.Float(), nullable=True),
        sa.Column("strain", sa.Float(), nullable=True),
        sa.Column("hrv_baseline_mean", sa.Float(), nullable=True),
        sa.Column("hrv_baseline_std", sa.Float(), nullable=True),
        sa.Column("rhr_baseline_mean", sa.Float(), nullable=True),
        sa.Column("sleep_baseline_mean", sa.Float(), nullable=True),
        sa.Column("missing_fields_mask", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="uq_user_date"),
    )
    op.create_index(op.f("ix_daily_metrics_date"), "daily_metrics", ["date"], unique=False)
    op.create_index(op.f("ix_daily_metrics_id"), "daily_metrics", ["id"], unique=False)
    op.create_index(op.f("ix_daily_metrics_user_id"), "daily_metrics", ["user_id"], unique=False)

    # Workouts table
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sport_type", sa.String(50), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("avg_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("training_effect", sa.Float(), nullable=True),
        sa.Column("intensity_zone", sa.String(20), nullable=True),
        sa.Column("gym_split", sa.String(20), nullable=True),
        sa.Column("trimp", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workouts_id"), "workouts", ["id"], unique=False)
    op.create_index(op.f("ix_workouts_start_time"), "workouts", ["start_time"], unique=False)
    op.create_index(op.f("ix_workouts_user_id"), "workouts", ["user_id"], unique=False)

    # Planned Sessions table
    op.create_table(
        "planned_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sport_type", sa.String(50), nullable=False),
        sa.Column("planned_start_time", sa.DateTime(), nullable=False),
        sa.Column("planned_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("planned_intensity", sa.String(20), nullable=True),
        sa.Column("gym_split", sa.String(20), nullable=True),
        sa.Column("goal", sa.String(50), nullable=True, server_default="endurance"),
        sa.Column("priority", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("is_completed", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("completed_workout_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["completed_workout_id"], ["workouts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_planned_sessions_id"), "planned_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_planned_sessions_planned_start_time"), "planned_sessions", ["planned_start_time"], unique=False)
    op.create_index(op.f("ix_planned_sessions_user_id"), "planned_sessions", ["user_id"], unique=False)

    # Symptoms table
    op.create_table(
        "symptoms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("pain_score", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("pain_location", sa.String(50), nullable=True),
        sa.Column("pain_description", sa.Text(), nullable=True),
        sa.Column("swelling", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("soreness_map", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("readiness", sa.Integer(), nullable=True, server_default="7"),
        sa.Column("fatigue", sa.Integer(), nullable=True, server_default="3"),
        sa.Column("physio_visit", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("diagnosis_tag", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_symptoms_id"), "symptoms", ["id"], unique=False)
    op.create_index(op.f("ix_symptoms_timestamp"), "symptoms", ["timestamp"], unique=False)
    op.create_index(op.f("ix_symptoms_user_id"), "symptoms", ["user_id"], unique=False)

    # Labels table
    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("planned_session_id", sa.Integer(), nullable=True),
        sa.Column("label_date", sa.DateTime(), nullable=False),
        sa.Column("overload_event", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("target_horizon", sa.String(20), nullable=True, server_default="'next_session'"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["planned_session_id"], ["planned_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_labels_id"), "labels", ["id"], unique=False)
    op.create_index(op.f("ix_labels_label_date"), "labels", ["label_date"], unique=False)
    op.create_index(op.f("ix_labels_user_id"), "labels", ["user_id"], unique=False)

    # Predictions table
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("planned_session_id", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("top_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation_text", sa.Text(), nullable=False),
        sa.Column("triggered_safety_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation_a", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendation_b", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("shap_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True, server_default="'heuristic_v1'"),
        sa.Column("feature_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["planned_session_id"], ["planned_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
    op.create_index(op.f("ix_predictions_planned_session_id"), "predictions", ["planned_session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_predictions_planned_session_id"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_id"), table_name="predictions")
    op.drop_table("predictions")

    op.drop_index(op.f("ix_labels_user_id"), table_name="labels")
    op.drop_index(op.f("ix_labels_label_date"), table_name="labels")
    op.drop_index(op.f("ix_labels_id"), table_name="labels")
    op.drop_table("labels")

    op.drop_index(op.f("ix_symptoms_user_id"), table_name="symptoms")
    op.drop_index(op.f("ix_symptoms_timestamp"), table_name="symptoms")
    op.drop_index(op.f("ix_symptoms_id"), table_name="symptoms")
    op.drop_table("symptoms")

    op.drop_index(op.f("ix_planned_sessions_user_id"), table_name="planned_sessions")
    op.drop_index(op.f("ix_planned_sessions_planned_start_time"), table_name="planned_sessions")
    op.drop_index(op.f("ix_planned_sessions_id"), table_name="planned_sessions")
    op.drop_table("planned_sessions")

    op.drop_index(op.f("ix_workouts_user_id"), table_name="workouts")
    op.drop_index(op.f("ix_workouts_start_time"), table_name="workouts")
    op.drop_index(op.f("ix_workouts_id"), table_name="workouts")
    op.drop_table("workouts")

    op.drop_index(op.f("ix_daily_metrics_user_id"), table_name="daily_metrics")
    op.drop_index(op.f("ix_daily_metrics_id"), table_name="daily_metrics")
    op.drop_index(op.f("ix_daily_metrics_date"), table_name="daily_metrics")
    op.drop_table("daily_metrics")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
