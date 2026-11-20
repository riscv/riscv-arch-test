##################################
# cp_csr_vxsat.py
#
# rwolk@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_csr_vxsat")
def make_cp_csr_vxsat(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Coverpoint generator that generates a case where VXSAT is set in cases where it is not satisfied by edge testing.
    """

    if instr_name != "vsmul.vx":
        # Edges reach vxsat for all other tests
        return []

    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks: list[TestChunk] = []
    for sew in sews:
        rs1_val = 1 << (min(test_data.config.xlen, sew) - 1)

        vs2_val_pointer = f"vs2_vxsat_1_case_sew{sew}"
        vs2_elements = [1 << (sew - 1)]
        test_data.register_vector_data(vs2_val_pointer, sew, elements=vs2_elements)

        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=1, sew=sew, rs1val=rs1_val, vs2_val_pointer=vs2_val_pointer
        )

        desc = f"vxsat (sew={sew})"
        bin_name = f"1_sew{sew}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks
