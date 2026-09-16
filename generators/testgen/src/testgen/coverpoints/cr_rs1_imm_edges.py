##################################
# cr_rs1_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cr_rs1_imm_edges coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES, get_general_edges, get_word_edges
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cr_rs1_imm_edges")
def make_cr_rs1_imm_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cross-product of rs1 and immediate edge values."""
    # A trailing "_w" selects 32-bit word edge values for rs1 (RV64 *w instructions).
    if coverpoint.endswith("_w"):
        edges_reg = get_word_edges(test_data.xlen)
        coverpoint_imm = coverpoint.removesuffix("_w")
    else:
        edges_reg = get_general_edges(test_data.xlen)
        coverpoint_imm = coverpoint
    if coverpoint_imm == "cr_rs1_imm_edges":
        edges_imm = IMMEDIATE_EDGES.imm_12bit
    elif coverpoint_imm.endswith("_6bit"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit
    elif coverpoint_imm.endswith("_6bit_n0"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit[1:]  # exclude imm=0
    elif coverpoint_imm.endswith("_c"):
        edges_imm = IMMEDIATE_EDGES.imm_64_c if test_data.xlen == 64 else IMMEDIATE_EDGES.imm_32_c
    elif coverpoint_imm.endswith("_uimmw"):
        edges_imm = IMMEDIATE_EDGES.imm_uimmw
    elif coverpoint_imm.endswith("_uimm"):
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
