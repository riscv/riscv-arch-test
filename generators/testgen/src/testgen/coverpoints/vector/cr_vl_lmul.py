##################################
# cr_vl_lmul.py
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


@add_coverpoint_generator("cr_vl_lmul")
def make_vl_lmul(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    lmul_exponents = list(range(4))  # lmul 1, 2, 4, 8
    if sew >= 16:
        lmul_exponents.insert(0, -1)  # mf2
    if sew >= 32:
        lmul_exponents.insert(0, -2)  # mf4
    if sew >= 64:
        lmul_exponents.insert(0, -3)  # mf8

    vl_options = ["vlmax", 1, "random"]

    test_chunks = []
    for l in lmul_exponents:
        lmul = 2.0**l
        for vl in vl_options:
            vta = random.randint(0, 1)
            vma = random.randint(0, 1)
            masked = random.random() < 0.5
            maskval = "vlmaxm1_ones" if masked else None
            no_overlap = _NO_OVERLAP_MASKED if masked else None

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul,
                suite="length",
                masked=masked,
                additional_no_overlap=no_overlap,
                maskval=maskval,
                vl=vl,
                ta=vta,
                ma=vma,
            )

            desc = f"cr_vl_lmul (Test lmul = {lmul}, vl = {vl})"
            bin_name = f"cp_vl_lmul_vl_{vl}_lmul_{lmul}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks
