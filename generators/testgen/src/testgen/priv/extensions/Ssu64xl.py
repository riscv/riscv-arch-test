##################################
# priv/extensions/Ssu64xl.py
#
# Ssu64xl privileged extension test generator.
# Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################


"""Ssu64xl privileged extension test generator."""

from testgen.asm.helpers import comment_banner, load_int_reg, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_ssu64xl_tests(test_data: TestData) -> list[str]:
    covergroup = "Ssu64xl_cg"
    coverpoint = "cp_ssu64xl"

    uxl_reg, val_reg, check_reg, orig_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            f"{coverpoint}",
            "sstatus.UXL=2 (UXLEN=64 for User mode)\nSet bit 63 in a GPR in U-mode and read it back.",
        ),
    ]

    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"CSRR(x{orig_reg}, sstatus)",
            f"CSRR(x{uxl_reg}, sstatus)",
            f"LI(x{val_reg}, {~(3 << 32) & 0xFFFFFFFFFFFFFFFF})",  # mask clears bits 33:32
            f"and x{uxl_reg}, x{uxl_reg}, x{val_reg}",
            f"LI(x{val_reg}, {2 << 32})",  # UXL=2 → bit 33 set
            f"or x{uxl_reg}, x{uxl_reg}, x{val_reg}",
            f"CSRW(sstatus, x{uxl_reg})",
            test_data.add_testcase("uxl_is_10", coverpoint, covergroup),
            f"CSRR(x{uxl_reg}, sstatus)",
            write_sigupd(uxl_reg, test_data),
        ]
    )

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "RVTEST_GOTO_LOWER_MODE Umode",
            test_data.add_testcase("uxlen64_gpr_bit63", coverpoint, covergroup),
            load_int_reg("value", check_reg, 0xFEDCBA9876543210, test_data),
            write_sigupd(check_reg, test_data),
        ]
    )

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"CSRW(sstatus, x{orig_reg})",
            "RVTEST_GOTO_MMODE",
        ]
    )

    test_data.int_regs.return_registers([uxl_reg, val_reg, check_reg, orig_reg])
    return lines


@add_priv_test_generator(
    "Ssu64xl",
    required_extensions=["S", "Ssu64xl"],
    march_extensions=["S"],
)
def make_ssu64xl(test_data: TestData) -> list[str]:
    lines: list[str] = []
    lines.extend(_generate_ssu64xl_tests(test_data))
    return lines
