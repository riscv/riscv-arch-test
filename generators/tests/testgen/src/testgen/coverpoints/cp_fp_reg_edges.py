##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.common import return_test_regs
from testgen.utils.edges import FLOAT_EDGES
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_fs1_edges")
def make_fs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs1 edge values."""
    if coverpoint == "cp_fs1_edges":
        edges = FLOAT_EDGES.single
    else:
        raise ValueError(f"Unknown cp_fs1_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val in edges:
        test_data.add_testcase_string(coverpoint)
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs1val=edge_val)
        desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs2_edges")
def make_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs2 edge values."""
    if coverpoint == "cp_fs2_edges":
        edges = FLOAT_EDGES.single
    else:
        raise ValueError(f"Unknown cp_fs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val in edges:
        test_data.add_testcase_string(coverpoint)
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs2val=edge_val)
        desc = f"{coverpoint} (Test source fs2 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cr_fs1_fs2_edges")
def make_cr_fs1_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for cross-product of rs1 and rs2 edge values."""
    if coverpoint == "cr_fs1_fs2_edges":
        edges1 = FLOAT_EDGES.single
        edges2 = FLOAT_EDGES.single
    else:
        raise ValueError(f"Unknown cr_fs1_fs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            test_data.add_testcase_string(coverpoint)
            test_lines.append("")
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs1val=edge_val1, fs2val=edge_val2)
            desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs2 = {test_data.flen_format_str.format(edge_val2)})"
            test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
            return_test_regs(test_data, params)

    return test_lines
