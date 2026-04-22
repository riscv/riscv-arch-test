# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vindexCorners

Tests two corner cases for vrgather-type instructions:
1. index >= vlmax → element should be zero
2. index > vl but < vlmax → element value should still be returned

Applies to .vv instructions (vrgather.vv, vrgatherei16.vv).
"""

from __future__ import annotations

from coverpoint_registry import register
from vector_testgen_common import (
    getLengthSuiteTestCount,
    incrementLengthtestCount,
    randomizeVectorInstructionData,
    vsAddressCount,
    writeTest,
)


@register("cp_custom_vindexCorners")
def make(test: str, sew: int) -> None:
    # Test 1: index >= vlmax (set vs1 to all-ones)
    description = f"cp_custom_vindexCorners_index_ge_vlmax ({test})"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getLengthSuiteTestCount(),
            suite="length", vs1_val=-1,
        )
        writeTest(description, test, data, sew=sew, suite="length")
        incrementLengthtestCount()
        vsAddressCount("length")
    except ValueError:
        pass

    # Test 2: index > vl < vlmax (set vs1 element 0 to 2, lmul=2, vl=1)
    description = f"cp_custom_vindexCorners_index_gt_vl_lt_vlmax ({test})"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getLengthSuiteTestCount(),
            suite="length", lmul=2, vs1_val=2,
        )
        writeTest(description, test, data, sew=sew, lmul=2, vl=1, suite="length")
        incrementLengthtestCount()
        vsAddressCount("length")
    except ValueError:
        pass
