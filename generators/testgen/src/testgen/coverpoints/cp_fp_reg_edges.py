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
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_fs1_edges")
def make_fs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs1 edge values."""
    if coverpoint.endswith("_D"):
        edges = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges = FLOAT_EDGES.half
    elif coverpoint.endswith("_BF16"):
        edges = FLOAT_EDGES.bf16
    else:
        edges = FLOAT_EDGES.single

    cross_frm = "_frm" in coverpoint

    # For dyn we sweep all 5 legal fcsr.frm values explicitly; relying on a random pick
    # lands on rne 20% of the time and hides a DUT that ignores fcsr.frm.
    if cross_frm:
        frm_variants: list[tuple[str | None, int | None]] = [("dyn", v) for v in range(5)]
        frm_variants += [(m, None) for m in ("rdn", "rmm", "rne", "rtz", "rup")]
    else:
        frm_variants = [(None, None)]

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        for frm_mode, csr_val in frm_variants:
            params = generate_random_params(
                test_data, instr_type, exclude_regs=[0], fs1val=edge_val, frm=frm_mode, csr_frm_val=csr_val
            )
            frm_tag = ""
            if frm_mode is not None:
                frm_tag = f"_{frm_mode}{csr_val}" if csr_val is not None else f"_{frm_mode}"
            bin_name = f"b{edge_val:#x}{frm_tag}"
            desc_tag = ""
            if frm_mode is not None:
                desc_tag = f", frm = {frm_mode}" + (f", fcsr.frm = {csr_val}" if csr_val is not None else "")
            desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(edge_val)}{desc_tag})"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_fs2_edges")
def make_fs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs2 edge values."""
    if coverpoint.endswith("_D"):
        edges = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges = FLOAT_EDGES.half
    elif coverpoint.endswith("_BF16"):
        edges = FLOAT_EDGES.bf16
    else:
        edges = FLOAT_EDGES.single

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs2val=edge_val)
        desc = f"{coverpoint} (Test source fs2 value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_fs3_edges")
def make_fs3_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs3 edge values."""
    if coverpoint.endswith("_D"):
        edges = FLOAT_EDGES.double
    elif coverpoint.endswith("_H"):
        edges = FLOAT_EDGES.half
    elif coverpoint.endswith("_BF16"):
        edges = FLOAT_EDGES.bf16
    else:
        edges = FLOAT_EDGES.single

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs3val=edge_val)
        desc = f"{coverpoint} (Test source fs3 value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
