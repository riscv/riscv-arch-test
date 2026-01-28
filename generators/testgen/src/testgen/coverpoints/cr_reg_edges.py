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
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cr_rs1_rs2_edges")
def make_cr_rs1_rs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for cross-product of rs1 and rs2 edge values."""
    if coverpoint == "cr_rs1_rs2_edges":
        edges1 = get_general_edges(test_data.xlen)
        edges2 = get_general_edges(test_data.xlen)
    else:
        raise ValueError(f"Unknown cr_rs1_rs2_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for edge_val1 in edges1:
        for edge_val2 in edges2:
            test_lines.append(test_data.add_testcase(coverpoint))
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=edge_val1, rs2val=edge_val2)
            desc = f"{coverpoint} (Test source rs1 = {test_data.xlen_format_str.format(edge_val1)} rs2 = {test_data.xlen_format_str.format(edge_val2)})"
            test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
            return_test_regs(test_data, params)

    return test_lines
