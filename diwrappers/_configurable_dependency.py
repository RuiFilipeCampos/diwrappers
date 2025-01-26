import contextlib
import enum
import functools
import typing as t
import uuid
from collections import abc
from dataclasses import dataclass

import diwrappers._commons._data as d

InjectorConfig = t.ParamSpec("InjectorConfig")


@dataclass
class ConfigurableInjector(t.Generic[InjectorConfig, d.Data]):
    """
    A dependency injection container.

    This class provides a flexible way to manage dependencies in your
    application, supporting both regular dependency injection and
    testing scenarios through context managers that allow temporary
    dependency replacement.

    """

    _constructor: t.Callable[InjectorConfig, d.Data]
    """Function that creates new instances of the dependency."""

    @contextlib.contextmanager
    def fake_value(self, val: d.Data) -> abc.Generator[d.Data, None, None]:
        """
        Temporarily replace the dependency with a specific value.

        Args:
            val: The value to use instead of the normal dependency.

        Yields:
            The provided fake value.

        """
        actual_constructor = self._constructor

        def temp_constructor(
            *_args: d.TaskParams.args,
            **_kwargs: d.TaskParams.kwargs,
        ):
            return val

        self._constructor = temp_constructor
        try:
            yield val
        finally:
            self._constructor = actual_constructor

    def faker(self, fake_constructor: t.Callable[InjectorConfig, d.Data]):
        """
        Create a context manager to replace the dependency constructor.

        Args:
            fake_constructor:
                A callable that will temporarily replace the normal
                dependency constructor.

        Returns:
            A context manager that can be used to temporarily
            replace the dependency constructor.

        """

        @contextlib.contextmanager
        def wrapper():
            tmp_constructor = self._constructor
            self._constructor = fake_constructor
            try:
                yield
            finally:
                self._constructor = tmp_constructor

        return wrapper

    def inject(
        self,
        *args: InjectorConfig.args,
        **kwargs: InjectorConfig.kwargs,
    ):
        def decorator(
            task: t.Callable[t.Concatenate[d.Data, d.TaskParams], d.TaskReturn],
        ) -> t.Callable[d.TaskParams, d.TaskReturn]:
            """
            Decorate a function to inject the dependency as its first argument.

            Args:
                task:
                    The function to be decorated.
                    Its first parameter must be of type d.Data.

            Returns:
                A wrapped function that will automatically
                receive the dependency as its first argument.

            """

            @functools.wraps(task)
            def _wrapper(
                *task_args: d.TaskParams.args,
                **task_kwargs: d.TaskParams.kwargs,
            ):
                """Create and inject the dependency."""
                data = self._constructor(*args, **kwargs)
                return task(data, *task_args, **task_kwargs)

            return _wrapper

        return decorator


def configurable_dependency(
    func: t.Callable[InjectorConfig, d.Data],
) -> ConfigurableInjector[InjectorConfig, d.Data]:
    """
    Create a dependency injector from a constructor function.

    Args:
        func: A constructor function that creates the dependency

    """
    return ConfigurableInjector(func)


if d.is_test_env():  # pragma: no cover
    # SECTION tests

    # fake data
    NAME = "user_name"
    PROD_TOKEN = uuid.uuid4().hex
    FAKE_TOKEN = uuid.uuid4().hex
    PROD_URL = "http://prod-api.com"
    FAKE_URL = "http://fake-api.com"
    FAKE_INT = 1234

    def test_token_injection() -> None:
        class Permission(enum.Enum):
            read = "read"
            write = "write"

        @configurable_dependency
        def token(
            scope_1: Permission,
            scope_2: Permission = Permission.read,
        ) -> str:
            return f"test_token_{scope_1.value}_{scope_2.value}"

        @token.inject(scope_1=Permission.read)
        def build_http_headers(token: str):
            return {"Authorization": f"Bearer {token}"}

        for i in range(3):
            headers = build_http_headers()
            assert headers["Authorization"] == "Bearer test_token_read_read", (
                f"Attempt {i}"
            )

    def test_config_affecting_logic() -> None:
        counter = 0

        @configurable_dependency
        def count(increment: int):
            nonlocal counter
            counter += increment
            return counter

        @count.inject(increment=10)
        def read_counter(counter: int):
            return counter

        for i in range(4):
            assert read_counter() == 10 * (i + 1)
