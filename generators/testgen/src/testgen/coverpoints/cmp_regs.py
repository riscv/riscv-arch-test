##################################
# cmp_regs.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Compare register coverpoint generators (cmp_rd_rs1, cmp_rd_rs2, cmp_rs1_rs2, cmp_rd_rs1_rs2)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cmp_rd_rs1")
def make_cmp_rd_rs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests where rd = rs1."""
    # Determine which rd registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cmp_rd_rs1":
        regs = range(test_data.int_regs.reg_count)
    elif coverpoint.endswith("_nx0"):
        regs = range(1, test_data.int_regs.reg_count)  # Exclude x0
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_nx0_pair"):
        regs = range(2, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions, exclude x0
        is_pair = True
    elif coverpoint.endswith("_pair"):
        regs = range(0, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions
        is_pair = True
    else:
        raise ValueError(f"Unknown cmp_rd_rs1 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for reg in regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(reg))
        else:
            test_lines.append(test_data.int_regs.consume_registers([reg]))
        params = generate_random_params(test_data, instr_type, rd=reg, rs1=reg)
        desc = f"{coverpoint} (Test rd = rs1 = x{reg})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cmp_rd_rs2")
def make_cmp_rd_rs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests where rd = rs2."""
    # Determine which rd registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cmp_rd_rs2":
        regs = range(test_data.int_regs.reg_count)
    elif coverpoint.endswith("_nx0"):
        regs = range(1, test_data.int_regs.reg_count)  # Exclude x0
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_nx0_pair"):
        regs = range(2, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions, exclude x0
        is_pair = True
    elif coverpoint.endswith("_pair"):
        regs = range(0, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions
        is_pair = True
    else:
        raise ValueError(f"Unknown cmp_rd_rs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for reg in regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(reg))
        else:
            test_lines.append(test_data.int_regs.consume_registers([reg]))
        params = generate_random_params(test_data, instr_type, rd=reg, rs2=reg)
        desc = f"{coverpoint} (Test rd = rs2 = x{reg})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cmp_rs1_rs2")
def make_cmp_rs1_rs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests where rs1 = rs2."""
    # Determine which rd registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cmp_rs1_rs2":
        regs = range(test_data.int_regs.reg_count)
    elif coverpoint.endswith("_nx0"):
        regs = range(1, test_data.int_regs.reg_count)  # Exclude x0
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_nx0_pair"):
        regs = range(2, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions, exclude x0
        is_pair = True
    elif coverpoint.endswith("_pair"):
        regs = range(0, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions
        is_pair = True
    else:
        raise ValueError(f"Unknown cmp_rs1_rs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for reg in regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(reg))
        else:
            test_lines.append(test_data.int_regs.consume_registers([reg]))
        params = generate_random_params(test_data, instr_type, rs1=reg, rs2=reg)
        desc = f"{coverpoint} (Test rs1 = rs2 = x{reg})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cmp_rd_rs1_rs2")
def make_cmp_rd_rs1_rs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests where rd = rs1 = rs2."""
    # Determine which rd registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cmp_rd_rs1_rs2":
        regs = range(test_data.int_regs.reg_count)
    elif coverpoint.endswith("_nx0"):
        regs = range(1, test_data.int_regs.reg_count)  # Exclude x0
    elif coverpoint.endswith("_nx0_pair"):
        regs = range(2, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions, exclude x0
        is_pair = True
    elif coverpoint.endswith("_pair"):
        regs = range(0, test_data.int_regs.reg_count, 2)  # Even registers for pair instructions
        is_pair = True
    else:
        raise ValueError(f"Unknown cmp_rd_rs1_rs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for reg in regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(reg))
        else:
            test_lines.append(test_data.int_regs.consume_registers([reg]))
        params = generate_random_params(test_data, instr_type, rd=reg, rs1=reg, rs2=reg)
        desc = f"{coverpoint} (Test rd = rs1 = rs2 = x{reg})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines
