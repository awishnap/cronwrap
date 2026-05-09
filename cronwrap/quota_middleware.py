"""Middleware that integrates quota enforcement into the job execution pipeline."""
from __future__ import annotations

from typing import Callable, Optional

from cronwrap.quota import QuotaConfig, QuotaEnforcer, QuotaExceededError, ResourceUsage
from cronwrap.quota_reporter import QuotaReporter, QuotaReport


class QuotaMiddleware:
    """Wraps a callable with pre/post quota checks and produces a report.

    Usage::

        middleware = QuotaMiddleware(config, usage_provider=my_usage_fn)
        report = middleware.run("my-job", my_callable)
    """

    def __init__(
        self,
        config: QuotaConfig,
        usage_provider: Optional[Callable[[], ResourceUsage]] = None,
    ) -> None:
        self._config = config
        self._enforcer = QuotaEnforcer(config)
        self._reporter = QuotaReporter(config)
        self._usage_provider = usage_provider or (lambda: ResourceUsage())

    def run(
        self,
        job_name: str,
        fn: Callable[[], None],
    ) -> QuotaReport:
        """Execute *fn* then check resource usage.  Returns a QuotaReport.

        Raises QuotaExceededError if any quota is breached and enforce=True.
        """
        fn()
        usage = self._usage_provider()
        self._enforcer.check(usage)
        return self._reporter.build_report(job_name, usage)

    def dry_run(
        self,
        job_name: str,
        usage: ResourceUsage,
    ) -> QuotaReport:
        """Check hypothetical *usage* without executing anything."""
        return self._reporter.build_report(job_name, usage)
