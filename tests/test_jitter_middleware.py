"""Tests for cronwrap.jitter_middleware."""

import pytest

from cronwrap.jitter import JitterConfig
from cronwrap.jitter_middleware import JitterMiddleware


@pytest.fixture()
def mw():
    cfg = JitterConfig(max_seconds=2.0, seed=0)
    slept = []

    from cronwrap import jitter as jitter_mod
    original = jitter_mod.time.sleep

    import cronwrap.jitter as jm
    import unittest.mock as mock

    with mock.patch("cronwrap.jitter.time.sleep", side_effect=slept.append):
        middleware = JitterMiddleware(cfg)
        yield middleware, slept


@pytest.fixture()
def mw_disabled():
    return JitterMiddleware(JitterConfig(max_seconds=0))


class TestJitterMiddleware:
    def test_run_returns_fn_result(self, mw_disabled):
        assert mw_disabled.run(lambda: 42) == 42

    def test_run_no_sleep_when_disabled(self, mw_disabled):
        slept = []
        import cronwrap.jitter as jm
        import unittest.mock as mock
        with mock.patch("cronwrap.jitter.time.sleep", side_effect=slept.append):
            mw_disabled.run(lambda: None)
        assert slept == []

    def test_config_property(self):
        cfg = JitterConfig(max_seconds=1.0)
        mw = JitterMiddleware(cfg)
        assert mw.config is cfg

    def test_default_config_created_when_none(self):
        mw = JitterMiddleware()
        assert isinstance(mw.config, JitterConfig)
        assert not mw.config.enabled

    def test_dry_run_returns_dict(self):
        cfg = JitterConfig(max_seconds=3.0, strategy="gaussian", seed=5)
        mw = JitterMiddleware(cfg)
        result = mw.dry_run()
        assert result["enabled"] is True
        assert result["strategy"] == "gaussian"
        assert result["max_seconds"] == 3.0
        assert "sampled_delay" in result
        assert 0.0 <= result["sampled_delay"] <= 3.0

    def test_dry_run_disabled(self):
        mw = JitterMiddleware(JitterConfig(max_seconds=0))
        result = mw.dry_run()
        assert result["enabled"] is False
        assert result["sampled_delay"] == 0.0
