"""Filesystem-based lock to prevent overlapping cron job executions."""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path


class LockAcquisitionError(Exception):
    """Raised when a job lock cannot be acquired."""

    def __init__(self, job_name: str, lock_file: str):
        self.job_name = job_name
        self.lock_file = lock_file
        super().__init__(
            f"Job '{job_name}' is already running (lock file: {lock_file})"
        )


@dataclass
class LockConfig:
    lock_dir: str = "/tmp/cronwrap/locks"
    stale_after_seconds: int = 3600

    def __post_init__(self):
        if self.stale_after_seconds < 0:
            raise ValueError("stale_after_seconds must be >= 0")


class JobLock:
    """Manages a per-job lock file to prevent concurrent executions."""

    def __init__(self, job_name: str, config: LockConfig | None = None):
        self.job_name = job_name
        self.config = config or LockConfig()
        self._lock_path = Path(self.config.lock_dir) / f"{job_name}.lock"
        self._acquired = False

    @property
    def lock_path(self) -> str:
        return str(self._lock_path)

    def _is_stale(self) -> bool:
        """Return True if an existing lock file is older than stale_after_seconds."""
        if self.config.stale_after_seconds == 0:
            return False
        try:
            mtime = self._lock_path.stat().st_mtime
            return (time.time() - mtime) > self.config.stale_after_seconds
        except FileNotFoundError:
            return False

    def acquire(self) -> None:
        """Create the lock file. Raises LockAcquisitionError if already locked."""
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self._lock_path.exists():
            if self._is_stale():
                self._lock_path.unlink(missing_ok=True)
            else:
                raise LockAcquisitionError(self.job_name, self.lock_path)
        self._lock_path.write_text(str(os.getpid()))
        self._acquired = True

    def release(self) -> None:
        """Remove the lock file if it was acquired by this instance."""
        if self._acquired:
            self._lock_path.unlink(missing_ok=True)
            self._acquired = False

    def __enter__(self) -> "JobLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def __repr__(self) -> str:
        return (
            f"JobLock(job_name={self.job_name!r}, "
            f"lock_path={self.lock_path!r}, acquired={self._acquired})"
        )
