"""Resource quota enforcement for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuotaConfig:
    """Configuration for resource quotas applied to a cron job."""

    max_cpu_percent: float = 100.0
    max_memory_mb: float = 0.0  # 0 means unlimited
    max_disk_write_mb: float = 0.0  # 0 means unlimited
    enforce: bool = True

    def __post_init__(self) -> None:
        if not (0.0 < self.max_cpu_percent <= 100.0):
            raise ValueError(
                f"max_cpu_percent must be in (0, 100], got {self.max_cpu_percent}"
            )
        if self.max_memory_mb < 0:
            raise ValueError(
                f"max_memory_mb must be >= 0, got {self.max_memory_mb}"
            )
        if self.max_disk_write_mb < 0:
            raise ValueError(
                f"max_disk_write_mb must be >= 0, got {self.max_disk_write_mb}"
            )

    @property
    def memory_limited(self) -> bool:
        return self.max_memory_mb > 0

    @property
    def disk_limited(self) -> bool:
        return self.max_disk_write_mb > 0


class QuotaExceededError(Exception):
    """Raised when a job exceeds a configured resource quota."""

    def __init__(self, resource: str, limit: float, actual: float) -> None:
        self.resource = resource
        self.limit = limit
        self.actual = actual
        super().__init__(
            f"Quota exceeded for '{resource}': limit={limit}, actual={actual:.2f}"
        )


@dataclass
class ResourceUsage:
    """Snapshot of resource consumption for a completed job run."""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_write_mb: float = 0.0


class QuotaEnforcer:
    """Checks a ResourceUsage snapshot against a QuotaConfig."""

    def __init__(self, config: QuotaConfig) -> None:
        self._config = config

    def check(self, usage: ResourceUsage) -> None:
        """Raise QuotaExceededError if any quota is breached."""
        if not self._config.enforce:
            return

        if usage.cpu_percent > self._config.max_cpu_percent:
            raise QuotaExceededError(
                "cpu_percent", self._config.max_cpu_percent, usage.cpu_percent
            )
        if self._config.memory_limited and usage.memory_mb > self._config.max_memory_mb:
            raise QuotaExceededError(
                "memory_mb", self._config.max_memory_mb, usage.memory_mb
            )
        if self._config.disk_limited and usage.disk_write_mb > self._config.max_disk_write_mb:
            raise QuotaExceededError(
                "disk_write_mb", self._config.max_disk_write_mb, usage.disk_write_mb
            )

    def is_within_quota(self, usage: ResourceUsage) -> bool:
        """Return True if usage is within all configured limits."""
        try:
            self.check(usage)
            return True
        except QuotaExceededError:
            return False
