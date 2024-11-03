# pyright: reportCallInDefaultInitializer=false
from pyinject import dep, inject, TypeConversionError
import os
import typing as t
import pytest
import pydantic as p

@dep
def copy_from_env(name: str):

    try:
        value = os.environ[name]
    except KeyError as err:
        raise EnvironmentError from err

    return value

@dep
def get_secret():
    return "some secret in plain text !! "

def test_type_error():
    import os
    os.environ["TEST_1"] = "this is not castable to int"

    @inject
    def main(
        test: int = copy_from_env("TEST_1"),
    ):
        assert False, f"Should never be called, got: {test}"

    with pytest.raises(TypeConversionError):
        _ = main()


def test_normal_run():
    import os
    os.environ["TEST_2"] = "123"

    @inject
    def main(
        test: int = copy_from_env("TEST_2"),
        secret: p.SecretStr = get_secret(),
    ):

        assert isinstance(test, int)
        assert isinstance(secret, p.SecretStr)
        return test, secret

    test, secret = main()
    assert isinstance(test, int)
    assert isinstance(secret, p.SecretStr)
    
    
    if t.TYPE_CHECKING:

        class MainCallable(t.Protocol):
            def __call__(
                self, 
                test: int,
                secret: p.SecretStr,
            ) -> tuple[int, p.SecretStr]: ...

        _: MainCallable = main
        t.assert_type(test, int)
        t.assert_type(secret, p.SecretStr)

