# pyright: reportCallInDefaultInitializer=false
from pyinject import dep, inject, TypeConversionError
import typing as t
import pytest
import pydantic as p
from typing import List, Optional
from datetime import datetime


def test_basic_injection():
    @dep
    def get_value() -> str:
        return "test_value"
    
    @inject
    def example_function(value: str = get_value()) -> str:
        return value
    
    assert example_function() == "test_value"

def test_type_conversion():
    @dep
    def get_number() -> str:
        return "42"
    
    @inject
    def number_function(num: int = get_number()) -> int:
        return num
    
    assert number_function() == 42
    assert isinstance(number_function(), int)

def test_multiple_dependencies():
    @dep
    def get_name() -> str:
        return "John"
    
    @dep
    def get_age() -> str:
        return "30"
    
    @inject
    def person_function(name: str = get_name(), age: int = get_age()):
        return name, age
    
    name, age = person_function()
    assert name == "John"
    assert age == 30
    assert isinstance(age, int)

def test_injection_with_args():
    @dep
    def get_config(key: str) -> str:
        configs = {"host": "localhost", "port": "8080"}
        return configs[key]
    
    @inject
    def connect(host: str = get_config("host"), port: int = get_config("port")):
        return f"{host}:{port}"
    
    assert connect() == "localhost:8080"

def test_optional_types():
    @dep
    def get_optional() -> str:
        return "optional_value"
    
    @inject
    def optional_function(value: str | None = get_optional()):
        return value
    
    assert optional_function() == "optional_value"

# def test_list_conversion():
#     @dep
#     def get_numbers() -> str:
#         return "[1, 2, 3]"
#     
#     @inject
#     def list_function(numbers: list[int] = get_numbers()):
#         return numbers
#     
#     result = list_function()
#     assert isinstance(result, list)
#     assert result == [1, 2, 3]

def test_type_conversion_error():
    @dep
    def get_invalid_number() -> str:
        return "not_a_number"
    
    @inject
    def invalid_function(num: int = get_invalid_number()):
        return num
    
    with pytest.raises(TypeConversionError):
        invalid_function()
    

def test_injection_override():
    @dep
    def get_default() -> str:
        return "default"
    
    @inject
    def override_function(value: str = get_default()):
        return value
    
    # Test default injection
    assert override_function() == "default"
    
    # Test override with explicit value
    assert override_function(value="override") == "override"

def test_nested_injection():
    @dep
    def get_inner() -> str:
        return "inner_value"
    
    @inject
    def inner_function(value: str = get_inner()):
        return value
    
    @inject
    def outer_function(inner: str = get_inner()):
        return inner_function() + "_" + inner
    
    assert outer_function() == "inner_value_inner_value"

def test_complex_type_conversion():
    @dep
    def get_date_str() -> str:
        return "2024-01-01T00:00:00"
    
    @inject
    def date_function(date: datetime = get_date_str()):
        return date
    
    result = date_function()
    assert isinstance(result, datetime)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 1

def test_non_injector_default():
    # Test that regular default values are not processed
    @inject
    def regular_default(value: str = "regular"):
        return value
    
    assert regular_default() == "regular"

def test_dependency_chain():
    @dep
    def get_base() -> str:
        return "10"
    
    @dep
    def get_multiplier() -> str:
        return "2"
    
    @inject
    def multiply(base: int = get_base(), multiplier: int = get_multiplier()):
        return base * multiplier
    
    assert multiply() == 20
