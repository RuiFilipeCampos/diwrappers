from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

import diwrappers._commons._data as d
import diwrappers._commons._exceptions as e

AsyncContextualConstructor = t.Callable[
    [],
    contextlib.AbstractAsyncContextManager[d.Data],
]

P = t.ParamSpec("P")
R = t.TypeVar("R")


@dataclass
class AsyncContextualInjector(t.Generic[d.Data]):
    """A dependency injector that manages contextual dependencies."""

    _constructor: AsyncContextualConstructor[d.Data]
    """Function that creates new instances of the dependency."""

    _data: d.Data | None = None

    def ensure(self, fn: t.Callable[P, t.Awaitable[R]]):
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

    def inject(
        self,
        task: t.Callable[
            t.Concatenate[d.Data, d.TaskParams], t.Awaitable[d.TaskReturn]
        ],
    ) -> t.Callable[d.TaskParams, t.Awaitable[d.TaskReturn]]:
        @functools.wraps(task)
        async def _wrapper(
            *args: d.TaskParams.args,
            **kwargs: d.TaskParams.kwargs,
        ):
            """Create and inject the dependency."""
            if self._data is None:
                raise e.MissingContextError

            return await task(self._data, *args, **kwargs)

        return _wrapper


def async_contextual_dependency(
    func: AsyncContextualConstructor[d.Data],
) -> AsyncContextualInjector[d.Data]:
    return AsyncContextualInjector(func)


if __name__ == "__main__":  # pragma: no cover

    @async_contextual_dependency
    @contextlib.asynccontextmanager
    async def db_conn():
        yield 1234

    @db_conn.inject
    async def do_work(db_conn: int):
        return db_conn

    @db_conn.ensure
    async def some_other_function(): ...

    async def main():
        return await do_work()

    res = main()

if d.is_test_env():  # pragma: no cover
    import pytest

    @pytest.mark.asyncio
    async def test_missing_context_error():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_db():
            yield "db_connection"

        @get_db.inject
        async def use_db(db: str):
            return "using " + db

        # Try to use without ensure context
        with pytest.raises(e.MissingContextError):
            await use_db()

    @pytest.mark.asyncio
    async def test_dependency_leak_error():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_secret():
            yield "secret_value"

        @get_secret.ensure
        @get_secret.inject
        async def leak_secret(secret: str):
            return secret

        with pytest.raises(e.DependencyLeakError):
            await leak_secret()

        @get_secret.ensure
        @get_secret.inject
        async def wrap_secret(secret: str):
            return f"prefix_{secret}"

        assert await wrap_secret() == "prefix_secret_value"

    @pytest.mark.asyncio
    async def test_nested_ensure_contexts():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_resource():
            yield "resource"

        @get_resource.ensure
        async def outer():
            # Should work - context exists
            assert await inner() == "using resource"

            @get_resource.ensure
            async def nested():
                return await inner()

            return await nested()

        @get_resource.inject
        async def inner(resource: str):
            return f"using {resource}"

        assert await outer() == "using resource"

    @pytest.mark.asyncio
    async def test_cleanup():
        cleanup_called = False

        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_resource():
            try:
                yield "resource"
            finally:
                nonlocal cleanup_called
                cleanup_called = True

        @get_resource.ensure
        async def use_resource():
            return "ok"

        await use_resource()
        assert cleanup_called, "Cleanup should be called"

    @pytest.mark.asyncio
    async def test_exception_handling():
        cleanup_called = False

        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_resource():
            try:
                yield "resource"
            finally:
                nonlocal cleanup_called
                cleanup_called = True

        @get_resource.ensure
        @get_resource.inject
        async def failing_function(_resource: str):
            msg = "Test error"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Test error"):
            await failing_function()

        assert cleanup_called, "Cleanup should be called even after exception"

    @pytest.mark.asyncio
    async def test_complex_dependency_leak():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_secret():
            yield "secret"

        @get_secret.ensure
        @get_secret.inject
        async def leak_in_dict(secret: str):
            return {"data": secret}

        @get_secret.ensure
        @get_secret.inject
        async def leak_in_list(secret: str):
            return [1, secret, 3]

        @get_secret.ensure
        @get_secret.inject
        async def leak_in_nested(secret: str):
            return {"outer": {"inner": [1, {"secret": secret}]}}

        for func in [leak_in_dict, leak_in_list, leak_in_nested]:
            with pytest.raises(e.DependencyLeakError):
                await func()

    @pytest.mark.asyncio
    async def test_multiple_injections():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_db():
            yield "db"

        @get_db.ensure
        async def process_data():
            res1 = await func1()
            res2 = await func2()
            return [res1, res2]

        @get_db.inject
        async def func1(db: str):
            return f"1_{db}"

        @get_db.inject
        async def func2(db: str):
            return f"2_{db}"

        result = await process_data()
        assert result == ["1_db", "2_db"]

    @pytest.mark.asyncio
    async def test_async_context_timing():
        events: list[str] = []

        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_resource():
            events.append("enter")
            yield "resource"
            events.append("exit")

        @get_resource.ensure
        @get_resource.inject
        async def use_resource(resource: str):
            events.append("use")
            return resource + "abc"

        await use_resource()
        assert events == ["enter", "use", "exit"]

    @pytest.mark.asyncio
    async def test_injection_with_parameters():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_prefix():
            yield "test"

        @get_prefix.ensure
        @get_prefix.inject
        async def format_string(prefix: str, name: str, count: int = 1):
            return f"{prefix}-{name}-{count}"

        result = await format_string("user", count=5)
        assert result == "test-user-5"

    @pytest.mark.asyncio
    async def test_ensure_without_inject():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def get_db():
            yield "db"

        # ensure without inject should work
        @get_db.ensure
        async def standalone():
            return "ok"

        assert await standalone() == "ok"

    @pytest.mark.asyncio
    async def test_multiple_resources():
        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def db():
            yield "db"

        @async_contextual_dependency
        @contextlib.asynccontextmanager
        async def cache():
            yield "cache"

        @db.ensure
        @cache.ensure
        @db.inject
        @cache.inject
        async def use_both(cache: str, db: str):
            return f"{cache}-{db}"

        assert await use_both() == "cache-db"
