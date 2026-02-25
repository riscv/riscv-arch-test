##################################
# ExceptionsZc.py
#
# ExceptionsZc privileged extension test generator.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsZc privileged extension test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    """Generate illegal compressed instructions."""
    ######################################
    covergroup = "ExceptionsZc_cg"
    coverpoint = "cp_illegal_instruction"
    ######################################

    lines = [
        comment_banner(
            "cp_illegal_instruction",
            "Illegal instructions of all 0s and all 1s",
        ),
        "",
        test_data.add_testcase("bin_zeros", coverpoint, covergroup),
        f"test_{test_data.test_count}:",
        ".insn 0x0000       # illegal instruction",
        "nop",  # exception handler skips following instruction
        test_data.add_testcase("bin_ones", coverpoint, covergroup),
        f"test_{test_data.test_count}:",
        ".insn 0xFFFF       # illegal instruction",
        ".insn 0xFFFF       # fill upper bits",
        "nop",  # exception handler skips following instruction
    ]

    return lines


@add_priv_test_generator(
    "ExceptionsZc",
    required_extensions=["Zicsr", "Sm", "Zca"],
    march_extensions=["Zicsr", "Zca", "Zcb", "Zcd", "F", "D"],
)
def make_exceptionszc(test_data: TestData) -> list[str]:
    """Generate tests for ExceptionsZc machine-mode extension."""
    lines: list[str] = []

    lines.extend(_generate_illegal_instruction_tests(test_data))

    return lines
