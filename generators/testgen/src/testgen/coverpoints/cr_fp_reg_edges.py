##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point cross-product register edge value coverpoint generators (cr_fs1_fs2_edges, cr_fs1_fs2_edges_frm, etc.)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cr_fs1_fs2_edges")
def make_cr_fs1_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for cross-product of fs1 and fs2 edge values."""
    if coverpoint.endswith("_D"):
        edges1 = FLOAT_EDGES.double
        edges2 = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges1 = FLOAT_EDGES.half
        edges2 = FLOAT_EDGES.half
    elif coverpoint.endswith("_BF16"):
        edges1 = FLOAT_EDGES.bf16
        edges2 = FLOAT_EDGES.bf16
    else:
        edges1 = FLOAT_EDGES.single
        edges2 = FLOAT_EDGES.single

    cross_frm = "_frm" in coverpoint

    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup") if cross_frm else [None]

    test_lines: list[str] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            # Explicit rounding modes (if needed)
            for frm_mode in frm_modes:
                test_lines.append(
                    test_data.add_testcase(f"rs1val={edge_val1:#x}, rs2val={edge_val2:#x}, frm={frm_mode}", coverpoint)
                )
                params = generate_random_params(
                    test_data, instr_type, exclude_regs=[0], fs1val=edge_val1, fs2val=edge_val2, frm=frm_mode
                )
                desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs2 = {test_data.flen_format_str.format(edge_val2)}{f', frm = {frm_mode}' if frm_mode is not None else ''})"
                test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
                return_test_regs(test_data, params)
            # Dynamic rounding modes
            # if cross_frm:
            #     for frm_mode in (4, 3, 2, 1, 0):  # csr frm modes 0-4, end at 0 so the rest of the test continues in rne
            #         test_data.add_testcase(f"rs1val={edge_val1:#x}, rs2val={edge_val2:#x}, frm_dyn={frm_mode}", coverpoint)
            #         test_lines.append(f"\nfsrmi 0x{frm_mode:x} # set fcsr.frm to mode {frm_mode}\n")
            #         params = generate_random_params(test_data, instr_type, exclude_regs=[0])
            #         desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs2 = {test_data.flen_format_str.format(edge_val2)}, fcsr.frm = {frm_mode})"
            #         test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
            #         return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cr_fs1_fs3_edges")
def make_cr_fs1_fs3_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for cross-product of fs1 and fs3 edge values."""
    if coverpoint.endswith("_D"):
        edges1 = FLOAT_EDGES.double
        edges2 = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges1 = FLOAT_EDGES.half
        edges2 = FLOAT_EDGES.half
    elif coverpoint.endswith("_BF16"):
        edges1 = FLOAT_EDGES.bf16
        edges2 = FLOAT_EDGES.bf16
    else:
        edges1 = FLOAT_EDGES.single
        edges2 = FLOAT_EDGES.single

    cross_frm = "_frm" in coverpoint

    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup") if cross_frm else [None]

    test_lines: list[str] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            # Explicit rounding modes (if needed)
            for frm_mode in frm_modes:
                test_lines.append(
                    test_data.add_testcase(f"fs1val={edge_val1:#x}, fs3val={edge_val2:#x}, frm={frm_mode}", coverpoint)
                )
                params = generate_random_params(
                    test_data, instr_type, exclude_regs=[0], fs1val=edge_val1, fs3val=edge_val2, frm=frm_mode
                )
                desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs3 = {test_data.flen_format_str.format(edge_val2)}{f', frm = {frm_mode}' if frm_mode is not None else ''})"
                test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
                return_test_regs(test_data, params)
            # Dynamic rounding modes
            # if cross_frm:
            #     for frm_mode in (4, 3, 2, 1, 0):  # csr frm modes 0-4, end at 0 so the rest of the test continues in rne
            #         test_data.add_testcase(f"fs1val={edge_val1:#x}, fs3val={edge_val2:#x}, frm_dyn={frm_mode}", coverpoint)
            #         test_lines.append(f"\nfsrmi 0x{frm_mode:x} # set fcsr.frm to mode {frm_mode}\n")
            #         params = generate_random_params(test_data, instr_type, exclude_regs=[0])
            #         desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs3 = {test_data.flen_format_str.format(edge_val2)}, fcsr.frm = {frm_mode})"
            #         test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
            #         return_test_regs(test_data, params)

    return test_lines
