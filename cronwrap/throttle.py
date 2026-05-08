"""Throttle support for cron jobs — limits execution frequency within a time window."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


@dataclass
class ThrottleConfig:
    """Configuration for job throttling."""

    min_interval_seconds: int = 0  # 0 means no throttling
    state_dir: str = "/tmp/cronwrap/throttle"

    def __post_init__(self) -> None:
        if self.min_interval_seconds < 0:
            raise ValueError(
                f"min_interval_seconds must be >= 0, got {self.min_interval_seconds}"
            )
        if not self.state_dir or not self.state_dir.strip():
            raise ValueError("state_dir must not be blank")

    @property
    def enabled(self) -> bool:
        return self.min_interval_seconds > 0


class ThrottleError(Exception):
    """Raised when a job is throttled."""

    def __init__(self, job_name: str, seconds_remaining: float) -> None:
        self.job_name = job_name
        self.seconds_remaining = seconds_remaining
        super().__init__(
            f"Job '{job_name}' is throttled; retry in {seconds_remaining:.1f}s"
        )


class JobThrottle:
    """Tracks last-run timestamps and enforces minimum intervals between runs."""

    def __init__(self, config: ThrottleConfig) -> None:
        self.config = config
        self._state_dir = Path(config.state_dir)

    def _state_file(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._state_dir / f"{safe}.json"

    def _read_last_run(self, job_name: str) -> Optional[float]:
        path = self._state_file(job_name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return float(data["last_run"])
        except (KeyError, ValueError, OSError):
            return None

    def _write_last_run(self, job_name: str, ts: float) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file(job_name).write_text(json.dumps({"last_run": ts}))

    def check(self, job_name: str) -> None:
        """Raise ThrottleError if the job ran too recently."""
        if not self.config.enabled:
            return
        last = self._read_last_run(job_name)
        if last is None:
            return
        elapsed = time.time() - last
        remaining = self.config.min_interval_seconds - elapsed
        if remaining > 0:
            raise ThrottleError(job_name, remaining)

    def record(self, job_name: str) -> None:
        """Record that the job ran right now."""
        self._write_last_run(job_name, time.time())

    def reset(self, job_name: str) -> None:
        """Clear the throttle state for a job."""
        path = self._state_file(job_name)
        if path.exists():
            path.unlink()
