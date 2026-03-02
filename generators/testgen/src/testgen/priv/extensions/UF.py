##################################
# UF.py
#
# UF floating-point from user mode privileged extension test generator.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""UF privileged extension test generator."""

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_ufcsr_tests(test_data: TestData) -> list[str]:
    """Generate CSR tests."""
    covergroup = "UF_ufcsr_cg"

    # fp CSRs
    csrs = ["fcsr", "frm", "fflags"]
    lines = []

    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n"])

    ######################################
    coverpoint = "cp_ufcsr_access"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all fp CSRs",
        )
    )

    for csr in csrs:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    ######################################
    coverpoint = "cp_ufcsrwalk"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Set and clear each bit individually in all writable fp CSRs",
        ),
    )

    for csr in csrs:
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    return lines


@add_priv_test_generator("UF", required_extensions=["Sm", "U", "F", "Zicsr"])
def make_uf(test_data: TestData) -> list[str]:
    """Generate tests for UF user-mode floating-point testsuite."""
    lines: list[str] = []

    lines.extend(_generate_ufcsr_tests(test_data))

    return lines
