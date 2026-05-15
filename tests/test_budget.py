"""Tests for cronwrap.budget."""
import pytest

from cronwrap.budget import (
    BudgetConfig,
    BudgetExceededError,
    BudgetStatus,
    BudgetTracker,
)


# ---------------------------------------------------------------------------
# BudgetConfig
# ---------------------------------------------------------------------------

class TestBudgetConfig:
    def test_defaults(self):
        cfg = BudgetConfig()
        assert cfg.max_seconds == 0.0
        assert cfg.warn_at_percent == 80.0
        assert cfg.state_dir == "/tmp/cronwrap/budget"

    def test_custom_values(self):
        cfg = BudgetConfig(max_seconds=60.0, warn_at_percent=50.0, state_dir="/var/run")
        assert cfg.max_seconds == 60.0
        assert cfg.warn_at_percent == 50.0

    def test_negative_max_seconds_raises(self):
        with pytest.raises(ValueError, match="max_seconds"):
            BudgetConfig(max_seconds=-1.0)

    def test_zero_warn_at_percent_raises(self):
        with pytest.raises(ValueError, match="warn_at_percent"):
            BudgetConfig(warn_at_percent=0.0)

    def test_over_100_warn_at_percent_raises(self):
        with pytest.raises(ValueError, match="warn_at_percent"):
            BudgetConfig(warn_at_percent=101.0)

    def test_blank_state_dir_raises(self):
        with pytest.raises(ValueError, match="state_dir"):
            BudgetConfig(state_dir="  ")

    def test_enabled_when_positive(self):
        cfg = BudgetConfig(max_seconds=30.0)
        assert cfg.enabled is True

    def test_disabled_when_zero(self):
        cfg = BudgetConfig(max_seconds=0.0)
        assert cfg.enabled is False

    def test_warn_threshold_seconds(self):
        cfg = BudgetConfig(max_seconds=100.0, warn_at_percent=75.0)
        assert cfg.warn_threshold_seconds == 75.0


# ---------------------------------------------------------------------------
# BudgetStatus
# ---------------------------------------------------------------------------

class TestBudgetStatus:
    def _make(self, elapsed=10.0, budget=60.0, exceeded=False, warn=False):
        return BudgetStatus(
            job_name="myjob",
            elapsed=elapsed,
            budget=budget,
            exceeded=exceeded,
            warn=warn,
        )

    def test_remaining(self):
        s = self._make(elapsed=20.0, budget=60.0)
        assert s.remaining == 40.0

    def test_remaining_never_negative(self):
        s = self._make(elapsed=100.0, budget=60.0)
        assert s.remaining == 0.0

    def test_percent_used(self):
        s = self._make(elapsed=30.0, budget=60.0)
        assert s.percent_used == pytest.approx(50.0)

    def test_percent_used_zero_budget(self):
        s = self._make(elapsed=5.0, budget=0.0)
        assert s.percent_used == 0.0

    def test_to_dict_keys(self):
        s = self._make()
        d = s.to_dict()
        assert "job_name" in d
        assert "percent_used" in d
        assert "remaining" in d


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------

class TestBudgetTracker:
    def test_evaluate_disabled_never_exceeded(self):
        tracker = BudgetTracker(BudgetConfig(max_seconds=0.0))
        status = tracker.evaluate("job", 9999.0)
        assert status.exceeded is False
        assert status.warn is False

    def test_evaluate_within_budget(self):
        tracker = BudgetTracker(BudgetConfig(max_seconds=60.0))
        status = tracker.evaluate("job", 30.0)
        assert status.exceeded is False
        assert status.warn is False

    def test_evaluate_warns_near_budget(self):
        tracker = BudgetTracker(BudgetConfig(max_seconds=60.0, warn_at_percent=80.0))
        status = tracker.evaluate("job", 50.0)  # 83 %
        assert status.warn is True
        assert status.exceeded is False

    def test_evaluate_exceeded(self):
        tracker = BudgetTracker(BudgetConfig(max_seconds=60.0))
        status = tracker.evaluate("job", 61.0)
        assert status.exceeded is True

    def test_check_raises_on_exceeded(self):
        tracker = BudgetTracker(BudgetConfig(max_seconds=10.0))
        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.check("myjob", 15.0)
        assert "myjob" in str(exc_info.value)

    def test_check_returns_status_when_ok(self):
        tracker = BudgetTracker(BudgetConfig(max_seconds=60.0))
        status = tracker.check("job", 5.0)
        assert isinstance(status, BudgetStatus)
