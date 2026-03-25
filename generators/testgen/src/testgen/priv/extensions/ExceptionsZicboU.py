##################################
# ExceptionsZicboU.py
#
# ExceptionsZicboU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_cbie_tests(test_data: TestData) -> list[str]:
    """Generate cbie trap tests."""
    covergroup, coverpoint = "ExceptionsZicboU_cg", "cp_cbie"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute cbo.inval in {machine/user} mode with menvcfg.cbie = {00/01/11}",
        ),
        "",
    ]
    modes = ["3", "0"]
    bins = ["00", "01", "11"]
    lines.append("#ifdef ZICBOM_SUPPORTED")
    for mode in modes:
        for b in bins:
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, {int(b, 2) << 4})",
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("RVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")
            else:
                lines.append("RVTEST_GOTO_MMODE")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"cbo.inval_mode{mode}_menvcfg.cbie{b}", coverpoint, covergroup),
                    f"cbo.inval    (x{addr_reg})",
                    "nop",
                ]
            )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbcfe_tests(test_data: TestData) -> list[str]:
    """Generate cbcfe trap tests."""
    covergroup, coverpoint = "ExceptionsZicboU_cg", "cp_cbcfe"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute cbo.{clean, flush} in {machine/user} mode with menvcfg.cbcfe = {0/1}",
        ),
        "",
    ]
    modes = ["3", "0"]
    bins = ["0", "1"]
    lines.append("#ifdef ZICBOM_SUPPORTED")
    for mode in modes:
        for b in bins:
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, {int(b, 2) << 6})",
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("RVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode")
            else:
                lines.append("RVTEST_GOTO_MMODE")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"cbo.clean_mode{mode}_menvcfg.cbcfe{b}", coverpoint, covergroup),
                    f"cbo.clean    (x{addr_reg})",
                    "nop",
                    test_data.add_testcase(f"cbo.flush_mode{mode}_menvcfg.cbcfe{b}", coverpoint, covergroup),
                    f"cbo.flush    (x{addr_reg})",
                    "nop",
                ]
            )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbze_tests(test_data: TestData) -> list[str]:
    """Generate cbze trap tests."""
    covergroup, coverpoint = "ExceptionsZicboU_cg", "cp_cbze"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute cbo.zero in {machine/user} mode with menvcfg.cbze = {0/1}",
        ),
        "",
    ]
    modes = ["3", "0"]
    bins = ["0", "1"]
    lines.append("#ifdef ZICBOZ_SUPPORTED")
    for mode in modes:
        for b in bins:
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, {int(b, 2) << 7})",
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("RVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode")
            else:
                lines.append("RVTEST_GOTO_MMODE")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"cbo.zero_mode{mode}_menvcfg.cbze{b}", coverpoint, covergroup),
                    f"cbo.zero    (x{addr_reg})",
                    "nop",
                ]
            )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbo_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate cbo access fault trap tests."""
    covergroup, coverpoint = "ExceptionsZicboU_cg", "cp_cbo_access_fault"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} Execute op to ACCESS_FAULT_ADDR with menvcfg enabled",
        ),
        "",
    ]
    modes = ["3", "0"]
    cbo_instrs = ["inval", "clean", "flush", "zero"]
    prefetch_instrs = ["i", "r", "w"]
    for mode in modes:
        for cbo in cbo_instrs:
            if cbo == "zero":
                lines.append("#ifdef ZICBOZ_SUPPORTED")
            else:
                lines.append("#ifdef ZICBOM_SUPPORTED")
            lines.extend(
                [
                    f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")
            else:
                lines.append("\tRVTEST_GOTO_MMODE\n")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"cbo.{cbo}_mode{mode}_access_fault", coverpoint, covergroup),
                    f"cbo.{cbo}    0(x{addr_reg})",
                    "nop",
                    "#endif",
                ]
            )
        for prefetch in prefetch_instrs:
            lines.extend(
                [
                    f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")
            else:
                lines.append("\tRVTEST_GOTO_MMODE\n")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"prefetch.{prefetch}_mode{mode}_access_fault", coverpoint, covergroup),
                    f"prefetch.{prefetch}    0(x{addr_reg})",
                    "nop",
                ]
            )
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbo_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate cbo misaligned trap tests."""
    covergroup, coverpoint = "ExceptionsZicboU_cg", "cp_cbo_misaligned"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} Execute op to valid address + 1 with menvcfg enabled",
        ),
        "",
    ]
    modes = ["3", "0"]
    cbo_instrs = ["inval", "clean", "flush", "zero"]
    prefetch_instrs = ["i", "r", "w"]
    for mode in modes:
        for cbo in cbo_instrs:
            if cbo == "zero":
                lines.append("#ifdef ZICBOZ_SUPPORTED")
            else:
                lines.append("#ifdef ZICBOM_SUPPORTED")
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"addi x{addr_reg}, x{addr_reg}, 1",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")
            else:
                lines.append("\tRVTEST_GOTO_MMODE\n")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"cbo.{cbo}_mode{mode}_misaligned", coverpoint, covergroup),
                    f"cbo.{cbo}    0(x{addr_reg})",
                    "nop",
                    "#endif",
                ]
            )
        for prefetch in prefetch_instrs:
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"addi x{addr_reg}, x{addr_reg}, 1",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                    f"csrw  menvcfg, x{menvcfg_reg}",
                ]
            )

            if mode == "0":
                lines.append("\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")
            else:
                lines.append("\tRVTEST_GOTO_MMODE\n")
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"prefetch.{prefetch}_mode{mode}_misaligned", coverpoint, covergroup),
                    f"prefetch.{prefetch}    0(x{addr_reg})",
                    "nop",
                ]
            )
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsZicboU",
    required_extensions=["Zicsr", "Sm", "U"],
    march_extensions=["Zicsr", "Zicbom", "Zicboz", "Zicbop"],
)
def make_exceptionszicbou(test_data: TestData) -> list[str]:
    """Generate tests for ExceptionsZicboU coverpoints"""
    lines = []

    lines.extend(["#ifdef S_SUPPORTED", "    LI(x11, -1)", "    csrw senvcfg, x11", "#endif"])
    lines.extend(_generate_cbie_tests(test_data))
    lines.extend(_generate_cbcfe_tests(test_data))
    lines.extend(_generate_cbze_tests(test_data))
    lines.extend(_generate_cbo_access_fault_tests(test_data))
    lines.extend(_generate_cbo_misaligned_tests(test_data))

    return lines
