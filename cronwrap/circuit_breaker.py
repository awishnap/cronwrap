"""Circuit breaker for cron jobs — stops execution when failure threshold is exceeded."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # blocking execution
    HALF_OPEN = "half_open"  # testing recovery


class CircuitBreakerError(Exception):
    def __init__(self, job_name: str, state: CircuitState) -> None:
        self.job_name = job_name
        self.state = state
        super().__init__(f"Circuit breaker is {state.value} for job '{job_name}'")


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds before attempting HALF_OPEN
    success_threshold: int = 1      # successes needed to close from HALF_OPEN

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")


class CircuitBreaker:
    """Tracks consecutive failures and opens the circuit to prevent cascading failures."""

    def __init__(self, job_name: str, config: Optional[CircuitBreakerConfig] = None) -> None:
        self.job_name = job_name
        self.config = config or CircuitBreakerConfig()
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._opened_at is not None:
                elapsed = time.monotonic() - self._opened_at
                if elapsed >= self.config.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
        return self._state

    def allow_execution(self) -> bool:
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._reset()
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._trip()
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.config.failure_threshold:
                self._trip()

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()

    def _reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CircuitBreaker(job={self.job_name!r}, state={self.state.value}, "
            f"failures={self._failure_count})"
        )
