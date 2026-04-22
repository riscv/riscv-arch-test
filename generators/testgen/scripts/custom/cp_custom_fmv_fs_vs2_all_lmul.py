# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_fmv_fs_vs2_all_lmul

Confirm vfmv.f.s ignores LMUL for source register.
Template: two independent crosses — std_vec × vs2_all_regs, std_vec × vtype_all_lmul.

Strategy: 32 vs2 values at LMUL=1 (covers vs2_all_regs) +
1 vs2 per additional LMUL (covers vtype_all_lmul). Total ~38 tests.
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


@register("cp_custom_fmv_fs_vs2_all_lmul")
def make(test: str, sew: int) -> None:
    if sew > common.flen:
        return

    # Filter: LMUL must be >= SEW/ELEN for valid vtype (fractional LMUL only supports SEW <= LMUL*ELEN)
    valid_lmuls = [l for l in ALL_LMULS if l >= sew / common.maxELEN]

    for lmul in valid_lmuls:
        # LMUL=1: all 32 regs. Others: just vs2=0 to hit the LMUL bin.
        vs2_values = range(32) if lmul == 1 else [0]
        for vs2 in vs2_values:
            description = f"cp_custom_fmv_fs_vs2_all_lmul (vs2=v{vs2}, lmul={lmul})"
            try:
                data = randomizeVectorInstructionData(
                    test, sew, getBaseSuiteTestCount(),
                    lmul=lmul, vs2=vs2,
                )
            except ValueError:
                continue
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
