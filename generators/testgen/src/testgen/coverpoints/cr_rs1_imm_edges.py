##################################
# cr_rs1_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cr_rs1_imm_edges coverpoint generator."""

from testgen.asm.helpers import format_zibi_branch, load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES, get_general_edges
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cr_rs1_imm_edges")
def make_cr_rs1_imm_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cross-product of rs1 and immediate edge values."""
    if coverpoint.endswith("_5bit_u_n0_offset"):
        return make_cr_rs1_imm_edges_5bit_u_n0_offset(instr_name, instr_type, coverpoint, test_data)

    edges_reg = get_general_edges(test_data.xlen)
    if coverpoint == "cr_rs1_imm_edges":
        edges_imm = IMMEDIATE_EDGES.imm_12bit
    elif coverpoint.endswith("_6bit"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit
    elif coverpoint.endswith("_6bit_n0"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit[1:]  # exclude imm=0
    elif coverpoint.endswith("_c"):
        edges_imm = IMMEDIATE_EDGES.imm_64_c if test_data.xlen == 64 else IMMEDIATE_EDGES.imm_32_c
    elif coverpoint.endswith("_uimmw"):
        edges_imm = IMMEDIATE_EDGES.imm_uimmw
    elif coverpoint.endswith("_uimm"):
        edges_imm = IMMEDIATE_EDGES.imm_uimm if test_data.xlen == 64 else IMMEDIATE_EDGES.imm_uimmw
    else:
        raise ValueError(f"Unknown cr_rs1_imm_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    for reg_edge_val in edges_reg:
        for imm_edge_val in edges_imm:
            params = generate_random_params(
                test_data, instr_type, exclude_regs=[0], rs1val=reg_edge_val, immval=imm_edge_val
            )
            desc = f"{coverpoint} (rs1 = {test_data.xlen_format_str.format(reg_edge_val)}, imm = {imm_edge_val})"
            bin_name = f"rs1val={reg_edge_val:#x}, immval={imm_edge_val:#x}"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks


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
                    f"1: ori x{params.temp_reg}, x{params.temp_reg}, 2 # backward branch (negative offset) taken",
                    "j 3f # jump forward; the backward branch is never re-executed (no infinite loop)",
                    (
                        f"2: {format_zibi_branch(instr_name, params.rs1, params.immval, '1b')} "
                        f"# {instr_name} x{params.rs1}, {params.immval}, 1b; backward branch, negative offset"
                    ),
                    (
                        f"3: {format_zibi_branch(instr_name, params.rs1, params.immval, '4f')} "
                        f"# {instr_name} x{params.rs1}, {params.immval}, 4f; forward branch, positive offset"
                    ),
                    "j 5f # forward branch not taken",
                    f"4: ori x{params.temp_reg}, x{params.temp_reg}, 1 # forward branch (positive offset) taken",
                    "5: # done with test",
                    write_sigupd(params.temp_reg, test_data),
                ]
            )
            return_testcase_registers(test_data, params)

    return [test_data.end_test_chunk()]
