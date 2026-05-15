"""Tests for cronwrap.budget_middleware."""
import pytest

from cronwrap.budget import BudgetConfig, BudgetExceededError, BudgetStatus
from cronwrap.budget_middleware import BudgetMiddleware


@pytest.fixture
def mw():
    """Middleware with a generous 60-second budget."""
    return BudgetMiddleware(BudgetConfig(max_seconds=60.0))


@pytest.fixture
def mw_disabled():
    return BudgetMiddleware(BudgetConfig(max_seconds=0.0))


class TestBudgetMiddleware:
    def test_run_returns_fn_result(self, mw):
        result = mw.run(lambda: 42, job_name="test")
        assert result == 42

    def test_run_sets_last_status(self, mw):
        mw.run(lambda: None, job_name="test")
        assert mw.last_status is not None
        assert isinstance(mw.last_status, BudgetStatus)

    def test_last_status_none_before_run(self):
        mw = BudgetMiddleware()
        assert mw.last_status is None

    def test_run_raises_when_budget_exceeded(self, monkeypatch):
        import time
        calls = []

        def fake_monotonic():
            if not calls:
                calls.append(1)
                return 0.0
            return 100.0  # simulates 100 s elapsed

        monkeypatch.setattr(time, "monotonic", fake_monotonic)
        mw = BudgetMiddleware(BudgetConfig(max_seconds=10.0))
        with pytest.raises(BudgetExceededError):
            mw.run(lambda: None, job_name="slow_job")

    def test_dry_run_returns_status(self, mw):
        status = mw.dry_run(lambda: None, job_name="test")
        assert isinstance(status, BudgetStatus)

    def test_dry_run_does_not_raise_on_exceeded(self, monkeypatch):
        import time
        calls = []

        def fake_monotonic():
            if not calls:
                calls.append(1)
                return 0.0
            return 200.0

        monkeypatch.setattr(time, "monotonic", fake_monotonic)
        mw = BudgetMiddleware(BudgetConfig(max_seconds=10.0))
        status = mw.dry_run(lambda: None, job_name="job")
        assert status.exceeded is True

    def test_disabled_budget_never_raises(self, mw_disabled):
        # Should not raise even with a very slow function (simulated)
        result = mw_disabled.run(lambda: "ok", job_name="job")
        assert result == "ok"
        assert mw_disabled.last_status.exceeded is False
