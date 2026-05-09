"""Reporting utilities for resource quota usage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwrap.quota import QuotaConfig, ResourceUsage


@dataclass
class QuotaReport:
    """Summary of quota usage for a single job run."""

    job_name: str
    usage: ResourceUsage
    config: QuotaConfig
    exceeded_resources: List[str]

    @property
    def any_exceeded(self) -> bool:
        return len(self.exceeded_resources) > 0

    def summary(self) -> str:
        lines = [
            f"Quota report for '{self.job_name}':",
            f"  CPU    : {self.usage.cpu_percent:.1f}% / {self.config.max_cpu_percent:.1f}%",
            f"  Memory : {self.usage.memory_mb:.1f} MB / "
            + (f"{self.config.max_memory_mb:.1f} MB" if self.config.memory_limited else "unlimited"),
            f"  Disk   : {self.usage.disk_write_mb:.1f} MB / "
            + (f"{self.config.max_disk_write_mb:.1f} MB" if self.config.disk_limited else "unlimited"),
        ]
        if self.any_exceeded:
            lines.append(f"  EXCEEDED: {', '.join(self.exceeded_resources)}")
        else:
            lines.append("  Status : OK")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "cpu_percent": self.usage.cpu_percent,
            "memory_mb": self.usage.memory_mb,
            "disk_write_mb": self.usage.disk_write_mb,
            "exceeded_resources": self.exceeded_resources,
            "any_exceeded": self.any_exceeded,
        }


class QuotaReporter:
    """Builds QuotaReport objects from usage data."""

    def __init__(self, config: QuotaConfig) -> None:
        self._config = config

    def build_report(self, job_name: str, usage: ResourceUsage) -> QuotaReport:
        exceeded: List[str] = []
        if self._config.enforce:
            if usage.cpu_percent > self._config.max_cpu_percent:
                exceeded.append("cpu_percent")
            if self._config.memory_limited and usage.memory_mb > self._config.max_memory_mb:
                exceeded.append("memory_mb")
            if self._config.disk_limited and usage.disk_write_mb > self._config.max_disk_write_mb:
                exceeded.append("disk_write_mb")
        return QuotaReport(
            job_name=job_name,
            usage=usage,
            config=self._config,
            exceeded_resources=exceeded,
        )
