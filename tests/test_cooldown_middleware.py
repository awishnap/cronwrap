"""Tests for cronwrap.cooldown_middleware."""
from __future__ import annotations

import time

import pytest

from cronwrap.cooldown import CooldownConfig, CooldownError
from cronwrap.cooldown_middleware import CooldownMiddleware


@pytest.fixture()
def mw(tmp_path):
    cfg = CooldownConfig(seconds=60, state_dir=str(tmp_path / "cd"))
    return CooldownMiddleware("test_job", cfg)


@pytest.fixture()
def mw_disabled(tmp_path):
    cfg = CooldownConfig(seconds=0, state_dir=str(tmp_path / "cd"))
    return CooldownMiddleware("test_job", cfg)


class TestCooldownMiddleware:
    def test_run_executes_fn(self, mw):
        called = []
        mw.run(lambda: called.append(1))
        assert called == [1]

    def test_run_returns_fn_result(self, mw):
        assert mw.run(lambda: 42) == 42

    def test_run_records_state(self, mw, tmp_path):
        mw.run(lambda: None)
        # Second call must raise CooldownError
        with pytest.raises(CooldownError):
            mw.run(lambda: None)

    def test_run_records_even_on_exception(self, mw):
        with pytest.raises(RuntimeError):
            mw.run(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        # Cooldown must still be active
        with pytest.raises(CooldownError):
            mw.run(lambda: None)

    def test_disabled_allows_repeated_runs(self, mw_disabled):
        mw_disabled.run(lambda: None)
        mw_disabled.run(lambda: None)  # must not raise

    def test_dry_run_no_cooldown(self, mw):
        info = mw.dry_run()
        assert info["in_cooldown"] is False
        assert info["remaining_seconds"] == 0.0
        assert info["job_name"] == "test_job"

    def test_dry_run_in_cooldown(self, mw):
        mw.run(lambda: None)
        info = mw.dry_run()
        assert info["in_cooldown"] is True
        assert info["remaining_seconds"] > 0

    def test_reset_allows_immediate_rerun(self, mw):
        mw.run(lambda: None)
        mw.reset()
        mw.run(lambda: None)  # must not raise
