from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

import diwrappers._data as d

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
                if d.contains_value(needle=data, haystack=res):
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
