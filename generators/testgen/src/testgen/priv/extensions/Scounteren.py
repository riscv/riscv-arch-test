##################################
# Scounteren.py
# ayesha.anwaar2005@gmail.com 22 April 2026
# Scounteren supervisor counter-enable register test generator.
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_scounteren_tests(test_data: TestData) -> list[str]:
    """Generate tests for scounteren CSR."""
    covergroup = "Sscounteren_cg"
    coverpoint = "cp_scounteren_writable"
    lines = [
        comment_banner(
            coverpoint,
            "Set and clear each bit individually in scounteren",
        ),
    ]

    lines.extend(csr_walk_test(test_data, "scounteren", covergroup, coverpoint))

    return lines


@add_priv_test_generator("Scounteren", required_extensions=["S", "Zicsr"])
def make_sscounteren(test_data: TestData) -> list[str]:
    """Generate tests for Scounteren supervisor counter-enable register."""
    lines: list[str] = []
    lines.extend(_generate_scounteren_tests(test_data))
    return lines
