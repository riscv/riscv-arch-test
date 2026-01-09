# testgen/priv/__init__.py
"""Coverpoint test boder generation with automatic generator discovery."""

from testgen.priv.registry import (
    add_priv_test_generator,
    get_priv_test_defines,
    get_priv_test_extensions,
    get_priv_test_generator,
)

__all__ = [
    "add_priv_test_generator",
    "get_priv_test_defines",
    "get_priv_test_extensions",
    "get_priv_test_generator",
]
