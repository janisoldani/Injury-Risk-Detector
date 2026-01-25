"""
Baseline calculation for user normalization.

Calculates rolling baselines (28 days) for HRV, RHR, and Sleep.
"""
from datetime import date, timedelta
from statistics import mean, stdev
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyMetrics


class BaselineCalculator:
    """Calculates and updates user baselines."""

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.window_days = 28

    async def calculate_baselines(self, target_date: date = None) -> dict:
        """Calculate all baselines for the target date."""
        if target_date is None:
            target_date = date.today()

        start_date = target_date - timedelta(days=self.window_days)

        # Get metrics for the baseline window
        result = await self.db.execute(
            select(DailyMetrics)
            .where(
                DailyMetrics.user_id == self.user_id,
                DailyMetrics.date >= start_date,
                DailyMetrics.date < target_date,  # Exclude target date
            )
            .order_by(DailyMetrics.date.desc())
        )
        metrics = result.scalars().all()

        return {
            "hrv_baseline_mean": self._calculate_mean([m.hrv_rmssd for m in metrics]),
            "hrv_baseline_std": self._calculate_std([m.hrv_rmssd for m in metrics]),
            "rhr_baseline_mean": self._calculate_mean([m.resting_hr for m in metrics]),
            "sleep_baseline_mean": self._calculate_mean([m.sleep_duration_minutes for m in metrics]),
        }

    async def update_daily_metrics_baselines(self, target_date: date = None) -> None:
        """Update the baselines in daily_metrics for a specific date."""
        if target_date is None:
            target_date = date.today()

        baselines = await self.calculate_baselines(target_date)

        # Get or create daily metrics for target date
        result = await self.db.execute(
            select(DailyMetrics).where(
                DailyMetrics.user_id == self.user_id,
                DailyMetrics.date == target_date,
            )
        )
        metrics = result.scalar_one_or_none()

        if metrics:
            metrics.hrv_baseline_mean = baselines["hrv_baseline_mean"]
            metrics.hrv_baseline_std = baselines["hrv_baseline_std"]
            metrics.rhr_baseline_mean = baselines["rhr_baseline_mean"]
            metrics.sleep_baseline_mean = baselines["sleep_baseline_mean"]
            await self.db.commit()

    def _calculate_mean(self, values: list) -> Optional[float]:
        """Calculate mean of non-None values."""
        filtered = [v for v in values if v is not None]
        if len(filtered) < 3:  # Minimum data points required
            return None
        return round(mean(filtered), 2)

    def _calculate_std(self, values: list) -> Optional[float]:
        """Calculate standard deviation of non-None values."""
        filtered = [v for v in values if v is not None]
        if len(filtered) < 3:
            return None
        try:
            return round(stdev(filtered), 2)
        except Exception:
            return None
