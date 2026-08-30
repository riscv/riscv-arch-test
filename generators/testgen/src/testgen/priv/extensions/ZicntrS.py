##################################
# ZicntrS.py
#
# ZicntrS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrS extension test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
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
            f"csrw mcounteren, x{ones_reg}  # enable all counters in M-mode",
            f"LI(x{walk_reg}, 1)",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_1_{i}", coverpoint, covergroup),
                "csrw scounteren, zero  # clear all bits",
                f"csrs scounteren, x{walk_reg}  # set current bit",
            ]
        )
        if mode != "Mmode":
            lines.append(f"RVTEST_GOTO_LOWER_MODE {mode}")
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
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in {mode}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in {mode}",
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
            f"csrw mcounteren, x{ones_reg}  # enable all counters in M-mode",
        ]
    )
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"csrs scounteren, x{ones_reg}  # set all bits",
                f"csrc scounteren, x{walk_reg}  # clear current bit",
            ]
        )
        if mode != "Mmode":
            lines.append(f"RVTEST_GOTO_LOWER_MODE {mode}")
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
                    f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in {mode}",
                    "#if __riscv_xlen == 32",
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i} in {mode}",
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
                "csrw mcounteren, zero  # clear all bits",
                f"csrs mcounteren, x{walk_reg}  # set current bit",
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
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"csrs mcounteren, x{ones_reg}  # set all bits",
                f"csrc mcounteren, x{walk_reg}  # clear current bit",
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
                "csrw mcounteren, zero  # clear all bits",
                f"csrs mcounteren, x{walk_reg}  # set current bit",
                "csrw scounteren, zero  # clear all bits",
                f"csrs scounteren, x{walk_reg}  # set current bit",
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
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"csrs mcounteren, x{ones_reg}  # set all bits",
                f"csrc mcounteren, x{walk_reg}  # clear current bit",
                f"csrs scounteren, x{ones_reg}  # set all bits",
                f"csrc scounteren, x{walk_reg}  # clear current bit",
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

    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg])
    return lines


def _generate_mcounter_inc_inaccessible_tests(test_data: TestData) -> list[str]:
    """start in M mode
    read instret and mcounteren = 0s
    goto S mode
    nop
    go back to M mode
    mcounteren = 1s
    go back to S mode
    read and sigupd change in instret
    """
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounter_inc_inaccessible"

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, _generate_mcounter_inc_inaccessible_tests.__doc__),
        "",
    ]
    lines.extend(
        [
            test_data.add_testcase("S", coverpoint, covergroup),
            f"csrr x{old_reg}, instret",
            "# make counter inaccessible in S mode",
            "csrw mcounteren, zero",
            "RVTEST_GOTO_LOWER_MODE Smode",
            "nop",
            "RVTEST_GOTO_MMODE",
            "# make counter accessible in S mode",
            f" LI(x{read_reg}, -1)",
            f"csrw mcounteren, x{read_reg}",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"csrr x{read_reg}, instret",
            f"sub x{read_reg}, x{read_reg}, x{old_reg}",
            "# SIGUPD the difference in instret",
            write_sigupd(read_reg, test_data),
            "RVTEST_GOTO_MMODE",
        ]
    )
    test_data.int_regs.return_registers([old_reg, read_reg])
    return lines


@add_priv_test_generator(
    "ZicntrS",
    required_extensions=["S", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm"],
    # TODO: Remove BOOT_TO_MMODE when converting this test to T-SBI.
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicntrs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrS coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_mcounteren_access_s_tests(test_data))
    tc.code.extend(_generate_scounteren_access_s_tests(test_data))
    tc.code.extend(_generate_scounteren_access_m_tests(test_data))
    tc.code.extend(_generate_scounteren_access_u_tests(test_data))
    tc.code.extend(_generate_mscounteren_access_u_tests(test_data))
    tc.code.extend(_generate_mcounter_inc_inaccessible_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
