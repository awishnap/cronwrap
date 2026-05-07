"""Tests for cronwrap.env module."""

import pytest

from cronwrap.env import EnvConfig, EnvManager, EnvValidationError


class TestEnvConfig:
    def test_defaults(self):
        cfg = EnvConfig()
        assert cfg.required == []
        assert cfg.defaults == {}
        assert cfg.inject == {}

    def test_custom_values(self):
        cfg = EnvConfig(
            required=["API_KEY"],
            defaults={"TIMEOUT": "30"},
            inject={"APP_ENV": "production"},
        )
        assert "API_KEY" in cfg.required
        assert cfg.defaults["TIMEOUT"] == "30"
        assert cfg.inject["APP_ENV"] == "production"

    def test_invalid_required_type_raises(self):
        with pytest.raises(TypeError):
            EnvConfig(required="API_KEY")  # type: ignore[arg-type]

    def test_blank_required_key_raises(self):
        with pytest.raises(ValueError):
            EnvConfig(required=[""])

    def test_invalid_defaults_type_raises(self):
        with pytest.raises(TypeError):
            EnvConfig(defaults=["x=y"])  # type: ignore[arg-type]


class TestEnvManager:
    def _manager(self, **kwargs) -> EnvManager:
        return EnvManager(EnvConfig(**kwargs))

    def test_validate_passes_when_all_present(self):
        mgr = self._manager(required=["FOO", "BAR"])
        mgr.validate(env={"FOO": "1", "BAR": "2"})

    def test_validate_raises_on_missing(self):
        mgr = self._manager(required=["MISSING_VAR"])
        with pytest.raises(EnvValidationError) as exc_info:
            mgr.validate(env={})
        assert "MISSING_VAR" in exc_info.value.missing

    def test_validate_reports_all_missing(self):
        mgr = self._manager(required=["A", "B", "C"])
        with pytest.raises(EnvValidationError) as exc_info:
            mgr.validate(env={"A": "1"})
        assert "B" in exc_info.value.missing
        assert "C" in exc_info.value.missing

    def test_build_env_applies_defaults(self):
        mgr = self._manager(defaults={"RETRIES": "3"})
        result = mgr.build_env(base={})
        assert result["RETRIES"] == "3"

    def test_build_env_defaults_do_not_override_existing(self):
        mgr = self._manager(defaults={"RETRIES": "3"})
        result = mgr.build_env(base={"RETRIES": "5"})
        assert result["RETRIES"] == "5"

    def test_build_env_inject_overrides_existing(self):
        mgr = self._manager(inject={"MODE": "test"})
        result = mgr.build_env(base={"MODE": "prod"})
        assert result["MODE"] == "test"

    def test_build_env_combines_all_sources(self):
        mgr = self._manager(
            defaults={"LOG_LEVEL": "INFO"},
            inject={"APP_ENV": "staging"},
        )
        result = mgr.build_env(base={"EXISTING": "yes"})
        assert result["EXISTING"] == "yes"
        assert result["LOG_LEVEL"] == "INFO"
        assert result["APP_ENV"] == "staging"

    def test_env_validation_error_message(self):
        err = EnvValidationError(["X", "Y"])
        assert "X" in str(err)
        assert "Y" in str(err)
