import contextlib
import functools
import typing as t
from collections import abc
from dataclasses import dataclass

import diwrappers._commons._data as d


@dataclass
class AsyncInjector(t.Generic[d.Data]):
    _constructor: t.Callable[[], abc.Awaitable[d.Data]]
    """Function that creates new instances of the dependency."""

    @contextlib.contextmanager
    def fake_value(self, val: d.Data):
        tmp_constructor = self._constructor

        async def new_constructor():
            return val

        self._constructor = new_constructor
        try:
            yield val
        finally:
            self._constructor = tmp_constructor

    def faker(self, fake_constructor: t.Callable[[], abc.Awaitable[d.Data]]):
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
        task: t.Callable[
            t.Concatenate[d.Data, d.TaskParams],
            abc.Awaitable[d.TaskReturn],
        ],
    ) -> t.Callable[d.TaskParams, abc.Awaitable[d.TaskReturn]]:
        @functools.wraps(task)
        async def _wrapper(
            *args: d.TaskParams.args,
            **kwargs: d.TaskParams.kwargs,
        ):
            """Create and inject the dependency."""
            data = await self._constructor()
            return await task(data, *args, **kwargs)

        return _wrapper


def async_dependency(
    func: t.Callable[[], abc.Awaitable[d.Data]],
) -> AsyncInjector[d.Data]:
    return AsyncInjector(func)


if d.is_test_env():  # pragma: no cover
    import pytest

    GT_USER_ID = 1234
    FAKE_ID = 5678

    @pytest.mark.asyncio
    async def test_simple_usage() -> None:
        @async_dependency
        async def user_id():
            # perform an http request
            return GT_USER_ID

        @user_id.inject
        async def return_injected_value(user_id: int):
            return user_id

        assert await return_injected_value() == GT_USER_ID

    @pytest.mark.asyncio
    async def test_fake_value_context():
        @async_dependency
        async def user_id() -> int:
            return GT_USER_ID

        @user_id.inject
        async def get_user(user_id: int):
            return f"User-{user_id}"

        # Test normal behavior
        assert await get_user() == f"User-{GT_USER_ID}"

        # Test with fake value
        with user_id.fake_value(FAKE_ID) as fake_id:
            assert await get_user() == f"User-{FAKE_ID}"
            assert fake_id == FAKE_ID

        # Test restoration
        assert await get_user() == f"User-{GT_USER_ID}"

    @pytest.mark.asyncio
    async def test_faker_context():
        @async_dependency
        async def user_id() -> int:
            return GT_USER_ID

        @user_id.faker
        async def fake_user_id():
            return FAKE_ID

        @user_id.inject
        async def get_user(user_id: int):
            return f"User-{user_id}"

        # Test normal behavior
        assert await get_user() == f"User-{GT_USER_ID}"

        # Test with faker
        with fake_user_id():
            assert await get_user() == f"User-{FAKE_ID}"

        # Test restoration
        assert await get_user() == f"User-{GT_USER_ID}"

    @pytest.mark.asyncio
    async def test_nested_async_dependencies():
        @async_dependency
        async def get_token():
            return "token-123"

        @async_dependency
        @get_token.inject
        async def get_client(token: str):
            return f"client-{token}"

        @get_client.inject
        async def make_request(client: str):
            return f"request-with-{client}"

        result = await make_request()
        assert result == "request-with-client-token-123"

    @pytest.mark.asyncio
    async def test_exception_handling():
        msg = "Async error"

        @async_dependency
        async def failing_dependency():
            raise ValueError(msg)

        @failing_dependency.inject
        async def use_failing(dep: str):
            return dep

        with pytest.raises(ValueError, match=msg):
            await use_failing()

    @pytest.mark.asyncio
    async def test_multiple_fake_contexts():
        @async_dependency
        async def user_id() -> int:
            return GT_USER_ID

        @async_dependency
        async def api_key() -> str:
            return "prod-key"

        @user_id.inject
        @api_key.inject
        async def make_request(api_key: str, user_id: int):
            return f"request-{api_key}-{user_id}"

        # Test multiple fake contexts simultaneously
        with (
            user_id.fake_value(FAKE_ID) as fake_user,
            api_key.fake_value("test-key") as fake_key,
        ):
            result = await make_request()
            assert result == f"request-test-key-{FAKE_ID}"
            assert fake_user == FAKE_ID
            assert fake_key == "test-key"

    @pytest.mark.asyncio
    async def test_nested_fakers():
        @async_dependency
        async def config():
            return {"env": "prod"}

        @config.faker
        async def test_config():
            return {"env": "test"}

        @config.faker
        async def dev_config():
            return {"env": "dev"}

        @config.inject
        async def get_env(config: dict[str, str]):
            return config["env"]

        assert await get_env() == "prod"

        with test_config():
            assert await get_env() == "test"

            with dev_config():
                assert await get_env() == "dev"

                with test_config():
                    assert await get_env() == "test"

                assert await get_env() == "dev"

            assert await get_env() == "test"

        assert await get_env() == "prod"

    @pytest.mark.asyncio
    async def test_injection_with_args():
        @async_dependency
        async def prefix():
            return "test"

        @prefix.inject
        async def format_string(prefix: str, name: str, count: int = 1):
            return f"{prefix}-{name}-{count}"

        result = await format_string("user", count=5)
        assert result == "test-user-5"

    @pytest.mark.asyncio
    async def test_complex_async_workflow():
        events: list[str] = []

        @async_dependency
        async def tracker():
            events.append("create")
            return events

        @tracker.inject
        async def workflow(tracker: list[str]):
            tracker.append("start")
            return len(tracker)

        # Normal flow
        n = 2
        assert await workflow() == n
        assert events == ["create", "start"]

        # With fake
        events.clear()
        with tracker.fake_value([]) as fake_tracker:
            assert await workflow() == 1
            assert fake_tracker == ["start"]
            assert events == []
