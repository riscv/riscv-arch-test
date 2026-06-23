##################################
# cp_masking_edges.py
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


@add_coverpoint_generator("cp_masking_edges")
def make_mask_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    cp_masking_edges_data = ["ones", "zeros", "vlmaxm1_ones", "vlmaxd2p1_ones", "cp_mask_random"]
    test_data.register_vector_data("cp_mask_random", test_data.config.sew, random_elements=1)

    test_chunks = []
    for m in cp_masking_edges_data:
        vma = random.randint(0, 1)
        vta = random.randint(0, 1)

        desc = f"cp_masking_edges (Test v0 = {m})"
        bin_name = f"cp_masking_edges_maskval_{m}"

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            1,
            suite="length",
            masked=True,
            additional_no_overlap={("vs1", "v0"), ("vs2", "v0"), ("vd", "v0"), ("vs3", "v0")},
            maskval=m,
            vl="vlmax",
            ma=vma,
            ta=vta,
        )
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
