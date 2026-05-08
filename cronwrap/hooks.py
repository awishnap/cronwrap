from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class HookConfig:
    pre_run: List[Callable] = field(default_factory=list)
    post_run: List[Callable] = field(default_factory=list)
    on_failure: List[Callable] = field(default_factory=list)
    on_success: List[Callable] = field(default_factory=list)
    stop_on_error: bool = False

    def __post_init__(self):
        for attr in ("pre_run", "post_run", "on_failure", "on_success"):
            val = getattr(self, attr)
            if not isinstance(val, list):
                raise TypeError(f"{attr} must be a list of callables")
            for item in val:
                if not callable(item):
                    raise TypeError(f"All items in {attr} must be callable")


class HookError(Exception):
    def __init__(self, hook_name: str, original: Exception):
        self.hook_name = hook_name
        self.original = original
        super().__init__(f"Hook '{hook_name}' raised: {original}")


class HookRunner:
    def __init__(self, config: HookConfig):
        self.config = config

    def _run_hooks(self, hooks: List[Callable], context: Optional[dict] = None) -> List[HookError]:
        errors: List[HookError] = []
        ctx = context or {}
        for hook in hooks:
            try:
                hook(ctx)
            except Exception as exc:
                err = HookError(getattr(hook, "__name__", repr(hook)), exc)
                if self.config.stop_on_error:
                    raise err
                errors.append(err)
        return errors

    def run_pre(self, context: Optional[dict] = None) -> List[HookError]:
        return self._run_hooks(self.config.pre_run, context)

    def run_post(self, context: Optional[dict] = None) -> List[HookError]:
        return self._run_hooks(self.config.post_run, context)

    def run_on_success(self, context: Optional[dict] = None) -> List[HookError]:
        return self._run_hooks(self.config.on_success, context)

    def run_on_failure(self, context: Optional[dict] = None) -> List[HookError]:
        return self._run_hooks(self.config.on_failure, context)
