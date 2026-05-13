# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vreductionw

Tests that widening reduction operations with LMUL=8 do not trap.
Since 2*8=16 >= 16 would normally be an undefined EMUL, but the widened
elements are treated as scalar values so it should not trap.
"""

from __future__ import annotations

from coverpoint_registry import register
from vector_testgen_common import (
    getBaseSuiteTestCount,
    incrementBasetestCount,
    randomizeVectorInstructionData,
    vsAddressCount,
    writeTest,
)


@register("cp_custom_vreductionw")
def make(test: str, sew: int) -> None:
    lmul = 8
    description = f"cp_custom_vreductionw_vd_vs1_emul_16 ({test}, lmul={lmul})"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=lmul,
        )
        writeTest(description, test, data, sew=sew, lmul=lmul)
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass
