##################################
# cp_imm_5bit_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_imm_5bit")
def make_imm_5bit(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests covering all values of the 5-bit immediate in a vector instruction.
    """

    imm_vals = range(32) if coverpoint.endswith("_u") else range(-16, 16)

    # TODO: These should depend on egs
    vl = 1
    lmul = 1

    test_chunks = []
    for imm in imm_vals:
        desc = f"{coverpoint} (Test imm={imm})"
        bin_name = f"imm{imm}"

        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, vl=vl, immval=imm)
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
