"""Health check support for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


class HealthCheckError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class HealthConfig:
    """Configuration for job health checks."""
    enabled: bool = False
    max_allowed_duration: Optional[float] = None  # seconds
    max_failure_streak: int = 3
    ping_url: Optional[str] = None

    def __post_init__(self) -> None:
        if self.max_allowed_duration is not None and self.max_allowed_duration <= 0:
            raise ValueError("max_allowed_duration must be positive")
        if self.max_failure_streak < 1:
            raise ValueError("max_failure_streak must be >= 1")


@dataclass
class HealthStatus:
    """Snapshot of a job's current health."""
    job_name: str
    is_healthy: bool
    failure_streak: int
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    details: str = ""

    @property
    def stale(self) -> bool:
        """True when the job has never succeeded."""
        return self.last_success is None


class HealthMonitor:
    """Tracks and evaluates health state for a single job."""

    def __init__(self, job_name: str, config: HealthConfig) -> None:
        self.job_name = job_name
        self.config = config
        self._failure_streak: int = 0
        self._last_run: Optional[datetime] = None
        self._last_success: Optional[datetime] = None

    def record(self, exit_code: int, duration: float) -> HealthStatus:
        """Update state based on the latest run and return the current status."""
        self._last_run = datetime.utcnow()
        details = ""

        if exit_code == 0:
            self._failure_streak = 0
            self._last_success = self._last_run
        else:
            self._failure_streak += 1

        is_healthy = self._evaluate(duration)
        if not is_healthy:
            details = self._build_details(exit_code, duration)

        return HealthStatus(
            job_name=self.job_name,
            is_healthy=is_healthy,
            failure_streak=self._failure_streak,
            last_run=self._last_run,
            last_success=self._last_success,
            details=details,
        )

    def _evaluate(self, duration: float) -> bool:
        if self._failure_streak >= self.config.max_failure_streak:
            return False
        if (
            self.config.max_allowed_duration is not None
            and duration > self.config.max_allowed_duration
        ):
            return False
        return True

    def _build_details(self, exit_code: int, duration: float) -> str:
        parts = []
        if self._failure_streak >= self.config.max_failure_streak:
            parts.append(
                f"failure streak {self._failure_streak} >= {self.config.max_failure_streak}"
            )
        if (
            self.config.max_allowed_duration is not None
            and duration > self.config.max_allowed_duration
        ):
            parts.append(
                f"duration {duration:.2f}s > {self.config.max_allowed_duration}s"
            )
        return "; ".join(parts)
