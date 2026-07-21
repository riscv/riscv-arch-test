##################################
# cp_reg_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Register edge value coverpoint generators (cp_rs1_edges, cp_rs2_edges)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import get_base_lmul
from testgen.data.edges import get_general_edges, get_orcb_edges
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_rs1_edges")
def make_rs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for rs1 edge values."""
    if coverpoint == "cp_rs1_edges":
        edges = get_general_edges(test_data.xlen)
    elif coverpoint.endswith("_orcb"):
        edges = get_orcb_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cp_rs1_edges coverpoint variant: {coverpoint} for {instr_name}")

    is_vector = instr_name.lower().startswith("v")
    if is_vector:
        assert test_data.config.sew is not None, "SEW must be set for vector tests"
        lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    else:
        lmul = 1  # Placeholder to keep the type-checker happy

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        if is_vector:
            params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, rs1val=edge_val)
        else:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=edge_val)
        desc = f"{coverpoint} (Test source rs1 value = {test_data.xlen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_rs2_edges")
def make_rs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for rs2 edge values."""
    if coverpoint == "cp_rs2_edges":
        edges = get_general_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cp_rs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs2val=edge_val)
        desc = f"{coverpoint} (Test source rs2 value = {test_data.xlen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
