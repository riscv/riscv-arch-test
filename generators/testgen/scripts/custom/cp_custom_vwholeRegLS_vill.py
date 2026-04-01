# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vwholeRegLS_vill

Check that whole register loads and stores are not affected by the vill bit.
Template: single coverpoint checking vill==1 AND vstart==0 AND no trap.

Strategy: Two-test approach.
1. First test with valid vtype (sew=8, lmul=1) loads data into registers
   and sets up rs1 with a valid memory address.
2. Second test uses an unsupported SEW/LMUL combo (sew=64, lmul=0.125)
   which sets vill=1. The whole register LS instruction should still
   execute without trapping because it ignores vtype.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
)


@register("cp_custom_vwholeRegLS_vill")
def make(test, sew):
    # Test 1: Normal test with valid vtype to set up memory address in rs1
    description = f"cp_custom_vwholeRegLS_vill setup ({test}, valid vtype)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=1,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass

    # Test 2: Use unsupported SEW/LMUL to set vill=1
    # sew=64, lmul=0.125 → SEW/LMUL = 512 > VLEN, sets vill=1
    # Whole register LS ignores vtype, so should not trap
    description = f"cp_custom_vwholeRegLS_vill ({test}, vill=1 via sew=64/lmul=mf8)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=1,
        )
        writeTest(description, test, data, sew=64, lmul=0.125, vl=0)
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass
