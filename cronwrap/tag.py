"""Job tagging and filtering support for cronwrap."""
from dataclasses import dataclass, field
from typing import List, Set


class TagValidationError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class TagConfig:
    """Configuration for job tags."""
    tags: List[str] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for tag in self.tags:
            if not isinstance(tag, str) or not tag.strip():
                raise TagValidationError("Each tag must be a non-empty string.")
            if " " in tag:
                raise TagValidationError(f"Tag '{tag}' must not contain spaces.")
        for tag in self.required_tags:
            if not isinstance(tag, str) or not tag.strip():
                raise TagValidationError("Each required tag must be a non-empty string.")
        self.tags = [t.lower() for t in self.tags]
        self.required_tags = [t.lower() for t in self.required_tags]


class TagManager:
    """Manages tag registration and filtering for cron jobs."""

    def __init__(self) -> None:
        self._registry: dict[str, Set[str]] = {}

    def register(self, job_name: str, config: TagConfig) -> None:
        """Register tags for a named job."""
        if not job_name or not job_name.strip():
            raise TagValidationError("job_name must be a non-empty string.")
        self._registry[job_name] = set(config.tags)

    def get_tags(self, job_name: str) -> Set[str]:
        """Return the set of tags for a job, or empty set if unknown."""
        return set(self._registry.get(job_name, set()))

    def filter_jobs(self, tag: str) -> List[str]:
        """Return job names that carry the given tag."""
        tag = tag.lower()
        return [name for name, tags in self._registry.items() if tag in tags]

    def has_tag(self, job_name: str, tag: str) -> bool:
        """Return True if the job is registered with the given tag."""
        return tag.lower() in self.get_tags(job_name)

    def all_jobs(self) -> List[str]:
        """Return all registered job names."""
        return list(self._registry.keys())

    def unregister(self, job_name: str) -> None:
        """Remove a job and its tags from the registry.

        Raises TagValidationError if the job is not registered.
        """
        if job_name not in self._registry:
            raise TagValidationError(f"Job '{job_name}' is not registered.")
        del self._registry[job_name]
