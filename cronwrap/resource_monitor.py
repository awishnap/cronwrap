"""Resource monitoring for cron jobs — tracks CPU and memory usage during execution."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ResourceSnapshot:
    """A point-in-time snapshot of resource usage."""
    timestamp: float
    cpu_percent: float
    memory_rss_bytes: int
    memory_vms_bytes: int

    @property
    def memory_rss_mb(self) -> float:
        return self.memory_rss_bytes / (1024 * 1024)


@dataclass
class ResourceSummary:
    """Aggregated resource statistics over a job run."""
    job_name: str
    snapshots: List[ResourceSnapshot] = field(default_factory=list)

    @property
    def peak_memory_rss_mb(self) -> float:
        if not self.snapshots:
            return 0.0
        return max(s.memory_rss_mb for s in self.snapshots)

    @property
    def avg_cpu_percent(self) -> float:
        if not self.snapshots:
            return 0.0
        return sum(s.cpu_percent for s in self.snapshots) / len(self.snapshots)

    @property
    def peak_cpu_percent(self) -> float:
        if not self.snapshots:
            return 0.0
        return max(s.cpu_percent for s in self.snapshots)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "peak_memory_rss_mb": round(self.peak_memory_rss_mb, 2),
            "avg_cpu_percent": round(self.avg_cpu_percent, 2),
            "peak_cpu_percent": round(self.peak_cpu_percent, 2),
            "sample_count": len(self.snapshots),
        }


class ResourceMonitor:
    """Polls resource usage of a process at a fixed interval."""

    def __init__(self, job_name: str, pid: Optional[int] = None, interval: float = 1.0) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")
        self._job_name = job_name
        self._pid = pid or os.getpid()
        self._interval = interval
        self._snapshots: List[ResourceSnapshot] = []

    def poll(self) -> Optional[ResourceSnapshot]:
        """Take a single resource snapshot. Returns None if process is unavailable."""
        try:
            import psutil  # type: ignore
            proc = psutil.Process(self._pid)
            mem = proc.memory_info()
            snapshot = ResourceSnapshot(
                timestamp=time.monotonic(),
                cpu_percent=proc.cpu_percent(interval=None),
                memory_rss_bytes=mem.rss,
                memory_vms_bytes=mem.vms,
            )
            self._snapshots.append(snapshot)
            return snapshot
        except Exception:
            return None

    def summary(self) -> ResourceSummary:
        return ResourceSummary(job_name=self._job_name, snapshots=list(self._snapshots))

    def reset(self) -> None:
        self._snapshots.clear()
