"""Tests for cronwrap.cooldown."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.cooldown import CooldownConfig, CooldownError, CooldownManager


# ---------------------------------------------------------------------------
# CooldownConfig
# ---------------------------------------------------------------------------

class TestCooldownConfig:
    def test_defaults(self):
        cfg = CooldownConfig()
        assert cfg.seconds == 0
        assert cfg.state_dir == "/tmp/cronwrap/cooldown"

    def test_custom_values(self):
        cfg = CooldownConfig(seconds=120, state_dir="/tmp/cd")
        assert cfg.seconds == 120
        assert cfg.state_dir == "/tmp/cd"

    def test_negative_seconds_raises(self):
        with pytest.raises(ValueError, match="seconds"):
            CooldownConfig(seconds=-1)

    def test_blank_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            CooldownConfig(state_dir="   ")

    def test_disabled_when_zero(self):
        assert not CooldownConfig(seconds=0).enabled

    def test_enabled_when_positive(self):
        assert CooldownConfig(seconds=60).enabled


# ---------------------------------------------------------------------------
# CooldownManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager(tmp_path):
    cfg = CooldownConfig(seconds=60, state_dir=str(tmp_path / "cd"))
    return CooldownManager(cfg)


class TestCooldownManager:
    def test_check_passes_when_no_prior_run(self, manager):
        # Should not raise — no state file exists yet
        manager.check("job_a")

    def test_check_raises_immediately_after_record(self, manager):
        manager.record("job_b")
        with pytest.raises(CooldownError) as exc_info:
            manager.check("job_b")
        assert "job_b" in str(exc_info.value)
        assert exc_info.value.remaining > 0

    def test_check_passes_after_cooldown_elapsed(self, manager):
        past = time.time() - 120  # 120 s ago — beyond 60 s window
        state_file = manager._state_file("job_c")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(past))
        manager.check("job_c")  # should not raise

    def test_remaining_zero_when_disabled(self, tmp_path):
        cfg = CooldownConfig(seconds=0, state_dir=str(tmp_path))
        m = CooldownManager(cfg)
        assert m.remaining("job") == 0.0

    def test_remaining_positive_in_window(self, manager):
        manager.record("job_d")
        assert manager.remaining("job_d") > 0

    def test_reset_clears_state(self, manager):
        manager.record("job_e")
        manager.reset("job_e")
        # After reset, check should pass
        manager.check("job_e")

    def test_reset_no_op_when_no_state(self, manager):
        manager.reset("nonexistent")  # must not raise

    def test_record_creates_state_dir(self, tmp_path):
        state_dir = tmp_path / "new" / "nested"
        cfg = CooldownConfig(seconds=30, state_dir=str(state_dir))
        m = CooldownManager(cfg)
        m.record("job_f")
        assert state_dir.exists()
