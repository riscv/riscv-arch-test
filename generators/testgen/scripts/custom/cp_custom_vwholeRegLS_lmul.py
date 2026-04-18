# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vwholeRegLS_lmul

Check that whole register loads and stores work at all LMUL >= 1 settings
with vl == VLMAX.

Template cross: std_vec × vl_max × vtype_all_lmulge1
  vl_max: vl == VLMAX
  vtype_all_lmulge1: LMUL in {1, 2, 4, 8}
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

LMULS = [1, 2, 4, 8]


@register("cp_custom_vwholeRegLS_lmul")
def make(test, sew):
    for lmul in LMULS:
        description = f"cp_custom_vwholeRegLS_lmul ({test}, lmul={lmul}, vl=vlmax)"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=lmul,
            )
            writeTest(description, test, data, sew=sew, lmul=lmul, vl="vlmax")
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass
