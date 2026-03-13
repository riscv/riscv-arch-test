##################################
# cp_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges coverpoint generators."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES
from testgen.data.state import TestData
from testgen.data.testcase import TestCase
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_imm_edges")
def make_cp_imm_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestCase]:
    """Generate tests for immediate edge values."""
    if coverpoint == "cp_imm_edges":
        edges_imm = IMMEDIATE_EDGES.imm_12bit
    elif coverpoint.endswith("_20bit"):
        edges_imm = IMMEDIATE_EDGES.imm_20bit
    elif coverpoint.endswith("_6bit"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit
    elif coverpoint.endswith("_6bit_n0"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit[1:]  # exclude imm=0
    else:
        raise ValueError(f"Unknown cp_imm_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_cases: list[TestCase] = []

    for edge_val in edges_imm:
        params = generate_random_params(test_data, instr_type, immval=edge_val, exclude_regs=[0])
        desc = f"{coverpoint} (imm = {edge_val})"
        tc = format_single_test(instr_name, instr_type, test_data, params, desc, f"{edge_val:#x}", coverpoint)
        test_cases.append(tc)
        return_test_regs(test_data, params)

    return test_cases
