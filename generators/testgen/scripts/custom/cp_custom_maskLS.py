# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_maskLS

Cross: std_vec × lmulgt1 × sewgt8
Sweep LMUL {2,4,8} × SEW {16,32,64} to cover EMUL >= 16 for mask LS.
"""

import re
from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    writeLine,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
)

LMULS_GT1 = [2, 4, 8]


def _get_eew(instruction):
    """Get EEW from instruction name (e.g., vlseg3e64ff.v → 64)."""
    m = re.search(r'e(\d+)', instruction.split('seg')[-1] if 'seg' in instruction else instruction)
    return int(m.group(1)) if m else None

def _get_nf(instruction):
    """Get nfields from segmented instruction name. Returns 1 if not segmented."""
    m = re.search(r'seg(\d+)', instruction)
    return int(m.group(1)) if m else 1


@register("cp_custom_maskLS")
def make(test: str, sew: int) -> None:
    # For VlsCustom8: generate at sew=8 (to cover lmul/asm_count bins under sample guard)
    # plus higher SEWs (for cross bins in other extensions).
    # For VlsCustom16/32/64: generate at the matching sew only.
    sew_values = [8, 16, 32, 64] if sew == 8 else [sew]
    eew = _get_eew(test)
    nf = _get_nf(test)
    for test_sew in sew_values:
        for lmul in LMULS_GT1:
            if eew is not None:
                emul = eew * lmul // test_sew
            else:
                emul = lmul
            if emul * nf > 8:
                continue

            description = f"cp_custom_maskLS ({test}, lmul={lmul}, sew={test_sew})"
            try:
                data = randomizeVectorInstructionData(
                    test, test_sew, getBaseSuiteTestCount(), lmul=lmul,
                )
            except ValueError:
                continue
            writeLine("#ifdef RVMODEL_ACCESS_FAULT_ADDRESS")
            writeTest(description, test, data, sew=test_sew, lmul=lmul, vl="vlmax")
            writeLine("#endif")
            incrementBasetestCount()
            vsAddressCount()
