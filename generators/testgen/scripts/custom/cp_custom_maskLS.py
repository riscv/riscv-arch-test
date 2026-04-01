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
def make(test, sew):
    # emul_ge_16 — sweep LMUL > 1 with SEW > 8
    if sew > 8:
        eew = _get_eew(test)
        nf = _get_nf(test)
        for lmul in LMULS_GT1:
            # nf × EMUL must not exceed 8 (RISC-V V spec constraint — illegal otherwise)
            if eew is not None:
                emul = eew * lmul // sew
            else:
                emul = lmul
            if emul * nf > 8:
                continue

            description = f"cp_custom_maskLS_emul_ge_16 ({test}, lmul={lmul}, sew={sew})"
            try:
                data = randomizeVectorInstructionData(
                    test, sew, getBaseSuiteTestCount(), lmul=lmul,
                )
            except ValueError:
                continue
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
