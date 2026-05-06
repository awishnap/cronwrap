"""Tests for cronwrap.metrics module."""

from datetime import datetime, timezone
import pytest

from cronwrap.metrics import MetricsCollector, RunRecord


def _record(job="test-job", exit_code=0, duration=1.0, attempt=1, timed_out=False):
    return RunRecord(
        job_name=job,
        started_at=datetime.now(tz=timezone.utc),
        duration_seconds=duration,
        exit_code=exit_code,
        attempt=attempt,
        timed_out=timed_out,
    )


class TestRunRecord:
    def test_succeeded_on_zero_exit(self):
        assert _record(exit_code=0).succeeded

    def test_failed_on_nonzero_exit(self):
        assert not _record(exit_code=1).succeeded

    def test_timed_out_not_succeeded(self):
        assert not _record(exit_code=0, timed_out=True).succeeded


class TestMetricsCollector:
    def setup_method(self):
        self.collector = MetricsCollector()

    def test_empty_runs_for_unknown_job(self):
        assert self.collector.runs_for("ghost") == []

    def test_record_and_retrieve(self):
        self.collector.record(_record(job="job-a"))
        assert len(self.collector.runs_for("job-a")) == 1

    def test_success_rate_all_pass(self):
        for _ in range(4):
            self.collector.record(_record(exit_code=0))
        assert self.collector.success_rate("test-job") == 1.0

    def test_success_rate_mixed(self):
        self.collector.record(_record(exit_code=0))
        self.collector.record(_record(exit_code=1))
        assert self.collector.success_rate("test-job") == 0.5

    def test_success_rate_none_when_no_runs(self):
        assert self.collector.success_rate("missing") is None

    def test_average_duration(self):
        self.collector.record(_record(duration=2.0))
        self.collector.record(_record(duration=4.0))
        assert self.collector.average_duration("test-job") == 3.0

    def test_last_run_returns_most_recent(self):
        r1 = _record(exit_code=0)
        r2 = _record(exit_code=1)
        self.collector.record(r1)
        self.collector.record(r2)
        assert self.collector.last_run("test-job") is r2

    def test_summary_keys(self):
        self.collector.record(_record())
        s = self.collector.summary("test-job")
        assert "total_runs" in s
        assert "success_rate" in s
        assert "average_duration_seconds" in s

    def test_reset_clears_all(self):
        self.collector.record(_record())
        self.collector.reset()
        assert self.collector.runs_for("test-job") == []
