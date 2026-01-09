# testgen/coverpoints/__init__.py
"""Coverpoint test generation with automatic generator discovery."""

from testgen.coverpoints.registry import (
    add_coverpoint_generator,
    generate_tests_for_coverpoint,
)

__all__ = [
    "add_coverpoint_generator",
    "generate_tests_for_coverpoint",
]
