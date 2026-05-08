"""Tests for cronwrap.throttle."""
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwrap.throttle import (
    JobThrottle,
    ThrottleConfig,
    ThrottleError,
)


# ---------------------------------------------------------------------------
# ThrottleConfig
# ---------------------------------------------------------------------------

class TestThrottleConfig:
    def test_defaults(self):
        cfg = ThrottleConfig()
        assert cfg.min_interval_seconds == 0
        assert cfg.state_dir == "/tmp/cronwrap/throttle"

    def test_custom_values(self):
        cfg = ThrottleConfig(min_interval_seconds=60, state_dir="/var/throttle")
        assert cfg.min_interval_seconds == 60
        assert cfg.state_dir == "/var/throttle"

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError, match="min_interval_seconds"):
            ThrottleConfig(min_interval_seconds=-1)

    def test_blank_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            ThrottleConfig(state_dir="   ")

    def test_enabled_when_positive(self):
        assert ThrottleConfig(min_interval_seconds=30).enabled is True

    def test_disabled_when_zero(self):
        assert ThrottleConfig(min_interval_seconds=0).enabled is False


# ---------------------------------------------------------------------------
# JobThrottle
# ---------------------------------------------------------------------------

@pytest.fixture()
def throttle(tmp_path):
    cfg = ThrottleConfig(min_interval_seconds=60, state_dir=str(tmp_path))
    return JobThrottle(cfg)


class TestJobThrottle:
    def test_check_passes_when_no_state(self, throttle):
        throttle.check("my-job")  # should not raise

    def test_check_passes_when_disabled(self, tmp_path):
        cfg = ThrottleConfig(min_interval_seconds=0, state_dir=str(tmp_path))
        jt = JobThrottle(cfg)
        jt.record("my-job")  # record a run
        jt.check("my-job")   # still should not raise

    def test_check_raises_when_too_soon(self, throttle):
        throttle.record("my-job")
        with pytest.raises(ThrottleError) as exc_info:
            throttle.check("my-job")
        assert "my-job" in str(exc_info.value)
        assert exc_info.value.job_name == "my-job"
        assert exc_info.value.seconds_remaining > 0

    def test_check_passes_after_interval(self, throttle):
        past = time.time() - 120  # 2 minutes ago
        throttle._write_last_run("my-job", past)
        throttle.check("my-job")  # should not raise

    def test_record_creates_state_file(self, throttle, tmp_path):
        throttle.record("my-job")
        state_file = tmp_path / "my-job.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "last_run" in data

    def test_reset_removes_state_file(self, throttle, tmp_path):
        throttle.record("my-job")
        throttle.reset("my-job")
        assert not (tmp_path / "my-job.json").exists()

    def test_reset_noop_when_no_state(self, throttle):
        throttle.reset("nonexistent-job")  # should not raise

    def test_state_file_name_sanitises_slashes(self, throttle, tmp_path):
        throttle.record("ns/my-job")
        assert (tmp_path / "ns_my-job.json").exists()

    def test_corrupt_state_file_treated_as_no_state(self, throttle, tmp_path):
        (tmp_path / "bad-job.json").write_text("{invalid}")
        throttle.check("bad-job")  # should not raise
