# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfredosum_ordered_sum

Confirm correct order of summation by vfredosum.vs.
Template cross: std_vec × vl_ge_2 × vs1_0_maxNorm × vs2_0_neg_maxNorm × vtype_lmul_2

This tests ordered cancellation: (maxNorm + (-maxNorm)) + small = small (not 0).
vs1[0] = maxNorm (initial accumulator), vs2[0] = -maxNorm, vs2[1] = small.
With ordered sum: maxNorm + (-maxNorm) = 0, then 0 + small = small.
If unordered, could get catastrophic cancellation.

Needs: vl >= 2, lmul=2 (vlmul encoding = 1).
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    registerCustomData,
)

MAX_NORM = {
    16: 0x7BFF,
    32: 0x7F7FFFFF,
    64: 0x7FEFFFFFFFFFFFFF,
}

NEG_MAX_NORM = {
    16: 0xFBFF,
    32: 0xFF7FFFFF,
    64: 0xFFEFFFFFFFFFFFFF,
}


@register("cp_custom_vfredosum_ordered_sum")
def make(test, sew):
    if sew > common.flen:
        return

    max_val = MAX_NORM.get(sew)
    neg_max = NEG_MAX_NORM.get(sew)
    if max_val is None:
        return

    # vs1[0] = maxNorm (scalar accumulator element)
    label_vs1 = f"custom_redosum_maxnorm_sew{sew}"
    registerCustomData(label_vs1, [max_val], element_size=sew)

    # vs2[0] = -maxNorm (first element to add)
    label_vs2 = f"custom_redosum_negmaxnorm_sew{sew}"
    registerCustomData(label_vs2, [neg_max], element_size=sew)

    description = "cp_custom_vfredosum_ordered_sum (maxNorm + (-maxNorm) + small)"
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=2, vs1_val_pointer=label_vs1, vs2_val_pointer=label_vs2,
    )
    # vl >= 2, lmul=2 (vlmul encoding = 1 in vtype)
    writeTest(description, test, data, sew=sew, lmul=2, vl=2)
    incrementBasetestCount()
    vsAddressCount()
