"""Tests for cronwrap.circuit_breaker."""
import time
import pytest
from cronwrap.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold == 5
        assert cfg.recovery_timeout == 60.0
        assert cfg.success_threshold == 1

    def test_custom_values(self):
        cfg = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0, success_threshold=2)
        assert cfg.failure_threshold == 3
        assert cfg.recovery_timeout == 30.0
        assert cfg.success_threshold == 2

    def test_invalid_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreakerConfig(failure_threshold=0)

    def test_invalid_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreakerConfig(recovery_timeout=0)

    def test_invalid_success_threshold_raises(self):
        with pytest.raises(ValueError, match="success_threshold"):
            CircuitBreakerConfig(success_threshold=0)


class TestCircuitBreaker:
    def _make(self, **kwargs):
        cfg = CircuitBreakerConfig(**kwargs) if kwargs else CircuitBreakerConfig(failure_threshold=3)
        return CircuitBreaker("test-job", cfg)

    def test_initial_state_is_closed(self):
        cb = self._make()
        assert cb.state == CircuitState.CLOSED

    def test_allows_execution_when_closed(self):
        cb = self._make()
        assert cb.allow_execution() is True

    def test_trips_after_threshold_failures(self):
        cb = self._make()
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_blocks_execution_when_open(self):
        cb = self._make()
        for _ in range(3):
            cb.record_failure()
        assert cb.allow_execution() is False

    def test_success_resets_failure_count(self):
        cb = self._make()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # still closed, failure count reset
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # needs one more

    def test_transitions_to_half_open_after_timeout(self):
        cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.05)
        cb = CircuitBreaker("job", cfg)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_execution(self):
        cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.05)
        cb = CircuitBreaker("job", cfg)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)
        assert cb.allow_execution() is True

    def test_success_in_half_open_closes_circuit(self):
        cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.05)
        cb = CircuitBreaker("job", cfg)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.05)
        cb = CircuitBreaker("job", cfg)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_error_message(self):
        err = CircuitBreakerError("my-job", CircuitState.OPEN)
        assert "my-job" in str(err)
        assert "open" in str(err)
