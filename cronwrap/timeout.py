"""Timeout enforcement for cron job execution."""

import signal
from dataclasses import dataclass, field
from typing import Optional


class TimeoutError(Exception):  # noqa: A001
    """Raised when a job exceeds its allowed execution time."""

    def __init__(self, job_name: str, timeout_seconds: int):
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Job '{job_name}' timed out after {timeout_seconds} second(s)."
        )


@dataclass
class TimeoutConfig:
    seconds: int = 0  # 0 means no timeout
    kill_on_timeout: bool = True

    def __post_init__(self):
        if self.seconds < 0:
            raise ValueError("Timeout seconds must be >= 0 (0 = disabled).")

    @property
    def enabled(self) -> bool:
        return self.seconds > 0

    def __repr__(self) -> str:
        if not self.enabled:
            return "TimeoutConfig(disabled)"
        return f"TimeoutConfig(seconds={self.seconds}, kill={self.kill_on_timeout})"


class TimeoutGuard:
    """Context manager that enforces a wall-clock timeout using SIGALRM."""

    def __init__(self, config: TimeoutConfig, job_name: str = "unknown"):
        self.config = config
        self.job_name = job_name
        self._previous_handler = None

    def _handler(self, signum, frame):
        raise TimeoutError(self.job_name, self.config.seconds)

    def __enter__(self):
        if self.config.enabled:
            self._previous_handler = signal.signal(signal.SIGALRM, self._handler)
            signal.alarm(self.config.seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.config.enabled:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._previous_handler)
        return False
