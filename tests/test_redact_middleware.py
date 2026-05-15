"""Tests for cronwrap.redact_middleware."""
import pytest

from cronwrap.redact import RedactConfig
from cronwrap.redact_middleware import RedactMiddleware


@pytest.fixture
def mw():
    return RedactMiddleware()


@pytest.fixture
def mw_custom():
    return RedactMiddleware(RedactConfig(patterns=[r"\b\d{9}\b"], placeholder="***"))


class TestRedactMiddleware:
    def test_run_returns_redacted_string(self, mw):
        result = mw.run(lambda: "password=hunter2")
        assert "hunter2" not in result
        assert "[REDACTED]" in result

    def test_run_caches_last_redacted(self, mw):
        mw.run(lambda: "token=abc")
        assert mw.last_redacted is not None
        assert "abc" not in mw.last_redacted

    def test_last_redacted_none_before_run(self):
        fresh = RedactMiddleware()
        assert fresh.last_redacted is None

    def test_run_safe_text_unchanged(self, mw):
        result = mw.run(lambda: "all systems nominal")
        assert result == "all systems nominal"

    def test_clean_convenience(self, mw):
        result = mw.clean("secret=xyz")
        assert "xyz" not in result

    def test_clean_dict_convenience(self, mw):
        cleaned = mw.clean_dict({"api_key": "api_key=topsecret", "n": 1})
        assert "topsecret" not in cleaned["api_key"]
        assert cleaned["n"] == 1

    def test_custom_pattern_honoured(self, mw_custom):
        result = mw_custom.run(lambda: "ssn 123456789")
        assert "123456789" not in result
        assert "***" in result

    def test_config_property(self, mw):
        assert isinstance(mw.config, RedactConfig)
