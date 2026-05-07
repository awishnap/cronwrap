"""Environment variable validation and injection for cron jobs."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class EnvValidationError(Exception):
    """Raised when required environment variables are missing or invalid."""

    def __init__(self, missing: List[str]) -> None:
        self.missing = missing
        super().__init__(
            f"Missing required environment variables: {', '.join(missing)}"
        )


@dataclass
class EnvConfig:
    """Configuration for environment variable handling."""

    required: List[str] = field(default_factory=list)
    defaults: Dict[str, str] = field(default_factory=dict)
    inject: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.required, list):
            raise TypeError("required must be a list of strings")
        if not isinstance(self.defaults, dict):
            raise TypeError("defaults must be a dict")
        if not isinstance(self.inject, dict):
            raise TypeError("inject must be a dict")
        for key in self.required:
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"Invalid required env var name: {key!r}")


class EnvManager:
    """Validates and prepares environment variables for a cron job."""

    def __init__(self, config: EnvConfig) -> None:
        self._config = config

    def validate(self, env: Optional[Dict[str, str]] = None) -> None:
        """Raise EnvValidationError if any required variables are absent."""
        import os

        source = env if env is not None else dict(os.environ)
        missing = [
            key for key in self._config.required if key not in source
        ]
        if missing:
            raise EnvValidationError(missing)

    def build_env(self, base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Return a merged environment dict with defaults and injected values."""
        import os

        result: Dict[str, str] = dict(os.environ) if base is None else dict(base)
        for key, value in self._config.defaults.items():
            result.setdefault(key, value)
        result.update(self._config.inject)
        return result

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"EnvManager(required={self._config.required!r}, "
            f"defaults={self._config.defaults!r}, "
            f"inject={self._config.inject!r})"
        )
