##################################
# cp_cvt_edges.py
#
# david_harris@hmc.edu Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Conversion edge value coverpoint generators (cp_fs1_cvt_edges, cp_rs1_cvt_edges, cp_rs1_fp_edges)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import CONVERSION_EDGES, FLOAT_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params

STATIC_FRM_MODES = ("rdn", "rmm", "rne", "rtz", "rup")


def _cvt_cases(prefix: str, coverpoint: str) -> tuple[str, list[tuple[int, str | None]]]:
    """Edge key and (value, frm) pairs for a coverpoint named <prefix>[_frm]_<source>_<destination>."""
    key = coverpoint.removeprefix(prefix + "_")
    cross_frm = key.startswith("frm_")
    key = key.removeprefix("frm_")
    if key not in CONVERSION_EDGES.rounded and key not in CONVERSION_EDGES.exact:
        raise ValueError(f"Unknown conversion edge variant {key!r} in {coverpoint}")
    frm_modes = STATIC_FRM_MODES if cross_frm else (None,)
    rounded = [(val, frm) for val in CONVERSION_EDGES.rounded.get(key, ()) for frm in frm_modes]
    exact = [(val, None) for val in CONVERSION_EDGES.exact.get(key, ())]
    return key, rounded + exact


def _xlen_value(key: str, val: int, xlen: int) -> int:
    """Sign-extend 32-bit integer source values to XLEN."""
    if key in CONVERSION_EDGES.sign_extended and val >> 31:
        val |= ~0xFFFFFFFF
    return val & ((1 << xlen) - 1)


@add_coverpoint_generator("cp_fs1_cvt_edges")
def make_fs1_cvt_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs1 values at the rounding and range boundaries of a conversion."""
    test_chunks: list[TestChunk] = []
    _, cases = _cvt_cases("cp_fs1_cvt_edges", coverpoint)
    for val, frm in cases:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs1val=val, frm=frm)
        bin_name = f"b{val:#x}{f'_{frm}' if frm is not None else ''}"
        desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(val)}{f', frm = {frm}' if frm is not None else ''})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_rs1_cvt_edges")
def make_rs1_cvt_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for rs1 values at the rounding and range boundaries of an integer to float conversion."""
    test_chunks: list[TestChunk] = []
    key, cases = _cvt_cases("cp_rs1_cvt_edges", coverpoint)
    for val, frm in cases:
        rs1val = _xlen_value(key, val, test_data.xlen)
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=rs1val, frm=frm)
        bin_name = f"b{val:#x}{f'_{frm}' if frm is not None else ''}"
        desc = f"{coverpoint} (Test source rs1 value = {test_data.xlen_format_str.format(rs1val)}{f', frm = {frm}' if frm is not None else ''})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_rs1_fp_edges")
def make_rs1_fp_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests that move floating-point edge bit patterns from rs1."""
    if coverpoint == "cp_rs1_fp_edges":
        edges = FLOAT_EDGES.single
    elif coverpoint == "cp_rs1_fp_edges_D":
        edges = FLOAT_EDGES.double
    elif coverpoint == "cp_rs1_fp_edges_H":
        edges = FLOAT_EDGES.half
    else:
        raise ValueError(f"Unknown cp_rs1_fp_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []
    for val in edges:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=val)
        desc = f"{coverpoint} (Test source rs1 value = {test_data.xlen_format_str.format(val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks
