##################################
# U.py
#
# U user mode privileged extension test generator.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""U privileged extension test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_priv_inst_tests(test_data: TestData) -> list[str]:
    """Generate ecall and ebreak tests."""
    ######################################
    covergroup = "U_uprivinst_cg"
    coverpoint = "cp_uprvinst"
    ######################################

    lines = [
        comment_banner(
            "cp_uprvinst",
            "Execute privileged instructions\nShould cause ecall, breakpoint, illegal instruction traps",
        ),
        # ecall test
        test_data.add_testcase(coverpoint, "ecall", covergroup),
        "    ecall                 # test ecall instruction",
        "    nop",
        # ebreak test
        test_data.add_testcase(coverpoint, "ebreak", covergroup),
        "    ebreak                # test ebreak instruction",
        "    nop",
        # ebreak test
        test_data.add_testcase(coverpoint, "mret", covergroup),
        "    mret                  # test mret instruction",
        "    nop",
        # ebreak test
        test_data.add_testcase(coverpoint, "sret", covergroup),
        "    sret                  # test sret instruction",
        "    nop",
    ]

    return lines


def _generate_ucsr_tests(test_data: TestData) -> list[str]:
    """Generate CSR tests"""
    covergroup = "U_ucsr_cg"

    ######################################
    coverpoint = "cp_csr_insufficient_priv"
    ######################################

    lines = [
        comment_banner(
            f"{coverpoint}",
            "Attempt to read non-user-mode registers.  Should throw illegal instruction",
        ),
    ]
    for csr in (
        list(range(0x100, 0x400)) + list(range(0x500, 0x800)) + list(range(0x900, 0xC00)) + list(range(0xD00, 0x1000))
    ):
        lines.extend(
            [
                # Test the write value
                test_data.add_testcase(coverpoint, f"{csr}", covergroup),
                f"\tCSRR(t0, 0x{csr:03x})    # attempt to read CSR {csr:03x}; should get illegal instruction",
            ]
        )

    ######################################
    coverpoint = "cp_csr_ro"
    ######################################

    lines.append(
        comment_banner(
            f"{coverpoint}",
            "Attempt to write read-only CSRs.  Should throw illegal instruction",
        ),
    )

    lines.append("\tLI(t0, -1)          # t0 = all 1s\n")
    for csr in range(0xC00, 0xD00):
        lines.extend(
            [
                test_data.add_testcase(coverpoint, f"{csr}", covergroup),
                f"\tCSRW(0x{csr:03x}, t0)    # attempt to write read-only CSR {csr:03x}; should get illegal instruction\n",
            ]
        )

    return lines


@add_priv_test_generator("U", required_extensions=["Sm", "U", "Zicsr"])
def make_u(test_data: TestData) -> list[str]:
    """Generate tests for U user-mode testsuite."""
    lines: list[str] = []

    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n"])
    lines.extend(_generate_priv_inst_tests(test_data))
    lines.extend(_generate_ucsr_tests(test_data))

    return lines
