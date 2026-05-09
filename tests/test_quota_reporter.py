"""Tests for cronwrap.quota_reporter."""
import pytest

from cronwrap.quota import QuotaConfig, ResourceUsage
from cronwrap.quota_reporter import QuotaReport, QuotaReporter


def _reporter(**kwargs) -> QuotaReporter:
    return QuotaReporter(QuotaConfig(**kwargs))


class TestQuotaReport:
    def _make_report(self, exceeded=None) -> QuotaReport:
        cfg = QuotaConfig(max_cpu_percent=80.0, max_memory_mb=256.0)
        usage = ResourceUsage(cpu_percent=40.0, memory_mb=128.0)
        return QuotaReport(
            job_name="test-job",
            usage=usage,
            config=cfg,
            exceeded_resources=exceeded or [],
        )

    def test_any_exceeded_false_when_empty(self):
        report = self._make_report(exceeded=[])
        assert report.any_exceeded is False

    def test_any_exceeded_true_when_resources_listed(self):
        report = self._make_report(exceeded=["cpu_percent"])
        assert report.any_exceeded is True

    def test_summary_contains_job_name(self):
        report = self._make_report()
        assert "test-job" in report.summary()

    def test_summary_ok_when_no_exceeded(self):
        report = self._make_report(exceeded=[])
        assert "OK" in report.summary()

    def test_summary_exceeded_label_present(self):
        report = self._make_report(exceeded=["memory_mb"])
        assert "EXCEEDED" in report.summary()
        assert "memory_mb" in report.summary()

    def test_to_dict_keys(self):
        report = self._make_report()
        d = report.to_dict()
        assert "job_name" in d
        assert "cpu_percent" in d
        assert "exceeded_resources" in d
        assert "any_exceeded" in d


class TestQuotaReporter:
    def test_no_exceeded_when_within_limits(self):
        reporter = _reporter(max_cpu_percent=80.0, max_memory_mb=512.0)
        usage = ResourceUsage(cpu_percent=30.0, memory_mb=100.0)
        report = reporter.build_report("my-job", usage)
        assert not report.any_exceeded
        assert report.exceeded_resources == []

    def test_cpu_flagged_when_exceeded(self):
        reporter = _reporter(max_cpu_percent=40.0)
        usage = ResourceUsage(cpu_percent=90.0)
        report = reporter.build_report("my-job", usage)
        assert "cpu_percent" in report.exceeded_resources

    def test_memory_flagged_when_exceeded(self):
        reporter = _reporter(max_memory_mb=128.0)
        usage = ResourceUsage(memory_mb=256.0)
        report = reporter.build_report("my-job", usage)
        assert "memory_mb" in report.exceeded_resources

    def test_disk_flagged_when_exceeded(self):
        reporter = _reporter(max_disk_write_mb=10.0)
        usage = ResourceUsage(disk_write_mb=20.0)
        report = reporter.build_report("my-job", usage)
        assert "disk_write_mb" in report.exceeded_resources

    def test_multiple_exceeded_captured(self):
        reporter = _reporter(max_cpu_percent=10.0, max_memory_mb=64.0)
        usage = ResourceUsage(cpu_percent=80.0, memory_mb=200.0)
        report = reporter.build_report("my-job", usage)
        assert len(report.exceeded_resources) == 2

    def test_enforce_false_produces_no_exceeded(self):
        reporter = QuotaReporter(QuotaConfig(max_cpu_percent=5.0, enforce=False))
        usage = ResourceUsage(cpu_percent=99.0)
        report = reporter.build_report("my-job", usage)
        assert not report.any_exceeded
