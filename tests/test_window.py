"""Tests for cronwrap.window and cronwrap.window_middleware."""
from __future__ import annotations

from datetime import time

import pytest

from cronwrap.window import (
    TimeWindow,
    WindowConfig,
    WindowGuard,
    WindowViolationError,
)
from cronwrap.window_middleware import WindowMiddleware


# ---------------------------------------------------------------------------
# TimeWindow
# ---------------------------------------------------------------------------

class TestTimeWindow:
    def test_valid_window(self):
        w = TimeWindow(start=time(9, 0), end=time(17, 0))
        assert w.start == time(9, 0)
        assert w.end == time(17, 0)

    def test_start_must_be_before_end(self):
        with pytest.raises(ValueError, match="earlier than end"):
            TimeWindow(start=time(17, 0), end=time(9, 0))

    def test_equal_start_end_raises(self):
        with pytest.raises(ValueError):
            TimeWindow(start=time(9, 0), end=time(9, 0))

    def test_contains_true_within(self):
        w = TimeWindow(start=time(9, 0), end=time(17, 0))
        assert w.contains(time(12, 0)) is True

    def test_contains_false_outside(self):
        w = TimeWindow(start=time(9, 0), end=time(17, 0))
        assert w.contains(time(18, 0)) is False

    def test_contains_boundary_start(self):
        w = TimeWindow(start=time(9, 0), end=time(17, 0))
        assert w.contains(time(9, 0)) is True

    def test_contains_boundary_end(self):
        w = TimeWindow(start=time(9, 0), end=time(17, 0))
        assert w.contains(time(17, 0)) is True


# ---------------------------------------------------------------------------
# WindowConfig
# ---------------------------------------------------------------------------

class TestWindowConfig:
    def test_defaults(self):
        cfg = WindowConfig()
        assert cfg.windows == []
        assert cfg.timezone == "UTC"
        assert cfg.enabled is True

    def test_custom_values(self):
        w = TimeWindow(start=time(8, 0), end=time(20, 0))
        cfg = WindowConfig(windows=[w], timezone="US/Eastern", enabled=False)
        assert len(cfg.windows) == 1
        assert cfg.timezone == "US/Eastern"
        assert cfg.enabled is False

    def test_blank_timezone_raises(self):
        with pytest.raises(ValueError, match="timezone"):
            WindowConfig(timezone="   ")

    def test_non_list_windows_raises(self):
        with pytest.raises(TypeError, match="list"):
            WindowConfig(windows="bad")

    def test_invalid_window_type_raises(self):
        with pytest.raises(TypeError, match="TimeWindow"):
            WindowConfig(windows=["not-a-window"])


# ---------------------------------------------------------------------------
# WindowGuard
# ---------------------------------------------------------------------------

class TestWindowGuard:
    def _guard(self, *windows):
        cfg = WindowConfig(windows=list(windows))
        return WindowGuard(cfg)

    def test_allowed_when_disabled(self):
        cfg = WindowConfig(enabled=False)
        guard = WindowGuard(cfg)
        assert guard.is_allowed(time(3, 0)) is True

    def test_allowed_when_no_windows(self):
        guard = self._guard()
        assert guard.is_allowed(time(3, 0)) is True

    def test_allowed_within_window(self):
        guard = self._guard(TimeWindow(time(9, 0), time(17, 0)))
        assert guard.is_allowed(time(12, 0)) is True

    def test_not_allowed_outside_window(self):
        guard = self._guard(TimeWindow(time(9, 0), time(17, 0)))
        assert guard.is_allowed(time(18, 0)) is False

    def test_enforce_raises_violation(self):
        guard = self._guard(TimeWindow(time(9, 0), time(17, 0)))
        with pytest.raises(WindowViolationError):
            guard.enforce("my-job", at=time(18, 0))

    def test_enforce_passes_within_window(self):
        guard = self._guard(TimeWindow(time(9, 0), time(17, 0)))
        guard.enforce("my-job", at=time(12, 0))  # should not raise

    def test_dry_run_returns_dict(self):
        guard = self._guard(TimeWindow(time(9, 0), time(17, 0)))
        result = guard.dry_run("my-job", at=time(12, 0))
        assert result["allowed"] is True
        assert result["job_name"] == "my-job"


# ---------------------------------------------------------------------------
# WindowMiddleware
# ---------------------------------------------------------------------------

class TestWindowMiddleware:
    def _mw(self, *windows, enabled=True):
        cfg = WindowConfig(windows=list(windows), enabled=enabled)
        return WindowMiddleware("test-job", cfg)

    def test_run_executes_fn_within_window(self):
        mw = self._mw(TimeWindow(time(9, 0), time(17, 0)))
        result = mw.run(lambda: 42, at=time(12, 0))
        assert result == 42

    def test_run_raises_outside_window(self):
        mw = self._mw(TimeWindow(time(9, 0), time(17, 0)))
        with pytest.raises(WindowViolationError):
            mw.run(lambda: 42, at=time(20, 0))

    def test_run_executes_when_disabled(self):
        mw = self._mw(TimeWindow(time(9, 0), time(17, 0)), enabled=False)
        result = mw.run(lambda: "ok", at=time(3, 0))
        assert result == "ok"

    def test_last_result_stored(self):
        mw = self._mw(TimeWindow(time(0, 0), time(23, 59)))
        mw.run(lambda: 99, at=time(12, 0))
        assert mw.last_result == 99

    def test_dry_run_returns_dict(self):
        mw = self._mw(TimeWindow(time(9, 0), time(17, 0)))
        info = mw.dry_run(at=time(12, 0))
        assert info["allowed"] is True
        assert "windows" in info
