"""Tests for cronwrap.concurrency."""
from __future__ import annotations

import threading
import pytest

from cronwrap.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimitError,
    ConcurrencyManager,
)


# ---------------------------------------------------------------------------
# ConcurrencyConfig
# ---------------------------------------------------------------------------

class TestConcurrencyConfig:
    def test_defaults(self):
        cfg = ConcurrencyConfig()
        assert cfg.max_parallel == 1
        assert cfg.enabled is True

    def test_custom_values(self):
        cfg = ConcurrencyConfig(max_parallel=4, enabled=False)
        assert cfg.max_parallel == 4
        assert cfg.enabled is False

    def test_zero_max_parallel_raises(self):
        with pytest.raises(ValueError, match="max_parallel"):
            ConcurrencyConfig(max_parallel=0)

    def test_negative_max_parallel_raises(self):
        with pytest.raises(ValueError, match="max_parallel"):
            ConcurrencyConfig(max_parallel=-1)


# ---------------------------------------------------------------------------
# ConcurrencyManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager():
    return ConcurrencyManager()


class TestConcurrencyManager:
    def test_acquire_and_release(self, manager):
        manager.register("job", ConcurrencyConfig(max_parallel=1))
        assert manager.acquire("job") is True
        manager.release("job")

    def test_exceeding_limit_raises(self, manager):
        manager.register("job", ConcurrencyConfig(max_parallel=1))
        manager.acquire("job")  # takes the only slot
        with pytest.raises(ConcurrencyLimitError) as exc_info:
            manager.acquire("job")
        assert exc_info.value.job_name == "job"
        assert exc_info.value.limit == 1
        manager.release("job")

    def test_multiple_slots(self, manager):
        manager.register("job", ConcurrencyConfig(max_parallel=3))
        for _ in range(3):
            manager.acquire("job")
        with pytest.raises(ConcurrencyLimitError):
            manager.acquire("job")
        for _ in range(3):
            manager.release("job")

    def test_disabled_config_always_acquires(self, manager):
        manager.register("job", ConcurrencyConfig(max_parallel=1, enabled=False))
        # Should not raise even if called many times
        for _ in range(5):
            assert manager.acquire("job") is True

    def test_unregistered_job_acquires(self, manager):
        assert manager.acquire("unknown") is True

    def test_available_slots_decrements(self, manager):
        manager.register("job", ConcurrencyConfig(max_parallel=2))
        assert manager.available_slots("job") == 2
        manager.acquire("job")
        assert manager.available_slots("job") == 1
        manager.release("job")
        assert manager.available_slots("job") == 2

    def test_available_slots_unregistered_returns_minus_one(self, manager):
        assert manager.available_slots("ghost") == -1

    def test_thread_safety(self, manager):
        """Only max_parallel threads should succeed concurrently."""
        manager.register("job", ConcurrencyConfig(max_parallel=2))
        errors = []
        acquired_count = [0]
        lock = threading.Lock()

        def try_acquire():
            try:
                manager.acquire("job")
                with lock:
                    acquired_count[0] += 1
            except ConcurrencyLimitError:
                with lock:
                    errors.append(1)

        threads = [threading.Thread(target=try_acquire) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert acquired_count[0] == 2
        assert len(errors) == 3
