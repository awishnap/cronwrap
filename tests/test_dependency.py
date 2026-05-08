"""Tests for cronwrap.dependency."""
from datetime import datetime, timedelta

import pytest

from cronwrap.dependency import (
    DependencyChecker,
    DependencyConfig,
    DependencyError,
)


# ---------------------------------------------------------------------------
# DependencyConfig
# ---------------------------------------------------------------------------

class TestDependencyConfig:
    def test_defaults(self):
        cfg = DependencyConfig()
        assert cfg.required_jobs == []
        assert cfg.max_age_seconds == 3600
        assert cfg.strict is True

    def test_custom_values(self):
        cfg = DependencyConfig(required_jobs=["job_a", "job_b"], max_age_seconds=600, strict=False)
        assert cfg.required_jobs == ["job_a", "job_b"]
        assert cfg.max_age_seconds == 600
        assert cfg.strict is False

    def test_invalid_required_jobs_type_raises(self):
        with pytest.raises(TypeError):
            DependencyConfig(required_jobs="not_a_list")

    def test_blank_job_name_raises(self):
        with pytest.raises(ValueError):
            DependencyConfig(required_jobs=["  "])

    def test_zero_max_age_raises(self):
        with pytest.raises(ValueError):
            DependencyConfig(max_age_seconds=0)

    def test_negative_max_age_raises(self):
        with pytest.raises(ValueError):
            DependencyConfig(max_age_seconds=-1)


# ---------------------------------------------------------------------------
# DependencyChecker
# ---------------------------------------------------------------------------

@pytest.fixture()
def checker():
    cfg = DependencyConfig(required_jobs=["ingest", "transform"], max_age_seconds=3600)
    return DependencyChecker(cfg)


class TestDependencyChecker:
    def test_all_unsatisfied_initially(self, checker):
        missing = checker.check("export")
        assert set(missing) == {"ingest", "transform"}

    def test_satisfied_after_record(self, checker):
        checker.record_success("ingest")
        checker.record_success("transform")
        assert checker.check("export") == []

    def test_stale_dependency_is_unsatisfied(self, checker):
        old_time = datetime.utcnow() - timedelta(seconds=7200)
        checker.record_success("ingest", at=old_time)
        checker.record_success("transform")
        missing = checker.check("export")
        assert missing == ["ingest"]

    def test_assert_satisfied_raises_when_missing(self, checker):
        with pytest.raises(DependencyError) as exc_info:
            checker.assert_satisfied("export")
        err = exc_info.value
        assert err.job_name == "export"
        assert "ingest" in err.missing
        assert "transform" in err.missing

    def test_assert_satisfied_passes_when_all_met(self, checker):
        checker.record_success("ingest")
        checker.record_success("transform")
        checker.assert_satisfied("export")  # should not raise

    def test_non_strict_does_not_raise(self):
        cfg = DependencyConfig(required_jobs=["ingest"], strict=False)
        ch = DependencyChecker(cfg)
        ch.assert_satisfied("export")  # strict=False → no exception

    def test_dependency_error_message(self, checker):
        with pytest.raises(DependencyError, match="unsatisfied dependencies"):
            checker.assert_satisfied("export")

    def test_record_success_uses_utcnow_by_default(self, checker):
        before = datetime.utcnow()
        checker.record_success("ingest")
        after = datetime.utcnow()
        ts = checker._registry["ingest"]
        assert before <= ts <= after
