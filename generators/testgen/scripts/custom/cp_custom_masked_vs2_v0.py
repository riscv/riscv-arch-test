# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_masked_v0_operand

Verify correct execution of indexed LS instructions when masked (vm=0)
and vs2 (the index vector) is v0, so v0 serves as both mask and source.

Template cross:
  cp_custom_masked_vs2_v0: std_vec × mask_enabled × vs2=v0 × vd!=v0

Only indexed LS instructions have a real vs2 operand (bits[24:20]).
"""

from coverpoint_registry import register
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    indexed_ls_ins,
    indexed_stores,
)


@register("cp_custom_masked_vs2_v0")
def make(test: str, sew: int) -> None:
    if test not in indexed_ls_ins:
        return

    # For stores, bits[11:7] = vs3; for loads, bits[11:7] = vd.
    # Prevent the data register from being v0 so vd_not_v0 bin can hit.
    if test in indexed_stores:
        no_overlap = [['vs3', 'v0']]
    else:
        no_overlap = [['vd', 'v0']]

    description = f"cp_custom_masked_vs2_v0 ({test}, vs2=v0, masked)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=1,
            vs2=0,
            additional_no_overlap=no_overlap,
        )
        # maskval="ones" fills v0 with all 1s, giving wild index offsets.
        # Override v0[0] to 1 (mask bit 0 = active, index offset = 1).
        pre = [
            "vsetivli x0, 1, e64, m1, tu, mu",
            "vmv.v.i v0, 1",
            f"vsetivli x0, 1, e{sew}, m1, tu, mu",
        ]
        writeTest(
            description, test, data, sew=sew, lmul=1, vl=1,
            maskval="ones", pre_test_lines=pre,
        )
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass  # overlap constraints unsolvable for this instruction/sew combo
