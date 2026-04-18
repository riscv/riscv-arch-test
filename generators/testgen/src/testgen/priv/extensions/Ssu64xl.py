##################################
# priv/extensions/Ssu64xl.py
#
# Ssu64x privileged extension test generator.
# ammarahwakeel9@gmail.com UET (April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

##################################
# priv/extensions/Ssu64xl.py
##################################

"""Ssu64xl privileged extension test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_ssu64xl_tests(test_data: TestData) -> list[str]:
    covergroup = "Ssu64xl_cg"
    coverpoint = "cp_ssu64xl_UXLEN"

    save_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_ssu64xl_UXLEN",
            "sstatus.UXL=2 (UXLEN=64 for User mode)\nSet bit 63 in a GPR in U-mode and read it back.",
        ),
        "#if __riscv_xlen == 64",
    ]

    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"CSRR(x{save_reg}, sstatus)",
            f"LI(x{val_reg}, {3 << 32})",
            f"CSRC(sstatus, x{val_reg})",  # clear UXL bits [33:32]
            f"LI(x{val_reg}, {2 << 32})",
            f"CSRS(sstatus, x{val_reg})",  # set UXL=2 (UXLEN=64)
        ]
    )

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "RVTEST_GOTO_LOWER_MODE Umode",
            f"LI(x{val_reg}, 1)",
            f"slli x{val_reg}, x{val_reg}, 63",
            f"addi x{check_reg}, x{val_reg}, 0",  # rd_val[63]=1
            test_data.add_testcase("uxlen64_gpr_bit63", coverpoint, covergroup),
            write_sigupd(check_reg, test_data),
        ]
    )

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"CSRW(sstatus, x{save_reg})",
            "RVTEST_GOTO_MMODE",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([save_reg, val_reg, check_reg])
    return lines


@add_priv_test_generator(
    "Ssu64xl",
    required_extensions=["S", "Zicsr", "Ssu64xl"],
    march_extensions=["S", "Zicsr"],
)
def make_ssu64x(test_data: TestData) -> list[str]:
    lines: list[str] = []
    lines.extend(_generate_ssu64xl_tests(test_data))
    return lines
