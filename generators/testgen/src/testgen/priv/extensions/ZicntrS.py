##################################
# ZicntrS.py
#
# ZicntrS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrS extension test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _helper_scounteren_access(
    mode: str,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    read_reg, ones_reg, walk_reg = test_data.int_regs.get_registers(3)
    lines = []
    reg_list = ["cycle", "time", "instret"]
    lines.extend(
        [
            f"LI(x{ones_reg}, -1)",
            f"CSRW(mcounteren, x{ones_reg})  # enable all counters in M-mode",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_1_{i}", coverpoint, covergroup),
                "CSRW(scounteren, zero)  # clear all bits",
                f"CSRS(scounteren, x{walk_reg})  # set current bit",
            ]
        )
        if mode != "Mmode":
            lines.append(f"RVTEST_GOTO_LOWER_MODE {mode}")
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
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in {mode}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i} in {mode}",
                    "nop",
                    "#endif",
                    "#endif",
                ]
            )
        if mode != "Mmode":
            lines.append("RVTEST_GOTO_MMODE")
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")

    # walking a single 0

    lines.extend(
        [
            f"LI(x{walk_reg}, 1)",
            f"CSRW(mcounteren, x{ones_reg})  # enable all counters in M-mode",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"CSRS(scounteren, x{ones_reg})  # set all bits",
                f"CSRC(scounteren, x{walk_reg})  # clear current bit",
            ]
        )
        if mode != "Mmode":
            lines.append(f"RVTEST_GOTO_LOWER_MODE {mode}")
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
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in {mode}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i} in {mode}",
                    "nop",
                    "#endif",
                    "#endif",
                ]
            )
        if mode != "Mmode":
            lines.append("RVTEST_GOTO_MMODE")
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg])
    return lines


def _generate_mcounteren_access_s_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access s mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounteren_access_s"

    read_reg, ones_reg, walk_reg = test_data.int_regs.get_registers(3)
    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to mcounteren.  Read from corresponding counter and counterh in S-mode",
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
                "RVTEST_GOTO_LOWER_MODE Smode",
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
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in S-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i} in S-mode",
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
                "RVTEST_GOTO_LOWER_MODE Smode",
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
                    f"CSRR(x{read_reg}, hpmcounter{i}) # read from hpmcounter{i} in S-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i} in S-mode",
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


def _generate_scounteren_access_s_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access s mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_s"

    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in S-mode",
        ),
        "",
    ]
    lines.extend(_helper_scounteren_access("Smode", test_data, coverpoint, covergroup))
    return lines


def _generate_scounteren_access_m_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access m mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_m"

    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in M-mode",
        ),
        "",
    ]
    lines.extend(_helper_scounteren_access("Mmode", test_data, coverpoint, covergroup))
    return lines


def _generate_scounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_u"

    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in U-mode",
        ),
        "",
    ]
    lines.extend(_helper_scounteren_access("Umode", test_data, coverpoint, covergroup))
    return lines


def _generate_mscounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounteren_access_u"

    read_reg, ones_reg, walk_reg = test_data.int_regs.get_registers(3)
    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to both scounteren and mcounteren (same value in each).  Read from corresponding counter and counterh in U-mode",
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
                "CSRW(scounteren, zero)  # clear all bits",
                f"CSRS(scounteren, x{walk_reg})  # set current bit",
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
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i} in U-mode",
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
                f"CSRS(scounteren, x{ones_reg})  # set all bits",
                f"CSRC(scounteren, x{walk_reg})  # clear current bit",
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
                    f"CSRR(x{read_reg}, hpmcounter{i}h) # read from hpmcounter{i} in U-mode",
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


@add_priv_test_generator(
    "ZicntrS",
    required_extensions=["I", "Zicsr", "Sm", "S", "Zicntr"],
    march_extensions=["Zicsr", "Zicntr", "I", "Zihpm"],
)
def make_zicntrs(test_data: TestData) -> list[str]:
    """Generate tests for ZicntrS coverpoints"""
    lines = []

    lines.extend(_generate_mcounteren_access_s_tests(test_data))
    lines.extend(_generate_scounteren_access_s_tests(test_data))
    lines.extend(_generate_scounteren_access_m_tests(test_data))
    lines.extend(_generate_scounteren_access_u_tests(test_data))
    lines.extend(_generate_mscounteren_access_u_tests(test_data))
    return lines
