##################################
# cp_custom_vindex.py
#
# Tests for gather/index instruction edge cases (vrgather, vrgatherei16).
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import VX_CORNER_NAMES, get_corner_value
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_vindexedges_index_ge_vlmax")
def make_vindex_ge_vlmax(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test gather with index >= VLMAX: all elements of vd should be 0."""
    sew = test_data.config.sew
    assert sew is not None

    # -1 as an unsigned SEW-wide value is the maximum index, always >= VLMAX.
    label = f"vs1_index_allones_sew{sew}"
    if label not in test_data.vector_labels:
        element_count = test_data.config.vlen_max // sew
        test_data.register_vector_data(label, sew, elements=[(1 << sew) - 1] * element_count)

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
    """Test gather with index > VL but < VLMAX: element is 0 at positions beyond VL."""
    sew = test_data.config.sew
    assert sew is not None

    # Index value 2, with lmul=2: at small VL values (< 2) this index is
    # beyond active elements but still within VLMAX.
    label = f"vs1_index_two_sew{sew}"
    if label not in test_data.vector_labels:
        element_count = test_data.config.vlen_max // sew
        test_data.register_vector_data(label, sew, elements=[2] * element_count)

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=2,
        suite="length",
        vs1_val_pointer=label,
    )

    desc = "cp_custom_vindexedges_index_gt_vl_lt_vlmax (vs1=2, lmul=2: index > VL < VLMAX)"
    bin_name = "cp_custom_vindexedges_index_gt_vl_lt_vlmax"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_vindexCorners")
def make_vindex_corners(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test gather with corner-case index values covering boundary indices."""
    sew = test_data.config.sew
    assert sew is not None

    # Corner index values to test: a subset of VX_CORNER_NAMES interpreted as
    # gather indices.  "random" is excluded since the regular cp_vs1_edges
    # already exercises arbitrary values.
    corners = [c for c in VX_CORNER_NAMES if c != "random"]

    test_chunks = []
    for corner in corners:
        label = f"vs1_vindex_corner_{corner}_sew{sew}"
        if label not in test_data.vector_labels:
            element_count = test_data.config.vlen_max // sew
            val = get_corner_value(corner, "emul1", sew)
            test_data.register_vector_data(label, sew, elements=[val] * element_count)

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=1,
            suite="length",
            vs1_val_pointer=label,
        )

        desc = f"cp_custom_vindexCorners (vs1 index corner = {corner})"
        bin_name = f"cp_custom_vindexCorners_{corner}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
