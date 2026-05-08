"""Captures stdout/stderr from cron job subprocesses with optional truncation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OutputConfig:
    max_bytes: int = 65536  # 64 KB default cap
    capture_stdout: bool = True
    capture_stderr: bool = True
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        if self.max_bytes < 0:
            raise ValueError("max_bytes must be >= 0")
        if not self.encoding:
            raise ValueError("encoding must be a non-empty string")


@dataclass
class CapturedOutput:
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False

    def combined(self) -> str:
        """Return stdout and stderr joined with a separator when both are present."""
        parts = [p for p in (self.stdout, self.stderr) if p]
        return "\n--- stderr ---\n".join(parts) if len(parts) == 2 else (parts[0] if parts else "")

    def is_empty(self) -> bool:
        return not self.stdout and not self.stderr

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "truncated": self.truncated,
        }


class OutputCapture:
    """Processes raw bytes from a subprocess into a CapturedOutput respecting config limits."""

    def __init__(self, config: Optional[OutputConfig] = None) -> None:
        self._config = config or OutputConfig()

    def process(
        self,
        stdout_bytes: Optional[bytes],
        stderr_bytes: Optional[bytes],
    ) -> CapturedOutput:
        cfg = self._config
        truncated = False

        def decode(raw: Optional[bytes], capture: bool) -> str:
            if not capture or not raw:
                return ""
            return raw.decode(cfg.encoding, errors="replace")

        stdout_raw = decode(stdout_bytes, cfg.capture_stdout)
        stderr_raw = decode(stderr_bytes, cfg.capture_stderr)

        if cfg.max_bytes > 0:
            combined_len = len(stdout_raw.encode(cfg.encoding)) + len(stderr_raw.encode(cfg.encoding))
            if combined_len > cfg.max_bytes:
                truncated = True
                # Trim stdout first, then stderr to stay within budget
                budget = cfg.max_bytes
                stdout_bytes_enc = stdout_raw.encode(cfg.encoding)[:budget]
                stdout_raw = stdout_bytes_enc.decode(cfg.encoding, errors="replace")
                budget -= len(stdout_bytes_enc)
                if budget > 0:
                    stderr_raw = stderr_raw.encode(cfg.encoding)[:budget].decode(cfg.encoding, errors="replace")
                else:
                    stderr_raw = ""

        return CapturedOutput(stdout=stdout_raw, stderr=stderr_raw, truncated=truncated)
