"""Tests for cronwrap.alert module."""
import pytest
from cronwrap.alert import AlertConfig, AlertManager


class TestAlertConfig:
    def test_defaults(self):
        cfg = AlertConfig()
        assert cfg.failure_threshold == 1
        assert cfg.consecutive_failures == 1
        assert cfg.duration_threshold_seconds is None
        assert cfg.recipients == []

    def test_custom_values(self):
        cfg = AlertConfig(
            failure_threshold=3,
            consecutive_failures=2,
            duration_threshold_seconds=60.0,
            recipients=["ops@example.com"],
        )
        assert cfg.failure_threshold == 3
        assert cfg.consecutive_failures == 2
        assert cfg.duration_threshold_seconds == 60.0

    def test_invalid_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            AlertConfig(failure_threshold=0)

    def test_invalid_consecutive_failures_raises(self):
        with pytest.raises(ValueError, match="consecutive_failures"):
            AlertConfig(consecutive_failures=0)

    def test_invalid_duration_threshold_raises(self):
        with pytest.raises(ValueError, match="duration_threshold_seconds"):
            AlertConfig(duration_threshold_seconds=-5.0)


class TestAlertManager:
    def _manager(self, **kwargs) -> AlertManager:
        return AlertManager(AlertConfig(**kwargs))

    def test_no_alert_on_success(self):
        mgr = self._manager()
        alerts = mgr.evaluate(exit_code=0, duration_seconds=1.0, job_name="job")
        assert alerts == []

    def test_alert_on_failure(self):
        mgr = self._manager()
        alerts = mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        assert len(alerts) == 1
        assert "failed" in alerts[0]

    def test_consecutive_failure_threshold_not_met(self):
        mgr = self._manager(consecutive_failures=3)
        mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        alerts = mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        assert alerts == []

    def test_consecutive_failure_threshold_met(self):
        mgr = self._manager(consecutive_failures=2)
        mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        alerts = mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        assert len(alerts) == 1
        assert "2 consecutive" in alerts[0]

    def test_reset_clears_counter(self):
        mgr = self._manager()
        mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        assert mgr.consecutive_failure_count == 1
        mgr.reset()
        assert mgr.consecutive_failure_count == 0

    def test_success_resets_consecutive_count(self):
        mgr = self._manager()
        mgr.evaluate(exit_code=1, duration_seconds=1.0, job_name="job")
        mgr.evaluate(exit_code=0, duration_seconds=1.0, job_name="job")
        assert mgr.consecutive_failure_count == 0

    def test_duration_alert_triggered(self):
        mgr = self._manager(duration_threshold_seconds=5.0)
        alerts = mgr.evaluate(exit_code=0, duration_seconds=10.0, job_name="job")
        assert len(alerts) == 1
        assert "duration threshold" in alerts[0]

    def test_duration_alert_not_triggered_under_threshold(self):
        mgr = self._manager(duration_threshold_seconds=5.0)
        alerts = mgr.evaluate(exit_code=0, duration_seconds=3.0, job_name="job")
        assert alerts == []

    def test_multiple_alerts_combined(self):
        mgr = self._manager(duration_threshold_seconds=2.0)
        alerts = mgr.evaluate(exit_code=1, duration_seconds=5.0, job_name="job")
        assert len(alerts) == 2
