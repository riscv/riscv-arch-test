##################################
# io/vector_scalar_check.py
#
# Suite names for scalar self-checking vector tests (e.g. Vx8-scalarcheck).
# SPDX-License-Identifier: Apache-2.0
##################################

"""Suite names for scalar self-checking vector tests."""

from enum import Enum
from pathlib import Path

from testgen.io.testplans import get_extensions

VECTOR_SCALAR_CHECK_SUFFIX = "-scalarcheck"


class VectorCheck(str, Enum):
    """How vector tests check results: with vector instructions or with scalar code."""

    VECTOR = "vector"
    SCALAR = "scalar"


def get_vector_scalar_check_extensions(testplan_dir: Path) -> list[str]:
    """Get the vector suites that can also be generated with scalar self-checking (e.g. Vx8-scalarcheck)."""
    return [
        extension + VECTOR_SCALAR_CHECK_SUFFIX
        for extension in get_extensions(testplan_dir)
        if extension.startswith(("Vx", "Vls", "Vf"))
    ]


def split_vector_scalar_check(testsuite: str) -> tuple[str, bool]:
    """Split a suite name into its base suite and whether it uses scalar self-checking."""
    if testsuite.endswith(VECTOR_SCALAR_CHECK_SUFFIX):
        return testsuite.removesuffix(VECTOR_SCALAR_CHECK_SUFFIX), True
    return testsuite, False


def apply_vector_check(suites: list[str], testplan_dir: Path, vector_check: VectorCheck) -> list[str]:
    """With --vector-check scalar, replace each vector suite that has a scalar self-checking variant with it."""
    if vector_check != VectorCheck.SCALAR:
        return suites
    variants = set(get_vector_scalar_check_extensions(testplan_dir))
    return list(
        dict.fromkeys(
            suite + VECTOR_SCALAR_CHECK_SUFFIX if suite + VECTOR_SCALAR_CHECK_SUFFIX in variants else suite
            for suite in suites
        )
    )
