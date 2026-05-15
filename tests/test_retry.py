"""Tests for cronwrap.retry module."""

import time
import pytest
from unittest.mock import MagicMock, patch

from cronwrap.retry import RetryPolicy


class TestRetryPolicyInit:
    def test_defaults(self):
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.delay == 5.0
        assert policy.backoff == 2.0
        assert policy.max_delay == 120.0
        assert policy.exceptions == (Exception,)

    def test_custom_values(self):
        policy = RetryPolicy(max_attempts=5, delay=1.0, backoff=1.5, max_delay=60.0)
        assert policy.max_attempts == 5
        assert policy.delay == 1.0
        assert policy.backoff == 1.5
        assert policy.max_delay == 60.0

    def test_invalid_max_attempts(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)

    def test_invalid_delay(self):
        with pytest.raises(ValueError, match="delay"):
            RetryPolicy(delay=-1)

    def test_invalid_backoff(self):
        with pytest.raises(ValueError, match="backoff"):
            RetryPolicy(backoff=0.5)


class TestRetryPolicyExecute:
    def test_success_on_first_attempt(self):
        policy = RetryPolicy(max_attempts=3, delay=0)
        func = MagicMock(return_value="ok")
        result = policy.execute(func)
        assert result == "ok"
        assert func.call_count == 1

    @patch("cronwrap.retry.time.sleep")
    def test_success_on_second_attempt(self, mock_sleep):
        policy = RetryPolicy(max_attempts=3, delay=1.0)
        func = MagicMock(side_effect=[ValueError("fail"), "ok"])
        result = policy.execute(func)
        assert result == "ok"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("cronwrap.retry.time.sleep")
    def test_all_attempts_fail(self, mock_sleep):
        policy = RetryPolicy(max_attempts=3, delay=0.1)
        func = MagicMock(side_effect=RuntimeError("always fails"))
        with pytest.raises(RuntimeError, match="always fails"):
            policy.execute(func)
        assert func.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("cronwrap.retry.time.sleep")
    def test_backoff_applied(self, mock_sleep):
        policy = RetryPolicy(max_attempts=3, delay=1.0, backoff=3.0, max_delay=100.0)
        func = MagicMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):
            policy.execute(func)
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [1.0, 3.0]

    @patch("cronwrap.retry.time.sleep")
    def test_max_delay_respected(self, mock_sleep):
        policy = RetryPolicy(max_attempts=4, delay=10.0, backoff=10.0, max_delay=15.0)
        func = MagicMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):
            policy.execute(func)
        for call in mock_sleep.call_args_list:
            assert call.args[0] <= 15.0

    def test_only_specified_exceptions_retried(self):
        """Non-matching exceptions should propagate immediately without retrying."""
        policy = RetryPolicy(max_attempts=3, delay=0, exceptions=(ValueError,))
        func = MagicMock(side_effect=TypeError("wrong type"))
        with pytest.raises(TypeError, match="wrong type"):
            policy.execute(func)
        # Should not retry; only the first call should have been made
        assert func.call_count == 1

    @patch("cronwrap.retry.time.sleep")
    def test_only_specified_exceptions_are_retried(self, mock_sleep):
        """Matching exceptions should be retried while others propagate immediately."""
        policy = RetryPolicy(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        func = MagicMock(side_effect=[ValueError("retry me"), "ok"])
        result = policy.execute(func)
        assert result == "ok"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(0.1)
