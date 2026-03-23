##################################
# U.py
#
# U user mode privileged extension test generator.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""U privileged extension test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_priv_inst_tests(test_data: TestData) -> list[str]:
    """Generate ecall, ebreak, mret, sret tests."""
    ######################################
    covergroup = "U_uprivinst_cg"
    coverpoint = "cp_uprivinst"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Execute privileged instructions\nShould cause ecall, breakpoint, illegal instruction traps",
        ),
        test_data.add_testcase("ecall", coverpoint, covergroup),
        "ecall                 # test ecall instruction",
        "nop",
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak                # test ebreak instruction",
        "nop",
        test_data.add_testcase("mret", coverpoint, covergroup),
        "mret                  # test mret instruction",
        "nop",
        test_data.add_testcase("sret", coverpoint, covergroup),
        "sret                  # test sret instruction",
        "nop",
    ]

    return lines


def _generate_ucsr_tests(test_data: TestData) -> list[str]:
    """Generate CSR tests."""
    covergroup = "U_ucsr_cg"

    ######################################
    coverpoint = "cp_csr_insufficient_priv"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Attempt to read non-user-mode registers.  Should throw illegal instruction",
        ),
    ]
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])
    for csr in (
        list(range(0x100, 0x400)) + list(range(0x500, 0x800)) + list(range(0x900, 0xC00)) + list(range(0xD00, 0x1000))
    ):
        lines.extend(
            [
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"CSRR(x{temp_reg}, 0x{csr:03x})    # attempt to read CSR {csr:03x}; should get illegal instruction",
                "",
            ]
        )

    ######################################
    coverpoint = "cp_csr_ro"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Attempt to write read-only CSRs.  Should throw illegal instruction",
        ),
    )

    lines.append(f"LI(x{temp_reg}, -1)          # x{temp_reg} = all 1s\n")
    for csr in range(0xC00, 0xD00):
        lines.extend(
            [
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"CSRW(0x{csr:03x}, x{temp_reg})    # attempt to write read-only CSR {csr:03x}; should get illegal instruction",
                "",
            ]
        )

    test_data.int_regs.return_register(temp_reg)

    return lines


@add_priv_test_generator("U", required_extensions=["Sm", "U", "Zicsr"])
def make_u(test_data: TestData) -> list[str]:
    """Generate tests for U user-mode testsuite."""
    lines: list[str] = []

    lines.extend(["RVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n"])
    lines.extend(_generate_priv_inst_tests(test_data))
    lines.extend(_generate_ucsr_tests(test_data))

    return lines
