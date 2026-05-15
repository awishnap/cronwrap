"""Sensitive value redaction for logs and notifications."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Pattern


class RedactError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class RedactConfig:
    """Configuration for the redaction engine."""

    patterns: List[str] = field(default_factory=list)
    placeholder: str = "[REDACTED]"
    redact_env_values: bool = True

    def __post_init__(self) -> None:
        if not self.placeholder:
            raise RedactError("placeholder must not be blank")
        for p in self.patterns:
            if not p:
                raise RedactError("pattern must not be blank")
            try:
                re.compile(p)
            except re.error as exc:
                raise RedactError(f"invalid regex pattern {p!r}: {exc}") from exc


class Redactor:
    """Applies redaction rules to arbitrary text."""

    # Built-in patterns that are always applied.
    _BUILTIN_PATTERNS: List[str] = [
        r"(?i)(?:password|passwd|secret|token|api[_-]?key)\s*=\s*\S+",
        r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*",
    ]

    def __init__(self, config: RedactConfig | None = None) -> None:
        self.config = config or RedactConfig()
        self._compiled: List[Pattern[str]] = [
            re.compile(p) for p in self._BUILTIN_PATTERNS + list(self.config.patterns)
        ]

    def redact(self, text: str) -> str:
        """Return *text* with all sensitive values replaced by the placeholder."""
        for pattern in self._compiled:
            text = pattern.sub(self.config.placeholder, text)
        return text

    def redact_dict(self, data: dict) -> dict:
        """Return a shallow copy of *data* with sensitive string values redacted."""
        result: dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value)
            else:
                result[key] = value
        return result
