# diwrappers: Modern Dependency Injection for Python

diwrappers is a flexible, type-safe dependency injection framework for Python that supports both synchronous and asynchronous dependencies with contextual management.

## Features

- 🔄 **Sync & Async Support**: Handle both synchronous and asynchronous dependencies seamlessly
- 🎯 **Type Safety**: Full typing support with generics for better IDE integration
- 🔒 **Contextual Dependencies**: Manage resources with proper cleanup through context managers
- 🧪 **Testing Utilities**: Built-in support for mocking and faking dependencies
- 🧵 **Thread Safety**: Reliable behavior in multi-threaded environments

## Installation

```bash
pip install diwrappers
```

## Quick Start

### Basic Dependency Injection

```python
from diwrappers import dependency

@dependency
def database():
    return Database("connection_string")

@database.inject
def get_user(db: Database, user_id: int):
    return db.find_user(user_id)

# Use the function without manually passing the database
user = get_user(user_id=123)
```

### Contextual Dependencies

```python
from diwrappers import contextual_dependency
import contextlib

@contextual_dependency
@contextlib.contextmanager
def database():
    db = Database("connection_string")
    try:
        yield db
    finally:
        db.close()

# Define functions that need the database
@database.inject
def get_user(db: Database, user_id: int):
    return db.find_user(user_id)

@database.inject
def save_user(db: Database, user: User):
    return db.save(user)

# Ensure database context for a group of operations
@database.ensure
def process_user_data(user_id: int):
    # Multiple database operations within the same context
    user = get_user(user_id)
    user.last_login = datetime.now()
    save_user(user)
    return user

# Database connection is automatically managed
user = process_user_data(user_id=123)
```

### Async Support

```python
from diwrappers import async_dependency

@async_dependency
async def api_client():
    client = ApiClient()
    await client.connect()
    return client

@api_client.inject
async def fetch_data(client: ApiClient, endpoint: str):
    return await client.get(endpoint)

# Use with async/await
data = await fetch_data(endpoint="/users")
```

## Core Concepts

### 1. Basic Dependencies

The `@dependency` decorator creates injectors for regular dependencies:

- Use `@dependency` to define a dependency
- Use `.inject` to inject the dependency into functions
- Use `.fake_value()` or `.faker()` for testing

### 2. Contextual Dependencies

Contextual dependencies provide resource management:

- Use `@contextual_dependency` for dependencies needing cleanup
- Use `.ensure` to create a context where the dependency is valid
- Use `.inject` to use the dependency within that context

### 3. Async Dependencies

For asynchronous operations:

- Use `@async_dependency` for async dependencies
- Use `@async_contextual_dependency` for async contextual dependencies
- All async dependencies work with `async/await` syntax

## Testing

diwrappers provides robust testing utilities:

```python
@dependency
def config():
    return {"env": "production"}

@config.inject
def get_environment(config: dict):
    return config["env"]

# Test using fake_value
with config.fake_value({"env": "testing"}):
    assert get_environment() == "testing"

# Test using faker
@config.faker
def test_config():
    return {"env": "testing"}

with test_config():
    assert get_environment() == "testing"
```

## Error Handling

diwrappers provides clear error messages through custom exceptions:

- `DependencyInjectionError`: Base exception class
- `DependencyLeakError`: Raised when dependencies escape their context
- `MissingContextError`: Raised when using contextual dependencies without ensure

## Best Practices

1. **Resource Management**
   - Use contextual dependencies for resources requiring cleanup
   - Always use `.ensure` with contextual dependencies
   - Avoid returning dependencies from functions

2. **Testing**
   - Use `.fake_value()` for simple value replacement
   - Use `.faker()` for more complex fake implementations
   - Test both success and error cases

3. **Type Safety**
   - Always provide type hints for dependencies
   - Use generics when creating reusable patterns
   - Let your IDE help you with type checking

## Advanced Usage

### Nested Dependencies

```python
@dependency
def config():
    return {"db_url": "postgresql://..."}

@dependency
@config.inject
def database(config: dict):
    return Database(config["db_url"])

@database.inject
def get_user(db: Database, user_id: int):
    return db.find_user(user_id)
```

### Multiple Dependencies

```python
@dependency
def logger():
    return Logger()

@dependency
def database():
    return Database()

@logger.inject
@database.inject
def save_user(db: Database, logger: Logger, user: User):
    logger.info(f"Saving user {user.id}")
    db.save(user)
```

### Thread Safety

The package is thread-safe by default:

```python
@dependency
def counter():
    return Counter()

@counter.inject
def increment(counter: Counter):
    counter.increment()
    return counter.value

# Safe to use in multiple threads
threads = [Thread(target=increment) for _ in range(10)]
```

