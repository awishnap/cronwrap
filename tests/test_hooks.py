import pytest
from cronwrap.hooks import HookConfig, HookError, HookRunner


def _noop(ctx):
    pass


def _failing(ctx):
    raise ValueError("hook failed")


def _recording(store):
    def hook(ctx):
        store.append(ctx)
    return hook


class TestHookConfig:
    def test_defaults(self):
        cfg = HookConfig()
        assert cfg.pre_run == []
        assert cfg.post_run == []
        assert cfg.on_failure == []
        assert cfg.on_success == []
        assert cfg.stop_on_error is False

    def test_custom_callables(self):
        cfg = HookConfig(pre_run=[_noop], on_success=[_noop])
        assert len(cfg.pre_run) == 1
        assert len(cfg.on_success) == 1

    def test_non_callable_raises(self):
        with pytest.raises(TypeError):
            HookConfig(pre_run=["not_callable"])

    def test_non_list_raises(self):
        with pytest.raises(TypeError):
            HookConfig(pre_run=_noop)


class TestHookRunner:
    def test_run_pre_calls_hooks(self):
        store = []
        cfg = HookConfig(pre_run=[_recording(store)])
        runner = HookRunner(cfg)
        runner.run_pre({"job": "test"})
        assert store == [{"job": "test"}]

    def test_run_post_calls_hooks(self):
        store = []
        cfg = HookConfig(post_run=[_recording(store)])
        runner = HookRunner(cfg)
        runner.run_post()
        assert len(store) == 1

    def test_failing_hook_returns_errors_by_default(self):
        cfg = HookConfig(pre_run=[_failing])
        runner = HookRunner(cfg)
        errors = runner.run_pre()
        assert len(errors) == 1
        assert isinstance(errors[0], HookError)
        assert "_failing" in str(errors[0])

    def test_stop_on_error_raises(self):
        cfg = HookConfig(pre_run=[_failing], stop_on_error=True)
        runner = HookRunner(cfg)
        with pytest.raises(HookError):
            runner.run_pre()

    def test_multiple_hooks_all_called(self):
        store = []
        cfg = HookConfig(on_success=[_recording(store), _recording(store)])
        runner = HookRunner(cfg)
        runner.run_on_success()
        assert len(store) == 2

    def test_on_failure_called(self):
        store = []
        cfg = HookConfig(on_failure=[_recording(store)])
        runner = HookRunner(cfg)
        runner.run_on_failure({"exit_code": 1})
        assert store[0]["exit_code"] == 1

    def test_no_errors_on_success(self):
        cfg = HookConfig(pre_run=[_noop, _noop])
        runner = HookRunner(cfg)
        errors = runner.run_pre()
        assert errors == []
