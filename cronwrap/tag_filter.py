"""Utilities for evaluating tag-based filter expressions."""
from __future__ import annotations
from typing import Set


class TagFilterError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TagFilter:
    """Evaluates simple tag filter expressions against a set of tags.

    Supported syntax (space-separated tokens):
        - ``tag``          – job must have this tag
        - ``+tag``         – alias for required tag
        - ``-tag``         – job must NOT have this tag
        - ``tag1 tag2``    – job must have both tags (AND logic)
    """

    def __init__(self, expression: str) -> None:
        if not expression or not expression.strip():
            raise TagFilterError("Filter expression must be a non-empty string.")
        self.expression = expression.strip()
        self._required: Set[str] = set()
        self._excluded: Set[str] = set()
        self._parse(self.expression)

    def _parse(self, expression: str) -> None:
        for token in expression.split():
            if token.startswith("-"):
                tag = token[1:].lower()
                if not tag:
                    raise TagFilterError("Exclusion token '-' must be followed by a tag name.")
                self._excluded.add(tag)
            elif token.startswith("+"):
                tag = token[1:].lower()
                if not tag:
                    raise TagFilterError("Inclusion token '+' must be followed by a tag name.")
                self._required.add(tag)
            else:
                self._required.add(token.lower())

    def matches(self, tags: Set[str]) -> bool:
        """Return True if *tags* satisfies the filter expression."""
        normalised = {t.lower() for t in tags}
        if not self._required.issubset(normalised):
            return False
        if self._excluded & normalised:
            return False
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TagFilter(required={sorted(self._required)}, "
            f"excluded={sorted(self._excluded)})"
        )
