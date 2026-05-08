"""Pre/post execution hooks for cron jobs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)

HookFn = Callable[[str, dict], None]


@dataclass
class HookConfig:
    pre_run: list[HookFn] = field(default_factory=list)
    post_run: list[HookFn] = field(default_factory=list)
    on_failure: list[HookFn] = field(default_factory=list)
    stop_on_pre_error: bool = False


class HookError(Exception):
    def __init__(self, hook_name: str, cause: Exception) -> None:
        super().__init__(f"Hook '{hook_name}' raised: {cause}")
        self.hook_name = hook_name
        self.cause = cause


class HookRunner:
    """Invokes registered hooks around job execution."""

    def __init__(self, job_name: str, config: HookConfig) -> None:
        self.job_name = job_name
        self.config = config

    def _run_hooks(self, hooks: list[HookFn], context: dict, *, stop_on_error: bool = False) -> None:
        for hook in hooks:
            name = getattr(hook, "__name__", repr(hook))
            try:
                hook(self.job_name, context)
            except Exception as exc:  # noqa: BLE001
                log.warning("Hook '%s' failed: %s", name, exc)
                if stop_on_error:
                    raise HookError(name, exc) from exc

    def run_pre(self, context: Optional[dict] = None) -> None:
        self._run_hooks(
            self.config.pre_run,
            context or {},
            stop_on_error=self.config.stop_on_pre_error,
        )

    def run_post(self, context: Optional[dict] = None) -> None:
        self._run_hooks(self.config.post_run, context or {})

    def run_on_failure(self, context: Optional[dict] = None) -> None:
        self._run_hooks(self.config.on_failure, context or {})

    def run_all(
        self,
        execute_fn: Callable[[], None],
        context: Optional[dict] = None,
    ) -> None:
        ctx = context or {}
        self.run_pre(ctx)
        try:
            execute_fn()
        except Exception:
            self.run_on_failure(ctx)
            raise
        finally:
            self.run_post(ctx)
