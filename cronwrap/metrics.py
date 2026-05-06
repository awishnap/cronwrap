"""Simple in-process metrics collector for cron job runs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class RunRecord:
    job_name: str
    started_at: datetime
    duration_seconds: float
    exit_code: int
    attempt: int = 1
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class MetricsCollector:
    """Collects and summarises execution records for all jobs."""

    def __init__(self):
        self._records: List[RunRecord] = []

    def record(self, run: RunRecord) -> None:
        self._records.append(run)

    def runs_for(self, job_name: str) -> List[RunRecord]:
        return [r for r in self._records if r.job_name == job_name]

    def success_rate(self, job_name: str) -> Optional[float]:
        runs = self.runs_for(job_name)
        if not runs:
            return None
        return sum(1 for r in runs if r.succeeded) / len(runs)

    def average_duration(self, job_name: str) -> Optional[float]:
        runs = self.runs_for(job_name)
        if not runs:
            return None
        return sum(r.duration_seconds for r in runs) / len(runs)

    def last_run(self, job_name: str) -> Optional[RunRecord]:
        runs = self.runs_for(job_name)
        return runs[-1] if runs else None

    def summary(self, job_name: str) -> Dict:
        return {
            "job_name": job_name,
            "total_runs": len(self.runs_for(job_name)),
            "success_rate": self.success_rate(job_name),
            "average_duration_seconds": self.average_duration(job_name),
            "last_run": self.last_run(job_name),
        }

    def reset(self) -> None:
        self._records.clear()
