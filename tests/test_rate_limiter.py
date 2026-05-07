"""Tests for cronwrap.rate_limiter."""
import pytest

from cronwrap.rate_limiter import (
    RateLimitConfig,
    RateLimitExceededError,
    RateLimiter,
)


class TestRateLimitConfig:
    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.max_runs == 0
        assert cfg.window_seconds == 3600
        assert cfg.enabled is False

    def test_custom_values(self):
        cfg = RateLimitConfig(max_runs=5, window_seconds=60)
        assert cfg.max_runs == 5
        assert cfg.window_seconds == 60
        assert cfg.enabled is True

    def test_negative_max_runs_raises(self):
        with pytest.raises(ValueError, match="max_runs"):
            RateLimitConfig(max_runs=-1)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(max_runs=1, window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitConfig(max_runs=1, window_seconds=-10)


class TestRateLimiter:
    def _limiter(self, max_runs=3, window_seconds=60):
        cfg = RateLimitConfig(max_runs=max_runs, window_seconds=window_seconds)
        return RateLimiter(job_name="test-job", config=cfg)

    def test_check_passes_when_disabled(self):
        limiter = RateLimiter("job", RateLimitConfig(max_runs=0))
        # Should not raise regardless of how many times called
        for _ in range(100):
            limiter.check(now=0.0)

    def test_check_passes_under_limit(self):
        limiter = self._limiter(max_runs=3)
        now = 0.0
        for i in range(3):
            limiter.record(now=now + i)
        # Still one slot left — check at run 2 (index 2)
        limiter2 = self._limiter(max_runs=3)
        limiter2.record(now=0.0)
        limiter2.record(now=1.0)
        limiter2.check(now=2.0)  # 2 recorded, limit is 3 — OK

    def test_check_raises_at_limit(self):
        limiter = self._limiter(max_runs=2)
        limiter.record(now=0.0)
        limiter.record(now=1.0)
        with pytest.raises(RateLimitExceededError) as exc_info:
            limiter.check(now=2.0)
        assert "test-job" in str(exc_info.value)
        assert exc_info.value.max_runs == 2

    def test_old_records_pruned(self):
        limiter = self._limiter(max_runs=2, window_seconds=10)
        # Record two runs at t=0
        limiter.record(now=0.0)
        limiter.record(now=1.0)
        # At t=15, both are outside the 10s window
        limiter.check(now=15.0)  # should not raise

    def test_run_count_reflects_window(self):
        limiter = self._limiter(max_runs=5, window_seconds=10)
        limiter.record(now=0.0)
        limiter.record(now=5.0)
        # Manually prune by calling run_count via check at t=12
        limiter.check(now=12.0)  # t=0 is pruned, t=5 remains

    def test_record_increments_count(self):
        limiter = self._limiter(max_runs=10, window_seconds=3600)
        assert limiter.run_count == 0
        limiter.record()
        limiter.record()
        assert limiter.run_count == 2


class TestRateLimitExceededError:
    def test_message_contains_details(self):
        err = RateLimitExceededError("my-job", 5, 300)
        assert "my-job" in str(err)
        assert "5" in str(err)
        assert "300" in str(err)

    def test_attributes(self):
        err = RateLimitExceededError("j", 3, 60)
        assert err.job_name == "j"
        assert err.max_runs == 3
        assert err.window_seconds == 60
