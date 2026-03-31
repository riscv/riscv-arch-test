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


def _generate_mcounteren_access_s_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access s mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounteren_access_s"

    read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])
    # the registers(the ones other than x0) are excluded because they are used by the RVTEST_GOTO_LOWER_MODE Smode macro
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
            f"csrr x{ori_csr_reg}, mcounteren",
            f"LI(x{one_reg}, -1)",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 1 at {i}", coverpoint, covergroup),
                f"csrrc x{temp_reg}, mcounteren, x{one_reg}  # clear all bits",
                f"csrrs x{temp_reg}, mcounteren, x{walk_reg}  # set current bit",
                "RVTEST_GOTO_LOWER_MODE Smode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in S-mode",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in S-mode",
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
                test_data.add_testcase(f"walking 0 at {i}", coverpoint, covergroup),
                f"csrrs x{temp_reg}, mcounteren, x{one_reg}  # set all bits",
                f"csrrc x{temp_reg}, mcounteren, x{walk_reg}  # clear current bit",
                "RVTEST_GOTO_LOWER_MODE Smode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in S-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in S-mode",
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
    lines.append(f"csrrw x{temp_reg}, mcounteren, {ori_csr_reg}  # restore original csr value")

    test_data.int_regs.return_registers([read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg])
    return lines


