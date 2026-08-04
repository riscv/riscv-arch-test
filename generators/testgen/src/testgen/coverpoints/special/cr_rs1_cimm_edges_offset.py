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
    cimm_edges = (-1,) + IMMEDIATE_EDGES.imm_5bit_zibi[1:]  # exclude cimm field 0; add effective value -1 (Zibi)

    for edge_val1 in rs1_edges:
        for imm_val in cimm_edges:
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
            assert params.temp_reg is not None

            # Exercise both a backward (negative offset) and a forward (positive
            # offset) branch with the same condition. A marker register records
            # which branches were taken (bit 1 = backward, bit 0 = forward) and a
            # single signature update at the end captures the result.
            #
            # The only backward branch (at label 2) targets label 1, which
            # immediately jumps forward, so control always makes forward progress:
            # even if the DUT mispredicts a branch the test cannot infinite loop,
            # and any wrong branch direction changes the marker and shows up as a
            # signature mismatch against the reference model.
            tc.code.extend(
                [
                    "",
                    test_data.add_testcase(
                        f"rs1_{test_data.xlen_format_str.format(edge_val1)}_cimm_{imm_val}", coverpoint
                    ),
                    f"# {coverpoint} (Test source rs1 = {test_data.xlen_format_str.format(edge_val1)} cimm = {imm_val})",
                    load_int_reg("rs1", params.rs1, params.rs1val, test_data),
                    f"LI(x{params.temp_reg}, 0) # marker: records which branches are taken",
                    "j 2f # enter the test past the backward-branch target",
                    f"1: ori x{params.temp_reg}, x{params.temp_reg}, 2 # backward branch (negative offset) taken",
                    "j 3f # jump forward; the backward branch is never re-executed (no infinite loop)",
                    f"2: {instr_name} x{params.rs1}, {params.immval}, 1b # backward branch, negative offset",
                    f"3: {instr_name} x{params.rs1}, {params.immval}, 4f # forward branch, positive offset",
                    "j 5f # forward branch not taken",
                    f"4: ori x{params.temp_reg}, x{params.temp_reg}, 1 # forward branch (positive offset) taken",
                    "5: # done with test",
                    write_sigupd(params.temp_reg, test_data),
                ]
            )
            return_test_regs(test_data, params)
    return [test_data.end_test_chunk()]
