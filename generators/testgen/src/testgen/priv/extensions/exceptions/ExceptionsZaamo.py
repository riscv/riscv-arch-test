##################################
# priv/extensions/exceptions/ExceptionsZaamo.py
#
# ExceptionsZaamo extension exception test generator.
# huahuang@hmc.edu Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zaamo extension exception test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# Bytes reached by the misaligned tests: amocas.q at offset 31 touches bytes 31-46
WINDOW_BYTES = 48


def _window_word(offset: int, word: int) -> int:
    """Return a fill word with distinct bytes in the window and a distinct pattern per offset."""
    return sum(((5 * (4 * word + i) + 7 * offset + 0x11) & 0xFF) << (8 * i) for i in range(4))


def _fill_window(base_reg: int, data_reg: int, offset: int) -> list[str]:
    lines = []
    for word in range(WINDOW_BYTES // 4):
        lines.extend(
            [f"LI(x{data_reg}, {_window_word(offset, word):#010x})", f"sw x{data_reg}, {4 * word}(x{base_reg})"]
        )
    return lines


def _check_window(base_reg: int, check_reg: int, test_data: TestData) -> list[str]:
    """Read back the window with XLEN-wide loads and record each value in the signature."""
    lines = []
    for word in range(WINDOW_BYTES // 4):
        check = [f"LREG x{check_reg}, {4 * word}(x{base_reg})", write_sigupd(check_reg, test_data)]
        lines.extend(check if word % 2 == 0 else ["#if __riscv_xlen == 32", *check, "#endif"])
    return lines


def _generate_amo_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zaamo_cg", "cp_amo_address_misaligned"

    # Reserve dest/source as AMOCAS-capable register pairs for use later
    dest_reg = test_data.int_regs.get_register_pair()
    source_reg = test_data.int_regs.get_register_pair()
    addr_reg, base_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "Test amo instructions on misaligned addresses to check for traps\n"
            "Testing all offsets upto MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE+1",
        ),
    ]

    ops = ["amoswap.", "amoadd.", "amoxor.", "amoand.", "amoor.", "amomin.", "amomax.", "amominu.", "amomaxu."]
    for offset in range(32):
        lines.extend(
            [
                "",
                f"# Offset {offset} (LSBs: {offset:05b})",
                f"LA(x{base_reg}, scratch)",
                *_fill_window(base_reg, source_reg, offset),
                "",
                f"# Update scratch address to be misaligned with offset {offset}",
                f"addi x{addr_reg}, x{base_reg}, {offset}",
                "",
                f"LI(x{source_reg}, 1)",
            ]
        )
        for op in ops:
            lines.extend(
                [
                    f"LI(x{dest_reg}, 0xBAD)",
                    test_data.add_testcase(f"{op[:-1]}_w_offset_{offset}", coverpoint, covergroup),
                    f"{op}w x{dest_reg}, x{source_reg}, (x{addr_reg})",
                    write_sigupd(dest_reg, test_data),
                ]
            )

        lines.append("#if __riscv_xlen == 64")
        for op in ops:
            lines.extend(
                [
                    f"LI(x{dest_reg}, 0xBAD)",
                    test_data.add_testcase(f"{op[:-1]}_d_offset_{offset}", coverpoint, covergroup),
                    f"{op}d x{dest_reg}, x{source_reg}, (x{addr_reg})",
                    write_sigupd(dest_reg, test_data),
                ]
            )
        lines.append("#endif")

        lines.append("#ifdef ZABHA_SUPPORTED")
        for op in ops:
            lines.extend(
                [
                    f"LI(x{dest_reg}, 0xBAD)",
                    test_data.add_testcase(f"{op[:-1]}_h_offset_{offset}", coverpoint, covergroup),
                    f"{op}h x{dest_reg}, x{source_reg}, (x{addr_reg})",
                    write_sigupd(dest_reg, test_data),
                ]
            )
        for op in ops:
            lines.extend(
                [
                    f"LI(x{dest_reg}, 0xBAD)",
                    test_data.add_testcase(f"{op[:-1]}_b_offset_{offset}", coverpoint, covergroup),
                    f"{op}b x{dest_reg}, x{source_reg}, (x{addr_reg})",
                    write_sigupd(dest_reg, test_data),
                ]
            )
        lines.append("#endif")

        lines.append("#ifdef ZACAS_SUPPORTED")
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amocas_w_offset_{offset}", coverpoint, covergroup),
                f"amocas.w x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )

        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amocas_d_offset_{offset}", coverpoint, covergroup),
                f"amocas.d x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )

        lines.append("#if __riscv_xlen == 64")
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amocas_q_offset_{offset}", coverpoint, covergroup),
                f"amocas.q x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )
        lines.append("#endif")
        lines.append("#endif")

        lines.extend(
            [
                f"# Check memory after offset {offset}",
                test_data.add_testcase(f"memory_offset_{offset}", coverpoint, covergroup),
                *_check_window(base_reg, dest_reg, test_data),
            ]
        )

    test_data.int_regs.return_register_pair(dest_reg)
    test_data.int_regs.return_register_pair(source_reg)
    test_data.int_regs.return_registers([addr_reg, base_reg])

    return lines


