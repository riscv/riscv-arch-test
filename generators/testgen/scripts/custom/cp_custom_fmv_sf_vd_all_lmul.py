# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_fmv_sf_vd_all_lmul

Confirm vfmv.s.f ignores LMUL for destination register.
Template: two independent crosses — std_vec × vd_all_regs, std_vec × vtype_all_lmul.

Strategy: 32 vd values at LMUL=1 (covers vd_all_regs) +
1 test per additional LMUL (covers vtype_all_lmul). Total ~38 tests.
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

ALL_LMULS: list[float] = [0.125, 0.25, 0.5, 1, 2, 4, 8]


@register("cp_custom_fmv_sf_vd_all_lmul")
def make(test: str, sew: int) -> None:
    if sew > common.flen:
        return

    valid_lmuls = [l for l in ALL_LMULS if l >= sew / common.maxELEN]

    for lmul in valid_lmuls:
        # LMUL=1: all 32 regs (covers vd_all_regs cross). Others: just vd=0 (covers LMUL cross).
        vd_values = range(32) if lmul == 1 else [0]
        for vd in vd_values:
            description = f"cp_custom_fmv_sf_vd_all_lmul (vd=v{vd}, lmul={lmul})"
            try:
                data = randomizeVectorInstructionData(
                    test, sew, getBaseSuiteTestCount(),
                    lmul=lmul, vd=vd,
                )
            except ValueError:
                continue
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
