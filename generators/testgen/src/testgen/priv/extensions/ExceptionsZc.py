##################################
# priv/extensions/ExceptionsZc.py
#
# ExceptionsZc extension exception test generator.
# jgong@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Compressed exceptions test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
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
    t_lines.append(test_data.add_testcase(coverpoint, f"{op.lower()}_off{offset}", covergroup))

    # Load address and apply offset
    if is_sp:
        t_lines.append(f" mv x{base_reg}, sp")  # Save sp
        t_lines.append(" LA(sp, scratch)")
        t_lines.append(f" addi sp, sp, {offset}")
    else:
        t_lines.append(f" LA(x{addr_reg}, scratch)")
        t_lines.append(f" addi x{addr_reg}, x{addr_reg}, {offset}")

    # Perform load
    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"
    sig_reg = fp_reg if is_float else check_reg

    if is_sp:
        t_lines.append(f" {op} {reg_str}, 0(sp)")
        t_lines.append("# Trap handler skips the next 4 bytes; two c.nops provide 4 bytes")
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append(f" mv sp, x{base_reg}")  # Restore sp immediately
    else:
        t_lines.append(f" {op} {reg_str}, 0(x{addr_reg})")
        t_lines.append(
            "# Load access may throw a trap and the trap handler skips over the next 4 bytes. Two c.nops are used to get 4 bytes of instructions"
        )
        t_lines.append("c.nop")
        t_lines.append("c.nop")

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
    t_lines.append(test_data.add_testcase(coverpoint, f"{op.lower()}_off{offset}", covergroup))

    # Initialize store register to a known value before setting up address
    if is_float:
        t_lines.append(f" LA(x{addr_reg}, scratch)")
        if "fld" in op or "fsd" in op:
            t_lines.append(f" fld f{fp_reg}, 0(x{addr_reg})")
        else:
            t_lines.append(f" flw f{fp_reg}, 0(x{addr_reg})")
    else:
        t_lines.append(f" LI(x{check_reg}, 0xDEADBEEF)")

    # Load address and apply offset
    if is_sp:
        t_lines.append(f" mv x{base_reg}, sp")  # Save sp
        t_lines.append(" LA(sp, scratch)")
        t_lines.append(f" addi sp, sp, {offset}")
    else:
        t_lines.append(f" LA(x{addr_reg}, scratch)")
        t_lines.append(f" addi x{addr_reg}, x{addr_reg}, {offset}")

    # Perform store
    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"

    if is_sp:
        t_lines.append(f" {op} {reg_str}, 0(sp)")
        t_lines.append("# Trap handler skips the next 4 bytes; two c.nops provide 4 bytes")
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append(f" mv sp, x{base_reg}")  # Restore sp immediately
    else:
        t_lines.append(f" {op} {reg_str}, 0(x{addr_reg})")
        t_lines.append("c.nop")
        t_lines.append("c.nop")

    # Read 16 bytes from scratch as signature to verify the store result
    t_lines.append(f" LA(x{addr_reg}, scratch)")
    t_lines.append(f" lw x{check_reg}, 0(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))
    t_lines.append(f" lw x{check_reg}, 4(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))
    t_lines.append(f" lw x{check_reg}, 8(x{addr_reg})")
    t_lines.append(write_sigupd(check_reg, test_data))
    t_lines.append(f" lw x{check_reg}, 12(x{addr_reg})")
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

    t_lines.append(test_data.add_testcase(coverpoint, test_label, covergroup))

    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"

    if is_sp:
        t_lines.append(f" mv x{base_reg}, sp")
        t_lines.append(" li sp, RVMODEL_ACCESS_FAULT_ADDRESS")
        t_lines.append(f" {op} {reg_str}, 0(sp)")
        t_lines.append("# Trap handler skips the next 4 bytes; two c.nops provide 4 bytes")
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append(f" mv sp, x{base_reg}")
    else:
        t_lines.append(f" li x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS")
        t_lines.append(f" {op} {reg_str}, 0(x{addr_reg})")
        t_lines.append(
            "# Load access may throw a trap and the trap handler skips over the next 4 bytes. Two c.nops are used to get 4 bytes of instructions"
        )
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

    t_lines.append(test_data.add_testcase(coverpoint, test_label, covergroup))

    reg_str = f"f{fp_reg}" if is_float else f"x{check_reg}"

    if is_sp:
        t_lines.append(f" mv x{base_reg}, sp")
        t_lines.append(" li sp, RVMODEL_ACCESS_FAULT_ADDRESS")
        t_lines.append(f" {op} {reg_str}, 0(sp)")
        t_lines.append("# Trap handler skips the next 4 bytes; two c.nops provide 4 bytes")
        t_lines.append("c.nop")
        t_lines.append("c.nop")
        t_lines.append(f" mv sp, x{base_reg}")
    else:
        t_lines.append(f" li x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS")
        t_lines.append(f" {op} {reg_str}, 0(x{addr_reg})")
        t_lines.append(
            "# Store access may throw a trap and the trap handler skips over the next 4 bytes. Two c.nops are used to get 4 bytes of instructions"
        )
        t_lines.append("c.nop")
        t_lines.append("c.nop")

    test_data.int_regs.return_registers([addr_reg, base_reg, check_reg])
    test_data.float_regs.return_registers([fp_reg])

    return t_lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZc_cg", "cp_load_address_misaligned"

    lines = [comment_banner(coverpoint, "Compressed Misaligned Loads")]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")

        # Zca
        for instr in ["c.lw", "c.lwsp"]:
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        for instr in ["c.ld", "c.ldsp"]:
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # Zcb
        lines.append("\n#ifdef ZCB_SUPPORTED")
        for instr in ["c.lh", "c.lhu", "c.lbu"]:
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # Zcf
        lines.append("\n#ifdef ZCF_SUPPORTED")
        for instr in ["c.flw", "c.flwsp"]:
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # Zcd
        lines.append("\n#ifdef ZCD_SUPPORTED")
        for instr in ["c.fld", "c.fldsp"]:
            lines.extend(_add_load_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZc_cg", "cp_store_address_misaligned"

    lines = [comment_banner(coverpoint, "Compressed Misaligned Stores")]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")

        # Zca
        for instr in ["c.sw", "c.swsp"]:
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        for instr in ["c.sd", "c.sdsp"]:
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # Zcb
        lines.append("\n#ifdef ZCB_SUPPORTED")
        for instr in ["c.sb", "c.sh"]:
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # Zcf
        lines.append("\n#ifdef ZCF_SUPPORTED")
        for instr in ["c.fsw", "c.fswsp"]:
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # Zcd
        lines.append("\n#ifdef ZCD_SUPPORTED")
        for instr in ["c.fsd", "c.fsdsp"]:
            lines.extend(_add_store_test(instr, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZc_cg", "cp_load_access_fault"

    lines = [
        comment_banner(
            coverpoint,
            "Test every type of compressed load to a faulting address and check that each one throws a load access fault.",
        )
    ]

    # Zca
    for instr in ["c.lw", "c.lwsp"]:
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))

    lines.append("#if __riscv_xlen == 64")
    for instr in ["c.ld", "c.ldsp"]:
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    # Zcb
    lines.append("\n#ifdef ZCB_SUPPORTED")
    for instr in ["c.lh", "c.lhu", "c.lbu"]:
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    # Zcf
    lines.append("\n#ifdef ZCF_SUPPORTED")
    for instr in ["c.flw", "c.flwsp"]:
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    # Zcd
    lines.append("\n#ifdef ZCD_SUPPORTED")
    for instr in ["c.fld", "c.fldsp"]:
        lines.extend(_add_load_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    return lines


def _generate_store_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsZc_cg", "cp_store_access_fault"

    lines = [
        comment_banner(
            coverpoint,
            "Test every type of compressed store to a faulting address and check that each one throws a store access fault.",
        )
    ]

    # Zca
    for instr in ["c.sw", "c.swsp"]:
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))

    lines.append("#if __riscv_xlen == 64")
    for instr in ["c.sd", "c.sdsp"]:
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    # Zcb
    lines.append("\n#ifdef ZCB_SUPPORTED")
    for instr in ["c.sb", "c.sh"]:
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    # Zcf
    lines.append("\n#ifdef ZCF_SUPPORTED")
    for instr in ["c.fsw", "c.fswsp"]:
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    # Zcd
    lines.append("\n#ifdef ZCD_SUPPORTED")
    for instr in ["c.fsd", "c.fsdsp"]:
        lines.extend(_add_store_fault(instr, test_data, coverpoint, covergroup))
    lines.append("#endif")

    return lines


def _generate_breakpoint_tests(test_data: TestData) -> list[str]:
    """Generate breakpoint exception test."""
    covergroup, coverpoint = "ExceptionsZc_cg", "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "Breakpoint"),
        test_data.add_testcase(coverpoint, "c_ebreak", covergroup),
        " c.ebreak",
        "# Breakpoint may throw a trap and the trap handler skips over the next 4 bytes. Two c.nops are used to get 4 bytes of instructions",
        "c.nop",
        "c.nop",
    ]

    return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    """Generate illegal compressed instructions."""
    covergroup, coverpoint = "ExceptionsZc_cg", "cp_illegal_instruction"

    lines = [
        comment_banner(coverpoint, "Illegal Instruction"),
        # Align to ensure proper instruction fetch and trap handling"
        " .align 2",  # Add alignment
        test_data.add_testcase(coverpoint, "illegal0", covergroup),
        " .insn 0x00",  # use two byte for instruction alignment when trapping
        " # Illegal instruction may throw a trap and the trap handler skips over the next 4 bytes. Two c.nops are used to get 4 bytes of instructions",
        " c.nop",
        " c.nop",
    ]

    return lines


@add_priv_test_generator(
    "ExceptionsZc",
    required_extensions=["Zicsr", "Sm", "Zca"],
    march_extensions=["Zicsr", "Zca", "Zcb", "Zcd", "C", "F", "D"],
)
def make_exceptionszc(test_data: TestData) -> list[str]:
    """Main entry point for Zc exception test generation."""
    lines = []

    addr_reg, val_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines.extend(
        [
            "# Initialize scratch memory with test data",
            f" LA(x{addr_reg}, scratch)",
            f" LI(x{val_reg}, 0xDEADBEEF)",
            f" sw x{val_reg}, 0(x{addr_reg})",
            f" sw x{val_reg}, 4(x{addr_reg})",
            f" sw x{val_reg}, 8(x{addr_reg})",
            f" sw x{val_reg}, 12(x{addr_reg})",
            "",
            "# Load FP test data if FP is supported",
            "\n#ifdef RVTEST_FP",
            " # Load test value into f8 from scratch memory",
            "#if FLEN == 32",
            f" flw f8, 0(x{addr_reg})",
            "#elif FLEN == 64",
            f" fld f8, 0(x{addr_reg})",
            "#endif",
            "#endif",
            "",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, val_reg])

    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    lines.extend(_generate_breakpoint_tests(test_data))
    lines.extend(_generate_illegal_instruction_tests(test_data))

    return lines
