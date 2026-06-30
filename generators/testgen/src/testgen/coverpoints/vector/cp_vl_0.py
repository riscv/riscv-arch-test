##################################
# cp_vl_0.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import get_base_lmul
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vl_0")
def make_vl_0(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate length-suite tests where vl = 0.
    """

    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=get_base_lmul(instr_name, instr_type, test_data.config.sew),
        suite="length",
        vl=0,
    )

    desc = "cp_vl_0 (Test vl = 0)"
    bin_name = "cp_vl_0"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

    return_test_regs(test_data, params)
    return [tc]
