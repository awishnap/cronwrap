"""Persistent run history storage for cron jobs."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class HistoryEntry:
    job_name: str
    started_at: str
    finished_at: str
    exit_code: int
    timed_out: bool
    duration_seconds: float
    command: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(**data)


class JobHistory:
    """Stores and retrieves run history for a cron job as newline-delimited JSON."""

    def __init__(self, storage_dir: str = "/var/log/cronwrap", max_entries: int = 100) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.storage_dir = Path(storage_dir)
        self.max_entries = max_entries

    def _path_for(self, job_name: str) -> Path:
        safe_name = job_name.replace("/", "_").replace(" ", "_")
        return self.storage_dir / f"{safe_name}.jsonl"

    def record(self, entry: HistoryEntry) -> None:
        """Append an entry and prune to max_entries."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(entry.job_name)
        existing = self.load(entry.job_name)
        existing.append(entry)
        trimmed = existing[-self.max_entries :]
        with path.open("w", encoding="utf-8") as fh:
            for e in trimmed:
                fh.write(json.dumps(asdict(e)) + "\n")

    def load(self, job_name: str) -> List[HistoryEntry]:
        """Return all stored entries for a job, oldest first."""
        path = self._path_for(job_name)
        if not path.exists():
            return []
        entries: List[HistoryEntry] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(HistoryEntry.from_dict(json.loads(line)))
        return entries

    def last(self, job_name: str) -> Optional[HistoryEntry]:
        """Return the most recent entry, or None if no history exists."""
        entries = self.load(job_name)
        return entries[-1] if entries else None

    def clear(self, job_name: str) -> None:
        """Delete all history for a job."""
        path = self._path_for(job_name)
        if path.exists():
            path.unlink()
