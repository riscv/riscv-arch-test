##################################
# cr_vtype_agnostic.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import random

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params

_NO_OVERLAP_MASKED = {("vs1", "v0"), ("vs2", "v0"), ("vd", "v0"), ("vs3", "v0")}


@add_coverpoint_generator("cr_vtype_agnostic")
def make_vtype_agnostic(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    lmul_exponents = list(range(4))
    if sew >= 16:
        lmul_exponents.insert(0, -1)
    if sew >= 32:
        lmul_exponents.insert(0, -2)
    if sew >= 64:
        lmul_exponents.insert(0, -3)

    test_chunks = []
    for vta in [0, 1]:
        for vma in [0, 1]:
            lmul = 2.0 ** random.choice(lmul_exponents)

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul,
                suite="length",
                masked=True,
                additional_no_overlap=_NO_OVERLAP_MASKED,
                maskval="vlmaxm1_ones",
                vl="random",
                ta=vta,
                ma=vma,
            )

            desc = f"cr_vtype_agnostic (Test vta = {vta}, vma = {vma})"
            bin_name = f"cp_vtype_agnostic_vta_{vta}_vma_{vma}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks
