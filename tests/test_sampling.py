"""Tests for cronwrap.sampling."""
import pytest

from cronwrap.sampling import SamplingConfig, SamplingError, SamplingMiddleware


# ---------------------------------------------------------------------------
# SamplingConfig
# ---------------------------------------------------------------------------

class TestSamplingConfig:
    def test_defaults(self):
        cfg = SamplingConfig()
        assert cfg.rate == 1.0
        assert cfg.seed is None

    def test_custom_values(self):
        cfg = SamplingConfig(rate=0.25, seed=42)
        assert cfg.rate == 0.25
        assert cfg.seed == 42

    def test_rate_zero_allowed(self):
        cfg = SamplingConfig(rate=0.0)
        assert cfg.rate == 0.0

    def test_rate_one_allowed(self):
        cfg = SamplingConfig(rate=1.0)
        assert cfg.rate == 1.0

    def test_rate_above_one_raises(self):
        with pytest.raises(ValueError, match="rate must be between"):
            SamplingConfig(rate=1.1)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate must be between"):
            SamplingConfig(rate=-0.1)

    def test_enabled_when_below_one(self):
        assert SamplingConfig(rate=0.5).enabled is True

    def test_disabled_when_one(self):
        assert SamplingConfig(rate=1.0).enabled is False


# ---------------------------------------------------------------------------
# SamplingMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture
def mw():
    return SamplingMiddleware(SamplingConfig(rate=0.5, seed=0))


@pytest.fixture
def mw_always():
    return SamplingMiddleware(SamplingConfig(rate=1.0))


class TestSamplingMiddleware:
    def test_always_runs_when_rate_one(self, mw_always):
        calls = []
        mw_always.run(calls.append, 1)
        assert calls == [1]
        assert mw_always.last_skipped is False

    def test_never_runs_when_rate_zero(self):
        mw = SamplingMiddleware(SamplingConfig(rate=0.0))
        calls = []
        mw.run(calls.append, 1)
        assert calls == []
        assert mw.last_skipped is True

    def test_returns_none_when_skipped(self):
        mw = SamplingMiddleware(SamplingConfig(rate=0.0))
        result = mw.run(lambda: 42)
        assert result is None

    def test_returns_fn_result_when_executed(self, mw_always):
        result = mw_always.run(lambda: 99)
        assert result == 99

    def test_seed_makes_deterministic(self):
        results_a = []
        results_b = []
        for _ in range(20):
            m = SamplingMiddleware(SamplingConfig(rate=0.5, seed=7))
            results_a.append(m.run(lambda: True))
        for _ in range(20):
            m = SamplingMiddleware(SamplingConfig(rate=0.5, seed=7))
            results_b.append(m.run(lambda: True))
        assert results_a == results_b

    def test_dry_run_returns_dict(self, mw):
        info = mw.dry_run()
        assert info["rate"] == 0.5
        assert info["enabled"] is True
        assert info["seed"] == 0

    def test_last_skipped_initial_false(self, mw_always):
        assert mw_always.last_skipped is False
