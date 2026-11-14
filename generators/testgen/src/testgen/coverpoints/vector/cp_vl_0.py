##################################
# cp_vl_0.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vl_0")
def make_vl_0(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate length-suite tests where vl = 0.
    """

    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    # An element-group instruction needs LMUL * VLEN >= EGW = EGS * SEW even when vl = 0. LMUL = EGS
    # meets that at every legal VLEN (VLEN >= SEW), so the case is never skipped for a small VLEN.
    vector_data = get_instruction_type_config(instr_type).vector_data
    assert vector_data is not None
    lmul = vector_data.egs if vector_data.egs > 1 else get_base_lmul(instr_name, instr_type, test_data.config.sew)

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=lmul,
        suite="length",
        vl=0,
    )

    desc = "cp_vl_0 (Test vl = 0)"
    bin_name = "cp_vl_0"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

    return_testcase_registers(test_data, params)
    return [tc]
