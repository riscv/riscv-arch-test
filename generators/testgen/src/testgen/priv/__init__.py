# testgen/priv/__init__.py
"""Privileged test generation with automatic generator discovery."""

from testgen.priv.registry import (
    add_priv_test_generator,
    get_priv_test_defines,
    get_priv_test_extensions,
    get_priv_test_generator,
    get_priv_test_march_extensions,
    get_priv_test_required_extensions,
)

__all__ = [
    "add_priv_test_generator",
    "get_priv_test_defines",
    "get_priv_test_extensions",
    "get_priv_test_generator",
    "get_priv_test_march_extensions",
    "get_priv_test_required_extensions",
]
