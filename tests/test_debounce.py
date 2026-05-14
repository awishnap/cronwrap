"""Tests for cronwrap.debounce and cronwrap.debounce_middleware."""

from __future__ import annotations

import time
import pytest
from unittest.mock import patch, MagicMock

from cronwrap.debounce import DebounceConfig, Debouncer, DebounceError
from cronwrap.debounce_middleware import DebounceMiddleware


# ---------------------------------------------------------------------------
# DebounceConfig
# ---------------------------------------------------------------------------

class TestDebounceConfig:
    def test_defaults(self):
        cfg = DebounceConfig()
        assert cfg.cooldown_seconds == 0
        assert cfg.state_dir == "/tmp/cronwrap/debounce"

    def test_custom_values(self):
        cfg = DebounceConfig(cooldown_seconds=30, state_dir="/var/run/cw")
        assert cfg.cooldown_seconds == 30
        assert cfg.state_dir == "/var/run/cw"

    def test_disabled_when_zero(self):
        assert not DebounceConfig(cooldown_seconds=0).enabled

    def test_enabled_when_positive(self):
        assert DebounceConfig(cooldown_seconds=5).enabled

    def test_negative_cooldown_raises(self):
        with pytest.raises(ValueError, match="cooldown_seconds"):
            DebounceConfig(cooldown_seconds=-1)

    def test_blank_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            DebounceConfig(cooldown_seconds=10, state_dir="   ")


# ---------------------------------------------------------------------------
# Debouncer
# ---------------------------------------------------------------------------

class TestDebouncer:
    def _debouncer(self, tmp_path, cooldown=10):
        cfg = DebounceConfig(cooldown_seconds=cooldown, state_dir=str(tmp_path))
        return Debouncer(cfg)

    def test_check_passes_when_no_state(self, tmp_path):
        d = self._debouncer(tmp_path)
        d.check("my-job")  # should not raise

    def test_check_passes_when_disabled(self, tmp_path):
        d = self._debouncer(tmp_path, cooldown=0)
        d.record("my-job")  # record does nothing when disabled
        d.check("my-job")  # should not raise

    def test_check_raises_within_cooldown(self, tmp_path):
        d = self._debouncer(tmp_path, cooldown=60)
        # Manually write a very recent timestamp
        d._state_dir.mkdir(parents=True, exist_ok=True)
        d._state_file("job").write_text(str(time.monotonic()))
        with pytest.raises(DebounceError) as exc_info:
            d.check("job")
        assert exc_info.value.job_name == "job"
        assert exc_info.value.remaining > 0

    def test_check_passes_after_cooldown(self, tmp_path):
        d = self._debouncer(tmp_path, cooldown=1)
        d._state_dir.mkdir(parents=True, exist_ok=True)
        # Write a timestamp far in the past
        d._state_file("job").write_text(str(time.monotonic() - 100))
        d.check("job")  # should not raise

    def test_reset_clears_state(self, tmp_path):
        d = self._debouncer(tmp_path, cooldown=60)
        d._state_dir.mkdir(parents=True, exist_ok=True)
        d._state_file("job").write_text(str(time.monotonic()))
        d.reset("job")
        assert d._last_run("job") is None


# ---------------------------------------------------------------------------
# DebounceMiddleware
# ---------------------------------------------------------------------------

class TestDebounceMiddleware:
    def _mw(self, tmp_path, cooldown=60):
        cfg = DebounceConfig(cooldown_seconds=cooldown, state_dir=str(tmp_path))
        return DebounceMiddleware("test-job", cfg)

    def test_run_calls_func(self, tmp_path):
        mw = self._mw(tmp_path)
        result = mw.run(lambda: 42)
        assert result == 42

    def test_run_blocked_within_cooldown(self, tmp_path):
        mw = self._mw(tmp_path)
        mw._debouncer._state_dir.mkdir(parents=True, exist_ok=True)
        mw._debouncer._state_file("test-job").write_text(str(time.monotonic()))
        with pytest.raises(DebounceError):
            mw.run(lambda: None)

    def test_dry_run_not_blocked_initially(self, tmp_path):
        mw = self._mw(tmp_path)
        info = mw.dry_run()
        assert info["blocked"] is False
        assert info["remaining_seconds"] == 0.0

    def test_reset_unblocks(self, tmp_path):
        mw = self._mw(tmp_path)
        mw._debouncer._state_dir.mkdir(parents=True, exist_ok=True)
        mw._debouncer._state_file("test-job").write_text(str(time.monotonic()))
        mw.reset()
        info = mw.dry_run()
        assert info["blocked"] is False
