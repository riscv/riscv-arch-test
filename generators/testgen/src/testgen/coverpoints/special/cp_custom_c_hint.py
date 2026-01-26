##################################
# cp_custom_c_hint.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_c_hint coverpoint generator."""

from testgen.asm.helpers import to_hex, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData


@add_coverpoint_generator("cp_custom_chint")
def make_custom_c_hint(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for c.hint coverpoints."""
    return [
        "# TODO: The cp_custom_chint tests need more work to figure out how to detect the appropriate instruction.  Jordan recommends merging them into the relevant compressed instructions as a custom coverpoint, so they are decoded.  The decoder will have to stop excluding the hints.  ZihintntlZca should have some named instructions, as with Zihintntl."
    ]
    if instr_name != "c.hint":
        raise ValueError(f"cp_custom_chint generator only supports c.hint instruction, got {instr_name}")

    test_lines: list[str] = []

    # cp_chint_nop
    # c.nop with imm in [-32, 31] (excluding 0 which is true nop)
    for imm in range(-32, 32):
        if imm == 0:
            continue

        test_data.add_testcase_string("cp_chint_nop")

        test_lines.extend(
            [
                f"# Testcase: cp_chint_nop (imm = {imm})",
                f"c.nop {imm}",
                write_sigupd(0, test_data, "int"),  # Check x0 (always 0)
            ]
        )

    # cp_chint_addi
    # c.addi rd, 0 (where rd != 0)
    for rd in range(1, 32):
        test_data.add_testcase_string("cp_chint_addi")
        test_lines.extend(
            [
                test_data.int_regs.consume_registers([rd]),
                f"c.addi x{rd}, 0",
                write_sigupd(rd, test_data, "int"),
            ]
        )
        test_data.int_regs.return_registers([rd])

    # cp_chint_li
    # c.li x0, imm
    # Iterates all 6-bit immediates [-32, 31].
    for imm in range(-32, 32):
        test_data.add_testcase_string("cp_chint_li")

        test_lines.extend(
            [
                f"c.li x0, {imm}",
                write_sigupd(0, test_data, "int"),
            ]
        )

    # cp_chint_lui
    # c.lui x0, imm with imm in [-32, 31], excluding 0.
    for imm in range(-32, 32):
        if imm == 0:
            continue

        test_data.add_testcase_string("cp_chint_lui")

        test_lines.extend(
            [
                f"c.lui x0, {to_hex(imm, 20)}",
                write_sigupd(0, test_data, "int"),
            ]
        )

    # cp_chint_mv
    # c.mv x0, rs2 (where rs2 != 0)
    for rs2 in range(1, 32):
        test_data.add_testcase_string("cp_chint_mv")

        test_lines.extend(
            [
                test_data.int_regs.consume_registers([rs2]),
                f"c.mv x0, x{rs2}",
                write_sigupd(rs2, test_data, "int"),
            ]
        )
        test_data.int_regs.return_registers([rs2])

    # cp_chint_add
    # c.add x0, rs2
    for rs2 in range(1, 32):
        test_data.add_testcase_string("cp_chint_add")

        test_lines.extend(
            [
                test_data.int_regs.consume_registers([rs2]),
                f"c.add x0, x{rs2}",
                write_sigupd(0, test_data, "int"),
            ]
        )
        test_data.int_regs.return_registers([rs2])

    return test_lines
