"""Aggregate and report on budget usage across multiple jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwrap.budget import BudgetStatus


@dataclass
class BudgetReport:
    """Snapshot of budget usage for a single job."""

    job_name: str
    status: BudgetStatus

    @property
    def exceeded(self) -> bool:
        return self.status.exceeded

    @property
    def warned(self) -> bool:
        return self.status.warn

    def summary(self) -> str:
        pct = self.status.percent_used
        tag = "EXCEEDED" if self.exceeded else ("WARN" if self.warned else "OK")
        return (
            f"[{tag}] {self.job_name}: "
            f"{self.status.elapsed:.2f}s / {self.status.budget:.2f}s "
            f"({pct:.1f}%)"
        )


class BudgetReporter:
    """Collects BudgetStatus entries and produces aggregate reports."""

    def __init__(self) -> None:
        self._reports: List[BudgetReport] = []

    def record(self, status: BudgetStatus) -> None:
        self._reports.append(BudgetReport(job_name=status.job_name, status=status))

    @property
    def reports(self) -> List[BudgetReport]:
        return list(self._reports)

    @property
    def any_exceeded(self) -> bool:
        return any(r.exceeded for r in self._reports)

    @property
    def any_warned(self) -> bool:
        return any(r.warned for r in self._reports)

    def exceeded_reports(self) -> List[BudgetReport]:
        return [r for r in self._reports if r.exceeded]

    def warned_reports(self) -> List[BudgetReport]:
        return [r for r in self._reports if r.warned]

    def summary(self) -> str:
        if not self._reports:
            return "No budget records."
        lines = [r.summary() for r in self._reports]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total": len(self._reports),
            "exceeded": len(self.exceeded_reports()),
            "warned": len(self.warned_reports()),
            "reports": [r.status.to_dict() for r in self._reports],
        }
