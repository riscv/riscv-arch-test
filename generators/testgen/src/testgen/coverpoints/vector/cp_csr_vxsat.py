##################################
# cp_csr_vxsat.py
#
# rwolk@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_csr_vxsat")
def make_cp_csr_vxsat(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Coverpoint generator that generates a case where VXSAT is set in cases where it is not satisfied by edge testing.
    """

    if instr_name != "vsmul.vx":
        # Edges reach vxsat for all other tests
        return []

    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    rs1_val = 1 << (min(test_data.config.xlen, test_data.config.sew) - 1)

    vs2_val_pointer = "vs2_vxsat_1_case"
    vs2_elements = [1 << (test_data.config.sew - 1)]
    test_data.register_vector_data(vs2_val_pointer, test_data.config.sew, elements=vs2_elements)

    params = generate_random_vector_params(
        test_data, instr_name, instr_type, lmul=1, rs1val=rs1_val, vs2_val_pointer=vs2_val_pointer
    )

    desc = "vxsat"
    bin_name = "1"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)

    return [tc]
