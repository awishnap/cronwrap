"""Tests for cronwrap.jitter."""

import pytest

from cronwrap.jitter import JitterConfig, JitterError, JitterManager


# ---------------------------------------------------------------------------
# JitterConfig
# ---------------------------------------------------------------------------

class TestJitterConfig:
    def test_defaults(self):
        cfg = JitterConfig()
        assert cfg.max_seconds == 0.0
        assert cfg.strategy == "uniform"
        assert cfg.seed is None

    def test_custom_values(self):
        cfg = JitterConfig(max_seconds=5.0, strategy="gaussian", seed=42)
        assert cfg.max_seconds == 5.0
        assert cfg.strategy == "gaussian"
        assert cfg.seed == 42

    def test_negative_max_seconds_raises(self):
        with pytest.raises(ValueError, match="max_seconds"):
            JitterConfig(max_seconds=-1)

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="strategy"):
            JitterConfig(max_seconds=1.0, strategy="exponential")

    def test_disabled_when_zero(self):
        assert not JitterConfig(max_seconds=0).enabled

    def test_enabled_when_positive(self):
        assert JitterConfig(max_seconds=0.1).enabled


# ---------------------------------------------------------------------------
# JitterManager
# ---------------------------------------------------------------------------

class TestJitterManager:
    def _manager(self, **kwargs):
        slept = []
        cfg = JitterConfig(**kwargs)
        mgr = JitterManager(cfg, sleep_fn=slept.append)
        return mgr, slept

    def test_delay_zero_when_disabled(self):
        mgr, _ = self._manager(max_seconds=0)
        assert mgr.delay() == 0.0

    def test_delay_within_range_uniform(self):
        mgr, _ = self._manager(max_seconds=2.0, strategy="uniform", seed=0)
        for _ in range(20):
            d = mgr.delay()
            assert 0.0 <= d <= 2.0

    def test_delay_within_range_gaussian(self):
        mgr, _ = self._manager(max_seconds=3.0, strategy="gaussian", seed=7)
        for _ in range(20):
            d = mgr.delay()
            assert 0.0 <= d <= 3.0

    def test_run_calls_fn(self):
        mgr, slept = self._manager(max_seconds=0)
        result = mgr.run(lambda: "ok")
        assert result == "ok"
        assert slept == []

    def test_run_sleeps_when_enabled(self):
        mgr, slept = self._manager(max_seconds=1.0, seed=1)
        mgr.run(lambda: None)
        assert len(slept) == 1
        assert 0.0 <= slept[0] <= 1.0

    def test_dry_run_no_sleep(self):
        slept = []
        cfg = JitterConfig(max_seconds=5.0, seed=99)
        mgr = JitterManager(cfg, sleep_fn=slept.append)
        delay = mgr.dry_run()
        assert isinstance(delay, float)
        assert slept == []

    def test_seed_produces_reproducible_delays(self):
        def _delays(seed):
            cfg = JitterConfig(max_seconds=10.0, seed=seed)
            mgr = JitterManager(cfg)
            return [mgr.delay() for _ in range(5)]

        assert _delays(42) == _delays(42)
        assert _delays(42) != _delays(43)
