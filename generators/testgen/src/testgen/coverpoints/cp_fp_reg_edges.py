##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges, cp_fd_edges)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


def _edges_for(coverpoint: str) -> tuple[int, ...]:
    """Pick the edge value table matching the coverpoint's format suffix."""
    if coverpoint.endswith("_D"):
        return FLOAT_EDGES.double
    if coverpoint.endswith("_H"):
        return FLOAT_EDGES.half
    if coverpoint.endswith("_BF16"):
        return FLOAT_EDGES.bf16
    return FLOAT_EDGES.single


def _make_fs_edges(
    operand: str, instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Shared body for cp_fs1_edges / cp_fs2_edges / cp_fs3_edges."""
    edges = _edges_for(coverpoint)

    cross_frm = "_frm" in coverpoint
    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup") if cross_frm else [None]

    val_key = f"{operand}val"
    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        for frm_mode in frm_modes:
            params = generate_random_params(
                test_data,
                instr_type,
                exclude_regs=[0],
                **{val_key: edge_val},
                frm=frm_mode,
            )
            bin_name = f"b{edge_val:#x}{f'_{frm_mode}' if frm_mode is not None else ''}"
            desc = f"{coverpoint} (Test source {operand} value = {test_data.flen_format_str.format(edge_val)}{f', frm = {frm_mode}' if frm_mode is not None else ''})"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_fs1_edges")
def make_fs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs1 edge values."""
    return _make_fs_edges("fs1", instr_name, instr_type, coverpoint, test_data)


@add_coverpoint_generator("cp_fs2_edges")
def make_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs2 edge values."""
    return _make_fs_edges("fs2", instr_name, instr_type, coverpoint, test_data)


@add_coverpoint_generator("cp_fs3_edges")
def make_fs3_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs3 edge values."""
    return _make_fs_edges("fs3", instr_name, instr_type, coverpoint, test_data)


@add_coverpoint_generator("cp_fd_edges")
def make_fd_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests loading each edge value into fd to check that a load maintains all bits."""
    test_chunks: list[TestChunk] = []
    for edge_val in _edges_for(coverpoint):
        # temp_fval is the value placed in memory and loaded into fd.
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], temp_fval=edge_val)
        desc = f"{coverpoint} (Test loaded fd value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
