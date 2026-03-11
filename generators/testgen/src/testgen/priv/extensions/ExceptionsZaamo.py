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
    addr_reg, check_reg, limit_reg, reg1, reg2, reg3, reg4, reg5, reg6 = test_data.int_regs.get_registers(
        9, exclude_regs=[0]
    )

    lines = [
        comment_banner(coverpoint),
    ]

    ops = ["amoswap.", "amoadd.", "amoxor.", "amoand.", "amoor.", "amomin.", "amomax.", "amominu.", "amomaxu."]
    regs = [reg1, reg2, reg3, reg4, reg5, reg6]
    for offset in range(32):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")

        lines.extend(
            [
                test_data.add_testcase(f"{offset}", coverpoint, covergroup),
                f"    li      x{limit_reg}, {offset}",
                f"    li      x{check_reg}, 0",
                "",
                f"    la      x{addr_reg}, scratch",
                "",
                f"    li      x{reg1}, 0xDEADBEEF",
                "",
                f"    sw      x{reg1}, 0(x{addr_reg})",
                f"    sw      x{reg1}, 4(x{addr_reg})",
                f"    sw      x{reg1}, 8(x{addr_reg})",
                f"    sw      x{reg1}, 12(x{addr_reg})",
                "",
                "    # Update scratch address to be misaligned based a0 argument",
                f"    add     x{addr_reg}, x{limit_reg}, x{addr_reg}",
                "",
                f"    li      x{reg1}, 1",
            ]
        )
        for i in range(len(ops)):
            op = ops[i]
            dest_reg = regs[i % 6 + 1] if i % 6 != 5 else regs[0]
            source_reg = regs[i % 6]
            lines.append(f"      li x{check_reg}, 0")
            lines.append(f"      {op}w x{dest_reg}, x{source_reg}, (x{addr_reg})")
            lines.append("       nop")
            lines.append(f"      csrr x{check_reg}, mcause")
            lines.append(write_sigupd(check_reg, test_data))
        lines.extend(
            [
                "      #ifdef __riscv_xlen",
                "           #if __riscv_xlen == 64",
            ]
        )
        for i in range(len(ops)):
            op = ops[i]
            dest_reg = regs[i % 6 + 1] if i % 6 != 5 else regs[0]
            source_reg = regs[i % 6]
            lines.append(f"         li x{check_reg}, 0")
            lines.append(f"         {op}d x{dest_reg}, x{source_reg}, (x{addr_reg})")
            lines.append("          nop")
            lines.append(f"         csrr x{check_reg}, mcause")
            lines.append(write_sigupd(check_reg, test_data))
        lines.extend(
            [
                "           #endif",
                "      #endif",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, check_reg, limit_reg, reg1, reg2, reg3, reg4, reg5, reg6])

    return lines


def _generate_amo_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZaamo_cg", "cp_amo_access_fault"
    addr_reg, limit_reg, check_reg, reg1, reg2, reg3, reg4, reg5, reg6 = test_data.int_regs.get_registers(
        9, exclude_regs=[0]
    )

    lines = [
        comment_banner(coverpoint),
    ]

    lines.extend(
        [
            test_data.add_testcase("amo_access_fault", coverpoint, covergroup),
            f"    li  x{limit_reg}, 0",
            f"    li  x{check_reg}, 1",
            f"    la      x{addr_reg}, scratch",
            "",
            f"    li      x{reg1}, 0xDEADBEEF",
            "",
            f"    sw      x{reg1}, 0(x{addr_reg})",
            f"    sw      x{reg1}, 4(x{addr_reg})",
            f"    sw      x{reg1}, 8(x{addr_reg})",
            f"    sw      x{reg1}, 12(x{addr_reg})",
            "",
            "    # Update scratch address to be misaligned based a0 argument",
            f"    add     x{addr_reg}, x{limit_reg}, x{addr_reg}",
            "",
            f"    li      x{reg1}, 1",
            "",
            f"    li      x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
        ]
    )

    ops = ["amoswap.", "amoadd.", "amoxor.", "amoand.", "amoor.", "amomin.", "amomax.", "amominu.", "amomaxu."]
    regs = [reg1, reg2, reg3, reg4, reg5, reg6]
    for i in range(len(ops)):
        op = ops[i]
        dest_reg = regs[i % 6 + 1] if i % 6 != 5 else regs[0]
        source_reg = regs[i % 6]
        lines.append(f"      li      x{dest_reg}, 0")
        lines.append(f"      {op}w x{dest_reg}, x{source_reg}, (x{addr_reg})")
        lines.append("       nop")
        lines.append(write_sigupd(dest_reg, test_data))
    lines.extend(
        [
            "      #ifdef __riscv_xlen",
            "           #if __riscv_xlen == 64",
        ]
    )
    for i in range(len(ops)):
        op = ops[i]
        dest_reg = regs[i % 6 + 1] if i % 6 != 5 else regs[0]
        source_reg = regs[i % 6]
        lines.append(f"         li      x{dest_reg}, 0")
        lines.append(f"         {op}d x{dest_reg}, x{source_reg}, (x{addr_reg})")
        lines.append("          nop")
        lines.append(write_sigupd(dest_reg, test_data))
    lines.extend(
        [
            "           #endif",
            "      #endif",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, check_reg, limit_reg, reg1, reg2, reg3, reg4, reg5, reg6])
    return lines


@add_priv_test_generator(
    "ExceptionsZaamo", required_extensions=["I", "Zicsr", "Zaamo", "Sm"], march_extensions=["I", "Zicsr", "A", "Zaamo"]
)
def make_exceptionszaamo(test_data: TestData) -> list[str]:
    """Main entry point for Zaamo exception test generation."""
    lines = []

    lines.extend(_generate_amo_address_misaligned_tests(test_data))
    lines.extend(_generate_amo_access_fault_tests(test_data))
    return lines
