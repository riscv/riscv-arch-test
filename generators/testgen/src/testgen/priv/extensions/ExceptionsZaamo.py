##################################
# priv/extensions/ExceptionsZaamo.py
#
# ExceptionsZaamo extension exception test generator.
# huahuang@hmc.edu Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zaamo extension exception test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_amo_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZaamo_cg", "cp_amo_address_misaligned"
    addr_reg, limit_reg, dest_reg, source_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

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
                f"# Offset {offset} (LSBs: {offset:03b})",
                f"LI(x{limit_reg}, {offset})",
                f"LA(x{addr_reg}, scratch)",
                "",
                f"LI(x{source_reg}, 0xDEADBEEF)",
                "",
                f"sw x{source_reg}, 0(x{addr_reg})",
                f"sw x{source_reg}, 4(x{addr_reg})",
                f"sw x{source_reg}, 8(x{addr_reg})",
                f"sw x{source_reg}, 12(x{addr_reg})",
                "",
                f"# Update scratch address to be misaligned with offset {offset}",
                f"add x{addr_reg}, x{limit_reg}, x{addr_reg}",
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
                    "nop",
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
                    "nop",
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
                    "nop",
                    write_sigupd(dest_reg, test_data),
                ]
            )
        for op in ops:
            lines.extend(
                [
                    f"LI(x{dest_reg}, 0xBAD)",
                    test_data.add_testcase(f"{op[:-1]}_b_offset_{offset}", coverpoint, covergroup),
                    f"{op}b x{dest_reg}, x{source_reg}, (x{addr_reg})",
                    "nop",
                    write_sigupd(dest_reg, test_data),
                ]
            )
        lines.append("#endif")

    test_data.int_regs.return_registers([addr_reg, limit_reg, dest_reg, source_reg])

    return lines


def _generate_amo_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZaamo_cg", "cp_amo_access_fault"
    addr_reg, dest_reg, source_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
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
                "nop",
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
                "nop",
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
                "nop",
                write_sigupd(dest_reg, test_data),
            ]
        )
    for op in ops:
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amo_access_fault_{op[:-1]}_b", coverpoint, covergroup),
                f"{op}b x{dest_reg}, x{source_reg}, (x{addr_reg})",
                "nop",
                write_sigupd(dest_reg, test_data),
            ]
        )
    lines.append("#endif")

    test_data.int_regs.return_registers([addr_reg, dest_reg, source_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsZaamo",
    required_extensions=["I", "Zicsr", "Zaamo", "Sm"],
    march_extensions=["I", "Zicsr", "A", "Zaamo", "Zabha"],
)
def make_exceptionszaamo(test_data: TestData) -> list[str]:
    """Main entry point for Zaamo exception test generation."""
    lines = []

    lines.extend(_generate_amo_address_misaligned_tests(test_data))
    lines.extend(_generate_amo_access_fault_tests(test_data))
    return lines
