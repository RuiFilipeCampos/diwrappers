from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

import diwrappers._commons._data as d
import diwrappers._commons._exceptions as e

type AsyncContextualConstructor[Data] = t.Callable[
    [],
    contextlib.AbstractAsyncContextManager[Data],
]


@dataclass
class AsyncContextualInjector[Data]:
    """A dependency injector that manages contextual dependencies."""

    _constructor: AsyncContextualConstructor[Data]
    """Function that creates new instances of the dependency."""

    _data: Data | None = None

    def ensure[**P, R](self, fn: t.Callable[P, t.Awaitable[R]]):
        """Ensure that the dependency is available within the function scope."""

        async def wrapper(*args: P.args, **kwargs: P.kwargs):
            async with self._constructor() as data:
                self._data = data
                res = await fn(*args, **kwargs)
                if d.contains_value(needle=data, haystack=res):
                    raise e.DependencyLeakError
                self._data = None
            return res

        return wrapper

    def inject[**TaskParams, TaskReturn](
        self,
        task: t.Callable[t.Concatenate[Data, TaskParams], TaskReturn],
    ) -> t.Callable[TaskParams, t.Awaitable[TaskReturn]]:
        @functools.wraps(task)
        async def _wrapper(*args: TaskParams.args, **kwargs: TaskParams.kwargs):
            """Create and inject the dependency."""
            if self._data is None:
                raise e.MissingContextError

            return task(self._data, *args, **kwargs)

        return _wrapper


def async_contextual_dependency[Data](
    func: AsyncContextualConstructor[Data],
) -> AsyncContextualInjector[Data]:
    return AsyncContextualInjector(func)


if __name__ == "__main__":

    @async_contextual_dependency
    @contextlib.asynccontextmanager
    async def db_conn():
        yield 1234

    @db_conn.inject
    def do_work(db_conn: int):
        return db_conn

    @db_conn.ensure
    async def some_other_function(): ...

    async def main():
        return await do_work()

    res = main()
