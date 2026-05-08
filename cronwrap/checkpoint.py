"""Checkpoint support for resumable cron jobs."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CheckpointConfig:
    enabled: bool = False
    directory: str = "/tmp/cronwrap/checkpoints"
    ttl_seconds: int = 86400  # 24 hours

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")


@dataclass
class Checkpoint:
    job_name: str
    data: dict[str, Any] = field(default_factory=dict)
    saved_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.time() - self.saved_at) > ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "data": self.data,
            "saved_at": self.saved_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Checkpoint":
        return cls(
            job_name=raw["job_name"],
            data=raw.get("data", {}),
            saved_at=raw.get("saved_at", time.time()),
        )


class CheckpointManager:
    def __init__(self, config: CheckpointConfig) -> None:
        self.config = config
        self._dir = Path(config.directory)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.json"

    def save(self, job_name: str, data: dict[str, Any]) -> None:
        if not self.config.enabled:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        cp = Checkpoint(job_name=job_name, data=data)
        self._path(job_name).write_text(json.dumps(cp.to_dict()))

    def load(self, job_name: str) -> Optional[Checkpoint]:
        if not self.config.enabled:
            return None
        p = self._path(job_name)
        if not p.exists():
            return None
        cp = Checkpoint.from_dict(json.loads(p.read_text()))
        if cp.is_expired(self.config.ttl_seconds):
            self.clear(job_name)
            return None
        return cp

    def clear(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def exists(self, job_name: str) -> bool:
        return self.load(job_name) is not None
