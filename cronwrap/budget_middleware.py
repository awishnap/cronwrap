"""Middleware that enforces execution time budgets."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from cronwrap.budget import BudgetConfig, BudgetStatus, BudgetTracker


class BudgetMiddleware:
    """Wraps a callable and enforces the configured time budget."""

    def __init__(self, config: Optional[BudgetConfig] = None) -> None:
        self.config = config or BudgetConfig()
        self._tracker = BudgetTracker(self.config)
        self._last_status: Optional[BudgetStatus] = None

    def run(self, fn: Callable[[], Any], job_name: str = "job") -> Any:
        """Execute *fn*, then check budget; raises BudgetExceededError if over."""
        start = time.monotonic()
        result = fn()
        elapsed = time.monotonic() - start
        self._last_status = self._tracker.check(job_name, elapsed)
        return result

    def dry_run(self, fn: Callable[[], Any], job_name: str = "job") -> BudgetStatus:
        """Execute *fn* and return BudgetStatus without raising on excess."""
        start = time.monotonic()
        fn()
        elapsed = time.monotonic() - start
        self._last_status = self._tracker.evaluate(job_name, elapsed)
        return self._last_status

    @property
    def last_status(self) -> Optional[BudgetStatus]:
        return self._last_status
