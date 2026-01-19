##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_fs1_edges")
def make_fs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs1 edge values."""
    if coverpoint.endswith("_D"):
        edges = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges = FLOAT_EDGES.half
    else:
        edges = FLOAT_EDGES.single

    cross_frm = "_frm" in coverpoint

    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup") if cross_frm else [None]

    test_lines: list[str] = []
    for edge_val in edges:
        for frm_mode in frm_modes:
            test_lines.append(test_data.add_testcase(coverpoint))
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs1val=edge_val, frm=frm_mode)
            desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(edge_val)}{f', frm = {frm_mode}' if frm_mode is not None else ''})"
            test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
            return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs2_edges")
def make_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs2 edge values."""
    if coverpoint.endswith("_D"):
        edges = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges = FLOAT_EDGES.half
    else:
        edges = FLOAT_EDGES.single

    test_lines: list[str] = []
    for edge_val in edges:
        test_lines.append(test_data.add_testcase(coverpoint))
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs2val=edge_val)
        desc = f"{coverpoint} (Test source fs2 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs3_edges")
def make_fs3_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs3 edge values."""
    if coverpoint.endswith("_D"):
        edges = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges = FLOAT_EDGES.half
    else:
        edges = FLOAT_EDGES.single

    test_lines: list[str] = []
    for edge_val in edges:
        test_lines.append(test_data.add_testcase(coverpoint))
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs3val=edge_val)
        desc = f"{coverpoint} (Test source fs3 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines
