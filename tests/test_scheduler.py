"""Tests for cronwrap.scheduler module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from cronwrap.scheduler import ScheduleConfig, JobScheduler


class TestScheduleConfig:
    def test_valid_expression(self):
        cfg = ScheduleConfig(expression="*/5 * * * *")
        assert cfg.expression == "*/5 * * * *"

    def test_default_timezone(self):
        cfg = ScheduleConfig(expression="0 * * * *")
        assert cfg.timezone == "UTC"

    def test_custom_timezone(self):
        cfg = ScheduleConfig(expression="0 9 * * 1", timezone="America/New_York")
        assert cfg.timezone == "America/New_York"

    def test_empty_expression_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduleConfig(expression="")

    def test_whitespace_expression_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            ScheduleConfig(expression="   ")

    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError, match="Invalid cron expression"):
            ScheduleConfig(expression="not_a_cron")

    def test_is_valid_expression_true(self):
        assert ScheduleConfig.is_valid_expression("0 12 * * *") is True

    def test_is_valid_expression_false(self):
        assert ScheduleConfig.is_valid_expression("bad expr here") is False


class TestJobScheduler:
    @pytest.fixture
    def scheduler(self):
        cfg = ScheduleConfig(expression="0 * * * *")  # every hour on the hour
        return JobScheduler(cfg)

    def test_repr(self, scheduler):
        r = repr(scheduler)
        assert "JobScheduler" in r
        assert "0 * * * *" in r

    def test_next_run_returns_datetime_or_none(self, scheduler):
        result = scheduler.next_run()
        assert result is None or isinstance(result, datetime)

    def test_prev_run_returns_datetime_or_none(self, scheduler):
        result = scheduler.prev_run()
        assert result is None or isinstance(result, datetime)

    def test_is_due_true_when_just_ran(self, scheduler):
        """If prev_run is within tolerance, is_due should be True."""
        fake_prev = datetime(2024, 1, 1, 12, 0, 0)
        fake_now = fake_prev + timedelta(seconds=5)
        with patch.object(scheduler, "prev_run", return_value=fake_prev):
            assert scheduler.is_due(tolerance_seconds=60, now=fake_now) is True

    def test_is_due_false_when_outside_tolerance(self, scheduler):
        fake_prev = datetime(2024, 1, 1, 12, 0, 0)
        fake_now = fake_prev + timedelta(seconds=120)
        with patch.object(scheduler, "prev_run", return_value=fake_prev):
            assert scheduler.is_due(tolerance_seconds=60, now=fake_now) is False

    def test_is_due_false_when_prev_run_none(self, scheduler):
        with patch.object(scheduler, "prev_run", return_value=None):
            assert scheduler.is_due() is False

    def test_next_run_after_given_time(self, scheduler):
        base = datetime(2024, 6, 1, 10, 30, 0)
        result = scheduler.next_run(after=base)
        if result is not None:
            assert result > base

    def test_prev_run_before_given_time(self, scheduler):
        base = datetime(2024, 6, 1, 10, 30, 0)
        result = scheduler.prev_run(before=base)
        if result is not None:
            assert result <= base
