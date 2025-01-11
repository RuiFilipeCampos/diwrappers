import contextlib
import enum
import functools
import typing as t
from dataclasses import dataclass
from functools import cache
import pytest as pt
import random

@dataclass
class Injector[Data]:
    """
    A dependency injection container that manages the creation and injection of dependencies.

    This class provides a flexible way to manage dependencies in your application, supporting
    both regular dependency injection and testing scenarios through context managers that
    allow temporary dependency replacement.

    Type Parameters:
        Data: The type of the dependency being managed by this injector.

    Attributes:
        _constructor: A callable that creates new instances of the dependency.
    
    Example:
        ```python

        @dependency
        def api_token() -> str:
            return fetch_api_token()

        @api_token.inject
        def build_headers(api_token: str):
            return {
                'authorization': f'Bearer {api_token}'
            }

        ```
    """


    _constructor: t.Callable[[], Data]
    """Function that creates new instances of the dependency."""


    @contextlib.contextmanager
    def fake_value(self, val: Data):
        """
        Temporarily replace the dependency with a specific value.

        This context manager allows you to substitute the normal dependency with a fixed value
        for testing or debugging purposes. The original dependency is restored when exiting
        the context.

        Args:
            val: The value to use instead of the normal dependency.

        Yields:
            The provided fake value.

        Example:
            ```python
            @dependency
            def api_key() -> str:
                return "real_api_key"

            with api_key.fake_value("test_key") as fake_key:
                # Code here will use "test_key" instead of "real_api_key"
                assert fake_key == "test_key"
            ```
        """
        tmp_constructor = self._constructor
        self._constructor = lambda: val
        try:
            yield val
        finally:
            self._constructor = tmp_constructor

    
    def faker(self, fake_constructor: t.Callable[[], Data]):
        """
        Create a context manager that temporarily replaces the dependency constructor.

        This decorator creates a context manager that allows you to substitute the normal
        dependency constructor with a different one for testing or debugging purposes.
        The original constructor is restored when exiting the context.

        Args:
            fake_constructor: A callable that will temporarily replace the normal dependency constructor.

        Returns:
            A context manager that can be used to temporarily replace the dependency constructor.

        Example:
            ```python
            @dependency
            def random_int() -> int:
                return random.randint(1, 10)

            @random_int.faker
            def fake_random_int():
                return 42

            with fake_random_int():
                # Code here will always get 42 instead of a random number
                pass
            ```
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


    def inject[**TaskParams, TaskReturn](
        self,
        task: t.Callable[
            t.Concatenate[Data, TaskParams],
            TaskReturn
        ]
    ) -> t.Callable[TaskParams, TaskReturn]:
        """
        Decorates a function to inject the dependency as its first argument.

        This decorator automatically provides the dependency to the decorated function
        as its first argument. The dependency is created using the constructor function
        every time the decorated function is called (unless the constructor is cached).

        Type Parameters:
            TaskParams: Type parameters for the decorated function's arguments
            TaskReturn: Return type of the decorated function

        Args:
            task: The function to be decorated. Its first parameter must be of type Data.

        Returns:
            A wrapped function that will automatically receive the dependency as its first argument.

        Example:
            ```python
            @dependency
            def logger() -> Logger:
                return Logger()

            @logger.inject
            def process_data(logger: Logger, data: dict[str, str]) -> None:
                logger.info(f"Processing {data}")
                # ... process the data ...
            ```
        """

        @functools.wraps(task)
        def _wrapper(*args: TaskParams.args, **kwargs: TaskParams.kwargs):
            """Creates and injects the dependency."""

            data = self._constructor()
            return task(data, *args, **kwargs)

        return _wrapper

def dependency[Data](func: t.Callable[[], Data]) -> Injector[Data]:
    """
    Creates a dependency injector from a constructor function.

    This decorator creates an Injector instance that manages the creation and injection
    of dependencies. It can be used to create both regular dependencies and singletons
    (when combined with @cache).

    Type Parameters:
        Data: The type of the dependency being created

    Args:
        func: A constructor function that creates the dependency

    Returns:
        An Injector instance configured to manage the dependency

    Example:
        ```python
        # Regular dependency, will inject a different number each time
        @dependency
        def random_int():
            return random.random_int(1, 10)

        # Singleton dependency, will throw a random number and inject it until the end of the program
        @dependency
        @cache
        def random_int():
            return random.random_int(1, 10)
        ```

    Notes:
        - The constructor function should have no parameters
        - For singleton dependencies, apply @cache before @dependency
        - The resulting injector provides .inject, .faker, and .fake_value methods
    """

    return Injector(func)

# SECTION: tests

def test_token_injection():

    @dependency
    def token() -> str:
        return "test_token"

    @token.inject
    def build_http_headers(token: str):
        return {
            "Authorization": f"Bearer {token}"
        }

    for i in range(3):
        headers = build_http_headers()
        assert headers["Authorization"] == "Bearer test_token", f"Attempt {i}"

def test_singleton_dependency():

    counter = 0

    @dependency
    @cache
    def get_counter():
        nonlocal counter
        counter += 1
        return counter

    @get_counter.inject
    def read_counter(counter: int):
        return counter

    assert read_counter() == 1, "must always return the same value"
    assert read_counter() == 1, "must always return the same value"
    assert read_counter() == 1, "must always return the same value"
    assert read_counter() == 1, "must always return the same value"

    assert counter == 1, "constructor can only be called once"  # Constructor called only once


# types and data for using random during tests

class _NormalRange(enum.IntEnum):
    """Ground truth range for random number generation"""
    START = 1
    END = 10

class _TestRAnge(enum.IntEnum):
    """Modified range for testing purposes"""
    START = 11
    END = 15

N_TRIALS = 100
""" Number of times the distribution will be sampled """

SEED = 42
""" Seed for the pRNG """

@pt.fixture(autouse=True)
def set_random_seed():
    random.seed(SEED)
    yield


def test_faker_decorator():

    @dependency
    def random_int():
        return random.randint(_NormalRange.START, _NormalRange.END)

    @random_int.faker
    def fake_random_int():
        return random.randint(_TestRAnge.START, _TestRAnge.END)

    @random_int.inject
    def get_number(random_int: int):
        return random_int


    # Test normal behavior
    assert all(
        _NormalRange.START <= get_number() <= _NormalRange.END for _ in range(N_TRIALS)
    )

    # Test with faker
    with fake_random_int():
        assert all(
            _TestRAnge.START <= get_number() <= _TestRAnge.END for _ in range(N_TRIALS)
        )

    # Test restoration after context
    assert all(
        _NormalRange.START <= get_number() <= _NormalRange.END for _ in range(N_TRIALS)
    )

def test_fake_value_context():

    @dependency
    def random_int():
        return random.randint(_NormalRange.START, _NormalRange.END)

    @random_int.inject
    def get_number(random_int: int):
        return random_int


    # Test normal behavior
    assert all(
        _NormalRange.START <= get_number() <= _NormalRange.END for _ in range(N_TRIALS)
    )

    # Test with fake value
    with random_int.fake_value(42) as fake_int:
        assert get_number() == 42
        assert fake_int == 42

    # Test restoration after context
    assert all(
        _NormalRange.START <= get_number() <= _NormalRange.END for _ in range(N_TRIALS)
    )

def test_multiple_fake_contexts():

    FAKE_INT = 1234

    @dependency
    def random_int():
        return random.randint(_NormalRange.START, _NormalRange.END)


    PROD_TOKEN = "prod_token"
    FAKE_TOKEN = "fake_token"

    @dependency
    def token():
        return PROD_TOKEN

    PROD_URL = "http://prod-api.com"
    FAKE_URL = "http://fake-api.com"


    @dependency
    def api_base_url():
        return PROD_URL

    @random_int.inject
    @token.inject
    @api_base_url.inject
    def get_random_user(
        base_url: str,
        token: str,
        random_int: int,
        name: str
    ):
        return base_url, token, random_int, name

    NAME = "user_name"

    with (
        random_int.fake_value(FAKE_INT) as fake_int,
        token.fake_value(FAKE_TOKEN) as fake_token,
        api_base_url.fake_value(FAKE_URL) as fake_api_base_url
    ):

        assert FAKE_INT == fake_int
        assert FAKE_TOKEN == fake_token
        assert FAKE_URL == fake_api_base_url

        _base_url, _token, _random_int, _name = get_random_user(name=NAME)
        
        assert _base_url == fake_api_base_url
        assert _token == fake_token
        assert _random_int == fake_int
        assert _name == NAME


def test_chained_dependencies():

    @dependency
    def token():
        return "test_token"

    values: list[str] = []

    @dependency
    @token.inject
    def client(token: str):
        values.append(token)
        return "test_client"

    @client.inject
    def use_client(client: str):
        values.append(client)
        return client

    result = use_client()
    assert result == "test_client"
    assert values == ["test_token", "test_client"]



def test_multiple_dependencies():

    @dependency
    def logger() -> str:
        return "logger_instance"

    @dependency
    def db_connection() -> str:
        return "db_connection_instance"

    @logger.inject
    @db_connection.inject
    def use_services(db_connection: str, logger: str):
        return f"Using {db_connection} with {logger}"

    assert use_services() == "Using db_connection_instance with logger_instance"

def test_dependency_replacement():

    @dependency
    def config():
        return {"env": "production"}

    @config.inject
    def get_env(config: dict[str, str]):
        return config["env"]

    assert get_env() == "production"

    with config.fake_value({"env": "test"}):
        assert get_env() == "test"

    assert get_env() == "production"


def test_injected_function_exception():

    @dependency
    def db_connection() -> str:
        return "db"

    @db_connection.inject
    def failing_function(db_connection: str):
        print(db_connection)
        raise ValueError("Simulated error")

    with pt.raises(ValueError, match="Simulated error"):
        failing_function()


def test_thread_safety():

    import threading

    @dependency
    def random_number() -> int:
        return random.randint(1, 100)

    @random_number.inject
    def get_number(random_number: int):
        return random_number

    results: list[int] = []

    def worker():
        results.append(get_number())

    threads = [threading.Thread(target=worker) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(results) == 10
    assert all(isinstance(num, int) and 1 <= num <= 100 for num in results)



def test_nested_fakers():

    GT_TOKEN = "real_token"
    FAKE_1 = "fake_token_1"
    FAKE_2 = "fake_token_2"

    @dependency
    def token() -> str:
        return GT_TOKEN

    @token.faker
    def fake_token_1():
        return FAKE_1

    @token.faker
    def fake_token_2():
        return FAKE_2


    @token.inject
    def assert_gt(token: str):
        assert GT_TOKEN == token


    @token.inject
    def assert_fake_1(token: str):
        assert FAKE_1 == token

    @token.inject
    def assert_fake_2(token: str):
        assert FAKE_2 == token

    assert_gt()

    with fake_token_1():
        assert_fake_1()
        with fake_token_2():  
            assert_fake_2()
            with fake_token_1():
                assert_fake_1()
            assert_fake_2()

            assert_fake_2()
            with fake_token_1():
                assert_fake_1()
            assert_fake_2()

        assert_fake_1()

    assert_gt()




