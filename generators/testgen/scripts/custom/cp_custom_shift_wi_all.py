# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_shift_wi_all

Tests that narrowing shift instructions (vnsrl.wi, vnsra.wi, vnclip.wi,
vnclipu.wi) correctly handle vd overlapping the bottom of vs2 at LMUL 1/2/4.

The CSV column cp_custom_shift_wi_all is expanded by coverpointInclusions() into:
  cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1
  cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2
  cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4

Each cross requires: vd == vs2 (same base register), vs2 properly aligned for
2*LMUL, and the overlap check passes at the given LMUL granularity.
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

# LMUL → alignment for vs2 (= 2*LMUL since narrowing doubles source group).
# vs2 must be aligned to 2*LMUL; vd = vs2 (same base register) for overlap.
# We iterate ALL valid aligned registers to cover every cross bin.
LMUL_ALIGNMENT = {
    1: 2,   # vs2 aligned to 2, 16 valid registers (v0,v2,...,v30)
    2: 4,   # vs2 aligned to 4, 8 valid registers  (v0,v4,...,v28)
    4: 8,   # vs2 aligned to 8, 4 valid registers  (v0,v8,v16,v24)
}


def _make_overlap(test: str, sew: int, lmul: int) -> None:
    """Generate tests for vd/vs2 overlap at the given LMUL, all valid registers."""
    if 2 * lmul > 8:
        return
    align = LMUL_ALIGNMENT[lmul]
    for reg in range(0, 32, align):
        description = f"cp_custom_shift_wi_all ({test}, lmul={lmul}, vd=vs2=v{reg})"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=lmul,
                vd=reg, vs2=reg,
            )
            writeTest(description, test, data, sew=sew, lmul=lmul)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass


@register("cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1")
def make_lmul1(test: str, sew: int) -> None:
    _make_overlap(test, sew, 1)


@register("cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2")
def make_lmul2(test: str, sew: int) -> None:
    _make_overlap(test, sew, 2)


@register("cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4")
def make_lmul4(test: str, sew: int) -> None:
    _make_overlap(test, sew, 4)


# Fallback: if coverpointInclusions() fails to expand (list mutation bug),
# the original name arrives at the REGISTRY dispatch. Generate all 3 LMULs.
@register("cp_custom_shift_wi_all")
def make_all(test: str, sew: int) -> None:
    for lmul in (1, 2, 4):
        _make_overlap(test, sew, lmul)
