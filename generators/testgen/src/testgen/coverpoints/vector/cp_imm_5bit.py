##################################
# cp_imm_5bit_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instruction_type_config
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_imm_5bit")
def make_imm_5bit(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests covering all values of the 5-bit immediate in a vector instruction.
    """

    imm_vals = range(32) if coverpoint.endswith("_u") else range(-16, 16)

    instr_type_config = get_instruction_type_config(instr_type)
    assert instr_type_config.vector_data is not None, "vector_data must be provided for Vector instruction types"
    vl = instr_type_config.vector_data.egs
    lmul = instr_type_config.vector_data.egs

    test_chunks = []
    for imm in imm_vals:
        desc = f"{coverpoint} (Test imm={imm})"
        bin_name = f"imm{imm}"

        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, vl=vl, immval=imm)
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
