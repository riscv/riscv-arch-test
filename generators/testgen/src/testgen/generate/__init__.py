# testgen/generate/__init__.py
"""Test generation orchestration.

This module provides the main entry points for generating tests:
- generate_unpriv_extension_tests: Generate unprivileged tests from CSV testplans
- generate_priv_test: Generate tests for a single privileged extension
- generate_all_priv_tests: Generate tests for all registered privileged extensions
"""

from testgen.generate.priv import generate_priv_test
from testgen.generate.unpriv import generate_unpriv_extension_tests

__all__ = [
    "generate_priv_test",
    "generate_unpriv_extension_tests",
]
