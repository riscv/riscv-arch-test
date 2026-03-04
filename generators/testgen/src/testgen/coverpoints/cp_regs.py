##################################
# cp_regs.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Register coverpoint handlers (cp_rd, cp_rs1, cp_rs2)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_rd")
def make_rd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for destination register coverpoints."""
    # Determine which rd registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cp_rd":
        rd_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith("_nx0"):
        rd_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("rd_p"):
        rd_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_pair"):
        # Only even registers for pair instructions
        rd_regs = list(range(0, test_data.int_regs.reg_count, 2))
        is_pair = True
    else:
        raise ValueError(f"Unknown cp_rd coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for rd in rd_regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(rd))
        else:
            test_lines.append(test_data.int_regs.consume_registers([rd]))
        params = generate_random_params(test_data, instr_type, rd=rd)
        desc = f"{coverpoint} (Test destination rd = x{rd})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{rd}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_rs1")
def make_rs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for source register 1 coverpoints."""
    # Determine which rs1 registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cp_rs1":
        rs1_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith("_nx0"):
        rs1_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("_nx2"):
        rs1_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
        rs1_regs.remove(2)  # Exclude x2
    elif coverpoint.endswith("_p"):
        rs1_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_pair"):
        # Only even registers for pair instructions
        rs1_regs = list(range(0, test_data.int_regs.reg_count, 2))
        is_pair = True
    else:
        raise ValueError(f"Unknown cp_rs1 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for rs1 in rs1_regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(rs1))
        else:
            test_lines.append(test_data.int_regs.consume_registers([rs1]))
        params = generate_random_params(test_data, instr_type, rs1=rs1)
        desc = f"{coverpoint} (Test source rs1 = x{rs1})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{rs1}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_rs2")
def make_rs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for source register 2 coverpoints."""
    # Determine which rs2 registers to test based on coverpoint variant
    is_pair = False
    if coverpoint == "cp_rs2":
        rs2_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith("_nx0"):
        rs2_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("_p"):
        rs2_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_pair"):
        # Only even registers for pair instructions
        rs2_regs = list(range(0, test_data.int_regs.reg_count, 2))
        is_pair = True
    else:
        raise ValueError(f"Unknown cp_rs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for rs2 in rs2_regs:
        if is_pair:
            test_lines.append(test_data.int_regs.consume_register_pair(rs2))
        else:
            test_lines.append(test_data.int_regs.consume_registers([rs2]))
        params = generate_random_params(test_data, instr_type, rs2=rs2)
        desc = f"{coverpoint} (Test source rs2 = x{rs2})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, f"b{rs2}", coverpoint))
        return_test_regs(test_data, params)

    return test_lines
