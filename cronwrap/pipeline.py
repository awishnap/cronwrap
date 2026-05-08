"""Multi-step pipeline support for cron jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwrap.checkpoint import CheckpointManager


@dataclass
class PipelineStep:
    name: str
    fn: Callable[..., None]
    skip_on_checkpoint: bool = True


@dataclass
class StepResult:
    name: str
    success: bool
    duration: float
    error: Optional[str] = None


class PipelineError(Exception):
    def __init__(self, step: str, cause: Exception) -> None:
        super().__init__(f"Pipeline failed at step '{step}': {cause}")
        self.step = step
        self.cause = cause


class Pipeline:
    """Executes a sequence of named steps with optional checkpoint resume."""

    def __init__(
        self,
        job_name: str,
        steps: list[PipelineStep],
        checkpoint_manager: Optional[CheckpointManager] = None,
    ) -> None:
        self.job_name = job_name
        self.steps = steps
        self._cp = checkpoint_manager
        self.results: list[StepResult] = []

    def _completed_steps(self) -> set[str]:
        if self._cp is None:
            return set()
        cp = self._cp.load(self.job_name)
        if cp is None:
            return set()
        return set(cp.data.get("completed", []))

    def _mark_completed(self, step_name: str) -> None:
        if self._cp is None or not self._cp.config.enabled:
            return
        cp = self._cp.load(self.job_name)
        completed = list(cp.data.get("completed", [])) if cp else []
        if step_name not in completed:
            completed.append(step_name)
        self._cp.save(self.job_name, {"completed": completed})

    def run(self) -> list[StepResult]:
        completed = self._completed_steps()
        for step in self.steps:
            if step.skip_on_checkpoint and step.name in completed:
                self.results.append(StepResult(name=step.name, success=True, duration=0.0))
                continue
            start = time.monotonic()
            try:
                step.fn()
                duration = time.monotonic() - start
                self.results.append(StepResult(name=step.name, success=True, duration=duration))
                self._mark_completed(step.name)
            except Exception as exc:  # noqa: BLE001
                duration = time.monotonic() - start
                self.results.append(
                    StepResult(name=step.name, success=False, duration=duration, error=str(exc))
                )
                raise PipelineError(step.name, exc) from exc
        if self._cp is not None:
            self._cp.clear(self.job_name)
        return self.results

    @property
    def all_succeeded(self) -> bool:
        return all(r.success for r in self.results)
