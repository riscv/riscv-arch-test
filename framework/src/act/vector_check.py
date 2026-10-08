##################################
# vector_check.py
#
# Selection of the scalar self-checking vector suites (e.g. Vx8-scalarcheck) with --vector-check
# SPDX-License-Identifier: Apache-2.0
##################################

import re
import shutil
from collections.abc import Iterable
from enum import Enum
from pathlib import Path


class VectorCheck(str, Enum):
    """How vector tests check results: with vector instructions or with scalar code."""

    VECTOR = "vector"
    SCALAR = "scalar"


# Scalar self-checking vector suites are named after their base suite, e.g. Vx8-scalarcheck
VECTOR_SCALAR_CHECK_SUFFIX = "-scalarcheck"


def base_test_suite(suite: str) -> str:
    """Return the base suite of a scalar self-checking vector suite, or the suite itself."""
    return suite.removesuffix(VECTOR_SCALAR_CHECK_SUFFIX)


def has_scalar_check_variant(suite: str) -> bool:
    """Return whether a suite has a scalar self-checking variant."""
    return re.fullmatch(r"(Vx|Vls|Vf)\d+", suite) is not None


def requested_suite(suite: str, vector_check: VectorCheck) -> str:
    """Return the suite directory to build for a suite named in --extensions."""
    if vector_check == VectorCheck.SCALAR and has_scalar_check_variant(suite):
        return suite + VECTOR_SCALAR_CHECK_SUFFIX
    return suite


def selects_suite(suite: str, vector_check: VectorCheck) -> bool:
    """Return whether a suite directory is built when all suites are selected."""
    if vector_check == VectorCheck.SCALAR:
        return not has_scalar_check_variant(suite)
    return suite == base_test_suite(suite)


def remove_other_variant_elfs(elf_dir: Path, test_names: Iterable[str]) -> None:
    """Remove the ELFs of the unselected variant of each selected vector suite.

    ELFs from an earlier build with the other VECTOR_CHECK setting would otherwise be run as well.
    """
    selected_suites = {Path(test_name).parent.name for test_name in test_names}
    for suite in selected_suites:
        base_suite = base_test_suite(suite)
        if not has_scalar_check_variant(base_suite):
            continue
        other_suite = base_suite if suite != base_suite else base_suite + VECTOR_SCALAR_CHECK_SUFFIX
        if other_suite in selected_suites:
            continue
        for other_dir in elf_dir.glob(f"*/{other_suite}"):
            shutil.rmtree(other_dir)
