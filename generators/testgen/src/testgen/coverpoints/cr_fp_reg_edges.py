##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point cross-product register edge value coverpoint generators (cr_fs1_fs2_edges, cr_fs1_fs2_edges_frm, etc.)."""

from testgen.coverpoints.cp_fp_reg_edges import _fp_edges_for
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cr_fs1_fs2_edges")
def make_cr_fs1_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cross-product of fs1 and fs2 edge values."""
    edges1 = edges2 = _fp_edges_for(coverpoint, "cr_fs1_fs2_edges")

    cross_frm = "_frm" in coverpoint

    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup") if cross_frm else [None]

    test_chunks: list[TestChunk] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            # Explicit rounding modes (if needed)
            for frm_mode in frm_modes:
                params = generate_random_params(
                    test_data, instr_type, exclude_regs=[0], fs1val=edge_val1, fs2val=edge_val2, frm=frm_mode
                )
                bin_name = f"fs1val={edge_val1:#x}, fs2val={edge_val2:#x}, frm={frm_mode}"
                desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs2 = {test_data.flen_format_str.format(edge_val2)}{f', frm = {frm_mode}' if frm_mode is not None else ''})"
                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_fs1_fs3_edges")
def make_cr_fs1_fs3_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cross-product of fs1 and fs3 edge values."""
    edges1 = edges2 = _fp_edges_for(coverpoint, "cr_fs1_fs3_edges")

    cross_frm = "_frm" in coverpoint

    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup") if cross_frm else [None]

    test_chunks: list[TestChunk] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            # Explicit rounding modes (if needed)
            for frm_mode in frm_modes:
                params = generate_random_params(
                    test_data, instr_type, exclude_regs=[0], fs1val=edge_val1, fs3val=edge_val2, frm=frm_mode
                )
                desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val1)} fs3 = {test_data.flen_format_str.format(edge_val2)}{f', frm = {frm_mode}' if frm_mode is not None else ''})"
                bin_name = f"fs1val={edge_val1:#x}, fs3val={edge_val2:#x}, frm={frm_mode}"
                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_fs1_fs2_fs3_edges_frm4")
def make_cr_fs1_fs2_fs3_edges_frm4(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate the full three-source FMA edge product crossed with rounding modes."""
    if instr_type != "FR4":
        raise ValueError(f"{coverpoint} requires FR4, got {instr_type}")
    edges = _fp_edges_for(coverpoint, "cr_fs1_fs2_fs3_edges_frm4")
    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup")
    test_chunks: list[TestChunk] = []
    for i, value1 in enumerate(edges):
        for j, value2 in enumerate(edges):
            for k, value3 in enumerate(edges):
                for frm_mode in frm_modes:
                    params = generate_random_params(
                        test_data, instr_type, fs1val=value1, fs2val=value2, fs3val=value3, frm=frm_mode
                    )
                    desc = f"{coverpoint} (fs1={value1:#x}, fs2={value2:#x}, fs3={value3:#x}, frm={frm_mode})"
                    tc = format_single_testcase(
                        instr_name, instr_type, test_data, params, desc, f"b{i}_{j}_{k}_{frm_mode}", coverpoint
                    )
                    # Three-source testcases need smaller groups to stay below the 500 KB file limit.
                    tc.split_name = f"{coverpoint}_{len(test_chunks) // 400}"
                    test_chunks.append(tc)
                    return_testcase_registers(test_data, params)
    return test_chunks
