# DIWrappers

A lightweight, intuitive dependency injection library for Python that makes testing and dependency management a breeze.

## Features

- Simple decorator-based dependency injection
- Built-in support for singleton and transient dependencies
- Seamless integration with popular frameworks like FastAPI
- Powerful testing utilities with context managers
- Type hint friendly with full Pydantic support

## Installation

```bash
pip install diwrappers
```

## Quick Start

Here's a simple example showing how to inject a configuration dependency:

```python
from diwrappers import dependency
from pydantic import SecretStr
import os

@dependency
def api_token() -> SecretStr:
    return SecretStr(os.environ["API_TOKEN"])

@api_token.inject
def send_request(api_token: SecretStr):
    return f"Sending request with token: {api_token.get_secret_value()}"
```

## Core Concepts

### Dependency Types

#### Transient Dependencies

Transient dependencies are created each time they're requested. Perfect for generating random values or creating new instances:

```python
from diwrappers import dependency
import random

@dependency
def random_number():
    return random.randint(1, 10)

@random_number.inject
def play_game(random_number: int) -> str:
    return "win" if random_number > 5 else "lose"
```

#### Singleton Dependencies

Singleton dependencies are created once and reused. Ideal for database connections, configuration, or API clients:

```python
from functools import cache
from pydantic import HttpUrl

@dependency
@cache  # Makes this a singleton
def api_base_url():
    return HttpUrl("https://api.example.com")
```

### Chaining Dependencies

Dependencies can be chained together to build complex injection hierarchies:

```python
@dependency
def database():
    return Database("connection_string")

@dependency
@database.inject
def user_repository(database: Database):
    return UserRepository(database)

@user_repository.inject
def get_user(user_repository: UserRepository, user_id: int):
    return user_repository.get_user(user_id)
```

### Framework Integration

DIWrappers works seamlessly with popular frameworks like FastAPI:

```python
from fastapi import FastAPI
from diwrappers import dependency

app = FastAPI()

@dependency
def db_connection():
    return "database_connection"

@app.get("/users/{user_id}")
@db_connection.inject
def get_user(user_id: int, db_connection: str):
    return {"user_id": user_id, "connection": db_connection}
```

## Testing

DIWrappers provides powerful utilities for testing injected dependencies:

### Using Context Managers

```python
@dependency
def api_key():
    return "production_key"

@api_key.inject
def make_request(api_key: str):
    return f"Request with {api_key}"

def test_make_request():
    with api_key.fake_value("test_key"):
        assert make_request() == "Request with test_key"
```

### Dynamic Fake Data

Create dynamic fake data for more complex testing scenarios:

```python
@dependency
def user_id():
    return get_current_user_id()

@user_id.faker
def fake_user_id():
    return random.randint(1000, 9999)

def test_with_random_users():
    with fake_user_id():
        result = get_user_data()
        assert 1000 <= result.user_id <= 9999
```

### Multiple Fakes

Chain multiple fake dependencies in a single test:

```python
def test_complex_scenario():
    with (
        api_key.fake_value("test_key"),
        database.fake_value(MockDatabase()),
        user_id.fake_value(12345)
    ):
        result = perform_operation()
        assert result.success
```

## Coming Soon

- Contextual dependency injection (request-scoped, session-scoped)
- Async support
- Container lifecycle management
- Enhanced framework integrations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
