##################################
# cr_imm_rs1_rel.py
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""Cross-product of Zibi comparison constants with the relation of rs1 to the constant."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cr_imm_edges_5bit_u_n0_rs1_rel")
def make_cr_imm_edges_5bit_u_n0_rs1_rel(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate Zibi tests where rs1 equals, is adjacent to, or shares only the low word with the constant."""
    xlen = test_data.xlen
    mask = (1 << xlen) - 1
    test_chunks: list[TestChunk] = []

    for imm in IMMEDIATE_EDGES.imm_5bit_u_n0:
        relations = {
            "equal": imm & mask,
            "plus1": (imm + 1) & mask,
            "minus1": (imm - 1) & mask,
        }
        if xlen == 64:
            # Same low word as imm but a different upper word
            relations["low_word_equal_upper_differs"] = (imm & 0xFFFFFFFF) | (0 if imm < 0 else 1 << 32)

        for rel, rs1val in relations.items():
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=rs1val, immval=imm)
            desc = f"{coverpoint} (imm = {imm}, rs1 = {test_data.xlen_format_str.format(rs1val)}, {rel})"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{imm:#x}_{rel}", coverpoint)
            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks
