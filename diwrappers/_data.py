import typing as t
import os


def is_tuple(val: object) -> t.TypeGuard[tuple[object]]:
    """Check if a value is a tuple.

    Examples:
        >>> is_tuple((1, 2, 3))
        True

        >>> is_tuple([1, 2, 3])
        False

        >>> is_tuple(())
        True

        >>> is_tuple("not a tuple")
        False

        >>> is_tuple(tuple(range(3)))
        True

        >>> is_tuple(tuple())
        True

        >>> is_tuple(dict(a=1).items())  # dict_items is not a tuple
        False

    """
    return isinstance(val, tuple)


def is_list(val: object) -> t.TypeGuard[list[object]]:
    """Check if a value is a list.

    Examples:
        >>> is_list([1, 2, 3])
        True

        >>> is_list((1, 2, 3))
        False

        >>> is_list([])
        True

        >>> is_list("not a list")
        False

        >>> is_list(list(range(3)))
        True

        >>> is_list(list())
        True

        >>> is_list(dict(a=1).keys())  # dict_keys is not a list
        False

    """
    return isinstance(val, list)


def is_dict(val: object) -> t.TypeGuard[dict[object, object]]:
    """Check if a value is a dictionary.

    Examples:
        >>> is_dict({"a": 1, "b": 2})
        True

        >>> is_dict([("a", 1), ("b", 2)])
        False

        >>> is_dict({})
        True

        >>> is_dict("not a dict")
        False

        >>> is_dict(dict(a=1, b=2))
        True

        >>> is_dict(dict())
        True

        >>> class DictLike:
        ...     def __getitem__(self, key): return None
        ...     def __setitem__(self, key, value): pass
        >>> is_dict(DictLike())  # dict-like object but not a dict
        False

    """
    return isinstance(val, dict)


TEST_VAR_NAME = "DIWRAPPERS_TEST"
""" Env variable that indicates if this is a test run """


def is_test_env():
    return TEST_VAR_NAME in os.environ and os.environ[TEST_VAR_NAME] == "true"
