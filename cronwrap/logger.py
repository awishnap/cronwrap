import logging
import os
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class LogConfig:
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

    def __post_init__(self):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got '{self.log_level}'")
        self.log_level = self.log_level.upper()
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        if self.backup_count < 0:
            raise ValueError("backup_count must be non-negative")


class CronLogger:
    def __init__(self, job_name: str, config: Optional[LogConfig] = None):
        self.job_name = job_name
        self.config = config or LogConfig()
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"cronwrap.{self.job_name}")
        logger.setLevel(getattr(logging, self.config.log_level))

        if logger.handlers:
            logger.handlers.clear()

        formatter = logging.Formatter(
            fmt=self.config.log_format,
            datefmt=self.config.date_format,
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        if self.config.log_file:
            from logging.handlers import RotatingFileHandler
            os.makedirs(os.path.dirname(self.config.log_file), exist_ok=True) if os.path.dirname(self.config.log_file) else None
            file_handler = RotatingFileHandler(
                self.config.log_file,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def log_start(self, command: str) -> None:
        self._logger.info(f"Job '{self.job_name}' starting | command='{command}'")

    def log_success(self, command: str, duration: float, output: str = "") -> None:
        self._logger.info(
            f"Job '{self.job_name}' succeeded | command='{command}' duration={duration:.3f}s"
        )
        if output:
            self._logger.debug(f"Output: {output.strip()}")

    def log_failure(self, command: str, duration: float, exit_code: int, error: str = "") -> None:
        self._logger.error(
            f"Job '{self.job_name}' failed | command='{command}' exit_code={exit_code} duration={duration:.3f}s"
        )
        if error:
            self._logger.error(f"Error output: {error.strip()}")

    def log_retry(self, attempt: int, max_attempts: int, delay: float) -> None:
        self._logger.warning(
            f"Job '{self.job_name}' retrying | attempt={attempt}/{max_attempts} delay={delay}s"
        )

    def log_exception(self, exc: Exception) -> None:
        self._logger.exception(f"Job '{self.job_name}' raised an unexpected exception: {exc}")
