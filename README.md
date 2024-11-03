# pyinjector - A simple dependency injection package with type safety and runtime validation.

This module provides a lightweight dependency injection system that leverages Python's type 
hints and Pydantic for runtime type checking and validation.

Example:

```python

    @dep
    def get_config(name: str) -> str:
        return os.environ[name]

    @inject
    def my_function(config: int = get_config("CONFIG")):

        # NOTE: value has been converted to `int` automatically 

        reveal_type(config)  ■ Type of "config" is "int"
```

