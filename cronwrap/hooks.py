"""Hook support — run callables or shell commands before/after a cron job."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class HookConfig:
    """Defines pre/post hook commands or callables for a job."""

    pre_hooks: List[str] = field(default_factory=list)
    post_hooks: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    stop_on_failure: bool = True

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError(
                f"timeout_seconds must be > 0, got {self.timeout_seconds}"
            )


class HookError(Exception):
    """Raised when a hook command fails and stop_on_failure is True."""

    def __init__(self, hook: str, returncode: int) -> None:
        self.hook = hook
        self.returncode = returncode
        super().__init__(f"Hook '{hook}' failed with exit code {returncode}")


class HookRunner:
    """Executes shell-command hooks in order."""

    def __init__(self, config: HookConfig) -> None:
        self.config = config

    def run_pre(self) -> List[int]:
        """Run all pre-hooks; return list of exit codes."""
        return self._run_hooks(self.config.pre_hooks)

    def run_post(self) -> List[int]:
        """Run all post-hooks; return list of exit codes."""
        return self._run_hooks(self.config.post_hooks)

    def _run_hooks(self, hooks: List[str]) -> List[int]:
        results: List[int] = []
        for hook in hooks:
            code = self._execute(hook)
            results.append(code)
            if code != 0 and self.config.stop_on_failure:
                raise HookError(hook, code)
        return results

    def _execute(self, command: str) -> int:
        try:
            result = subprocess.run(
                command,
                shell=True,
                timeout=self.config.timeout_seconds,
                capture_output=True,
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            return 124  # standard timeout exit code
