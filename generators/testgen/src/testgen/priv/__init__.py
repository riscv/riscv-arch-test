# testgen/priv/__init__.py
"""Privileged test generation with automatic generator discovery."""

from testgen.priv.generate import generate_priv_test
from testgen.priv.registry import (
    add_priv_test_generator,
    get_priv_test_extensions,
)

__all__ = [
    "add_priv_test_generator",
    "generate_priv_test",
    "get_priv_test_extensions",
]
