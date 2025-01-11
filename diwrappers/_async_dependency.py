import contextlib
import collections.abc as abc
import enum
import functools
import typing as t
from dataclasses import dataclass
from functools import cache
import pytest as pt
import random

@dataclass
class AsyncInjector[Data]:

    _constructor: t.Callable[[], abc.Awaitable[Data]]
    """Function that creates new instances of the dependency."""


    @contextlib.contextmanager
    def fake_value(self, val: Data):
        tmp_constructor = self._constructor
        async def new_constructor():
            return val
        self._constructor = new_constructor
        try:
            yield val
        finally:
            self._constructor = tmp_constructor

    
    def faker(self, fake_constructor: t.Callable[[], abc.Awaitable[Data]]):
        @contextlib.contextmanager
        def wrapper():
            tmp_constructor = self._constructor
            self._constructor = fake_constructor
            try:
                yield 
            finally:
                self._constructor = tmp_constructor

        return wrapper


    def inject[**TaskParams, TaskReturn](
        self,
        task: t.Callable[
            t.Concatenate[Data, TaskParams],
            abc.Awaitable[TaskReturn]
        ]
    ) -> t.Callable[TaskParams, abc.Awaitable[TaskReturn]]:
        @functools.wraps(task)
        async def _wrapper(*args: TaskParams.args, **kwargs: TaskParams.kwargs):
            """Creates and injects the dependency."""

            data = await self._constructor()
            return await task(data, *args, **kwargs)

        return _wrapper

def async_dependency[Data](func: t.Callable[[], abc.Awaitable[Data]]) -> AsyncInjector[Data]:
    return AsyncInjector(func)



@pt.mark.asyncio
async def test_simple_usage():

    GT_USER_ID = 1234

    @async_dependency
    async def user_id():
        # perform an http request
        return GT_USER_ID

    @user_id.inject
    async def return_injected_value(user_id: int):
        return user_id

    assert GT_USER_ID == await return_injected_value()



