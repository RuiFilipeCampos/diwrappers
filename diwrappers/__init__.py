"""Entrypoint of diwrappers."""

from ._async_dependency import async_dependency
from ._dependency import dependency

__all__ = ["async_dependency", "dependency"]
