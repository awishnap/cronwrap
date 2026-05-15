"""Tests for cronwrap.redact."""
import pytest

from cronwrap.redact import RedactConfig, RedactError, Redactor


# ---------------------------------------------------------------------------
# RedactConfig
# ---------------------------------------------------------------------------

class TestRedactConfig:
    def test_defaults(self):
        cfg = RedactConfig()
        assert cfg.patterns == []
        assert cfg.placeholder == "[REDACTED]"
        assert cfg.redact_env_values is True

    def test_custom_values(self):
        cfg = RedactConfig(patterns=[r"\d{4}-\d{4}"], placeholder="***", redact_env_values=False)
        assert cfg.placeholder == "***"
        assert cfg.redact_env_values is False

    def test_blank_placeholder_raises(self):
        with pytest.raises(RedactError, match="placeholder"):
            RedactConfig(placeholder="")

    def test_blank_pattern_raises(self):
        with pytest.raises(RedactError, match="pattern"):
            RedactConfig(patterns=[""])

    def test_invalid_regex_raises(self):
        with pytest.raises(RedactError, match="invalid regex"):
            RedactConfig(patterns=["[unclosed"])


# ---------------------------------------------------------------------------
# Redactor — built-in patterns
# ---------------------------------------------------------------------------

class TestRedactorBuiltins:
    def setup_method(self):
        self.r = Redactor()

    def test_redacts_password_assignment(self):
        result = self.r.redact("password=supersecret")
        assert "supersecret" not in result
        assert "[REDACTED]" in result

    def test_redacts_bearer_token(self):
        result = self.r.redact("Authorization: Bearer abc123xyz")
        assert "abc123xyz" not in result

    def test_leaves_safe_text_unchanged(self):
        safe = "running backup job at 03:00"
        assert self.r.redact(safe) == safe

    def test_case_insensitive_password(self):
        result = self.r.redact("PASSWORD=hunter2")
        assert "hunter2" not in result


# ---------------------------------------------------------------------------
# Redactor — custom patterns
# ---------------------------------------------------------------------------

class TestRedactorCustomPatterns:
    def test_custom_pattern_applied(self):
        cfg = RedactConfig(patterns=[r"\b\d{16}\b"])
        r = Redactor(cfg)
        result = r.redact("card: 1234567890123456")
        assert "1234567890123456" not in result
        assert "[REDACTED]" in result

    def test_custom_placeholder(self):
        cfg = RedactConfig(placeholder="***")
        r = Redactor(cfg)
        result = r.redact("token=abc")
        assert "***" in result

    def test_redact_dict_replaces_string_values(self):
        r = Redactor()
        data = {"api_key": "api_key=secret", "count": 5}
        cleaned = r.redact_dict(data)
        assert "secret" not in cleaned["api_key"]
        assert cleaned["count"] == 5

    def test_redact_dict_preserves_non_string(self):
        r = Redactor()
        data = {"retries": 3, "enabled": True}
        assert r.redact_dict(data) == data
