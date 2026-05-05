"""Retry logic for cronwrap jobs."""

import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Defines retry behavior for a cron job."""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 5.0,
        backoff: float = 2.0,
        max_delay: float = 120.0,
        exceptions: tuple = (Exception,),
    ):
        """
        Args:
            max_attempts: Maximum number of total attempts (including first).
            delay: Initial delay in seconds between retries.
            backoff: Multiplier applied to delay after each retry.
            max_delay: Maximum delay in seconds between retries.
            exceptions: Tuple of exception types that trigger a retry.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        if backoff < 1.0:
            raise ValueError("backoff must be >= 1.0")

        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.exceptions = exceptions

    def execute(self, func: Callable, *args, **kwargs):
        """Execute func with retry logic.

        Returns:
            The return value of func on success.

        Raises:
            The last exception raised if all attempts fail.
        """
        last_exception: Optional[Exception] = None
        current_delay = self.delay

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug("Attempt %d/%d", attempt, self.max_attempts)
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info("Succeeded on attempt %d/%d", attempt, self.max_attempts)
                return result
            except self.exceptions as exc:
                last_exception = exc
                logger.warning(
                    "Attempt %d/%d failed: %s",
                    attempt,
                    self.max_attempts,
                    exc,
                )
                if attempt < self.max_attempts:
                    sleep_time = min(current_delay, self.max_delay)
                    logger.debug("Retrying in %.1f seconds...", sleep_time)
                    time.sleep(sleep_time)
                    current_delay *= self.backoff

        logger.error("All %d attempts failed.", self.max_attempts)
        raise last_exception

    def __repr__(self) -> str:
        return (
            f"RetryPolicy(max_attempts={self.max_attempts}, delay={self.delay}, "
            f"backoff={self.backoff}, max_delay={self.max_delay})"
        )
