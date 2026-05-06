"""Tests for cronwrap.history."""

import json
import pytest
from pathlib import Path
from cronwrap.history import HistoryEntry, JobHistory


JOB_NAME = "backup-db"


def _entry(**kwargs) -> HistoryEntry:
    defaults = dict(
        job_name=JOB_NAME,
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:01:00",
        exit_code=0,
        timed_out=False,
        duration_seconds=60.0,
        command="pg_dump mydb",
    )
    defaults.update(kwargs)
    return HistoryEntry(**defaults)


@pytest.fixture()
def history(tmp_path):
    return JobHistory(storage_dir=str(tmp_path))


class TestHistoryEntry:
    def test_succeeded_on_zero_exit(self):
        assert _entry(exit_code=0).succeeded is True

    def test_failed_on_nonzero_exit(self):
        assert _entry(exit_code=1).succeeded is False

    def test_timed_out_not_succeeded(self):
        assert _entry(exit_code=0, timed_out=True).succeeded is False

    def test_from_dict_roundtrip(self):
        e = _entry()
        restored = HistoryEntry.from_dict(
            {"job_name": e.job_name, "started_at": e.started_at,
             "finished_at": e.finished_at, "exit_code": e.exit_code,
             "timed_out": e.timed_out, "duration_seconds": e.duration_seconds,
             "command": e.command}
        )
        assert restored == e


class TestJobHistory:
    def test_load_empty_when_no_file(self, history):
        assert history.load(JOB_NAME) == []

    def test_last_none_when_no_history(self, history):
        assert history.last(JOB_NAME) is None

    def test_record_and_load(self, history):
        e = _entry()
        history.record(e)
        entries = history.load(JOB_NAME)
        assert len(entries) == 1
        assert entries[0] == e

    def test_last_returns_most_recent(self, history):
        e1 = _entry(started_at="2024-01-01T00:00:00")
        e2 = _entry(started_at="2024-01-02T00:00:00")
        history.record(e1)
        history.record(e2)
        assert history.last(JOB_NAME).started_at == "2024-01-02T00:00:00"

    def test_max_entries_enforced(self, tmp_path):
        h = JobHistory(storage_dir=str(tmp_path), max_entries=3)
        for i in range(5):
            h.record(_entry(started_at=f"2024-01-0{i+1}T00:00:00"))
        assert len(h.load(JOB_NAME)) == 3

    def test_oldest_entries_pruned(self, tmp_path):
        h = JobHistory(storage_dir=str(tmp_path), max_entries=2)
        for i in range(4):
            h.record(_entry(started_at=f"2024-01-0{i+1}T00:00:00"))
        entries = h.load(JOB_NAME)
        assert entries[0].started_at == "2024-01-03T00:00:00"

    def test_clear_removes_file(self, history, tmp_path):
        history.record(_entry())
        history.clear(JOB_NAME)
        assert history.load(JOB_NAME) == []

    def test_invalid_max_entries_raises(self, tmp_path):
        with pytest.raises(ValueError):
            JobHistory(storage_dir=str(tmp_path), max_entries=0)

    def test_job_name_with_slashes(self, history):
        e = _entry(job_name="jobs/backup/db")
        history.record(e)
        assert history.last("jobs/backup/db").job_name == "jobs/backup/db"
