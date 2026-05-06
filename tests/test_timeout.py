"""Tests for cronwrap.timeout module."""

import time
import pytest

from cronwrap.timeout import TimeoutConfig, TimeoutError, TimeoutGuard


class TestTimeoutConfig:
    def test_default_disabled(self):
        cfg = TimeoutConfig()
        assert cfg.seconds == 0
        assert not cfg.enabled

    def test_enabled_when_seconds_positive(self):
        cfg = TimeoutConfig(seconds=30)
        assert cfg.enabled

    def test_negative_seconds_raises(self):
        with pytest.raises(ValueError, match=">= 0"):
            TimeoutConfig(seconds=-1)

    def test_zero_is_disabled(self):
        cfg = TimeoutConfig(seconds=0)
        assert not cfg.enabled

    def test_repr_disabled(self):
        assert "disabled" in repr(TimeoutConfig())

    def test_repr_enabled(self):
        r = repr(TimeoutConfig(seconds=10))
        assert "10" in r
        assert "TimeoutConfig" in r


class TestTimeoutError:
    def test_message_contains_job_name(self):
        err = TimeoutError("my-job", 5)
        assert "my-job" in str(err)

    def test_message_contains_seconds(self):
        err = TimeoutError("my-job", 5)
        assert "5" in str(err)

    def test_attributes(self):
        err = TimeoutError("backup", 60)
        assert err.job_name == "backup"
        assert err.timeout_seconds == 60


class TestTimeoutGuard:
    def test_no_timeout_when_disabled(self):
        cfg = TimeoutConfig(seconds=0)
        with TimeoutGuard(cfg, "job"):
            time.sleep(0.01)  # should not raise

    def test_raises_on_timeout(self):
        cfg = TimeoutConfig(seconds=1)
        with pytest.raises(TimeoutError):
            with TimeoutGuard(cfg, "slow-job"):
                time.sleep(3)

    def test_no_raise_when_fast(self):
        cfg = TimeoutConfig(seconds=5)
        with TimeoutGuard(cfg, "fast-job"):
            pass  # completes instantly

    def test_alarm_cleared_after_exit(self):
        import signal
        cfg = TimeoutConfig(seconds=5)
        with TimeoutGuard(cfg, "job"):
            pass
        # alarm should be cancelled; remaining time should be 0
        remaining = signal.alarm(0)
        assert remaining == 0
