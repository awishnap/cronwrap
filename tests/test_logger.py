import logging
import os
import tempfile
import pytest
from cronwrap.logger import LogConfig, CronLogger


class TestLogConfig:
    def test_defaults(self):
        config = LogConfig()
        assert config.log_level == "INFO"
        assert config.log_file is None
        assert config.max_bytes == 10 * 1024 * 1024
        assert config.backup_count == 5

    def test_custom_values(self):
        config = LogConfig(log_level="DEBUG", backup_count=3, max_bytes=1024)
        assert config.log_level == "DEBUG"
        assert config.backup_count == 3
        assert config.max_bytes == 1024

    def test_log_level_normalized_to_upper(self):
        config = LogConfig(log_level="debug")
        assert config.log_level == "DEBUG"

    def test_invalid_log_level_raises(self):
        with pytest.raises(ValueError, match="log_level must be one of"):
            LogConfig(log_level="VERBOSE")

    def test_invalid_max_bytes_raises(self):
        with pytest.raises(ValueError, match="max_bytes must be a positive integer"):
            LogConfig(max_bytes=0)

    def test_invalid_backup_count_raises(self):
        with pytest.raises(ValueError, match="backup_count must be non-negative"):
            LogConfig(backup_count=-1)


class TestCronLogger:
    def test_creates_logger(self):
        logger = CronLogger("test_job")
        assert logger.job_name == "test_job"
        assert logger._logger is not None

    def test_uses_default_config_when_none(self):
        logger = CronLogger("test_job")
        assert logger.config.log_level == "INFO"

    def test_logger_name_includes_job_name(self):
        logger = CronLogger("my_cron_job")
        assert "my_cron_job" in logger._logger.name

    def test_log_start_does_not_raise(self, caplog):
        logger = CronLogger("test_job")
        with caplog.at_level(logging.INFO, logger="cronwrap.test_job"):
            logger.log_start("echo hello")
        assert "starting" in caplog.text

    def test_log_success_does_not_raise(self, caplog):
        logger = CronLogger("test_job")
        with caplog.at_level(logging.INFO, logger="cronwrap.test_job"):
            logger.log_success("echo hello", duration=0.123)
        assert "succeeded" in caplog.text

    def test_log_failure_does_not_raise(self, caplog):
        logger = CronLogger("test_job")
        with caplog.at_level(logging.ERROR, logger="cronwrap.test_job"):
            logger.log_failure("bad_cmd", duration=0.5, exit_code=1, error="not found")
        assert "failed" in caplog.text
        assert "exit_code=1" in caplog.text

    def test_log_retry_does_not_raise(self, caplog):
        logger = CronLogger("test_job")
        with caplog.at_level(logging.WARNING, logger="cronwrap.test_job"):
            logger.log_retry(attempt=2, max_attempts=3, delay=5.0)
        assert "retrying" in caplog.text

    def test_file_logging(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            config = LogConfig(log_file=log_path)
            logger = CronLogger("file_test_job", config=config)
            logger.log_start("echo test")
            with open(log_path) as lf:
                contents = lf.read()
            assert "starting" in contents
        finally:
            os.unlink(log_path)
