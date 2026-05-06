from datetime import datetime
import pytest
from cronwrap.execution_result import ExecutionResult


class TestExecutionResult:
    def _make_result(self, exit_code=0, **kwargs) -> ExecutionResult:
        return ExecutionResult(
            job_name="backup",
            command="pg_dump mydb",
            exit_code=exit_code,
            **kwargs,
        )

    def test_succeeded_when_exit_code_zero(self):
        result = self._make_result(exit_code=0)
        assert result.succeeded is True
        assert result.failed is False

    def test_failed_when_exit_code_nonzero(self):
        result = self._make_result(exit_code=1)
        assert result.succeeded is False
        assert result.failed is True

    def test_summary_contains_job_name(self):
        result = self._make_result(exit_code=0)
        assert "backup" in result.summary()

    def test_summary_contains_success_label(self):
        result = self._make_result(exit_code=0)
        assert "SUCCESS" in result.summary()

    def test_summary_contains_failure_label(self):
        result = self._make_result(exit_code=2)
        assert "FAILURE" in result.summary()

    def test_to_dict_keys(self):
        result = self._make_result(exit_code=0, duration=1.5, attempt=2)
        d = result.to_dict()
        assert "job_name" in d
        assert "exit_code" in d
        assert "succeeded" in d
        assert "duration" in d
        assert "attempt" in d

    def test_to_dict_succeeded_true(self):
        result = self._make_result(exit_code=0)
        assert result.to_dict()["succeeded"] is True

    def test_to_dict_succeeded_false(self):
        result = self._make_result(exit_code=1)
        assert result.to_dict()["succeeded"] is False

    def test_to_dict_duration_rounded(self):
        result = self._make_result(exit_code=0, duration=1.123456789)
        assert result.to_dict()["duration"] == round(1.123456789, 4)

    def test_to_dict_finished_at_none_when_not_set(self):
        result = self._make_result(exit_code=0)
        assert result.to_dict()["finished_at"] is None

    def test_to_dict_finished_at_iso_format(self):
        now = datetime.utcnow()
        result = self._make_result(exit_code=0, finished_at=now)
        assert result.to_dict()["finished_at"] == now.isoformat()

    def test_repr_contains_job_name(self):
        result = self._make_result(exit_code=0)
        assert "backup" in repr(result)

    def test_repr_contains_exit_code(self):
        result = self._make_result(exit_code=42)
        assert "42" in repr(result)

    def test_default_attempt_is_one(self):
        result = self._make_result()
        assert result.attempt == 1

    def test_default_stdout_empty(self):
        result = self._make_result()
        assert result.stdout == ""

    def test_custom_stdout(self):
        result = self._make_result(stdout="backup complete")
        assert result.stdout == "backup complete"
