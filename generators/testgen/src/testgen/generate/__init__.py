# SPDX-License-Identifier: Apache-2.0
"""High-level test-generation operations."""

from testgen.generate.priv import generate_priv_test
from testgen.generate.unpriv import generate_unpriv_extension_tests

__all__ = [
    "generate_priv_test",
    "generate_unpriv_extension_tests",
]
