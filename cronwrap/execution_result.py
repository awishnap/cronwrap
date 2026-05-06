from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ExecutionResult:
    """Holds the outcome of a single cron job execution attempt."""

    job_name: str
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    attempt: int = 1
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def failed(self) -> bool:
        return not self.succeeded

    def summary(self) -> str:
        status = "SUCCESS" if self.succeeded else "FAILURE"
        return (
            f"[{status}] job='{self.job_name}' command='{self.command}' "
            f"exit_code={self.exit_code} duration={self.duration:.3f}s "
            f"attempt={self.attempt}"
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": round(self.duration, 4),
            "attempt": self.attempt,
            "succeeded": self.succeeded,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionResult(job='{self.job_name}', exit_code={self.exit_code}, "
            f"succeeded={self.succeeded}, attempt={self.attempt})"
        )
