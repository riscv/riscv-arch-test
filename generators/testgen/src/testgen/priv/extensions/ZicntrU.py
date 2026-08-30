##################################
# ZicntrU.py
#
# ZicntrU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrU extension test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
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
                "csrw mcounteren, zero  # clear all bits",
                f"csrs mcounteren, x{walk_reg}  # set current bit",
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
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in U-mode",
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
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in U-mode",
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
                "csrw mcounteren, zero  # clear all bits",
                f"csrs mcounteren, x{walk_reg}  # set current bit",
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
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in M-mode",
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
                f"csrs mcounteren, x{ones_reg}  # set all bits",
                f"csrc mcounteren, x{walk_reg}  # clear current bit",
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
                    f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in M-mode",
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


def _generate_mcounter_inc_inaccessible_tests(test_data: TestData) -> list[str]:
    """start in M mode
    read instret and mcounteren = 0s
    goto U mode
    nop
    go back to M mode
    mcounteren = 1s
    go back to U mode
    read and sigupd change in instret
    """
    covergroup, coverpoint = "ZicntrU_cg", "cp_mcounter_inc_inaccessible"

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, _generate_mcounter_inc_inaccessible_tests.__doc__),
        "",
    ]
    lines.extend(
        [
            test_data.add_testcase("U", coverpoint, covergroup),
            f"csrr x{old_reg}, instret",
            "# make counter inaccessible in U mode",
            "csrw mcounteren, zero",
            "#ifdef S_SUPPORTED",
            "csrw scounteren, zero",
            "#endif",
            "RVTEST_GOTO_LOWER_MODE Umode",
            "nop",
            "RVTEST_GOTO_MMODE",
            "# make counter accessible in U mode",
            f" LI(x{read_reg}, -1)",
            f"csrw mcounteren, x{read_reg}",
            "#ifdef S_SUPPORTED",
            f"csrw scounteren, x{read_reg}",
            "#endif",
            "RVTEST_GOTO_LOWER_MODE Umode",
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
    "ZicntrU",
    required_extensions=["U", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm"],
    # TODO: Remove BOOT_TO_MMODE when converting this test to T-SBI.
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicntru(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrU coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tmpreg = test_data.int_regs.get_register()
    tc.code.extend(
        [
            "#ifdef S_SUPPORTED",
            "# Initialize scounteren if S-mode is supported (the boot logic should do this but isn't implemented yet)",
            f"LI(x{tmpreg}, -1)",
            f"csrw scounteren, x{tmpreg}",
            "#endif",
            "",
        ]
    )

    tc.code.extend(_generate_mcounteren_access_u_tests(test_data))
    tc.code.extend(_generate_mcounteren_access_m_tests(test_data))
    tc.code.extend(_generate_mcounter_inc_inaccessible_tests(test_data))
    test_data.int_regs.return_register(tmpreg)

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
