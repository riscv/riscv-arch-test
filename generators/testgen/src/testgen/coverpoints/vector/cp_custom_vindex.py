##################################
# cp_custom_vindex.py
#
# Tests for gather/index instruction edge cases (vrgather, vrgatherei16).
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_vindexedges_index_ge_vlmax")
def make_vindex_ge_vlmax(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a test for gather instruction with index >= VLMAX. The result should be all elements of vd equal to 0.
    """
    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    # -1 as an unsigned SEW-wide value is the maximum index, always >= VLMAX.
    label = f"vs1_index_allones_sew{sew}"
    if label not in test_data.vector_labels:
        element_count = VLEN_MAX // sew
        elements = [(1 << sew) - 1 for _ in range(element_count)]
        test_data.register_vector_data(label, sew, elements=elements)

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        suite="length",
        vs1_val_pointer=label,
    )

    desc = "cp_custom_vindexedges_index_ge_vlmax (vs1 all-ones: index always >= VLMAX)"
    bin_name = "cp_custom_vindexedges_index_ge_vlmax"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_vindexedges_index_gt_vl_lt_vlmax")
def make_vindex_gt_vl_lt_vlmax(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate test of gather instruction with index > VL but < VLMAX. These elements should be read regardless of vl
    """
    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    # Index value 2, with lmul=2: at small VL values (< 2) this index is
    # beyond active elements but still within VLMAX.
    label = f"vs1_index_two_sew{sew}"
    if label not in test_data.vector_labels:
        element_count = VLEN_MAX // sew
        elements = [2 for _ in range(element_count)]
        test_data.register_vector_data(label, sew, elements=elements)

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=2,
        suite="length",
        vs1_val_pointer=label,
        vl=1,
    )

    desc = "cp_custom_vindexedges_index_gt_vl_lt_vlmax (vs1=2, lmul=2: index > VL < VLMAX)"
    bin_name = "cp_custom_vindexedges_index_gt_vl_lt_vlmax"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_vindexCorners")
def make_vindex_corners(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Aggregator coverpoint containing vindex_ge_vlmax and vindex_gt_vl_lt_vlmax
    """

    return [
        *make_vindex_ge_vlmax(instr_name, instr_type, coverpoint, test_data),
        *make_vindex_gt_vl_lt_vlmax(instr_name, instr_type, coverpoint, test_data),
    ]
