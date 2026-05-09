"""Tests for cronwrap.audit_query module."""
import pytest
from cronwrap.audit import AuditConfig, AuditEvent, AuditLog
from cronwrap.audit_query import AuditQuery


def _make_events():
    return [
        AuditEvent(job_name="j", event_type="success", exit_code=0, duration_seconds=1.0, timestamp="2024-01-01T00:00:00+00:00"),
        AuditEvent(job_name="j", event_type="failure", exit_code=1, duration_seconds=2.0, timestamp="2024-01-02T00:00:00+00:00"),
        AuditEvent(job_name="j", event_type="failure", exit_code=1, duration_seconds=3.0, timestamp="2024-01-03T00:00:00+00:00"),
    ]


class TestAuditQuery:
    def test_count(self):
        q = AuditQuery(_make_events())
        assert q.count() == 3

    def test_failures(self):
        q = AuditQuery(_make_events()).failures()
        assert q.count() == 2

    def test_successes(self):
        q = AuditQuery(_make_events()).successes()
        assert q.count() == 1

    def test_by_event_type(self):
        q = AuditQuery(_make_events()).by_event_type("failure")
        assert all(e.event_type == "failure" for e in q.all())

    def test_since_filters(self):
        q = AuditQuery(_make_events()).since("2024-01-02T00:00:00+00:00")
        assert q.count() == 2

    def test_where_predicate(self):
        q = AuditQuery(_make_events()).where(lambda e: e.duration_seconds and e.duration_seconds > 1.5)
        assert q.count() == 2

    def test_latest_returns_last_n(self):
        events = AuditQuery(_make_events()).latest(2)
        assert len(events) == 2
        assert events[-1].timestamp == "2024-01-03T00:00:00+00:00"

    def test_average_duration(self):
        avg = AuditQuery(_make_events()).average_duration()
        assert avg == pytest.approx(2.0)

    def test_average_duration_none_when_empty(self):
        assert AuditQuery([]).average_duration() is None

    def test_consecutive_failures_trailing(self):
        q = AuditQuery(_make_events())
        assert q.consecutive_failures() == 2

    def test_consecutive_failures_none(self):
        events = [AuditEvent(job_name="j", event_type="success")]
        assert AuditQuery(events).consecutive_failures() == 0

    def test_for_job_integration(self, tmp_path):
        cfg = AuditConfig(audit_dir=str(tmp_path))
        log = AuditLog(cfg)
        log.record(AuditEvent(job_name="myjob", event_type="success", exit_code=0))
        log.record(AuditEvent(job_name="myjob", event_type="failure", exit_code=1))
        q = AuditQuery.for_job(log, "myjob")
        assert q.count() == 2
        assert q.failures().count() == 1