def _generate_amo_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zaamo_cg", "cp_amo_access_fault"

    # Reserve dest/source as AMOCAS-capable register pairs before choosing the
    # long-lived address register so addr_reg cannot break either even/odd pair.
    dest_reg = test_data.int_regs.get_register_pair()
    source_reg = test_data.int_regs.get_register_pair()
    addr_reg = test_data.int_regs.get_register()

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(coverpoint, "Test amo instructions on restricted memory and check for access fault"),
    ]

    lines.extend(
        [
            f"LI(x{source_reg}, 1)",
            "",
            f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        ]
    )

    ops = ["amoswap.", "amoadd.", "amoxor.", "amoand.", "amoor.", "amomin.", "amomax.", "amominu.", "amomaxu."]
    for op in ops:
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amo_access_fault_{op[:-1]}_w", coverpoint, covergroup),
                f"{op}w x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )
    lines.append("#if __riscv_xlen == 64")
    for op in ops:
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amo_access_fault_{op[:-1]}_d", coverpoint, covergroup),
                f"{op}d x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )
    lines.append("#endif")

    # Zabha
    lines.append("#ifdef ZABHA_SUPPORTED")
    for op in ops:
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amo_access_fault_{op[:-1]}_h", coverpoint, covergroup),
                f"{op}h x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )
    for op in ops:
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amo_access_fault_{op[:-1]}_b", coverpoint, covergroup),
                f"{op}b x{dest_reg}, x{source_reg}, (x{addr_reg})",
                write_sigupd(dest_reg, test_data),
            ]
        )
    lines.append("#endif")

    lines.append("#ifdef ZACAS_SUPPORTED")
    lines.extend(
        [
            f"LI(x{dest_reg}, 0xBAD)",
            test_data.add_testcase("amo_access_fault_amocas_w", coverpoint, covergroup),
            f"amocas.w x{dest_reg}, x{source_reg}, (x{addr_reg})",
            write_sigupd(dest_reg, test_data),
        ]
    )
    lines.extend(
        [
            f"LI(x{dest_reg}, 0xBAD)",
            test_data.add_testcase("amo_access_fault_amocas_d", coverpoint, covergroup),
            f"amocas.d x{dest_reg}, x{source_reg}, (x{addr_reg})",
            write_sigupd(dest_reg, test_data),
        ]
    )
    lines.append("#if __riscv_xlen == 64")
    lines.extend(
        [
            f"LI(x{dest_reg}, 0xBAD)",
            test_data.add_testcase("amo_access_fault_amocas_q", coverpoint, covergroup),
            f"amocas.q x{dest_reg}, x{source_reg}, (x{addr_reg})",
            write_sigupd(dest_reg, test_data),
        ]
    )
    lines.append("#endif")
    lines.append("#endif")

    lines.append("#endif")
    test_data.int_regs.return_register_pair(dest_reg)
    test_data.int_regs.return_register_pair(source_reg)
    test_data.int_regs.return_register(addr_reg)
    return lines


@add_priv_test_generator(
    "Exceptions",
    required_extensions=["Zaamo", ["Sm", "U"]],
    march_extensions=["Zaamo", "Zabha", "Zacas"],
)
def make_exceptionszaamo(test_data: TestData) -> list[TestChunk]:
    """Main entry point for Zaamo exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Zaamo")

    tc.code.extend(_generate_amo_address_misaligned_tests(test_data))
    tc.code.extend(_generate_amo_access_fault_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
