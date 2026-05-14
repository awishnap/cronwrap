"""Tests for cronwrap.deadline and cronwrap.deadline_middleware."""
from __future__ import annotations

import time

import pytest

from cronwrap.deadline import (
    DeadlineConfig,
    DeadlineExceededError,
    DeadlineTracker,
)
from cronwrap.deadline_middleware import DeadlineMiddleware


# ---------------------------------------------------------------------------
# DeadlineConfig
# ---------------------------------------------------------------------------

class TestDeadlineConfig:
    def test_defaults(self):
        cfg = DeadlineConfig()
        assert cfg.max_runtime_seconds == 0
        assert cfg.strict is True
        assert cfg.enabled is False

    def test_custom_values(self):
        cfg = DeadlineConfig(max_runtime_seconds=120, strict=False)
        assert cfg.max_runtime_seconds == 120
        assert cfg.strict is False
        assert cfg.enabled is True

    def test_negative_max_raises(self):
        with pytest.raises(ValueError, match="max_runtime_seconds"):
            DeadlineConfig(max_runtime_seconds=-1)

    def test_zero_is_disabled(self):
        cfg = DeadlineConfig(max_runtime_seconds=0)
        assert cfg.enabled is False

    def test_invalid_strict_raises(self):
        with pytest.raises(TypeError, match="strict"):
            DeadlineConfig(strict="yes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DeadlineTracker
# ---------------------------------------------------------------------------

class TestDeadlineTracker:
    def test_elapsed_before_start_is_zero(self):
        tracker = DeadlineTracker("job", DeadlineConfig(max_runtime_seconds=10))
        assert tracker.elapsed_seconds() == 0.0

    def test_remaining_none_when_disabled(self):
        tracker = DeadlineTracker("job", DeadlineConfig())
        assert tracker.remaining_seconds() is None

    def test_remaining_positive_after_start(self):
        tracker = DeadlineTracker("job", DeadlineConfig(max_runtime_seconds=60))
        tracker.start()
        remaining = tracker.remaining_seconds()
        assert remaining is not None
        assert 0 < remaining <= 60

    def test_check_passes_within_deadline(self):
        tracker = DeadlineTracker("job", DeadlineConfig(max_runtime_seconds=60))
        tracker.start()
        tracker.check()  # should not raise

    def test_check_raises_when_strict_and_exceeded(self):
        cfg = DeadlineConfig(max_runtime_seconds=1, strict=True)
        tracker = DeadlineTracker("myjob", cfg)
        tracker.start()
        time.sleep(1.05)
        with pytest.raises(DeadlineExceededError, match="myjob"):
            tracker.check()

    def test_check_sets_breached_when_not_strict(self):
        cfg = DeadlineConfig(max_runtime_seconds=1, strict=False)
        tracker = DeadlineTracker("job", cfg)
        tracker.start()
        time.sleep(1.05)
        tracker.check()  # must not raise
        assert tracker.breached is True

    def test_check_no_op_when_disabled(self):
        tracker = DeadlineTracker("job", DeadlineConfig())
        tracker.start()
        tracker.check()  # should never raise
        assert tracker.breached is False


# ---------------------------------------------------------------------------
# DeadlineMiddleware
# ---------------------------------------------------------------------------

class TestDeadlineMiddleware:
    def test_run_returns_exit_code(self):
        mw = DeadlineMiddleware("job", DeadlineConfig(max_runtime_seconds=10))
        assert mw.run(lambda: 0) == 0

    def test_run_raises_on_exceeded(self):
        cfg = DeadlineConfig(max_runtime_seconds=1, strict=True)
        mw = DeadlineMiddleware("job", cfg)
        with pytest.raises(DeadlineExceededError):
            mw.run(lambda: (time.sleep(1.05), 0)[1])

    def test_dry_run_returns_metadata(self):
        cfg = DeadlineConfig(max_runtime_seconds=30)
        mw = DeadlineMiddleware("myjob", cfg)
        info = mw.dry_run()
        assert info["job_name"] == "myjob"
        assert info["enabled"] is True
        assert info["max_runtime_seconds"] == 30
        assert info["strict"] is True

    def test_tracker_exposed(self):
        mw = DeadlineMiddleware("job", DeadlineConfig(max_runtime_seconds=10))
        assert isinstance(mw.tracker, DeadlineTracker)

    def test_default_config_used_when_none_provided(self):
        mw = DeadlineMiddleware("job")
        assert mw.dry_run()["enabled"] is False
