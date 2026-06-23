##################################
# cp_vs_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector._corner_helpers import CORNER_NAMES, make_corner_label
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vs2_edges")
def make_vs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    test_chunks = []
    for corner in CORNER_NAMES:
        label = make_corner_label(corner, sew, test_data)
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vs2_val_pointer=label)

        desc = f"cp_vs2_edges (Test source vs2 value = {corner})"
        bin_name = f"cp_vs2_edges_b{corner}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vs1_edges")
def make_vs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    test_chunks = []
    for corner in CORNER_NAMES:
        label = make_corner_label(corner, sew, test_data)
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vs1_val_pointer=label)

        desc = f"cp_vs1_edges (Test source vs1 value = {corner})"
        bin_name = f"cp_vs1_edges_b{corner}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
