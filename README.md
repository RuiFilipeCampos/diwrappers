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

In the above code, `get_config("CONFIG")` does not actually call the `get_config` function. Instead, it freezes it in place by storing its arguments. The `get_config` function will only get called once `my_funcion` is called:

```python
my_function() # @inject executes `get_config` here
```

Without pyinject:

```python

def get_config(name: str) -> str:
    return os.environ[name]

def my_function(config: int = get_config("CONFIG")):

    # NOTE: value has been converted to `int` automatically 

    reveal_type(config)  ■ Type of "config" is "int"
```

and due to `os.environ`, this code might raise a `KeyError` *while* the module is being imported, thus making it hard to test `my_function`.

