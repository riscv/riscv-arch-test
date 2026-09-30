##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params

_FP_EDGES_BY_WIDTH: dict[str, tuple[int, ...]] = {
    "D": FLOAT_EDGES.double,
    "H": FLOAT_EDGES.half,
    "BF16": FLOAT_EDGES.bf16,
}
_FP_EDGE_MODIFIERS = {"frm", "frm4", "v", "bf16"}


def _fp_edges_for(coverpoint: str, base: str) -> tuple[int, ...]:
    """Select the edge set for a cp_fs*/cr_fs* variant, rejecting unknown suffix tokens."""
    suffix = coverpoint.removeprefix(base)
    tokens = filter(None, suffix.split("_"))
    edges = FLOAT_EDGES.single

    for token in tokens:
        if token in _FP_EDGES_BY_WIDTH:
            edges = _FP_EDGES_BY_WIDTH[token]
        elif token not in _FP_EDGE_MODIFIERS:
            raise ValueError(
                f"Unknown suffix {token!r} in coverpoint {coverpoint!r}; "
                f"expected width {sorted(_FP_EDGES_BY_WIDTH)} "
                f"or modifier {sorted(_FP_EDGE_MODIFIERS)}"
            )

    return edges


def _make_fs_edges(
    operand: str, instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Shared body for cp_fs1_edges / cp_fs2_edges / cp_fs3_edges."""
    edges = _fp_edges_for(coverpoint, f"cp_{operand}_edges")

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
