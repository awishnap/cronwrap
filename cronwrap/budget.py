"""Execution time budget tracking for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BudgetConfig:
    """Configuration for an execution time budget."""

    max_seconds: float = 0.0  # 0 means no budget
    warn_at_percent: float = 80.0  # warn when this % of budget is consumed
    state_dir: str = "/tmp/cronwrap/budget"

    def __post_init__(self) -> None:
        if self.max_seconds < 0:
            raise ValueError("max_seconds must be >= 0")
        if not (0.0 < self.warn_at_percent <= 100.0):
            raise ValueError("warn_at_percent must be in range (0, 100]")
        if not self.state_dir or not self.state_dir.strip():
            raise ValueError("state_dir must not be blank")

    @property
    def enabled(self) -> bool:
        return self.max_seconds > 0

    @property
    def warn_threshold_seconds(self) -> float:
        return self.max_seconds * (self.warn_at_percent / 100.0)


class BudgetExceededError(Exception):
    def __init__(self, job_name: str, elapsed: float, budget: float) -> None:
        self.job_name = job_name
        self.elapsed = elapsed
        self.budget = budget
        super().__init__(
            f"Job '{job_name}' exceeded time budget: "
            f"{elapsed:.2f}s > {budget:.2f}s"
        )


@dataclass
class BudgetStatus:
    """Result of a budget evaluation."""

    job_name: str
    elapsed: float
    budget: float
    exceeded: bool
    warn: bool

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget - self.elapsed)

    @property
    def percent_used(self) -> float:
        if self.budget <= 0:
            return 0.0
        return min(100.0, (self.elapsed / self.budget) * 100.0)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "elapsed": self.elapsed,
            "budget": self.budget,
            "exceeded": self.exceeded,
            "warn": self.warn,
            "remaining": self.remaining,
            "percent_used": round(self.percent_used, 2),
        }


class BudgetTracker:
    """Evaluates whether a job has consumed its time budget."""

    def __init__(self, config: BudgetConfig) -> None:
        self.config = config

    def evaluate(self, job_name: str, elapsed: float) -> BudgetStatus:
        """Return a BudgetStatus for the given elapsed time."""
        if not self.config.enabled:
            return BudgetStatus(
                job_name=job_name,
                elapsed=elapsed,
                budget=self.config.max_seconds,
                exceeded=False,
                warn=False,
            )
        exceeded = elapsed > self.config.max_seconds
        warn = not exceeded and elapsed >= self.config.warn_threshold_seconds
        return BudgetStatus(
            job_name=job_name,
            elapsed=elapsed,
            budget=self.config.max_seconds,
            exceeded=exceeded,
            warn=warn,
        )

    def check(self, job_name: str, elapsed: float) -> BudgetStatus:
        """Evaluate and raise BudgetExceededError if budget is exceeded."""
        status = self.evaluate(job_name, elapsed)
        if status.exceeded:
            raise BudgetExceededError(job_name, elapsed, self.config.max_seconds)
        return status
