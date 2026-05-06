"""Tests for cronwrap.lock module."""

import os
import time
from pathlib import Path

import pytest

from cronwrap.lock import JobLock, LockAcquisitionError, LockConfig


class TestLockConfig:
    def test_defaults(self):
        cfg = LockConfig()
        assert cfg.lock_dir == "/tmp/cronwrap/locks"
        assert cfg.stale_after_seconds == 3600

    def test_custom_values(self):
        cfg = LockConfig(lock_dir="/var/lock", stale_after_seconds=300)
        assert cfg.lock_dir == "/var/lock"
        assert cfg.stale_after_seconds == 300

    def test_negative_stale_raises(self):
        with pytest.raises(ValueError, match="stale_after_seconds"):
            LockConfig(stale_after_seconds=-1)

    def test_zero_stale_allowed(self):
        cfg = LockConfig(stale_after_seconds=0)
        assert cfg.stale_after_seconds == 0


class TestJobLock:
    def _make_lock(self, tmp_path, job_name="test_job", stale=3600):
        cfg = LockConfig(lock_dir=str(tmp_path), stale_after_seconds=stale)
        return JobLock(job_name, cfg)

    def test_acquire_creates_lock_file(self, tmp_path):
        lock = self._make_lock(tmp_path)
        lock.acquire()
        assert Path(lock.lock_path).exists()
        lock.release()

    def test_lock_file_contains_pid(self, tmp_path):
        lock = self._make_lock(tmp_path)
        lock.acquire()
        content = Path(lock.lock_path).read_text()
        assert content == str(os.getpid())
        lock.release()

    def test_release_removes_lock_file(self, tmp_path):
        lock = self._make_lock(tmp_path)
        lock.acquire()
        lock.release()
        assert not Path(lock.lock_path).exists()

    def test_double_acquire_raises(self, tmp_path):
        lock1 = self._make_lock(tmp_path)
        lock2 = self._make_lock(tmp_path)
        lock1.acquire()
        with pytest.raises(LockAcquisitionError) as exc_info:
            lock2.acquire()
        assert "test_job" in str(exc_info.value)
        lock1.release()

    def test_context_manager_acquires_and_releases(self, tmp_path):
        lock = self._make_lock(tmp_path)
        with lock:
            assert Path(lock.lock_path).exists()
        assert not Path(lock.lock_path).exists()

    def test_context_manager_releases_on_exception(self, tmp_path):
        lock = self._make_lock(tmp_path)
        with pytest.raises(RuntimeError):
            with lock:
                raise RuntimeError("boom")
        assert not Path(lock.lock_path).exists()

    def test_stale_lock_is_replaced(self, tmp_path):
        lock = self._make_lock(tmp_path, stale=1)
        lock.acquire()
        lock_path = Path(lock.lock_path)
        # Backdate the file to make it stale
        old_time = time.time() - 10
        os.utime(lock_path, (old_time, old_time))

        new_lock = self._make_lock(tmp_path, stale=1)
        new_lock.acquire()  # should not raise
        assert lock_path.exists()
        new_lock.release()

    def test_repr(self, tmp_path):
        lock = self._make_lock(tmp_path)
        r = repr(lock)
        assert "test_job" in r
        assert "acquired=False" in r
