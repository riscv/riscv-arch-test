##################################
# cr_rs1_cimm_edges_offset.py
#
# tjc.challenger1024@gmail.com Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Cross-product register edge value and immediate edge value for Zibi branches coverpoint generator (cr_rs1_cimm_edges_offset)."""

from testgen.asm.helpers import load_int_reg, return_test_regs, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES, get_general_edges
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cr_rs1_cimm_edges_offset")
def make_cr_rs1_cimm_edges_offset(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate tests for cross-product of rs1 edge values and immediate edge values with branch offset testing."""
    tc = test_data.begin_test_chunk()

    rs1_edges = get_general_edges(test_data.xlen)
    cimm_edges = (-1,) + IMMEDIATE_EDGES.imm_5bit[1:]  # exclude imm=0

    test_lines: list[str] = []

    for edge_val1 in rs1_edges:
        for imm_val in cimm_edges:
            test_lines.append("")
            params = generate_random_params(
                test_data,
                instr_type,
                exclude_regs=[0],
                rs1val=edge_val1,
                immval=imm_val,
            )
            assert params.rs1 is not None
            assert params.rs1val is not None
            assert params.immval is not None

            test_lines.extend(
                [
                    test_data.add_testcase(
                        f"rs1_{test_data.xlen_format_str.format(edge_val1)}_cimm_{imm_val}", coverpoint
                    ),
                    f"# {coverpoint} (Test source rs1 = {test_data.xlen_format_str.format(edge_val1)} cimm = {imm_val})",
                    load_int_reg("rs1", params.rs1, params.rs1val, test_data),
                    "0: # destination for backwards branch that is never taken",
                    f"{instr_name} x{params.rs1}, {params.immval}, 3f # forward branch, if taken",
                    "1: # goes here if not taken",
                    f"{instr_name} x{params.rs1}, {params.immval}, 0b # backward branch, never taken",
                    write_sigupd(0, test_data),  # signature 0 for not taken
                    "j 4f # done with test",
                    "2: # goes here during backward branch if taken",
                    f"LI(x{params.rs1}, 1)",
                    write_sigupd(params.rs1, test_data) + " # signature 1 for taken",
                    "j 4f # done with test",
                    "3: # goes here during forward branch if taken",
                    f"{instr_name} x{params.rs1}, {params.immval}, 2b # backward branch, definitely taken",
                    "4: # done with test",
                ]
            )
            return_test_regs(test_data, params)
    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
