"""Cooldown enforcement between successive job runs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CooldownConfig:
    """Configuration for inter-run cooldown."""

    seconds: int = 0
    state_dir: str = "/tmp/cronwrap/cooldown"

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError("seconds must be >= 0")
        if not self.state_dir or not self.state_dir.strip():
            raise ValueError("state_dir must not be blank")

    @property
    def enabled(self) -> bool:
        return self.seconds > 0


class CooldownError(Exception):
    """Raised when a job is invoked before its cooldown has elapsed."""

    def __init__(self, job_name: str, remaining: float) -> None:
        self.job_name = job_name
        self.remaining = remaining
        super().__init__(
            f"Job '{job_name}' is in cooldown; {remaining:.1f}s remaining."
        )


class CooldownManager:
    """Tracks and enforces per-job cooldown windows."""

    def __init__(self, config: CooldownConfig) -> None:
        self._config = config
        self._dir = Path(config.state_dir)

    def _state_file(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.cooldown"

    def _last_run(self, job_name: str) -> float:
        path = self._state_file(job_name)
        try:
            return float(path.read_text().strip())
        except (FileNotFoundError, ValueError):
            return 0.0

    def record(self, job_name: str) -> None:
        """Record the current timestamp as the last run for *job_name*."""
        self._dir.mkdir(parents=True, exist_ok=True)
        self._state_file(job_name).write_text(str(time.time()))

    def check(self, job_name: str) -> None:
        """Raise *CooldownError* if the cooldown window has not elapsed."""
        if not self._config.enabled:
            return
        elapsed = time.time() - self._last_run(job_name)
        remaining = self._config.seconds - elapsed
        if remaining > 0:
            raise CooldownError(job_name, remaining)

    def reset(self, job_name: str) -> None:
        """Remove the cooldown state for *job_name*."""
        self._state_file(job_name).unlink(missing_ok=True)

    def remaining(self, job_name: str) -> float:
        """Return seconds remaining in the cooldown window (0 if none)."""
        if not self._config.enabled:
            return 0.0
        elapsed = time.time() - self._last_run(job_name)
        return max(0.0, self._config.seconds - elapsed)
