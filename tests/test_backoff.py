"""Tests for cronwrap.backoff."""
import pytest

from cronwrap.backoff import BackoffCalculator, BackoffConfig


class TestBackoffConfig:
    def test_defaults(self):
        cfg = BackoffConfig()
        assert cfg.strategy == "fixed"
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 300.0
        assert cfg.multiplier == 2.0
        assert cfg.jitter_range == 0.5

    def test_custom_values(self):
        cfg = BackoffConfig(strategy="exponential", base_delay=2.0, max_delay=60.0)
        assert cfg.strategy == "exponential"
        assert cfg.base_delay == 2.0

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="strategy must be one of"):
            BackoffConfig(strategy="random_walk")

    def test_negative_base_delay_raises(self):
        with pytest.raises(ValueError, match="base_delay must be"):
            BackoffConfig(base_delay=-1.0)

    def test_max_delay_less_than_base_raises(self):
        with pytest.raises(ValueError, match="max_delay must be"):
            BackoffConfig(base_delay=10.0, max_delay=5.0)

    def test_zero_multiplier_raises(self):
        with pytest.raises(ValueError, match="multiplier must be"):
            BackoffConfig(multiplier=0.0)

    def test_jitter_range_out_of_bounds_raises(self):
        with pytest.raises(ValueError, match="jitter_range"):
            BackoffConfig(jitter_range=1.5)


class TestBackoffCalculator:
    def test_fixed_strategy_constant_delay(self):
        calc = BackoffCalculator(BackoffConfig(strategy="fixed", base_delay=5.0))
        assert calc.delay_for(1) == 5.0
        assert calc.delay_for(3) == 5.0
        assert calc.delay_for(10) == 5.0

    def test_linear_strategy_grows_linearly(self):
        calc = BackoffCalculator(BackoffConfig(strategy="linear", base_delay=2.0))
        assert calc.delay_for(1) == 2.0
        assert calc.delay_for(2) == 4.0
        assert calc.delay_for(5) == 10.0

    def test_exponential_strategy_grows_exponentially(self):
        calc = BackoffCalculator(
            BackoffConfig(strategy="exponential", base_delay=1.0, multiplier=2.0)
        )
        assert calc.delay_for(1) == 1.0
        assert calc.delay_for(2) == 2.0
        assert calc.delay_for(4) == 8.0

    def test_max_delay_caps_result(self):
        calc = BackoffCalculator(
            BackoffConfig(strategy="exponential", base_delay=1.0, max_delay=10.0)
        )
        assert calc.delay_for(20) == 10.0

    def test_jitter_strategy_within_bounds(self):
        cfg = BackoffConfig(
            strategy="jitter", base_delay=4.0, max_delay=300.0, jitter_range=0.5
        )
        calc = BackoffCalculator(cfg)
        for _ in range(50):
            d = calc.delay_for(1)
            assert 0.0 <= d <= 300.0

    def test_invalid_attempt_raises(self):
        calc = BackoffCalculator(BackoffConfig())
        with pytest.raises(ValueError, match="attempt must be"):
            calc.delay_for(0)

    def test_zero_base_delay_returns_zero(self):
        calc = BackoffCalculator(
            BackoffConfig(strategy="fixed", base_delay=0.0, max_delay=0.0)
        )
        assert calc.delay_for(1) == 0.0
