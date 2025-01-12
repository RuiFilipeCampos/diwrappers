from diwrappers import dependency

NUMBER = 1234


@dependency
def number() -> int:
    return NUMBER


@number.inject
def test_injection(number: int):
    return number


assert test_injection() == NUMBER

print("No errors. Exiting program.")
