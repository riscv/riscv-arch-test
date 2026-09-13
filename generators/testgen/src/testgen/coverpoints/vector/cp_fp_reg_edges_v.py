##################################
# cp_fp_reg_edges_v.py
#
# rwolk@g.hmc.edu September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import VECTOR_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_fs1_edges_v")
def make_fs1_edges_v(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs1 edge values in vector instructions."""
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew

    if sew == 16:
        fs1_edges = VECTOR_EDGES.f16
    elif sew == 32:
        fs1_edges = VECTOR_EDGES.f32
    elif sew == 64:
        fs1_edges = VECTOR_EDGES.f64
    else:
        raise ValueError(f"Unsupported SEW ({sew}) for cr_vs2_fs2_edges")

    lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)

    test_chunks: list[TestChunk] = []
    for edge_name in fs1_edges:
        edge_val = fs1_edges[edge_name]

        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, fs1val=edge_val)
        bin_name = edge_name
        desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(edge_val)} ({edge_name}))"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
