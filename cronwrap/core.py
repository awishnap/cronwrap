"""Core module for cronwrap — handles job execution, logging, retries, and alerting."""

import subprocess
import logging
import time
import sys
from datetime import datetime
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)


class CronJob:
    """
    Wraps a shell command or Python callable with retry logic,
    structured logging, and optional alert callbacks.
    """

    def __init__(
        self,
        command: str,
        name: Optional[str] = None,
        retries: int = 0,
        retry_delay: float = 5.0,
        timeout: Optional[float] = None,
        on_failure: Optional[List[Callable[[str, Exception], None]]] = None,
        on_success: Optional[List[Callable[[str, float], None]]] = None,
    ):
        """
        Initialize a CronJob wrapper.

        Args:
            command:     Shell command to execute.
            name:        Human-readable job name for log messages.
            retries:     Number of retry attempts on failure (0 = no retries).
            retry_delay: Seconds to wait between retries.
            timeout:     Maximum seconds to allow the command to run.
            on_failure:  List of callables invoked with (job_name, exception) on final failure.
            on_success:  List of callables invoked with (job_name, elapsed_seconds) on success.
        """
        self.command = command
        self.name = name or command[:40]
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.on_failure: List[Callable] = on_failure or []
        self.on_success: List[Callable] = on_success or []

    def run(self) -> int:
        """
        Execute the wrapped command, applying retry logic and triggering alerts.

        Returns:
            The exit code of the command (0 on success).

        Raises:
            SystemExit: Exits with the command's non-zero exit code after all retries
                        are exhausted.
        """
        attempts = self.retries + 1
        last_exception: Optional[Exception] = None
        start_time = datetime.utcnow()

        for attempt in range(1, attempts + 1):
            logger.info(
                "[%s] Starting attempt %d/%d at %s",
                self.name,
                attempt,
                attempts,
                start_time.isoformat(),
            )
            try:
                elapsed = self._execute()
                logger.info(
                    "[%s] Completed successfully in %.2fs", self.name, elapsed
                )
                self._notify_success(elapsed)
                return 0
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                last_exception = exc
                logger.warning(
                    "[%s] Attempt %d failed: %s", self.name, attempt, exc
                )
                if attempt < attempts:
                    logger.info(
                        "[%s] Retrying in %.1fs...", self.name, self.retry_delay
                    )
                    time.sleep(self.retry_delay)

        logger.error(
            "[%s] All %d attempt(s) failed. Last error: %s",
            self.name,
            attempts,
            last_exception,
        )
        self._notify_failure(last_exception)
        exit_code = (
            last_exception.returncode
            if isinstance(last_exception, subprocess.CalledProcessError)
            else 1
        )
        sys.exit(exit_code)

    def _execute(self) -> float:
        """
        Run the shell command and return elapsed time in seconds.

        Raises:
            subprocess.CalledProcessError: If the command exits with a non-zero status.
            subprocess.TimeoutExpired:      If the command exceeds the configured timeout.
        """
        t0 = time.monotonic()
        result = subprocess.run(
            self.command,
            shell=True,
            check=True,
            timeout=self.timeout,
            capture_output=False,
        )
        return time.monotonic() - t0

    def _notify_success(self, elapsed: float) -> None:
        """Invoke all registered success callbacks."""
        for callback in self.on_success:
            try:
                callback(self.name, elapsed)
            except Exception as exc:  # noqa: BLE001
                logger.error("[%s] Success callback raised: %s", self.name, exc)

    def _notify_failure(self, exc: Optional[Exception]) -> None:
        """Invoke all registered failure callbacks."""
        for callback in self.on_failure:
            try:
                callback(self.name, exc)
            except Exception as cb_exc:  # noqa: BLE001
                logger.error(
                    "[%s] Failure callback raised: %s", self.name, cb_exc
                )
