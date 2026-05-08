"""Tests for cronwrap.pipeline."""
import pytest
from unittest.mock import MagicMock, call

from cronwrap.pipeline import Pipeline, PipelineStep, PipelineError, StepResult
from cronwrap.checkpoint import CheckpointConfig, CheckpointManager


def _make_step(name: str, fn=None) -> PipelineStep:
    return PipelineStep(name=name, fn=fn or (lambda: None))


class TestStepResult:
    def test_success_flag(self):
        r = StepResult(name="s", success=True, duration=1.0)
        assert r.success is True
        assert r.error is None

    def test_failed_has_error(self):
        r = StepResult(name="s", success=False, duration=0.5, error="boom")
        assert not r.success
        assert r.error == "boom"


class TestPipeline:
    def test_all_steps_run_in_order(self):
        calls = []
        steps = [
            _make_step("a", lambda: calls.append("a")),
            _make_step("b", lambda: calls.append("b")),
            _make_step("c", lambda: calls.append("c")),
        ]
        p = Pipeline("job", steps)
        results = p.run()
        assert calls == ["a", "b", "c"]
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_pipeline_stops_on_failure(self):
        calls = []

        def fail():
            raise RuntimeError("oops")

        steps = [
            _make_step("a", lambda: calls.append("a")),
            _make_step("b", fail),
            _make_step("c", lambda: calls.append("c")),
        ]
        p = Pipeline("job", steps)
        with pytest.raises(PipelineError) as exc_info:
            p.run()
        assert exc_info.value.step == "b"
        assert "c" not in calls

    def test_pipeline_error_wraps_cause(self):
        cause = ValueError("bad")
        steps = [_make_step("x", lambda: (_ for _ in ()).throw(cause))]
        p = Pipeline("job", steps)
        with pytest.raises(PipelineError) as exc_info:
            p.run()
        assert exc_info.value.cause is cause

    def test_all_succeeded_true(self):
        p = Pipeline("job", [_make_step("a"), _make_step("b")])
        p.run()
        assert p.all_succeeded is True

    def test_all_succeeded_false_on_error(self):
        p = Pipeline("job", [_make_step("a", lambda: (_ for _ in ()).throw(RuntimeError()))])
        with pytest.raises(PipelineError):
            p.run()
        assert p.all_succeeded is False

    def test_duration_recorded(self):
        p = Pipeline("job", [_make_step("a")])
        results = p.run()
        assert results[0].duration >= 0

    def test_checkpoint_skips_completed_steps(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, directory=str(tmp_path))
        mgr = CheckpointManager(cfg)
        mgr.save("job", {"completed": ["a"]})

        calls = []
        steps = [
            _make_step("a", lambda: calls.append("a")),
            _make_step("b", lambda: calls.append("b")),
        ]
        p = Pipeline("job", steps, checkpoint_manager=mgr)
        p.run()
        assert "a" not in calls
        assert "b" in calls

    def test_checkpoint_cleared_on_success(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, directory=str(tmp_path))
        mgr = CheckpointManager(cfg)
        p = Pipeline("job", [_make_step("a")], checkpoint_manager=mgr)
        p.run()
        assert not mgr.exists("job")

    def test_checkpoint_persists_on_failure(self, tmp_path):
        cfg = CheckpointConfig(enabled=True, directory=str(tmp_path))
        mgr = CheckpointManager(cfg)
        steps = [
            _make_step("a"),
            _make_step("b", lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
        ]
        p = Pipeline("job", steps, checkpoint_manager=mgr)
        with pytest.raises(PipelineError):
            p.run()
        assert mgr.exists("job")
