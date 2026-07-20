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
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_amo_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZaamo_cg", "cp_amo_address_misaligned"

    # Reserve dest/source as AMOCAS-capable register pairs for use later
    dest_reg = test_data.int_regs.get_register_pair()
    source_reg = test_data.int_regs.get_register_pair()
    addr_reg = test_data.int_regs.get_register()

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
                f"addi x{addr_reg}, x{addr_reg}, {offset}",
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

        lines.append("#ifdef ZACAS_SUPPORTED")
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amocas_w_offset_{offset}", coverpoint, covergroup),
                f"amocas.w x{dest_reg}, x{source_reg}, (x{addr_reg})",
                "nop",
                write_sigupd(dest_reg, test_data),
            ]
        )

        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amocas_d_offset_{offset}", coverpoint, covergroup),
                f"amocas.d x{dest_reg}, x{source_reg}, (x{addr_reg})",
                "nop",
                write_sigupd(dest_reg, test_data),
            ]
        )

        lines.append("#if __riscv_xlen == 64")
        lines.extend(
            [
                f"LI(x{dest_reg}, 0xBAD)",
                test_data.add_testcase(f"amocas_q_offset_{offset}", coverpoint, covergroup),
                f"amocas.q x{dest_reg}, x{source_reg}, (x{addr_reg})",
                "nop",
                write_sigupd(dest_reg, test_data),
            ]
        )
        lines.append("#endif")
        lines.append("#endif")

    test_data.int_regs.return_register_pair(dest_reg)
    test_data.int_regs.return_register_pair(source_reg)
    test_data.int_regs.return_register(addr_reg)

    return lines


def _generate_amo_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZaamo_cg", "cp_amo_access_fault"

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

    lines.append("#ifdef ZACAS_SUPPORTED")
    lines.extend(
        [
            f"LI(x{dest_reg}, 0xBAD)",
            test_data.add_testcase("amo_access_fault_amocas_w", coverpoint, covergroup),
            f"amocas.w x{dest_reg}, x{source_reg}, (x{addr_reg})",
            "nop",
            write_sigupd(dest_reg, test_data),
        ]
    )
    lines.extend(
        [
            f"LI(x{dest_reg}, 0xBAD)",
            test_data.add_testcase("amo_access_fault_amocas_d", coverpoint, covergroup),
            f"amocas.d x{dest_reg}, x{source_reg}, (x{addr_reg})",
            "nop",
            write_sigupd(dest_reg, test_data),
        ]
    )
    lines.append("#if __riscv_xlen == 64")
    lines.extend(
        [
            f"LI(x{dest_reg}, 0xBAD)",
            test_data.add_testcase("amo_access_fault_amocas_q", coverpoint, covergroup),
            f"amocas.q x{dest_reg}, x{source_reg}, (x{addr_reg})",
            "nop",
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
    "ExceptionsZaamo",
    required_extensions=["Zaamo", "Sm"],
    march_extensions=["I", "Zicsr", "Zaamo", "Zabha", "Zacas"],
)
def make_exceptionszaamo(test_data: TestData) -> list[TestChunk]:
    """Main entry point for Zaamo exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_amo_address_misaligned_tests(test_data))
    tc.code.extend(_generate_amo_access_fault_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
