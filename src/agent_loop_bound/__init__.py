"""agent-loop-bound-py — hard cap on agent loop iterations to prevent runaway execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class LoopLimitExceeded(Exception):
    """Raised when an agent loop exceeds its configured iteration limit."""

    def __init__(self, limit: int, label: str = "") -> None:
        self.limit = limit
        self.label = label
        prefix = f"[{label}] " if label else ""
        super().__init__(f"{prefix}Agent loop exceeded {limit} iteration(s).")


@dataclass
class LoopBound:
    """
    Hard cap on agent loop iterations.

    Use as a context manager or call `.tick()` each iteration.
    Raises LoopLimitExceeded when the cap is hit.

    Example::

        bound = LoopBound(max_iterations=10)

        while not done:
            bound.tick()          # raises after 10 calls
            result = agent.step()
            done = result.done

        # Or as a context manager (same effect):
        with LoopBound(max_iterations=10) as bound:
            while not done:
                bound.tick()
                ...

        # Wrap a callable:
        @bound.wrap
        def run_loop():
            while not done:
                bound.tick()
                ...
    """

    max_iterations: int
    label: str = ""
    _count: int = field(default=0, init=False, repr=False)

    def tick(self) -> int:
        """
        Advance the iteration counter by one.

        Returns:
            The current iteration number (1-indexed).

        Raises:
            LoopLimitExceeded: If `max_iterations` has been reached.
        """
        self._count += 1
        if self._count > self.max_iterations:
            raise LoopLimitExceeded(self.max_iterations, self.label)
        return self._count

    @property
    def count(self) -> int:
        """Number of iterations completed so far."""
        return self._count

    @property
    def remaining(self) -> int:
        """Iterations remaining before the limit is hit."""
        return max(0, self.max_iterations - self._count)

    @property
    def exhausted(self) -> bool:
        """True if the limit has been reached (tick would raise)."""
        return self._count >= self.max_iterations

    def reset(self) -> "LoopBound":
        """Reset the counter to zero."""
        self._count = 0
        return self

    def __enter__(self) -> "LoopBound":
        self._count = 0
        return self

    def __exit__(self, *_) -> None:
        pass

    def wrap(self, fn: Callable) -> Callable:
        """Decorator that resets this bound and runs fn in a context."""
        import functools

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return fn(*args, **kwargs)
        return wrapper


def bounded(max_iterations: int, label: str = "") -> LoopBound:
    """Convenience factory for LoopBound."""
    return LoopBound(max_iterations=max_iterations, label=label)


def iter_bounded(iterable, max_iterations: int, label: str = ""):
    """
    Iterate over an iterable, raising LoopLimitExceeded after max_iterations.

    Example::

        for item in iter_bounded(agent_steps(), max_iterations=20):
            process(item)
    """
    bound = LoopBound(max_iterations=max_iterations, label=label)
    for item in iterable:
        bound.tick()
        yield item


__all__ = ["LoopBound", "LoopLimitExceeded", "bounded", "iter_bounded"]
