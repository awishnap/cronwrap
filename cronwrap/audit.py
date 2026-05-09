"""Audit trail for cron job executions."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditConfig:
    audit_dir: str = "/var/log/cronwrap/audit"
    max_entries: int = 1000
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        if not self.audit_dir or not self.audit_dir.strip():
            raise ValueError("audit_dir must not be blank")


@dataclass
class AuditEvent:
    job_name: str
    event_type: str  # 'start', 'success', 'failure', 'retry', 'timeout'
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = None
    attempt: int = 1
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "attempt": self.attempt,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        return cls(
            job_name=data["job_name"],
            event_type=data["event_type"],
            timestamp=data.get("timestamp", ""),
            exit_code=data.get("exit_code"),
            duration_seconds=data.get("duration_seconds"),
            attempt=data.get("attempt", 1),
            message=data.get("message", ""),
        )


class AuditLog:
    def __init__(self, config: AuditConfig) -> None:
        self.config = config
        self._path = Path(config.audit_dir)

    def _log_file(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self._path / f"{safe}.audit.jsonl"

    def record(self, event: AuditEvent) -> None:
        if not self.config.enabled:
            return
        self._path.mkdir(parents=True, exist_ok=True)
        log_file = self._log_file(event.job_name)
        entries = self._read_all(log_file)
        entries.append(event.to_dict())
        if len(entries) > self.config.max_entries:
            entries = entries[-self.config.max_entries:]
        with log_file.open("w") as fh:
            for entry in entries:
                fh.write(json.dumps(entry) + "\n")

    def get_events(self, job_name: str) -> List[AuditEvent]:
        log_file = self._log_file(job_name)
        return [AuditEvent.from_dict(d) for d in self._read_all(log_file)]

    def _read_all(self, path: Path) -> list:
        if not path.exists():
            return []
        entries = []
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries
