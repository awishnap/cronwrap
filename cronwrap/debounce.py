"""Debounce support: suppress rapid re-runs of a job within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DebounceConfig:
    """Configuration for job debouncing."""

    cooldown_seconds: int = 0
    state_dir: str = "/tmp/cronwrap/debounce"

    def __post_init__(self) -> None:
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        if not self.state_dir or not self.state_dir.strip():
            raise ValueError("state_dir must not be blank")

    @property
    def enabled(self) -> bool:
        return self.cooldown_seconds > 0


class DebounceError(Exception):
    """Raised when a job is suppressed due to debounce cooldown."""

    def __init__(self, job_name: str, remaining: float) -> None:
        self.job_name = job_name
        self.remaining = remaining
        super().__init__(
            f"Job '{job_name}' is debounced; {remaining:.1f}s remaining in cooldown."
        )


class Debouncer:
    """Tracks last-run timestamps and enforces cooldown windows."""

    def __init__(self, config: DebounceConfig) -> None:
        self.config = config
        self._state_dir = Path(config.state_dir)

    def _state_file(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._state_dir / f"{safe}.debounce"

    def _last_run(self, job_name: str) -> Optional[float]:
        path = self._state_file(job_name)
        try:
            return float(path.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None

    def _record(self, job_name: str) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file(job_name).write_text(str(time.monotonic()))

    def check(self, job_name: str) -> None:
        """Raise DebounceError if the job is still within its cooldown window."""
        if not self.config.enabled:
            return
        last = self._last_run(job_name)
        if last is None:
            return
        elapsed = time.monotonic() - last
        remaining = self.config.cooldown_seconds - elapsed
        if remaining > 0:
            raise DebounceError(job_name, remaining)

    def record(self, job_name: str) -> None:
        """Record that the job ran right now."""
        if self.config.enabled:
            self._record(job_name)

    def reset(self, job_name: str) -> None:
        """Clear the debounce state for a job."""
        self._state_file(job_name).unlink(missing_ok=True)
