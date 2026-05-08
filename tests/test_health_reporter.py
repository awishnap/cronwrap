"""Tests for cronwrap.health_reporter."""
from datetime import datetime

import pytest

from cronwrap.health import HealthStatus
from cronwrap.health_reporter import HealthReport, HealthReporter, _status_to_dict


def _make_status(name: str, healthy: bool, streak: int = 0) -> HealthStatus:
    return HealthStatus(
        job_name=name,
        is_healthy=healthy,
        failure_streak=streak,
        last_run=datetime(2024, 1, 1, 12, 0),
        last_success=datetime(2024, 1, 1, 11, 0) if healthy else None,
        details="" if healthy else "failure streak 3 >= 3",
    )


class TestHealthReport:
    def test_all_healthy_true_when_no_failures(self):
        report = HealthReport([_make_status("a", True), _make_status("b", True)])
        assert report.all_healthy is True

    def test_all_healthy_false_when_any_unhealthy(self):
        report = HealthReport([_make_status("a", True), _make_status("b", False)])
        assert report.all_healthy is False

    def test_unhealthy_filters_correctly(self):
        report = HealthReport([_make_status("a", True), _make_status("b", False)])
        assert len(report.unhealthy) == 1
        assert report.unhealthy[0].job_name == "b"

    def test_summary_all_healthy(self):
        report = HealthReport([_make_status("a", True)])
        assert "healthy" in report.summary()
        assert "1" in report.summary()

    def test_summary_includes_unhealthy_names(self):
        report = HealthReport([_make_status("a", False), _make_status("b", True)])
        summary = report.summary()
        assert "a" in summary
        assert "1/2" in summary

    def test_to_dict_structure(self):
        report = HealthReport([_make_status("a", True)])
        d = report.to_dict()
        assert d["all_healthy"] is True
        assert d["total"] == 1
        assert d["unhealthy_count"] == 0
        assert len(d["jobs"]) == 1


class TestHealthReporter:
    def test_add_and_report(self):
        reporter = HealthReporter()
        reporter.add(_make_status("job1", True))
        reporter.add(_make_status("job2", False))
        report = reporter.report()
        assert len(report.statuses) == 2

    def test_clear_resets_statuses(self):
        reporter = HealthReporter()
        reporter.add(_make_status("job1", True))
        reporter.clear()
        report = reporter.report()
        assert len(report.statuses) == 0

    def test_report_is_snapshot(self):
        reporter = HealthReporter()
        reporter.add(_make_status("job1", True))
        report = reporter.report()
        reporter.add(_make_status("job2", False))
        assert len(report.statuses) == 1  # snapshot not affected by later add


class TestStatusToDict:
    def test_keys_present(self):
        d = _status_to_dict(_make_status("myjob", True))
        for key in ("job_name", "is_healthy", "failure_streak", "last_run", "last_success", "details"):
            assert key in d

    def test_none_last_success_serialises_to_none(self):
        d = _status_to_dict(_make_status("myjob", False))
        assert d["last_success"] is None

    def test_datetime_serialised_as_isoformat(self):
        d = _status_to_dict(_make_status("myjob", True))
        assert "2024-01-01" in d["last_run"]
