class DependencyInjectionError(Exception):
    """Base exception for all dependency injection related errors."""


class DependencyLeakError(DependencyInjectionError):
    """Raised when a dependency is returned or leaked from its context."""

    def __init__(self) -> None:
        super().__init__("Dependency cannot be returned or leaked from its context")


class MissingContextError(DependencyInjectionError):
    """Raised when trying to inject a dependency without an ensure context."""

    def __init__(self) -> None:
        super().__init__(
            "Dependency injection requires an ensure context - please use ensure decorator",
        )
