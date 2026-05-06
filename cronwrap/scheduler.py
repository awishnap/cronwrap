"""Cron expression parsing and schedule validation for cronwrap."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:
    from croniter import croniter
except ImportError:
    croniter = None  # type: ignore


@dataclass
class ScheduleConfig:
    """Configuration for a cron schedule."""

    expression: str
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        if not self.expression or not self.expression.strip():
            raise ValueError("Cron expression must not be empty.")
        if not self.is_valid_expression(self.expression):
            raise ValueError(f"Invalid cron expression: '{self.expression}'")

    @staticmethod
    def is_valid_expression(expression: str) -> bool:
        """Return True if the expression is a valid cron string."""
        if croniter is None:
            # Fallback: basic field count check (5 or 6 fields)
            parts = expression.strip().split()
            return len(parts) in (5, 6)
        return croniter.is_valid(expression)


class JobScheduler:
    """Utility for working with cron schedules."""

    def __init__(self, config: ScheduleConfig) -> None:
        self.config = config

    def next_run(self, after: Optional[datetime] = None) -> Optional[datetime]:
        """Return the next scheduled datetime after *after* (defaults to now)."""
        if croniter is None:
            return None
        base = after or datetime.utcnow()
        itr = croniter(self.config.expression, base)
        return itr.get_next(datetime)

    def prev_run(self, before: Optional[datetime] = None) -> Optional[datetime]:
        """Return the most recent scheduled datetime before *before* (defaults to now)."""
        if croniter is None:
            return None
        base = before or datetime.utcnow()
        itr = croniter(self.config.expression, base)
        return itr.get_prev(datetime)

    def is_due(self, tolerance_seconds: int = 60, now: Optional[datetime] = None) -> bool:
        """Return True if the job is due to run within *tolerance_seconds* of *now*."""
        prev = self.prev_run(before=now)
        if prev is None:
            return False
        reference = now or datetime.utcnow()
        delta = (reference - prev).total_seconds()
        return 0 <= delta <= tolerance_seconds

    def __repr__(self) -> str:
        return (
            f"JobScheduler(expression={self.config.expression!r}, "
            f"timezone={self.config.timezone!r})"
        )
