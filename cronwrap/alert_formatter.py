"""Formats alert messages for different output channels."""
from dataclasses import dataclass
from typing import List


@dataclass
class AlertPayload:
    """Structured representation of an alert event."""
    job_name: str
    messages: List[str]
    exit_code: int
    duration_seconds: float

    @property
    def subject(self) -> str:
        return f"[cronwrap] Alert for job '{self.job_name}'"

    def as_text(self) -> str:
        lines = [
            self.subject,
            f"Job      : {self.job_name}",
            f"Exit code: {self.exit_code}",
            f"Duration : {self.duration_seconds:.2f}s",
            "",
            "Triggered alerts:",
        ]
        for msg in self.messages:
            lines.append(f"  - {msg}")
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "alerts": self.messages,
        }


class AlertFormatter:
    """Converts raw alert messages into structured AlertPayload objects."""

    @staticmethod
    def format(
        job_name: str,
        messages: List[str],
        exit_code: int,
        duration_seconds: float,
    ) -> AlertPayload:
        if not messages:
            raise ValueError("Cannot format an empty alert message list")
        return AlertPayload(
            job_name=job_name,
            messages=messages,
            exit_code=exit_code,
            duration_seconds=duration_seconds,
        )
