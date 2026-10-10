##################################
# cr_reg_imm_edges_offset.py
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""Cross-product register and immediate edge values with branch offsets."""

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES, get_general_edges
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cr_rs1_imm_edges_5bit_u_n0_offset")
def make_cr_rs1_imm_edges_5bit_u_n0_offset(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate Zibi tests crossing rs1 and immediate edges with branch direction."""
    tc = test_data.begin_test_chunk()

    for reg_edge_val in get_general_edges(test_data.xlen):
        for imm_edge_val in IMMEDIATE_EDGES.imm_5bit_u_n0:
            params = generate_random_params(
                test_data,
                instr_type,
                exclude_regs=[0],
                rs1val=reg_edge_val,
                immval=imm_edge_val,
            )
            assert params.rs1 is not None
            assert params.rs1val is not None
            assert params.immval is not None
            assert params.temp_reg is not None
            desc = (
                f"# {coverpoint} (Test source rs1 = "
                f"{test_data.xlen_format_str.format(reg_edge_val)} imm = {imm_edge_val})"
            )

            tc.code.extend(
                [
                    "",
                    test_data.add_testcase(
                        f"rs1_{test_data.xlen_format_str.format(reg_edge_val)}_imm_{imm_edge_val}", coverpoint
                    ),
                    desc,
                    load_int_reg("rs1", params.rs1, params.rs1val, test_data),
                    f"LI(x{params.temp_reg}, 0) # marker: records which branches are taken",
                    "j 2f # enter the test past the backward-branch target",
                    f"1: ori x{params.temp_reg}, x{params.temp_reg}, 2 # backward branch taken",
                    "j 3f # continue with the forward branch",
                    f"2: {instr_name} x{params.rs1}, {params.immval}, 1b # backward branch",
                    f"3: {instr_name} x{params.rs1}, {params.immval}, 4f # forward branch",
                    "j 5f # forward branch not taken",
                    f"4: ori x{params.temp_reg}, x{params.temp_reg}, 1 # forward branch taken",
                    "5: # done with test",
                    write_sigupd(params.temp_reg, test_data),
                ]
            )
            return_testcase_registers(test_data, params)

    return [test_data.end_test_chunk()]
