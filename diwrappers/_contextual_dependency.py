from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

import diwrappers._commons._data as d
import diwrappers._commons._exceptions as e

ContextualConstructor = t.Callable[
    [],
    contextlib.AbstractContextManager[d.Data],
]

P = t.ParamSpec("P")
R = t.TypeVar("R")


@dataclass
class ContextualInjector(t.Generic[d.Data]):
    """A dependency injector that manages contextual dependencies."""

    _constructor: ContextualConstructor[d.Data]
    """Function that creates new instances of the dependency."""

    _data: d.Data | None = None

    def ensure(self, fn: t.Callable[P, R]):
        """Ensure that the dependency is available within the function scope."""

        def wrapper(*args: P.args, **kwargs: P.kwargs):
            with self._constructor() as data:
                self._data = data
                try:
                    res = fn(*args, **kwargs)
                except:
                    self._data = None
                    raise
                if d.contains_value(needle=data, haystack=res):
                    raise e.DependencyLeakError
                self._data = None
            return res

        return wrapper

    def inject(
        self,
        task: t.Callable[t.Concatenate[d.Data, d.TaskParams], d.TaskReturn],
    ) -> t.Callable[d.TaskParams, d.TaskReturn]:
        @functools.wraps(task)
        def _wrapper(*args: d.TaskParams.args, **kwargs: d.TaskParams.kwargs):
            """Create and inject the dependency."""
            if self._data is None:
                raise e.MissingContextError

            return task(self._data, *args, **kwargs)

        return _wrapper


def contextual_dependency(
    func: ContextualConstructor[d.Data],
) -> ContextualInjector[d.Data]:
    return ContextualInjector(func)


if d.is_test_env():  # pragma: no cover
    import pytest

    def test_missing_context_error():
        @contextual_dependency
        @contextlib.contextmanager
        def get_db():
            yield "db_connection"

        @get_db.inject
        def use_db(db: str):
            return "using " + db

        with pytest.raises(e.MissingContextError):
            use_db()

    def test_dependency_leak_error():
        @contextual_dependency
        @contextlib.contextmanager
        def get_secret():
            yield "secret_value"

        @get_secret.ensure
        @get_secret.inject
        def leak_secret(secret: str):
            return secret

        with pytest.raises(e.DependencyLeakError):
            leak_secret()

        @get_secret.ensure
        @get_secret.inject
        def wrap_secret(secret: str):
            return f"prefix_{secret}"

        assert wrap_secret() == "prefix_secret_value"

    def test_nested_ensure_contexts():
        @contextual_dependency
        @contextlib.contextmanager
        def get_secret():
            yield "secret"

        @get_secret.ensure
        def outer():
            assert inner() == "using secret"

            @get_secret.ensure
            def nested():
                return inner()

            return nested()

        @get_secret.inject
        def inner(secret: str):
            return f"using {secret}"

        assert outer() == "using secret"

    def test_multiple_injections_same_context():
        @contextual_dependency
        @contextlib.contextmanager
        def get_db():
            yield "db"

        @get_db.ensure
        def process_data():
            res1 = func1()
            res2 = func2()
            return res1 + res2

        @get_db.inject
        def func1(db: str):
            return f"1_{db}"

        @get_db.inject
        def func2(db: str):
            return f"2_{db}"

        assert process_data() == "1_db2_db"

    def test_context_cleanup():
        cleanup_happened = False

        @contextual_dependency
        @contextlib.contextmanager
        def get_resource():
            nonlocal cleanup_happened
            yield "resource"
            cleanup_happened = True

        @get_resource.ensure
        def use_resource():
            return "ok"

        use_resource()
        assert cleanup_happened, "Context should clean up after use"

    def test_exception_during_execution():
        entered_context = False
        exited_context = False

        @contextual_dependency
        @contextlib.contextmanager
        def resource():
            nonlocal entered_context
            entered_context = True

            try:
                yield "resource"
            finally:
                nonlocal exited_context
                exited_context = True

        @resource.ensure
        @resource.inject
        def failing_function(_resource: str):
            msg = "Something went wrong"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Something went wrong"):
            failing_function()

        assert entered_context, "Context should be entered"
        assert exited_context, (
            "Context should be cleaned up even after exception"
        )

    def test_complex_dependency_leak():
        @contextual_dependency
        @contextlib.contextmanager
        def get_secret():
            yield "secret"

        @get_secret.ensure
        @get_secret.inject
        def leak_in_dict(secret: str):
            return {"data": secret}  # Leak in dict

        @get_secret.ensure
        @get_secret.inject
        def leak_in_list(secret: str):
            return [1, 2, secret]  # Leak in list

        @get_secret.ensure
        @get_secret.inject
        def leak_in_nested(secret: str):
            return {"outer": {"inner": [1, {"secret": secret}]}}  # Nested leak

        for func in [leak_in_dict, leak_in_list, leak_in_nested]:
            with pytest.raises(e.DependencyLeakError):
                func()

    def test_ensure_decorator_return_types():
        @contextual_dependency
        @contextlib.contextmanager
        def get_db():
            yield "db"

        # Test with different return types
        @get_db.ensure
        def return_none():
            return None

        number = 42

        @get_db.ensure
        def return_int():
            return number

        @get_db.ensure
        def return_dict():
            return {"safe": "value"}

        assert return_none() is None
        assert return_int() == number
        assert return_dict() == {"safe": "value"}

    def test_ensure_without_injection():
        @contextual_dependency
        @contextlib.contextmanager
        def get_db():
            yield "db"

        # ensure can be used without inject
        @get_db.ensure
        def standalone():
            return "ok"

        assert standalone() == "ok"


if __name__ == "__main__":  # pragma: no cover

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
