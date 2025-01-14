from __future__ import annotations

import contextlib
import functools
import typing as t
from dataclasses import dataclass

MAX_DEPTH = 5

type ContextualConstructor[Data] = t.Callable[[], t.ContextManager[Data]]


def is_tuple(val: object) -> t.TypeIs[tuple[object]]:
    return isinstance(val, tuple)


def is_list(val: object) -> t.TypeIs[list[object]]:
    return isinstance(val, list)


def is_dict(val: object) -> t.TypeIs[dict[object, object]]:
    return isinstance(val, dict)


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

    if is_tuple(haystack) or is_list(haystack):
        return any(contains_value(needle, item, depth=depth) for item in haystack)

    if is_dict(haystack):
        return any(
            contains_value(needle, k, depth=depth) or contains_value(needle, v, depth=depth)
            for k, v in haystack.items()
        )

    if hasattr(haystack, "__dict__"):
        return contains_value(needle, vars(haystack), depth=depth)

    return False


@dataclass
class ContextualInjector[Data]:
    """A dependency injector that manages contextual dependencies.

    Examples:
        >>> @dataclass
        ... class Database:
        ...     connection: str
        ...
        >>> @contextlib.contextmanager
        ... def create_db():
        ...     db = Database("test_connection")
        ...     yield db
        ...
        >>> db_injector = contextual_dependency(create_db)
        >>>
        >>> @db_injector.ensure
        ... def process_data():
        ...     @db_injector.inject
        ...     def _inner(db: Database):
        ...         return f"Using {db.connection}"
        ...     return _inner()
        >>>
        >>> process_data()
        'Using test_connection'

        Example showing error when returning injected dependency:
            >>> @db_injector.ensure
            ... def bad_function():
            ...     @db_injector.inject
            ...     def _inner(db: Database):
            ...         return db  # This will raise an error
            ...     return _inner()
            >>> try:
            ...     bad_function()
            ... except RuntimeError:
            ...     print("Caught expected RuntimeError")
            Caught expected RuntimeError

        Example showing error when using inject without ensure:
            >>> @db_injector.inject
            ... def standalone_function(db: Database):
            ...     return f"Using {db.connection}"
            >>> try:
            ...     standalone_function()
            ... except RuntimeError as e:
            ...     print(str(e))
            Please use ensure.

    """

    _constructor: ContextualConstructor[Data]
    """Function that creates new instances of the dependency."""

    _data: Data | None = None

    def ensure[**P, R](self, fn: t.Callable[P, R]):
        """Ensure that the dependency is available within the function scope.

        >>> @dataclass
        ... class Resource:
        ...     name: str

        >>> @contextlib.contextmanager
        ... def create_resource():
        ...     yield Resource("test")
        >>> injector = contextual_dependency(create_resource)
        >>> @injector.ensure
        ... def use_resource():
        ...     return "success"
        >>> use_resource()
        'success'
        """

        def wrapper(*args: P.args, **kwargs: P.kwargs):
            with self._constructor() as data:
                self._data = data
                res = fn(*args, **kwargs)
                if contains_value(needle=data, haystack=res):
                    raise RuntimeError
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


if __name__ == "__main__":

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

    res = main()
