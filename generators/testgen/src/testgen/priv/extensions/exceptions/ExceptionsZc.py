##################################
# priv/extensions/exceptions/ExceptionsZc.py
#
# ExceptionsZc extension exception test generator.
# jgong@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Compressed exceptions test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _add_load_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, base_reg, check_reg = test_data.int_regs.get_registers(
        3, reg_range=list(range(8, 16))
    )  # registers x8-x15 used for compressed instructions

    fp_reg = test_data.float_regs.get_register(reg_range=list(range(8, 16)))  # exclude registers outside of f8-f15
    is_float = op.startswith("c.f")
    is_sp = op.endswith("sp")
    t_lines = []

    # Load address and apply offset
    if is_sp:
        t_lines.append(f"mv x{base_reg}, sp")  # Save sp
        t_lines.append("LA(sp, scratch)")
        t_lines.append(f"addi sp, sp, {offset}")
    else:
        t_lines.append(f"LA(x{addr_reg}, scratch)")
        t_lines.append(f"addi x{addr_reg}, x{addr_reg}, {offset}")

    # Perform load
    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"
    sig_reg = fp_reg if is_float else check_reg

    if is_sp:
        t_lines.append(test_data.add_testcase(f"{op.lower()}_off{offset}", coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(sp)")
        t_lines.append(f"mv sp, x{base_reg}")  # Restore sp immediately
    else:
        t_lines.append(test_data.add_testcase(f"{op.lower()}_off{offset}", coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(x{addr_reg})")

    t_lines.append(write_sigupd(sig_reg, test_data, sig_type="float" if is_float else "int"))

    test_data.int_regs.return_registers([addr_reg, base_reg, check_reg])
    test_data.float_regs.return_registers([fp_reg])
    return t_lines


def _add_store_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, base_reg, check_reg = test_data.int_regs.get_registers(3, reg_range=list(range(8, 16)))
    fp_reg = test_data.float_regs.get_register(reg_range=list(range(8, 16)))

    is_float = op.startswith("c.f")
    is_sp = op.endswith("sp")
    t_lines = []

    # Initialize scratch before each store so a missing store changes the signature.
    t_lines.extend(
        (
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{base_reg}, {0x0C0DE000 | offset:#x})",
            f"sw x{base_reg}, 0(x{addr_reg})",
            f"sw x{base_reg}, 4(x{addr_reg})",
            f"sw x{base_reg}, 8(x{addr_reg})",
            f"sw x{base_reg}, 12(x{addr_reg})",
        )
    )

    # Load the floating-point value from outside the bytes checked below.
    if is_float:
        t_lines.append(f"LA(x{addr_reg}, scratch)")
        t_lines.append(f"addi x{addr_reg}, x{addr_reg}, 32")
        if "fld" in op or "fsd" in op:
            t_lines.append(f"fld f{fp_reg}, 0(x{addr_reg})")
        else:
            t_lines.append(f"flw f{fp_reg}, 0(x{addr_reg})")
    else:
        t_lines.append(f"LI(x{check_reg}, 0xDEADBEEF)")

    # Load address and apply offset
    if is_sp:
        t_lines.append(f"mv x{base_reg}, sp")  # Save sp
        t_lines.append("LA(sp, scratch)")
        t_lines.append(f"addi sp, sp, {offset}")
    else:
        t_lines.append(f"LA(x{addr_reg}, scratch)")
        t_lines.append(f"addi x{addr_reg}, x{addr_reg}, {offset}")

    # Perform store
    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"

    if is_sp:
        t_lines.append(test_data.add_testcase(f"{op.lower()}_off{offset}", coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(sp)")
        t_lines.append(f"mv sp, x{base_reg}")  # Restore sp immediately
    else:
        t_lines.append(test_data.add_testcase(f"{op.lower()}_off{offset}", coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(x{addr_reg})")

    # Read scratch back as the signature to verify the store result
    t_lines.append(f"LA(x{addr_reg}, scratch)")
    t_lines.append(f"lw x{check_reg}, 0(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))
    t_lines.append(f"lw x{check_reg}, 4(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))
    t_lines.append(f"lw x{check_reg}, 8(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))
    t_lines.append(f"lw x{check_reg}, 12(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))

    test_data.int_regs.return_registers([addr_reg, base_reg, check_reg])
    test_data.float_regs.return_registers([fp_reg])

    return t_lines


def _add_load_fault(
    op: str,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, base_reg, check_reg = test_data.int_regs.get_registers(3, reg_range=list(range(8, 16)))
    fp_reg = test_data.float_regs.get_register(reg_range=list(range(8, 16)))

    is_sp = op.endswith("sp")
    is_float = op.startswith("c.f")
    t_lines = []
    test_label = f"{op.lower()}_fault"

    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"

    if is_sp:
        t_lines.append(f"mv x{base_reg}, sp")
        t_lines.append("LI(sp, RVMODEL_ACCESS_FAULT_ADDRESS)")
        t_lines.append(test_data.add_testcase(test_label, coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(sp)")
        t_lines.append(
            f"{INDENT}#Faulting compressed instruction can land on or 2 bytes past a 4 byte boundary (Resume address is 8 or 6 bytes after instr addr); Three c.nops provide 6 bytes buffer"
        )
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append(f"mv sp, x{base_reg}")
    else:
        t_lines.append(f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        t_lines.append(test_data.add_testcase(test_label, coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(x{addr_reg})")
        t_lines.append(
            f"{INDENT}#Faulting compressed instruction can land on or 2 bytes past a 4 byte boundary (Resume address is 8 or 6 bytes after instr addr); Three c.nops provide 6 bytes buffer"
        )
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append("c.nop")

    test_data.int_regs.return_registers([addr_reg, base_reg, check_reg])
    test_data.float_regs.return_registers([fp_reg])

    return t_lines


def _add_store_fault(
    op: str,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, base_reg, check_reg = test_data.int_regs.get_registers(3, reg_range=list(range(8, 16)))
    fp_reg = test_data.float_regs.get_register(reg_range=list(range(8, 16)))

    is_sp = op.endswith("sp")
    is_float = op.startswith("c.f")
    t_lines = []
    test_label = f"{op.lower()}_fault"

    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"

    if is_sp:
        t_lines.append(f"mv x{base_reg}, sp")
        t_lines.append("LI(sp, RVMODEL_ACCESS_FAULT_ADDRESS)")
        t_lines.append(test_data.add_testcase(test_label, coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(sp)")
        t_lines.append(
            f"{INDENT}#Faulting compressed instruction can land on or 2 bytes past a 4 byte boundary (Resume address is 8 or 6 bytes after instr addr); Three c.nops provide 6 bytes buffer"
        )
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append(f"mv sp, x{base_reg}")
    else:
        t_lines.append(f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        t_lines.append(test_data.add_testcase(test_label, coverpoint, covergroup))
        t_lines.append(f"{op} {reg_str}, 0(x{addr_reg})")
        t_lines.append(
            f"{INDENT}#Faulting compressed instruction can land on or 2 bytes past a 4 byte boundary (Resume address is 8 or 6 bytes after instr addr); Three c.nops provide 6 bytes buffer"
        )
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append("c.nop")

    test_data.int_regs.return_registers([addr_reg, base_reg, check_reg])
    test_data.float_regs.return_registers([fp_reg])

    return t_lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zc_cg", "cp_load_address_misaligned"

    lines = [comment_banner(coverpoint, "Compressed Misaligned Loads")]

    for offset in range(8):
        # Zca
        for instr in ["c.lw", "c.lwsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))

        lines.append("\n#if __riscv_xlen == 64")
        for instr in ["c.ld", "c.ldsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

        # Zcb
        lines.append("\n#ifdef ZCB_SUPPORTED")
        for instr in ["c.lh", "c.lhu", "c.lbu"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

        # Zcf
        lines.append("\n#ifdef ZCF_SUPPORTED")
        for instr in ["c.flw", "c.flwsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

        # Zcd
        lines.append("\n#ifdef ZCD_SUPPORTED")
        for instr in ["c.fld", "c.fldsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zc_cg", "cp_store_address_misaligned"

    lines = [comment_banner(coverpoint, "Compressed Misaligned Stores")]

    for offset in range(8):
        # Zca
        for instr in ["c.sw", "c.swsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))

        lines.append("\n#if __riscv_xlen == 64")
        for instr in ["c.sd", "c.sdsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

        # Zcb
        lines.append("\n#ifdef ZCB_SUPPORTED")
        for instr in ["c.sb", "c.sh"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

        # Zcf
        lines.append("\n#ifdef ZCF_SUPPORTED")
        for instr in ["c.fsw", "c.fswsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

        # Zcd
        lines.append("\n#ifdef ZCD_SUPPORTED")
        for instr in ["c.fsd", "c.fsdsp"]:
            lines.append(f"\n# Testcase: misaligned {instr} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zc_cg", "cp_load_access_fault"

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(
            coverpoint,
            "Test every type of compressed load to a faulting address and check that each one throws a load access fault.",
        ),
    ]

    # Zca
    for instr in ["c.lw", "c.lwsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))

    lines.append("\n#if __riscv_xlen == 64")
    for instr in ["c.ld", "c.ldsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    # Zcb
    lines.append("\n#ifdef ZCB_SUPPORTED")
    for instr in ["c.lh", "c.lhu", "c.lbu"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    # Zcf
    lines.append("\n#ifdef ZCF_SUPPORTED")
    for instr in ["c.flw", "c.flwsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    # Zcd
    lines.append("\n#ifdef ZCD_SUPPORTED")
    for instr in ["c.fld", "c.fldsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    lines.append("#endif")
    return lines


def _generate_store_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zc_cg", "cp_store_access_fault"

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(
            coverpoint,
            "Test every type of compressed store to a faulting address and check that each one throws a store access fault.",
        ),
    ]

    # Zca
    for instr in ["c.sw", "c.swsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))

    lines.append("\n#if __riscv_xlen == 64")
    for instr in ["c.sd", "c.sdsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    # Zcb
    lines.append("\n#ifdef ZCB_SUPPORTED")
    for instr in ["c.sb", "c.sh"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    # Zcf
    lines.append("\n#ifdef ZCF_SUPPORTED")
    for instr in ["c.fsw", "c.fswsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    # Zcd
    lines.append("\n#ifdef ZCD_SUPPORTED")
    for instr in ["c.fsd", "c.fsdsp"]:
        lines.append(f"\n# Testcase: {instr} with faulting address")
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("\n#endif")

    lines.append("#endif")
    return lines


def _generate_breakpoint_tests(test_data: TestData) -> list[str]:
    """Generate breakpoint exception test."""
    covergroup, coverpoint = "Exceptions_Zc_cg", "cp_breakpoint"

    lines = [comment_banner(coverpoint, "Breakpoint")]
    for pc_bit_1 in (0, 1):
        lines.append(f"\n# Testcase: c.ebreak at pc[1] = {pc_bit_1}")
        lines.append(".p2align 2")
        if pc_bit_1:
            lines.append("c.nop")
        lines.append(test_data.add_testcase(f"c_ebreak_pc_bit_1_{pc_bit_1}", coverpoint, covergroup))
        lines.append("c.ebreak")

    return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    """Generate illegal compressed instructions."""
    covergroup, coverpoint = "Exceptions_Zc_cg", "cp_illegal_instruction"

    check_reg = test_data.int_regs.get_register()
    lines = [comment_banner(coverpoint, "Illegal Instruction")]
    for pc_bit_1 in (0, 1):
        lines.append(f"\n# Testcase: c.illegal (0x0000) at pc[1] = {pc_bit_1}")
        lines.append(f"LI(x{check_reg}, 0xBAD)")
        lines.append(".p2align 2")
        if pc_bit_1:
            lines.append("c.nop")
        lines.append(test_data.add_testcase(f"illegal0_pc_bit_1_{pc_bit_1}", coverpoint, covergroup))
        lines.append(".insn 0x00")
        # Legal nonzero halfword after the illegal instruction. If mtval reports 32 bits,
        # this encoding shows in mtval[31:16]. The handler resumes here at mepc+2.
        lines.append(f"c.li x{check_reg}, 1")
        lines.append(write_sigupd(check_reg, test_data))
    test_data.int_regs.return_registers([check_reg])

    return lines


@add_priv_test_generator(
    "Exceptions",
    required_extensions=[["Sm", "U"], "Zca"],
    march_extensions=["Zca", "Zcb", "Zcd", "C", "F", "D"],
)
def make_exceptionszc(test_data: TestData) -> list[TestChunk]:
    """Main entry point for Zc exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Zc")

    tc.code.extend(_generate_load_address_misaligned_tests(test_data))
    tc.code.extend(_generate_store_address_misaligned_tests(test_data))
    tc.code.extend(_generate_load_access_fault_tests(test_data))
    tc.code.extend(_generate_store_access_fault_tests(test_data))
    tc.code.extend(_generate_breakpoint_tests(test_data))
    tc.code.extend(_generate_illegal_instruction_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
