# DIWrappers

A lightweight, type-safe dependency injection library for Python that supports synchronous, asynchronous, and contextual dependencies.

## Features

- Type-safe dependency injection with Python type hints
- Three injection patterns:
  - Regular dependencies (`@dependency`)
  - Async dependencies (`@async_dependency`)
  - Contextual dependencies (`@contextual_dependency`)
- Testing utilities for mocking dependencies
- Support for singleton dependencies via `@cache`
- Minimal boilerplate and intuitive API

## Installation

```bash
pip install diwrappers
```

## Usage

### Basic Dependency Injection

```python
from diwrappers import dependency

@dependency
def api_token() -> str:
    return "your-api-token"

@api_token.inject
def make_request(api_token: str, endpoint: str):
    return f"Calling {endpoint} with token {api_token}"

# The api_token will be automatically injected
result = make_request("/users")
```

### Async Dependencies

For dependencies that require asynchronous initialization:

```python
from diwrappers import async_dependency

@async_dependency
async def database():
    connection = await establish_db_connection()
    return connection

@database.inject
async def get_user(db, user_id: int):
    return await db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Use with async/await
user = await get_user(123)
```

### Contextual Dependencies

For dependencies that need proper resource management:

```python
from diwrappers import contextual_dependency
import contextlib

@contextual_dependency
@contextlib.contextmanager
def db_transaction():
    transaction = start_transaction()
    try:
        yield transaction
        transaction.commit()
    except:
        transaction.rollback()
        raise

@db_transaction.inject
def update_user(transaction, user_id: int, data: dict):
    transaction.execute("UPDATE users SET ...", data)

# Must be wrapped in ensure() to properly manage the context
@db_transaction.ensure
def main():
    update_user(123, {"name": "New Name"})
```

## Testing

The library provides utilities for mocking dependencies in tests:

### Using fake_value

```python
@dependency
def current_time() -> float:
    return time.time()

# In tests
with current_time.fake_value(1234567890.0):
    assert get_timestamp() == 1234567890.0
```

### Using faker

```python
@dependency
def random_id() -> str:
    return str(uuid.uuid4())

@random_id.faker
def fixed_id():
    return "test-id-123"

# In tests
with fixed_id():
    assert create_resource().id == "test-id-123"
```

## Singleton Dependencies

To create singleton dependencies that are cached for the lifetime of the program:

```python
from functools import cache

@dependency
@cache
def config():
    return load_config_from_file()
```

## Type Safety

The library leverages Python's type hints to ensure type safety:

```python
@dependency
def logger() -> Logger:
    return Logger()

@logger.inject
def process_data(logger: Logger, data: dict) -> None:
    logger.info(f"Processing {data}")  # Type-checked by your IDE/mypy
```

## Best Practices

1. Keep dependency constructors simple and focused
2. Use `@cache` for expensive-to-create dependencies that can be reused
3. Prefer contextual dependencies for resources that need cleanup
4. Always wrap contextual dependency usage with `ensure()`
5. Use async dependencies for I/O-bound operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
