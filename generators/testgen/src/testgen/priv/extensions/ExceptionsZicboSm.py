##################################
# ExceptionsZicboSm.py
#
# ExceptionsZicboSm privileged extension test generator.
# aman.murad@10xengineers.ai August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator (machine-mode only)."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_cbie_tests(test_data: TestData) -> list[str]:
    """Generate cbie tests in machine mode."""
    covergroup, coverpoint = "ExceptionsZicboSm_cg", "cp_cbie"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "Execute cbo.inval in machine mode with menvcfg.cbie = {00/01/11}",
        ),
        "",
        "#ifdef ZICBOM_SUPPORTED",
    ]
    bins = ["00", "01", "11"]
    for b in bins:
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"LI(x{menvcfg_reg}, {int(b, 2) << 4})",
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                test_data.add_testcase(f"cbo.inval_menvcfg.cbie{b}", coverpoint, covergroup),
                f"cbo.inval    (x{addr_reg})",
            ]
        )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbcfe_tests(test_data: TestData) -> list[str]:
    """Generate cbcfe tests in machine mode."""
    covergroup, coverpoint = "ExceptionsZicboSm_cg", "cp_cbcfe"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "Execute cbo.{clean, flush} in machine mode with menvcfg.cbcfe = {0/1}",
        ),
        "",
        "#ifdef ZICBOM_SUPPORTED",
    ]
    bins = ["0", "1"]
    for b in bins:
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"LI(x{menvcfg_reg}, {int(b, 2) << 6})",
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                test_data.add_testcase(f"cbo.clean_menvcfg.cbcfe{b}", coverpoint, covergroup),
                f"cbo.clean    (x{addr_reg})",
                test_data.add_testcase(f"cbo.flush_menvcfg.cbcfe{b}", coverpoint, covergroup),
                f"cbo.flush    (x{addr_reg})",
            ]
        )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbze_tests(test_data: TestData) -> list[str]:
    """Generate cbze tests in machine mode."""
    covergroup, coverpoint = "ExceptionsZicboSm_cg", "cp_cbze"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "Execute cbo.zero in machine mode with menvcfg.cbze = {0/1}",
        ),
        "",
        "#ifdef ZICBOZ_SUPPORTED",
    ]
    bins = ["0", "1"]
    for b in bins:
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"LI(x{menvcfg_reg}, {int(b, 2) << 7})",
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                test_data.add_testcase(f"cbo.zero_menvcfg.cbze{b}", coverpoint, covergroup),
                f"cbo.zero    (x{addr_reg})",
            ]
        )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbo_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate cbo access fault trap tests in machine mode."""
    covergroup, coverpoint = "ExceptionsZicboSm_cg", "cp_cbo_access_fault"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2)

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(
            coverpoint,
            "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} Execute op to ACCESS_FAULT_ADDR in machine mode with menvcfg enabled",
        ),
        "",
    ]
    cbo_instrs = ["inval", "clean", "flush", "zero"]
    prefetch_instrs = ["i", "r", "w"]
    for cbo in cbo_instrs:
        if cbo == "zero":
            lines.append("#ifdef ZICBOZ_SUPPORTED")
        else:
            lines.append("#ifdef ZICBOM_SUPPORTED")
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                test_data.add_testcase(f"cbo.{cbo}_access_fault_0", coverpoint, covergroup),
                f"cbo.{cbo}    0(x{addr_reg})",
                f"addi x{addr_reg}, x{addr_reg}, 1  # attempt access again with misalignment, check misaligned address is reported in mtval if applicable",
                test_data.add_testcase(f"cbo.{cbo}_access_fault_1", coverpoint, covergroup),
                f"cbo.{cbo}    0(x{addr_reg})",
                "#endif",
            ]
        )
    for prefetch in prefetch_instrs:
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                "# No need to gate prefetch instructions with ZICBOP_SUPPORTED because they are hints that fall back to defined behavior",
                test_data.add_testcase(f"prefetch.{prefetch}_access_fault_0", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
                f"addi x{addr_reg}, x{addr_reg}, 1  # attempt access again with misalignment",
                test_data.add_testcase(f"prefetch.{prefetch}_access_fault_1", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
            ]
        )
    lines.append("#endif")
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


def _generate_cbo_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate cbo misaligned trap tests in machine mode."""
    covergroup, coverpoint = "ExceptionsZicboSm_cg", "cp_cbo_misaligned"

    addr_reg, menvcfg_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} Execute op to valid address + 1 in machine mode with menvcfg enabled",
        ),
        "",
    ]
    cbo_instrs = ["inval", "clean", "flush", "zero"]
    prefetch_instrs = ["i", "r", "w"]
    for cbo in cbo_instrs:
        if cbo == "zero":
            lines.append("#ifdef ZICBOZ_SUPPORTED")
        else:
            lines.append("#ifdef ZICBOM_SUPPORTED")
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, 1",
                f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                test_data.add_testcase(f"cbo.{cbo}_misaligned", coverpoint, covergroup),
                f"cbo.{cbo}    0(x{addr_reg})",
                "#endif",
            ]
        )
    for prefetch in prefetch_instrs:
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, 1",
                f"LI(x{menvcfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                f"csrw  menvcfg, x{menvcfg_reg}",
                "nop",
                "# No need to gate prefetch instructions with ZICBOP_SUPPORTED because they are hints that fall back to defined behavior",
                test_data.add_testcase(f"prefetch.{prefetch}_misaligned", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
            ]
        )
    test_data.int_regs.return_registers([addr_reg, menvcfg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsZicboSm",
    required_extensions=["Sm"],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
)
def make_exceptionszicbosm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboSm coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_cbie_tests(test_data))
    tc.code.extend(_generate_cbcfe_tests(test_data))
    tc.code.extend(_generate_cbze_tests(test_data))
    tc.code.extend(_generate_cbo_access_fault_tests(test_data))
    tc.code.extend(_generate_cbo_misaligned_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
