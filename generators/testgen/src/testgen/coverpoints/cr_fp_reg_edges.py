##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point cross-product register edge value coverpoint generators (cr_fs1_fs2_edges, cr_fs1_fs2_edges_frm, etc.)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.data.ties import TIE_FRM_MODES, tie_edges_for, tie_partners_for
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cr_fs1_fs2_edges")
def make_cr_fs1_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
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


@add_coverpoint_generator("cr_fs1_fs2_edges_ties")
def make_cr_fs1_fs2_edges_ties(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate tests crossing fs1 exact-tie values with +-1.0 under RNE and RMM."""
    edges = tie_edges_for(coverpoint)
    partners = tie_partners_for(coverpoint)
    # FR4 adds the fs3 addend, so pin it to 1.0 to keep fs1 * fs2 + fs3 an exact tie.
    fs3_pin = {"fs3val": partners[0]} if instr_type == "FR4" else {}

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        for partner_val in partners:
            for frm_mode in TIE_FRM_MODES:
                params = generate_random_params(
                    test_data,
                    instr_type,
                    exclude_regs=[0],
                    fs1val=edge_val,
                    fs2val=partner_val,
                    frm=frm_mode,
                    **fs3_pin,
                )
                bin_name = f"fs1val={edge_val:#x}, fs2val={partner_val:#x}, frm={frm_mode}"
                desc = f"{coverpoint} (Test source fs1 = {test_data.flen_format_str.format(edge_val)} fs2 = {test_data.flen_format_str.format(partner_val)}, frm = {frm_mode})"
                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_testcase_registers(test_data, params)

    return test_chunks
