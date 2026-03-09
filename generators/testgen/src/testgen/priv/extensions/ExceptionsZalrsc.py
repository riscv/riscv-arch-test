##################################
# ExceptionsZalrsc.py
#
# ExceptionsZalrsc privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zalrsc extension exception test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate load address misaligned exception tests."""
    covergroup, coverpoint = "ExceptionsZalrsc_cg", "cp_load_address_misaligned"

    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint)]

    for offset in range(8):
        lines.extend(
            [
                f"\n# Offset {offset} (LSBs: {offset:03b})",
                f"    LA(x{addr_reg}, scratch)",
                f"    addi x{addr_reg}, x{addr_reg}, {offset}",
                f"    LI(x{check_reg}, 0xBAD)",
                test_data.add_testcase(f"lr.w_off{offset}", coverpoint, covergroup),
                f"    lr.w x{check_reg}, (x{addr_reg})",
                "    nop",
                write_sigupd(check_reg, test_data),
                "#if __riscv_xlen == 64",
                f"    LI(x{check_reg}, 0xBAD)",
                test_data.add_testcase(f"lr.d_off{offset}", coverpoint, covergroup),
                f"    lr.d x{check_reg}, (x{addr_reg})",
                "    nop",
                write_sigupd(check_reg, test_data),
                "#endif",
                "",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate store address misaligned exception tests."""
    covergroup, coverpoint = "ExceptionsZalrsc_cg", "cp_store_address_misaligned"
    addr_reg, data_reg, rd_reg, temp_reg, base_reg, check_reg = test_data.int_regs.get_registers(6, exclude_regs=[0])

    lines = [comment_banner(coverpoint)]
    # illegal sc.w does not get coverage as SAIL stores content in by bytes instead of giving exceptions
    # Sail issue: https://github.com/riscv/sail-riscv/issues/1574

    for offset in range(8):
        lines.extend(
            [
                f"\n# Offset {offset} (LSBs: {offset:03b})",
                f"    LA(x{base_reg}, scratch)",
                f"    addi x{addr_reg}, x{base_reg}, {offset}",  # addr = aligned base + offset
                f"    LI(x{data_reg}, 0xDECAFCAB)",
                f"    LI(x{temp_reg}, 0xBAD)",
                test_data.add_testcase(f"lr.w_off{offset}", coverpoint, covergroup),
                f"    lr.w x{temp_reg}, (x{addr_reg})",  # establish reservation
                "    nop",
                write_sigupd(temp_reg, test_data),
                f"    LI(x{rd_reg}, 0xBAD)",  # previous rd greater than 1
                test_data.add_testcase(f"sc.w_off{offset}", coverpoint, covergroup),
                f"    sc.w x{rd_reg}, x{data_reg}, (x{addr_reg})",
                "    nop",
                write_sigupd(rd_reg, test_data),
                f"    lw x{check_reg}, 0(x{base_reg})",
                write_sigupd(check_reg, test_data),
                f"    lw x{check_reg}, 4(x{base_reg})",
                write_sigupd(check_reg, test_data),
                f"    lw x{check_reg}, 8(x{base_reg})",
                write_sigupd(check_reg, test_data),
                f"    lw x{check_reg}, 12(x{base_reg})",
                write_sigupd(check_reg, test_data),
                "#if __riscv_xlen == 64",
                f"    LI(x{temp_reg}, 0xBAD)",
                test_data.add_testcase(f"lr.d_off{offset}", coverpoint, covergroup),
                f"    lr.d x{temp_reg}, (x{addr_reg})",  # establish reservation
                "    nop",
                write_sigupd(temp_reg, test_data),
                f"    LI(x{rd_reg}, 0xBAD)",  # previous rd greater than 1
                test_data.add_testcase(f"sc.d_off{offset}", coverpoint, covergroup),
                f"    sc.d x{rd_reg}, x{data_reg}, (x{addr_reg})",
                "    nop",
                write_sigupd(rd_reg, test_data),
                f"    lw x{check_reg}, 0(x{base_reg})",
                write_sigupd(check_reg, test_data),
                f"    lw x{check_reg}, 4(x{base_reg})",
                write_sigupd(check_reg, test_data),
                f"    lw x{check_reg}, 8(x{base_reg})",
                write_sigupd(check_reg, test_data),
                f"    lw x{check_reg}, 12(x{base_reg})",
                write_sigupd(check_reg, test_data),
                "#endif",
                "",
            ]
        )
    test_data.int_regs.return_registers([addr_reg, data_reg, rd_reg, base_reg, temp_reg, check_reg])
    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate load access fault exception tests."""
    covergroup, coverpoint = "ExceptionsZalrsc_cg", "cp_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint),
        f"    LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        f"    LI(x{check_reg}, 0xBAD)",
        test_data.add_testcase("lr.w_load_access_fault", coverpoint, covergroup),
        f"    lr.w x{check_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(check_reg, test_data),
        "#if __riscv_xlen == 64",
        f"    LI(x{check_reg}, 0xBAD)",
        test_data.add_testcase("lr.d_load_access_fault", coverpoint, covergroup),
        f"    lr.d x{check_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(check_reg, test_data),
        "#endif",
        "",
    ]

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def _generate_load_misaligned_priority_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned and access fault exception tests."""
    covergroup, coverpoint = "ExceptionsZalrsc_cg", "cp_load_misaligned_priority"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint),
        f"    LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        f"    addi x{addr_reg}, x{addr_reg}, 1",
        f"    LI(x{check_reg}, 0xBAD)",
        test_data.add_testcase("lr.w_off1_priority", coverpoint, covergroup),
        f"    lr.w x{check_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(check_reg, test_data),
        "#if __riscv_xlen == 64",
        f"    LI(x{check_reg}, 0xBAD)",
        test_data.add_testcase("lr.d_off1_priority", coverpoint, covergroup),
        f"    lr.d x{check_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(check_reg, test_data),
        "#endif",
        "",
    ]

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def _generate_store_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate store access fault exception tests."""
    covergroup, coverpoint = "ExceptionsZalrsc_cg", "cp_store_access_fault"
    addr_reg, data_reg, rd_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])
    # sc.w at illegal address does not trigger exception in QEMU
    # QEMU issue: https://gitlab.com/qemu-project/qemu/-/issues/3323
    lines = [
        comment_banner(coverpoint),
        f"    LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        f"    LI(x{data_reg}, 0xADDEDCAB)",
        f"    LI(x{rd_reg}, 0xBAD)",
        test_data.add_testcase("lr.w_store_fault", coverpoint, covergroup),
        f"    lr.w x{rd_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(rd_reg, test_data),
        f"    LI(x{rd_reg}, 0xBAD)",  # previous rd greater than 1
        test_data.add_testcase("sc.w_fault", coverpoint, covergroup),
        f"    sc.w x{rd_reg}, x{data_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(rd_reg, test_data),
        "#if __riscv_xlen == 64",
        f"    LI(x{data_reg}, 0xDEADBEEFDECAFCAB)",
        f"    LI(x{rd_reg}, 0xBAD)",
        test_data.add_testcase("lr.d_store_fault", coverpoint, covergroup),
        f"    lr.d x{rd_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(rd_reg, test_data),
        f"    LI(x{rd_reg}, 0xBAD)",  # previous rd greater than 1
        test_data.add_testcase("sc.d_fault", coverpoint, covergroup),
        f"    sc.d x{rd_reg}, x{data_reg}, (x{addr_reg})",
        "    nop",
        write_sigupd(rd_reg, test_data),
        "#endif",
        "",
    ]

    test_data.int_regs.return_registers([addr_reg, data_reg, rd_reg])
    return lines


