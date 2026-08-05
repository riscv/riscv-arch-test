# SPDX-License-Identifier: Apache-2.0
"""High-level privileged test-generator operations."""

from testgen.priv.registry import (
    get_priv_test_defines,
    get_priv_test_extensions,
    get_priv_test_generator,
    get_priv_test_march_extensions,
    get_priv_test_params,
    get_priv_test_required_extensions,
)

__all__ = [
    "get_priv_test_defines",
    "get_priv_test_extensions",
    "get_priv_test_generator",
    "get_priv_test_march_extensions",
    "get_priv_test_params",
    "get_priv_test_required_extensions",
]
