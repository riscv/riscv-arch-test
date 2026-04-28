##################################
# cr_reg_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Cross-product register edge value coverpoint generator (cr_rs1_rs2_edges)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import get_general_edges
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cr_rs1_rs2_edges")
def make_cr_rs1_rs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cross-product of rs1 and rs2 edge values."""
    if coverpoint == "cr_rs1_rs2_edges":
        edges1 = get_general_edges(test_data.xlen)
        edges2 = get_general_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cr_rs1_rs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=edge_val1, rs2val=edge_val2)
            bin_name = f"rs1val={edge_val1:#x}, rs2val={edge_val2:#x}"
            desc = f"{coverpoint} (Test source rs1 = {test_data.xlen_format_str.format(edge_val1)} rs2 = {test_data.xlen_format_str.format(edge_val2)})"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks
