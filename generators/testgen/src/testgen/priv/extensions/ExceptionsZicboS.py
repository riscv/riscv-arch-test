##################################
# ExceptionsZicboS.py
#
# ExceptionsZicboS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_cbie_tests(test_data: TestData) -> list[str]:
    """Generate cbie trap tests."""
    covergroup, coverpoint = "ExceptionsZicboS_cg", "cp_cbie"

    addr_reg, envcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint)]
    modes = ["3", "1", "0"]
    menvcfg = ["00", "01", "11"]
    senvcfg = ["00", "01", "11"]
    for mode in modes:
        for m_val in menvcfg:
            for s_val in senvcfg:
                lines.extend(
                    [
                        "#ifdef __riscv_zicbom",
                        f"    LA(x{addr_reg}, scratch)",
                        f"\tRVTEST_GOTO_MMODE \n    LI(x{envcfg_reg}, {int(m_val, 2) << 4})",
                        f"    csrw  menvcfg, x{envcfg_reg}",
                        f"    LI(x{envcfg_reg}, {int(s_val, 2) << 4})",
                        f"    csrw  senvcfg, x{envcfg_reg}",
                    ]
                )

                if mode == "0":
                    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Umode \n"])
                elif mode == "1":
                    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Smode \n"])
                else:
                    lines.extend(["\tRVTEST_GOTO_MMODE\n"])
                lines.extend(
                    [
                        "    nop",
                        test_data.add_testcase(f"cbo.inval_mode{mode}_mval{m_val}_sval{s_val}", coverpoint, covergroup),
                        f"    cbo.inval    0(x{addr_reg})",
                        "    nop",
                        "#endif",
                        "",
                    ]
                )

    test_data.int_regs.return_registers([addr_reg, envcfg_reg])
    return lines


def _generate_cbcfe_tests(test_data: TestData) -> list[str]:
    """Generate cbcfe trap tests."""
    covergroup, coverpoint = "ExceptionsZicboS_cg", "cp_cbcfe"

    addr_reg, envcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint)]
    modes = ["3", "1", "0"]
    menvcfg = ["0", "1"]
    senvcfg = ["0", "1"]
    for mode in modes:
        for m_val in menvcfg:
            for s_val in senvcfg:
                lines.extend(
                    [
                        "#ifdef __riscv_zicbom",
                        f"    LA(x{addr_reg}, scratch)",
                        f"\tRVTEST_GOTO_MMODE \n    LI(x{envcfg_reg}, {int(m_val, 2) << 6})",
                        f"    csrw  menvcfg, x{envcfg_reg}",
                        f"    LI(x{envcfg_reg}, {int(s_val, 2) << 6})",
                        f"    csrw  senvcfg, x{envcfg_reg}",
                    ]
                )

                if mode == "0":
                    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Umode \n"])
                elif mode == "1":
                    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Smode \n"])
                else:
                    lines.extend(["\tRVTEST_GOTO_MMODE\n"])
                lines.extend(
                    [
                        "    nop",
                        test_data.add_testcase(f"cbo.clean_mode{mode}_mval{m_val}_sval{s_val}", coverpoint, covergroup),
                        f"    cbo.clean    0(x{addr_reg})",
                        "    nop",
                        test_data.add_testcase(f"cbo.flush_mode{mode}_mval{m_val}_sval{s_val}", coverpoint, covergroup),
                        f"    cbo.flush    0(x{addr_reg})",
                        "    nop",
                        "#endif",
                        "",
                    ]
                )

    test_data.int_regs.return_registers([addr_reg, envcfg_reg])
    return lines


def _generate_cbze_tests(test_data: TestData) -> list[str]:
    """Generate cbze trap tests."""
    covergroup, coverpoint = "ExceptionsZicboS_cg", "cp_cbze"

    addr_reg, envcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint)]
    modes = ["3", "1", "0"]
    menvcfg = ["0", "1"]
    senvcfg = ["0", "1"]
    for mode in modes:
        for m_val in menvcfg:
            for s_val in senvcfg:
                lines.extend(
                    [
                        "#ifdef __riscv_zicboz",
                        f"    LA(x{addr_reg}, scratch)",
                        f"\tRVTEST_GOTO_MMODE \n    LI(x{envcfg_reg}, {int(m_val, 2) << 7})",
                        f"    csrw  menvcfg, x{envcfg_reg}",
                        f"    LI(x{envcfg_reg}, {int(s_val, 2) << 7})",
                        f"    csrw  senvcfg, x{envcfg_reg}",
                    ]
                )

                if mode == "0":
                    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Umode \n"])
                elif mode == "1":
                    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Smode \n"])
                else:
                    lines.extend(["\tRVTEST_GOTO_MMODE\n"])
                lines.extend(
                    [
                        "    nop",
                        test_data.add_testcase(f"cbo.zero_mode{mode}_mval{m_val}_sval{s_val}", coverpoint, covergroup),
                        f"    cbo.zero    0(x{addr_reg})",
                        "    nop",
                        "#endif",
                        "",
                    ]
                )

    test_data.int_regs.return_registers([addr_reg, envcfg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsZicboS", required_extensions=["Zicsr", "Sm", "U", "S"], march_extensions=["Zicsr", "Zicbom", "Zicboz"]
)
def make_exceptionszalrsc(test_data: TestData) -> list[str]:
    """Generate tests for ExceptionsZicboS coverpoints"""
    lines = []

    lines.extend(
        [
            "# Initialize scratch memory with test data",
            "    LA(x10, scratch)",
            "    LI(x11, 0xDEADBEEF)",
            "    sw x11, 0(x10)",
            "    sw x11, 4(x10)",
            "    sw x11, 8(x10)",
            "    sw x11, 12(x10)",
            "",
        ]
    )

    lines.extend(_generate_cbie_tests(test_data))
    lines.extend(_generate_cbcfe_tests(test_data))
    lines.extend(_generate_cbze_tests(test_data))

    return lines
