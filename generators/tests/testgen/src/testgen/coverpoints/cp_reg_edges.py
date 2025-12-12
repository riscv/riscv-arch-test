##################################
# cp_reg_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Register edge value coverpoint generators (cp_rs1_edges, cp_rs2_edges)."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.edges import get_general_edges, get_orcb_edges
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_rs1_edges")
def make_rs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for rs1 edge values."""
    if coverpoint == "cp_rs1_edges":
        edges = get_general_edges(test_data.xlen)
    elif coverpoint.endswith("_orcb"):
        edges = get_orcb_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cp_rs1_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val in edges:
        test_data.add_testcase_string(coverpoint)
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=edge_val)
        desc = f"{coverpoint} (Test source rs1 value = {test_data.xlen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines


@add_coverpoint_generator("cp_rs2_edges")
def make_rs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for rs2 edge values."""
    if coverpoint == "cp_rs2_edges":
        edges = get_general_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cp_rs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val in edges:
        test_data.add_testcase_string(coverpoint)
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs2val=edge_val)
        desc = f"{coverpoint} (Test source rs2 value = {test_data.xlen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines


@add_coverpoint_generator("cr_rs1_rs2_edges")
def make_cr_rs1_rs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for cross-product of rs1 and rs2 edge values."""
    if coverpoint == "cr_rs1_rs2_edges":
        edges1 = get_general_edges(test_data.xlen)
        edges2 = get_general_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cr_rs1_rs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            test_data.add_testcase_string(coverpoint)
            test_lines.append("")
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=edge_val1, rs2val=edge_val2)
            desc = f"{coverpoint} (Test source rs1 = {test_data.xlen_format_str.format(edge_val1)} rs2 = {test_data.xlen_format_str.format(edge_val2)})"
            test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
            test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines


@add_coverpoint_generator("cr_rs1_rs2_edges_offset")
def make_cr_rs1_rs2_edges_offset(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for cross-product of rs1/rs2 edges with branch offset testing."""
    edges1 = get_general_edges(test_data.xlen)
    edges2 = get_general_edges(test_data.xlen)

    test_lines: list[str] = []

    for edge_val1 in edges1:
        for edge_val2 in edges2:
            test_lines.append("")
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=edge_val1, rs2val=edge_val2)
            assert params.rs1 is not None and params.rs2 is not None
            test_data.add_testcase_string(coverpoint)
            test_lines.extend(
                [
                    f"# {coverpoint} (Test source rs1 = {test_data.xlen_format_str.format(edge_val1)} rs2 = {test_data.xlen_format_str.format(edge_val2)})",
                    load_int_reg("rs1", params.rs1, edge_val1, test_data),
                    load_int_reg("rs2", params.rs2, edge_val2, test_data),
                    "0: # destination for backwards branch that is never taken",
                    f"{instr_name} x{params.rs1}, x{params.rs2}, 3f # forward branch, if taken",
                    "1: # goes here if not taken",
                    f"{instr_name} x{params.rs1}, x{params.rs2}, 0b # backward branch, never taken",
                    write_sigupd(0, test_data),  # signature 0 for not taken
                    "j 4f # done with test",
                    "2: # goes here during backward branch if taken",
                    f"LI(x{params.rs1}, 1)",
                    write_sigupd(params.rs1, test_data) + " # signature 1 for taken",
                    "j 4f # done with test",
                    "3: # goes here during forward branch if taken",
                    f"{instr_name} x{params.rs1}, x{params.rs2}, 2b # backward branch, definitely taken",
                    "4: # done with test",
                ]
            )
            test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines
