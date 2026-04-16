##################################
# cp_c_hint.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_c_hint coverpoint generator for compressed instruction hint encodings."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters.params import generate_random_params
from testgen.formatters.registry import format_single_testcase


@add_coverpoint_generator("cp_c_hint")
def make_cp_c_hint(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cp_c_hint coverpoints (hint encodings of compressed instructions)."""
    test_chunks: list[TestChunk] = []

    # c.nop with imm in [-32, 31].
    if coverpoint == "cp_c_hint_nop":
        for imm in range(-32, 32):
            params = generate_random_params(test_data, instr_type, immval=imm)
            tc = format_single_testcase(
                instr_name, instr_type, test_data, params, f"{coverpoint}: imm = {imm}", f"imm{imm}", coverpoint
            )
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    # c.addi x{rd}, 0 (rd != 0). rs1 == rd in the CI encoding.
    elif coverpoint == "cp_c_hint_addi":
        for rd in range(1, test_data.int_regs.reg_count):
            asm_setup = test_data.int_regs.consume_registers([rd])
            params = generate_random_params(test_data, instr_type, rs1=rd, immval=0)
            tc = format_single_testcase(
                instr_name, instr_type, test_data, params, f"{coverpoint}: rd = x{rd}", f"rd{rd}", coverpoint
            )
            if asm_setup:
                tc.code = asm_setup + "\n" + tc.code
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    # {c.li, c.lui} x0, imm for all 6-bit signed immediates.
    elif coverpoint == "cp_c_hint_li" or coverpoint == "cp_c_hint_lui":
        for imm in range(-32, 32):
            params = generate_random_params(test_data, instr_type, rs1=0, immval=imm)
            tc = format_single_testcase(
                instr_name, instr_type, test_data, params, f"{coverpoint}: imm = {imm}", f"imm{imm}", coverpoint
            )
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    # {c.mv, c.add} x0, x{rs2} (rs2 != 0). rs1 serves as rd in the CR encoding.
    elif coverpoint in ("cp_c_hint_mv", "cp_c_hint_add"):
        for rs2 in range(1, test_data.int_regs.reg_count):
            asm_setup = test_data.int_regs.consume_registers([rs2])
            params = generate_random_params(test_data, instr_type, rs1=0, rs2=rs2)
            tc = format_single_testcase(
                instr_name, instr_type, test_data, params, f"{coverpoint}: rs2 = x{rs2}", f"rs2{rs2}", coverpoint
            )
            if asm_setup:
                tc.code = asm_setup + "\n" + tc.code
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    else:
        raise ValueError(f"Unknown cp_c_hint variant: {coverpoint}")

    return test_chunks
