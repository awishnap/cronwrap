"""Job dependency management — ensures prerequisite jobs have run successfully."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


class DependencyError(Exception):
    """Raised when a job dependency is not satisfied."""

    def __init__(self, job_name: str, missing: List[str]) -> None:
        self.job_name = job_name
        self.missing = missing
        super().__init__(
            f"Job '{job_name}' has unsatisfied dependencies: {', '.join(missing)}"
        )


@dataclass
class DependencyConfig:
    """Configuration for job dependencies."""

    required_jobs: List[str] = field(default_factory=list)
    max_age_seconds: int = 3600  # how recent the dependency run must be
    strict: bool = True  # if True, raise on missing; if False, just warn

    def __post_init__(self) -> None:
        if not isinstance(self.required_jobs, list):
            raise TypeError("required_jobs must be a list")
        for name in self.required_jobs:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Each required job name must be a non-blank string")
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be a positive integer")


class DependencyChecker:
    """Checks whether job dependencies have been satisfied."""

    def __init__(self, config: DependencyConfig) -> None:
        self._config = config
        # Maps job_name -> last successful run timestamp
        self._registry: dict[str, datetime] = {}

    def record_success(self, job_name: str, at: Optional[datetime] = None) -> None:
        """Record a successful run for *job_name*."""
        self._registry[job_name] = at or datetime.utcnow()

    def check(self, for_job: str) -> List[str]:
        """Return a list of unsatisfied dependency names."""
        cutoff = datetime.utcnow() - timedelta(seconds=self._config.max_age_seconds)
        unsatisfied = []
        for dep in self._config.required_jobs:
            last_run = self._registry.get(dep)
            if last_run is None or last_run < cutoff:
                unsatisfied.append(dep)
        return unsatisfied

    def assert_satisfied(self, for_job: str) -> None:
        """Raise *DependencyError* if any dependency is unsatisfied."""
        missing = self.check(for_job)
        if missing and self._config.strict:
            raise DependencyError(for_job, missing)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DependencyChecker(required={self._config.required_jobs}, "
            f"max_age={self._config.max_age_seconds}s, strict={self._config.strict})"
        )