def _generate_store_misaligned_priority_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned and access fault exception tests."""
    covergroup, coverpoint = "ExceptionsZalrsc_cg", "cp_store_misaligned_priority"
    addr_reg, data_reg, rd_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [comment_banner(coverpoint)]

    lines.extend(
        [
            f"    LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"    addi x{addr_reg}, x{addr_reg}, 1",
            f"    LI(x{data_reg}, 0xDECAFCAB)",  # Match original value
            f"    LI(x{rd_reg}, 0xDECAFCAB)",
            test_data.add_testcase("lr.w_off1_priority", coverpoint, covergroup),
            f"    lr.w x{rd_reg}, (x{addr_reg})",
            "    nop",
            write_sigupd(rd_reg, test_data),
            f"    LI(x{rd_reg}, 0xBAD)",  # previous rd greater than 1
            test_data.add_testcase("sc.w_off1_priority", coverpoint, covergroup),
            f"    sc.w x{rd_reg}, x{data_reg}, (x{addr_reg})",
            "    nop",
            write_sigupd(rd_reg, test_data),
            "#if __riscv_xlen == 64",
            f"    LI(x{data_reg}, 0xDEADBEEFDECAFCAB)",  # Match original value
            f"    LI(x{rd_reg}, 0xDECAFCAB)",
            test_data.add_testcase("lr.d_off1_priority", coverpoint, covergroup),
            f"    lr.d x{rd_reg}, (x{addr_reg})",
            "    nop",
            write_sigupd(rd_reg, test_data),
            f"    LI(x{rd_reg}, 0xBAD)",  # previous rd greater than 1
            test_data.add_testcase("sc.d_off1_priority", coverpoint, covergroup),
            f"    sc.d x{rd_reg}, x{data_reg}, (x{addr_reg})",
            "    nop",
            write_sigupd(rd_reg, test_data),
            "#endif",
            "",
        ]
    )
    test_data.int_regs.return_registers([addr_reg, data_reg, rd_reg])
    return lines


@add_priv_test_generator("ExceptionsZalrsc", required_extensions=["Zicsr", "Zalrsc", "Sm"])
def make_exceptionszalrsc(test_data: TestData) -> list[str]:
    """Generate tests for ExceptionsZalrsc coverpoints"""
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

    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_load_misaligned_priority_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    lines.extend(_generate_store_misaligned_priority_tests(test_data))

    return lines
