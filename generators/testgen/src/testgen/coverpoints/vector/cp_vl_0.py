##################################
# cp_vl_0.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vl_0")
def make_vl_0(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate length-suite tests where vl = 0.
    """

    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks = []
    for sew in sews:
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            get_base_lmul(instr_name, instr_type, sew),
            sew,
            suite="length",
            vl=0,
        )

        desc = f"cp_vl_0 (Test vl = 0, sew={sew})"
        bin_name = f"cp_vl_0_sew{sew}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks
