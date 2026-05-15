"""Execution window enforcement — restrict jobs to allowed time ranges."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import List, Optional
import datetime


class WindowViolationError(Exception):
    def __init__(self, job_name: str, current_time: time, windows: list) -> None:
        self.job_name = job_name
        self.current_time = current_time
        self.windows = windows
        super().__init__(
            f"Job '{job_name}' attempted to run at {current_time} "
            f"which is outside allowed windows: {windows}"
        )


@dataclass
class TimeWindow:
    start: time
    end: time

    def __post_init__(self) -> None:
        if not isinstance(self.start, time):
            raise TypeError("start must be a datetime.time instance")
        if not isinstance(self.end, time):
            raise TypeError("end must be a datetime.time instance")
        if self.start >= self.end:
            raise ValueError(
                f"start ({self.start}) must be earlier than end ({self.end})"
            )

    def contains(self, t: time) -> bool:
        return self.start <= t <= self.end

    def __repr__(self) -> str:  # pragma: no cover
        return f"TimeWindow({self.start}-{self.end})"


@dataclass
class WindowConfig:
    windows: List[TimeWindow] = field(default_factory=list)
    timezone: str = "UTC"
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.windows, list):
            raise TypeError("windows must be a list of TimeWindow instances")
        for w in self.windows:
            if not isinstance(w, TimeWindow):
                raise TypeError(f"Each window must be a TimeWindow, got {type(w)}")
        if not self.timezone or not self.timezone.strip():
            raise ValueError("timezone must not be blank")


class WindowGuard:
    """Checks whether the current time falls within any allowed window."""

    def __init__(self, config: WindowConfig) -> None:
        self._config = config

    @property
    def config(self) -> WindowConfig:
        return self._config

    def is_allowed(self, at: Optional[time] = None) -> bool:
        if not self._config.enabled or not self._config.windows:
            return True
        current = at if at is not None else datetime.datetime.now().time()
        return any(w.contains(current) for w in self._config.windows)

    def enforce(self, job_name: str, at: Optional[time] = None) -> None:
        if not self.is_allowed(at):
            current = at if at is not None else datetime.datetime.now().time()
            raise WindowViolationError(job_name, current, self._config.windows)

    def dry_run(self, job_name: str, at: Optional[time] = None) -> dict:
        current = at if at is not None else datetime.datetime.now().time()
        allowed = self.is_allowed(at)
        return {
            "job_name": job_name,
            "current_time": str(current),
            "allowed": allowed,
            "windows": [str(w) for w in self._config.windows],
        }
