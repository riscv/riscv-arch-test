##################################
# cp_masking_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.asm.helpers import return_test_regs
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import get_base_lmul
from testgen.data.params import PresetMask
from testgen.data.random import random_range
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_masking_edges")
def make_mask_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate length suite tests with edge values in the mask register. Edges include zeros, ones, VLMAX-1 Ones,
    VLMAX/2 + 1 Ones, and a random mask
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    cp_masking_edges_data = [
        PresetMask.ONES,
        PresetMask.ZEROS,
        PresetMask.VLMAX_M1_ONES,
        PresetMask.VLMAX_D2_P1_ONES,
        "cp_mask_random",
    ]
    test_data.register_vector_data(
        "cp_mask_random", test_data.config.sew, random_elements=VLEN_MAX // test_data.config.sew
    )

    test_chunks = []
    lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)

    for m in cp_masking_edges_data:
        vma = random_range(0, 1)
        vta = random_range(0, 1)

        desc = f"cp_masking_edges (Test v0 = {m})"
        bin_name = f"cp_masking_edges_maskval_{m}"

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul,
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
