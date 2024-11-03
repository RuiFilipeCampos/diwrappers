# pyright: reportCallInDefaultInitializer=false
"""
pyinjector - A simple dependency injection package with type safety and runtime validation.

This module provides a lightweight dependency injection system that leverages Python's type 
hints and Pydantic for runtime type checking and validation.


Example:

    @dep
    def get_config(name: str) -> str:
        return os.environ[name]

    @inject
    def my_function(config: int = get_config()):

        # NOTE: value has been converted to `int` automatically 

        reveal_type(config)  ■ Type of "config" is "int"
"""

import pydantic as p
import inspect
import functools
import typing as t

T = t.TypeVar('T', type, object)
P = t.ParamSpec('P')
R = t.TypeVar("R")

Injector = t.Callable[..., T]

IS_INJECTOR_ATTR = "__isinjector__"

def is_injector(val: object) -> t.TypeGuard[Injector[object]]:
    return callable(val) and hasattr(val, IS_INJECTOR_ATTR)

def is_class(obj: object) -> t.TypeGuard[type[object]]:
    return inspect.isclass(obj)





class InjectionError(Exception):
    """Base exception for injection-related errors."""

class TypeConversionError(InjectionError, t.Generic[T]):
    """Raised when a dependency value cannot be converted to the expected type."""

    expected_type: type[T]
    raw_value: object
    param_name: str
    err_msg: str | None

    def __init__(
        self,
        expected_type: type[T],
        raw_value: object,
        param_name: str,
        err_msg: str | None
    ):

        self.expected_type = expected_type
        self.raw_value = raw_value
        self.param_name = param_name
        self.err_msg = err_msg

        full_msg = f"Error when converting parameter `{param_name}` of value `{raw_value}` to type `{expected_type}`"

        if err_msg is not None:
            full_msg += ": " + err_msg

        super().__init__(full_msg)




    
def runtime_cast(val: object, to_type: type[T], name: str) -> T:
    """
    Safely cast a value to the specified type using Pydantic validation.
    
    Args:
        val: The value to cast
        to_type: The target type
        name: Parameter name for error reporting
        
    Returns:
        The validated and converted value
        
    Raises:
        TypeConversionError: If the value cannot be converted to the target type
    """
    try:
        return p.TypeAdapter(to_type).validate_python(val)
    except p.ValidationError as val_err:

        err_msg = None

        for err in val_err.errors():
            err_msg = err["msg"]

        raise TypeConversionError(
            expected_type = to_type,
            param_name = name,
            raw_value = val,
            err_msg = err_msg

        ) from val_err

def dep(func: t.Callable[P, R]) -> t.Callable[P, T]:
    """
    Decorator that marks a function as a dependency provider.
    
    Args:
        func: The function that provides the dependency value
        
    Returns:
        A wrapped function that can be used as a default argument in @inject functions
    """
    
    def injector_factory(*args: P.args, **kwargs: P.kwargs) -> T:

        def injector():
            return func(*args, **kwargs)

        setattr(injector, IS_INJECTOR_ATTR, True)

        # WARNING: this cast will be enforced via @injector
        return t.cast(
            T,
            injector
        )

    return injector_factory




def inject(func: t.Callable[P, R]) -> t.Callable[P, R]:

    params = inspect.signature(func).parameters

    # @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:


        for name, param in params.items():

            param_default= t.cast(object, param.default)

            if name in kwargs or not is_injector(param_default):
                print(name, "not injector")
                continue
            
            # NOTE: casting Any to object
            expected_type = t.cast(
                object | None,
                t.get_type_hints(func).get(name)
            )

            raw_value = param_default()

            if expected_type is None:
                kwargs[name] = raw_value
                continue
            
            # if not is_class(expected_type):
            #     raise RuntimeError



            kwargs[name] = runtime_cast(
                val = raw_value,
                to_type = expected_type,
                name = param.name
            )

        return func(*args, **kwargs)

    return wrapper


