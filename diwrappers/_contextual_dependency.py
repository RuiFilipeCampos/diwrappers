from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

import diwrappers._data as d

MAX_DEPTH = 5

type ContextualConstructor[Data] = t.Callable[[], contextlib.AbstractContextManager[Data]]


class DependencyInjectionError(Exception):
    """Base exception for all dependency injection related errors."""


class DependencyLeakError(DependencyInjectionError):
    """Raised when a dependency is returned or leaked from its context."""

    def __init__(self) -> None:
        super().__init__("Dependency cannot be returned or leaked from its context")


class MissingContextError(DependencyInjectionError):
    """Raised when trying to inject a dependency without an ensure context."""

    def __init__(self) -> None:
        super().__init__(
            "Dependency injection requires an ensure context - please use ensure decorator",
        )


def contains_value(needle: object, haystack: object, depth: int = 1) -> bool:
    """Check if needle exists within haystack, including in nested structures.

    Examples:
        >>> contains_value(5, 5)
        True

        >>> contains_value("test", "different")
        False

        >>> contains_value(42, [1, 2, [3, 4, [42]]])
        True

        >>> contains_value("x", {"a": 1, "b": {"c": "x"}})
        True

        >>> contains_value("missing", [1, 2, 3])
        False

        >>> contains_value(True, {"a": False, "b": [{"c": True}]})
        True

        >>> class TestClass:
        ...     def __init__(self):
        ...         self.value = ["hidden"]
        >>> obj = TestClass()
        >>> contains_value("hidden", obj)
        True

        >>> contains_value(None, [1, None, 3])
        True

        >>> contains_value("key", {"key": "value"})
        True

    """
    if needle == haystack:
        return True

    if isinstance(haystack, (int, str, bool)) or depth == MAX_DEPTH:
        return False

    depth = depth + 1

    if d.is_tuple(haystack) or d.is_list(haystack):
        return any(contains_value(needle, item, depth=depth) for item in haystack)

    if d.is_dict(haystack):
        return any(
            contains_value(needle, k, depth=depth) or contains_value(needle, v, depth=depth)
            for k, v in haystack.items()
        )

    if hasattr(haystack, "__dict__"):
        return contains_value(needle, vars(haystack), depth=depth)

    return False


@dataclass
class ContextualInjector[Data]:
    """A dependency injector that manages contextual dependencies."""

    _constructor: ContextualConstructor[Data]
    """Function that creates new instances of the dependency."""

    _data: Data | None = None

    def ensure[**P, R](self, fn: t.Callable[P, R]):
        """Ensure that the dependency is available within the function scope."""

        def wrapper(*args: P.args, **kwargs: P.kwargs):
            with self._constructor() as data:
                self._data = data
                res = fn(*args, **kwargs)
                if contains_value(needle=data, haystack=res):
                    raise DependencyLeakError
                self._data = None
            return res

        return wrapper

    def inject[**TaskParams, TaskReturn](
        self,
        task: t.Callable[t.Concatenate[Data, TaskParams], TaskReturn],
    ) -> t.Callable[TaskParams, TaskReturn]:
        @functools.wraps(task)
        def _wrapper(*args: TaskParams.args, **kwargs: TaskParams.kwargs):
            """Create and inject the dependency."""
            if self._data is None:
                raise MissingContextError

            return task(self._data, *args, **kwargs)

        return _wrapper


def contextual_dependency[Data](func: ContextualConstructor[Data]) -> ContextualInjector[Data]:
    return ContextualInjector(func)


if __name__ == "__main__":

    @contextual_dependency
    @contextlib.contextmanager
    def db_conn():
        yield 1234

    @db_conn.inject
    def do_work(db_conn: int):
        return db_conn

    @db_conn.ensure
    def some_other_function(): ...

    def main():
        return do_work()

    res = main()
