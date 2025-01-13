from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

type ContextualConstructor[Data] = t.Callable[[], t.ContextManager[Data]]


@dataclass
class ContextualInjector[Data]:
    _constructor: ContextualConstructor[Data]
    """Function that creates new instances of the dependency."""

    _data: Data | None = None

    def ensure[**P, R](self, fn: t.Callable[P, R]):
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            with self._constructor() as data:
                self._data = data
                res = fn(*args, **kwargs)
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
                msg = "Please use ensure."
                raise RuntimeError(msg)

            return task(self._data, *args, **kwargs)

        return _wrapper


def contextual_dependency[Data](func: ContextualConstructor[Data]) -> ContextualInjector[Data]:
    return ContextualInjector(func)


@contextual_dependency
@contextlib.contextmanager
def db_conn():
    yield 1234


@db_conn.inject
def do_work(db_conn: int):
    return db_conn


@db_conn.ensure
def main():
    return do_work()


if __name__ == "__main__":
    res = main()
