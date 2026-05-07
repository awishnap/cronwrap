"""Tests for cronwrap.alert_formatter module."""
import pytest
from cronwrap.alert_formatter import AlertFormatter, AlertPayload


def _payload(**kwargs) -> AlertPayload:
    defaults = dict(
        job_name="backup",
        messages=["[ALERT] Job 'backup' failed with exit code 1 (1 consecutive failure(s))."],
        exit_code=1,
        duration_seconds=3.5,
    )
    defaults.update(kwargs)
    return AlertFormatter.format(**defaults)


class TestAlertPayload:
    def test_subject_contains_job_name(self):
        p = _payload()
        assert "backup" in p.subject
        assert "cronwrap" in p.subject

    def test_as_text_contains_exit_code(self):
        p = _payload(exit_code=2)
        text = p.as_text()
        assert "Exit code: 2" in text

    def test_as_text_contains_duration(self):
        p = _payload(duration_seconds=7.123)
        text = p.as_text()
        assert "7.12" in text

    def test_as_text_lists_all_messages(self):
        msgs = ["alert one", "alert two"]
        p = _payload(messages=msgs)
        text = p.as_text()
        assert "alert one" in text
        assert "alert two" in text

    def test_as_dict_keys(self):
        p = _payload()
        d = p.as_dict()
        assert set(d.keys()) == {"job_name", "exit_code", "duration_seconds", "alerts"}

    def test_as_dict_values(self):
        p = _payload(job_name="sync", exit_code=3, duration_seconds=1.0)
        d = p.as_dict()
        assert d["job_name"] == "sync"
        assert d["exit_code"] == 3
        assert d["duration_seconds"] == 1.0


class TestAlertFormatter:
    def test_returns_alert_payload(self):
        payload = AlertFormatter.format(
            job_name="job",
            messages=["some alert"],
            exit_code=1,
            duration_seconds=2.0,
        )
        assert isinstance(payload, AlertPayload)

    def test_empty_messages_raises(self):
        with pytest.raises(ValueError, match="empty"):
            AlertFormatter.format(
                job_name="job",
                messages=[],
                exit_code=1,
                duration_seconds=1.0,
            )

    def test_multiple_messages_preserved(self):
        msgs = ["msg1", "msg2", "msg3"]
        payload = AlertFormatter.format(
            job_name="job",
            messages=msgs,
            exit_code=1,
            duration_seconds=1.0,
        )
        assert payload.messages == msgs
