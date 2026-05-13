"""Concurrency control for cron jobs — limits parallel executions."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Semaphore
from typing import Dict


class ConcurrencyLimitError(Exception):
    """Raised when the concurrency limit for a job is exceeded."""

    def __init__(self, job_name: str, limit: int) -> None:
        self.job_name = job_name
        self.limit = limit
        super().__init__(
            f"Job '{job_name}' has reached its concurrency limit of {limit}."
        )


@dataclass
class ConcurrencyConfig:
    """Configuration for concurrency limiting."""

    max_parallel: int = 1
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_parallel < 1:
            raise ValueError("max_parallel must be at least 1.")


class ConcurrencyManager:
    """Manages per-job semaphores to cap parallel executions."""

    def __init__(self) -> None:
        self._semaphores: Dict[str, Semaphore] = {}
        self._configs: Dict[str, ConcurrencyConfig] = {}

    def register(self, job_name: str, config: ConcurrencyConfig) -> None:
        """Register a job with its concurrency config."""
        if job_name in self._semaphores:
            return
        self._configs[job_name] = config
        self._semaphores[job_name] = Semaphore(config.max_parallel)

    def acquire(self, job_name: str) -> bool:
        """Try to acquire a slot for *job_name*.

        Returns True if acquired, raises ConcurrencyLimitError otherwise.
        """
        config = self._configs.get(job_name)
        if config is None or not config.enabled:
            return True
        sem = self._semaphores[job_name]
        acquired = sem.acquire(blocking=False)
        if not acquired:
            raise ConcurrencyLimitError(job_name, config.max_parallel)
        return True

    def release(self, job_name: str) -> None:
        """Release a previously acquired slot for *job_name*."""
        sem = self._semaphores.get(job_name)
        if sem is not None:
            sem.release()

    def available_slots(self, job_name: str) -> int:
        """Return the number of available slots for *job_name*."""
        config = self._configs.get(job_name)
        if config is None or not config.enabled:
            return -1  # unlimited / untracked
        sem = self._semaphores[job_name]
        return sem._value  # type: ignore[attr-defined]
