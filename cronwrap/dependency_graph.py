"""Topological ordering and cycle detection for multi-job dependency graphs."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Set


class CyclicDependencyError(Exception):
    """Raised when a cycle is detected in the dependency graph."""

    def __init__(self, cycle: List[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Cyclic dependency detected: {' -> '.join(cycle)}")


class DependencyGraph:
    """Directed acyclic graph of job dependencies with topological sort."""

    def __init__(self) -> None:
        self._deps: Dict[str, Set[str]] = defaultdict(set)

    def add_job(self, job: str, depends_on: List[str] | None = None) -> None:
        """Register *job* and optionally declare its upstream dependencies."""
        if not job.strip():
            raise ValueError("Job name must be a non-blank string")
        self._deps.setdefault(job, set())
        for dep in depends_on or []:
            if not dep.strip():
                raise ValueError("Dependency name must be a non-blank string")
            self._deps[job].add(dep)
            self._deps.setdefault(dep, set())

    def dependencies_of(self, job: str) -> Set[str]:
        """Return the direct dependencies of *job*."""
        return set(self._deps.get(job, set()))

    def topological_order(self) -> List[str]:
        """Return jobs in topological order (dependencies first).

        Raises *CyclicDependencyError* if a cycle is found.
        """
        in_degree: Dict[str, int] = {job: 0 for job in self._deps}
        for job, deps in self._deps.items():
            for dep in deps:
                in_degree[dep]  # ensure key exists (defaultdict)
                in_degree[job] += 1  # job depends on dep, so job has higher in-degree

        # Reset and compute correctly: edge is dep -> job
        in_degree = {job: 0 for job in self._deps}
        for job, deps in self._deps.items():
            for _dep in deps:
                in_degree[job] += 1

        queue: deque[str] = deque(j for j, d in in_degree.items() if d == 0)
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            # find jobs that depend on *node* and reduce their in-degree
            for job, deps in self._deps.items():
                if node in deps:
                    in_degree[job] -= 1
                    if in_degree[job] == 0:
                        queue.append(job)

        if len(order) != len(self._deps):
            remaining = [j for j in self._deps if j not in order]
            raise CyclicDependencyError(remaining)

        return order

    def __len__(self) -> int:
        return len(self._deps)

    def __repr__(self) -> str:  # pragma: no cover
        return f"DependencyGraph(jobs={list(self._deps.keys())})"