def _generate_scounteren_access_s_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access s mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_s"

    read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])
    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in S-mode",
        ),
        "",
    ]
    lines.extend(
        [
            f"LI(x{one_reg}, -1)",
            f"csrw mcounteren, x{one_reg}  # enable all counters in M-mode",
            f"csrr x{ori_csr_reg}, scounteren",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 1 at {i}", coverpoint, covergroup),
                f"csrrc x{temp_reg}, scounteren, x{one_reg}  # clear all bits",
                f"csrrs x{temp_reg}, scounteren, x{walk_reg}  # set current bit",
                "RVTEST_GOTO_LOWER_MODE Smode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in S-mode",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in S-mode",
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
            f"csrw mcounteren, x{one_reg}  # enable all counters in M-mode",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 0 at {i}", coverpoint, covergroup),
                f"csrrs x{temp_reg}, scounteren, x{one_reg}  # set all bits",
                f"csrrc x{temp_reg}, scounteren, x{walk_reg}  # clear current bit",
                "RVTEST_GOTO_LOWER_MODE Smode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in S-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in S-mode",
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
    lines.append(f"csrrw x{temp_reg}, scounteren, {ori_csr_reg}  # restore original csr value")

    test_data.int_regs.return_registers([read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg])
    return lines


def _generate_scounteren_access_m_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access m mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_m"

    read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])
    # the registers(the ones other than x0) are excluded because they are used by the RVTEST_GOTO_LOWER_MODE Smode macro
    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in M-mode",
        ),
        "",
    ]
    lines.extend(
        [
            f"LI(x{one_reg}, -1)",
            f"csrw mcounteren, x{one_reg}  # enable all counters in M-mode",
            f"csrr x{ori_csr_reg}, scounteren",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 1 at {i}", coverpoint, covergroup),
                f"csrrc x{temp_reg}, scounteren, x{one_reg}  # clear all bits",
                f"csrrs x{temp_reg}, scounteren, x{walk_reg}  # set current bit",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in M-mode",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in M-mode",
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
            f"csrw mcounteren, x{one_reg}  # enable all counters in M-mode",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 0 at {i}", coverpoint, covergroup),
                f"csrrs x{temp_reg}, scounteren, x{one_reg}  # set all bits",
                f"csrrc x{temp_reg}, scounteren, x{walk_reg}  # clear current bit",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in M-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in M-mode",
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
    lines.append(f"csrrw x{temp_reg}, scounteren, {ori_csr_reg}  # restore original csr value")

    test_data.int_regs.return_registers([read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg])
    return lines


def _generate_scounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_u"

    read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])
    # the registers(the ones other than x0) are excluded because they are used by the RVTEST_GOTO_LOWER_MODE Smode macro
    reg_list = ["cycle", "time", "instret"]
    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in U-mode",
        ),
        "",
    ]
    lines.extend(
        [
            f"LI(x{one_reg}, -1)",
            f"csrw mcounteren, x{one_reg}  # enable all counters in M-mode",
            f"csrr x{ori_csr_reg}, scounteren",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 1 at {i}", coverpoint, covergroup),
                f"csrrc x{temp_reg}, scounteren, x{one_reg}  # clear all bits",
                f"csrrs x{temp_reg}, scounteren, x{walk_reg}  # set current bit",
                "RVTEST_GOTO_LOWER_MODE Umode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in U-mode",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in U-mode",
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
            f"csrw mcounteren, x{one_reg}  # enable all counters in M-mode",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 0 at {i}", coverpoint, covergroup),
                f"csrrs x{temp_reg}, scounteren, x{one_reg}  # set all bits",
                f"csrrc x{temp_reg}, scounteren, x{walk_reg}  # clear current bit",
                "RVTEST_GOTO_LOWER_MODE Umode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in U-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in U-mode",
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
    lines.append(f"csrrw x{temp_reg}, scounteren, {ori_csr_reg}  # restore original csr value")

    test_data.int_regs.return_registers([read_reg, ori_csr_reg, one_reg, walk_reg, temp_reg])
    return lines


def _generate_mcounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounteren_access_u"

    read_reg, ori_m_reg, ori_s_reg, one_reg, walk_reg, temp_reg = test_data.int_regs.get_registers(6, exclude_regs=[0])
    # the registers(the ones other than x0) are excluded because they are used by the RVTEST_GOTO_LOWER_MODE Smode macro
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
            f"csrr x{ori_m_reg}, mcounteren",
            f"csrr x{ori_s_reg}, scounteren",
            f"LI(x{one_reg}, -1)",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking 1 at {i}", coverpoint, covergroup),
                f"csrrc x{temp_reg}, mcounteren, x{one_reg}  # clear all bits",
                f"csrrs x{temp_reg}, mcounteren, x{walk_reg}  # set current bit",
                f"csrrc x{temp_reg}, scounteren, x{one_reg}  # clear all bits",
                f"csrrs x{temp_reg}, scounteren, x{walk_reg}  # set current bit",
                "RVTEST_GOTO_LOWER_MODE Umode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in U-mode",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in U-mode",
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
                test_data.add_testcase(f"walking 0 at {i}", coverpoint, covergroup),
                f"csrrs x{temp_reg}, mcounteren, x{one_reg}  # set all bits",
                f"csrrc x{temp_reg}, mcounteren, x{walk_reg}  # clear current bit",
                f"csrrs x{temp_reg}, scounteren, x{one_reg}  # set all bits",
                f"csrrc x{temp_reg}, scounteren, x{walk_reg}  # clear current bit",
                "RVTEST_GOTO_LOWER_MODE Umode",
            ]
        )
        if i < 3:
            lines.extend(
                [
                    f"csrr x{read_reg}, {reg_list[i]}",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, {reg_list[i]}h",
                    "nop",
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    "#ifdef ZIHPM_SUPPORTED",
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in U-mode",
                    "nop",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in U-mode",
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
    lines.append(f"csrrw x{temp_reg}, mcounteren, {ori_m_reg}  # restore original csr value")
    lines.append(f"csrrw x{temp_reg}, scounteren, {ori_s_reg}")

    test_data.int_regs.return_registers([read_reg, ori_s_reg, ori_m_reg, one_reg, walk_reg, temp_reg])
    return lines


@add_priv_test_generator(
    "ZicntrS",
    required_extensions=["I", "Zicsr", "Sm", "S", "Zicntr"],
    march_extensions=["Zicsr", "Zicntr", "I", "Zihpm"],
)
def make_exceptionszicntrs(test_data: TestData) -> list[str]:
    """Generate tests for ZicntrS coverpoints"""
    lines = []

    lines.extend(_generate_mcounteren_access_s_tests(test_data))
    lines.extend(_generate_scounteren_access_s_tests(test_data))
    lines.extend(_generate_scounteren_access_m_tests(test_data))
    lines.extend(_generate_scounteren_access_u_tests(test_data))
    lines.extend(_generate_mcounteren_access_u_tests(test_data))
    return lines
