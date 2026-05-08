"""Tests for cronwrap.health."""
import pytest
from cronwrap.health import (
    HealthConfig,
    HealthCheckError,
    HealthMonitor,
    HealthStatus,
)


# ---------------------------------------------------------------------------
# HealthConfig
# ---------------------------------------------------------------------------

class TestHealthConfig:
    def test_defaults(self):
        cfg = HealthConfig()
        assert cfg.enabled is False
        assert cfg.max_allowed_duration is None
        assert cfg.max_failure_streak == 3
        assert cfg.ping_url is None

    def test_custom_values(self):
        cfg = HealthConfig(enabled=True, max_allowed_duration=60.0, max_failure_streak=5)
        assert cfg.enabled is True
        assert cfg.max_allowed_duration == 60.0
        assert cfg.max_failure_streak == 5

    def test_zero_max_allowed_duration_raises(self):
        with pytest.raises(ValueError, match="max_allowed_duration must be positive"):
            HealthConfig(max_allowed_duration=0)

    def test_negative_max_allowed_duration_raises(self):
        with pytest.raises(ValueError, match="max_allowed_duration must be positive"):
            HealthConfig(max_allowed_duration=-1.0)

    def test_zero_failure_streak_raises(self):
        with pytest.raises(ValueError, match="max_failure_streak must be >= 1"):
            HealthConfig(max_failure_streak=0)


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------

class TestHealthStatus:
    def _make(self, last_success=None):
        return HealthStatus(
            job_name="test-job",
            is_healthy=True,
            failure_streak=0,
            last_success=last_success,
        )

    def test_stale_when_no_last_success(self):
        assert self._make(last_success=None).stale is True

    def test_not_stale_after_success(self):
        from datetime import datetime
        assert self._make(last_success=datetime.utcnow()).stale is False


# ---------------------------------------------------------------------------
# HealthMonitor
# ---------------------------------------------------------------------------

@pytest.fixture
def monitor():
    cfg = HealthConfig(enabled=True, max_allowed_duration=10.0, max_failure_streak=2)
    return HealthMonitor(job_name="backup", config=cfg)


class TestHealthMonitor:
    def test_healthy_after_success(self, monitor):
        status = monitor.record(exit_code=0, duration=1.0)
        assert status.is_healthy is True
        assert status.failure_streak == 0

    def test_unhealthy_after_streak(self, monitor):
        monitor.record(exit_code=1, duration=1.0)
        status = monitor.record(exit_code=1, duration=1.0)
        assert status.is_healthy is False
        assert status.failure_streak == 2

    def test_streak_resets_on_success(self, monitor):
        monitor.record(exit_code=1, duration=1.0)
        status = monitor.record(exit_code=0, duration=1.0)
        assert status.failure_streak == 0
        assert status.is_healthy is True

    def test_unhealthy_when_duration_exceeded(self, monitor):
        status = monitor.record(exit_code=0, duration=15.0)
        assert status.is_healthy is False
        assert "duration" in status.details

    def test_details_empty_when_healthy(self, monitor):
        status = monitor.record(exit_code=0, duration=1.0)
        assert status.details == ""

    def test_last_run_set_after_record(self, monitor):
        status = monitor.record(exit_code=0, duration=1.0)
        assert status.last_run is not None

    def test_last_success_set_only_on_success(self, monitor):
        status = monitor.record(exit_code=1, duration=1.0)
        assert status.last_success is None
        status = monitor.record(exit_code=0, duration=1.0)
        assert status.last_success is not None
