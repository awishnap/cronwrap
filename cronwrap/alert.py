"""Alert thresholds and alerting logic for cron job monitoring."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AlertConfig:
    """Configuration for job alerting thresholds."""
    failure_threshold: int = 1
    duration_threshold_seconds: Optional[float] = None
    consecutive_failures: int = 1
    recipients: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.consecutive_failures < 1:
            raise ValueError("consecutive_failures must be >= 1")
        if self.duration_threshold_seconds is not None and self.duration_threshold_seconds <= 0:
            raise ValueError("duration_threshold_seconds must be positive")


class AlertManager:
    """Evaluates execution results against thresholds and fires alerts."""

    def __init__(self, config: AlertConfig):
        self._config = config
        self._consecutive_failure_count: int = 0

    def evaluate(self, exit_code: int, duration_seconds: float, job_name: str) -> List[str]:
        """Return a list of alert messages triggered by this result."""
        alerts: List[str] = []

        if exit_code != 0:
            self._consecutive_failure_count += 1
        else:
            self._consecutive_failure_count = 0

        if (
            exit_code != 0
            and self._consecutive_failure_count >= self._config.consecutive_failures
        ):
            alerts.append(
                f"[ALERT] Job '{job_name}' failed with exit code {exit_code} "
                f"({self._consecutive_failure_count} consecutive failure(s))."
            )

        if (
            self._config.duration_threshold_seconds is not None
            and duration_seconds > self._config.duration_threshold_seconds
        ):
            alerts.append(
                f"[ALERT] Job '{job_name}' exceeded duration threshold: "
                f"{duration_seconds:.2f}s > {self._config.duration_threshold_seconds:.2f}s."
            )

        return alerts

    def reset(self) -> None:
        """Reset consecutive failure counter."""
        self._consecutive_failure_count = 0

    @property
    def consecutive_failure_count(self) -> int:
        return self._consecutive_failure_count
