"""Tests for cronwrap.audit module."""
import pytest
from cronwrap.audit import AuditConfig, AuditEvent, AuditLog


class TestAuditConfig:
    def test_defaults(self):
        cfg = AuditConfig()
        assert cfg.audit_dir == "/var/log/cronwrap/audit"
        assert cfg.max_entries == 1000
        assert cfg.enabled is True

    def test_custom_values(self):
        cfg = AuditConfig(audit_dir="/tmp/audit", max_entries=50, enabled=False)
        assert cfg.audit_dir == "/tmp/audit"
        assert cfg.max_entries == 50
        assert cfg.enabled is False

    def test_zero_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            AuditConfig(max_entries=0)

    def test_negative_max_entries_raises(self):
        with pytest.raises(ValueError, match="max_entries"):
            AuditConfig(max_entries=-1)

    def test_blank_audit_dir_raises(self):
        with pytest.raises(ValueError, match="audit_dir"):
            AuditConfig(audit_dir="   ")


class TestAuditEvent:
    def test_to_dict_round_trip(self):
        ev = AuditEvent(
            job_name="myjob",
            event_type="success",
            exit_code=0,
            duration_seconds=1.5,
            attempt=1,
            message="ok",
        )
        d = ev.to_dict()
        restored = AuditEvent.from_dict(d)
        assert restored.job_name == "myjob"
        assert restored.event_type == "success"
        assert restored.exit_code == 0
        assert restored.duration_seconds == 1.5

    def test_default_timestamp_set(self):
        ev = AuditEvent(job_name="j", event_type="start")
        assert ev.timestamp != ""

    def test_from_dict_missing_optional_fields(self):
        ev = AuditEvent.from_dict({"job_name": "j", "event_type": "retry"})
        assert ev.exit_code is None
        assert ev.duration_seconds is None
        assert ev.attempt == 1


class TestAuditLog:
    def test_record_and_retrieve(self, tmp_path):
        cfg = AuditConfig(audit_dir=str(tmp_path))
        log = AuditLog(cfg)
        ev = AuditEvent(job_name="job1", event_type="success", exit_code=0)
        log.record(ev)
        events = log.get_events("job1")
        assert len(events) == 1
        assert events[0].event_type == "success"

    def test_disabled_does_not_write(self, tmp_path):
        cfg = AuditConfig(audit_dir=str(tmp_path), enabled=False)
        log = AuditLog(cfg)
        log.record(AuditEvent(job_name="job1", event_type="success"))
        assert log.get_events("job1") == []

    def test_max_entries_trimmed(self, tmp_path):
        cfg = AuditConfig(audit_dir=str(tmp_path), max_entries=3)
        log = AuditLog(cfg)
        for i in range(5):
            log.record(AuditEvent(job_name="job1", event_type="success", attempt=i))
        events = log.get_events("job1")
        assert len(events) == 3

    def test_empty_job_returns_empty_list(self, tmp_path):
        cfg = AuditConfig(audit_dir=str(tmp_path))
        log = AuditLog(cfg)
        assert log.get_events("nonexistent") == []

    def test_multiple_jobs_isolated(self, tmp_path):
        cfg = AuditConfig(audit_dir=str(tmp_path))
        log = AuditLog(cfg)
        log.record(AuditEvent(job_name="job_a", event_type="success"))
        log.record(AuditEvent(job_name="job_b", event_type="failure"))
        assert len(log.get_events("job_a")) == 1
        assert len(log.get_events("job_b")) == 1
        assert log.get_events("job_a")[0].event_type == "success"
