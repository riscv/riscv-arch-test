##################################
# ZicntrU.py
#
# ZicntrU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrU extension test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_mcounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrU_cg", "cp_mcounteren_access_u"

    read_reg, ones_reg, walk_reg = test_data.int_regs.get_registers(3)

    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to mcounteren.  Read from corresponding counter and counterh in U-mode",
        ),
        "",
    ]
    lines.extend(
        [
            f"LI(x{ones_reg}, -1)",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_1_{i}", coverpoint, covergroup),
                "CSRW(mcounteren, zero)  # clear all bits",
                f"CSRS(mcounteren, x{walk_reg})  # set current bit",
                "RVTEST_GOTO_LOWER_MODE Umode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"CSRR(x{read_reg}, {reg_list[i]})",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, {reg_list[i]}h)",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in U-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i}h in U-mode",
                    "nop",
                    "#endif",
                    "#endif",
                ]
            )

        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )

    # walking a single 0

    lines.extend(
        [
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"CSRS(mcounteren, x{ones_reg})  # set all bits",
                f"CSRC(mcounteren, x{walk_reg})  # clear current bit",
                "RVTEST_GOTO_LOWER_MODE Umode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"CSRR(x{read_reg}, {reg_list[i]})",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, {reg_list[i]}h)",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in U-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i}h in U-mode",
                    "nop",
                    "#endif",
                    "#endif",
                ]
            )
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg])
    return lines


def _generate_mcounteren_access_m_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access m mode tests."""
    covergroup, coverpoint = "ZicntrU_cg", "cp_mcounteren_access_m"

    read_reg, ones_reg, walk_reg = test_data.int_regs.get_registers(3)

    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to mcounteren.  Read from corresponding counter and counterh in M-mode",
        ),
        "",
    ]
    lines.extend(
        [
            f"LI(x{ones_reg}, -1)",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_1_{i}", coverpoint, covergroup),
                "CSRW(mcounteren, zero)  # clear all bits",
                f"CSRS(mcounteren, x{walk_reg})  # set current bit",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"CSRR(x{read_reg}, {reg_list[i]})",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, {reg_list[i]}h)",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in M-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i}h in M-mode",
                    "nop",
                    "#endif",
                    "#endif",
                ]
            )

        lines.extend(
            [
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )

    # walking a single 0

    lines.extend(
        [
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"CSRS(mcounteren, x{ones_reg})  # set all bits",
                f"CSRC(mcounteren, x{walk_reg})  # clear current bit",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"CSRR(x{read_reg}, {reg_list[i]})",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, {reg_list[i]}h)",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in M-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i}h in M-mode",
                    "nop",
                    "#endif",
                    "#endif",
                ]
            )
        lines.extend(
            [
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )

    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg])
    return lines


@add_priv_test_generator(
    "ZicntrU",
    required_extensions=["U", "Zicntr"],
    march_extensions=["Zicsr", "Zicntr", "I", "Zihpm"],
)
def make_zicntru(test_data: TestData) -> list[str]:
    """Generate tests for ZicntrU coverpoints"""
    lines = []

    tmpreg = test_data.int_regs.get_register()
    lines.extend(
        [
            "#ifdef S_SUPPORTED",
            "# Initialize scounteren if S-mode is supported (the boot logic should do this but isn't implemented yet)",
            f"LI(x{tmpreg}, -1)",
            f"CSRW(scounteren, x{tmpreg})",
            "#endif",
            "",
        ]
    )

    lines.extend(_generate_mcounteren_access_u_tests(test_data))
    lines.extend(_generate_mcounteren_access_m_tests(test_data))

    test_data.int_regs.return_register(tmpreg)

    return lines
