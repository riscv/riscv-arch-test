# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_ffLS_update_vl

Confirm fault-only-first loads update VL when a fault occurs on a non-first
element.

Template cross: std_vec × vtype_lmul_2 × vl_max × mask_enabled ×
                v0_eq_1 × rs1_at_fault_addr

This requires:
- LMUL=2, vl=VLMAX
- Masking enabled (vm=0) with v0=1 (first element active)
- rs1 pointing to the fault address boundary

NOTE: rs1_at_fault_addr requires RVMODEL_ACCESS_FAULT_ADDRESS which is
DUT-specific. The framework's writeTest sets rs1 as a load base address
pointing to valid memory. For this coverpoint to work, the DUT's
model_test.h must define RVMODEL_ACCESS_FAULT_ADDRESS and we need rs1
set near that boundary. We generate basic structure tests; full fault
testing may need manual tuning.
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


def _get_eew(instruction):
    """Get EEW from instruction name (e.g., vlseg3e64ff.v → 64)."""
    m = re.search(r'e(\d+)', instruction.split('seg')[-1] if 'seg' in instruction else instruction)
    return int(m.group(1)) if m else None

def _get_nf(instruction):
    """Get nfields from segmented instruction name. Returns 1 if not segmented."""
    m = re.search(r'seg(\d+)', instruction)
    return int(m.group(1)) if m else 1


@register("cp_custom_ffLS_update_vl")
def make(test, sew):
    lmul = 2

    # nf × EMUL must not exceed 8 (RISC-V V spec constraint — illegal otherwise)
    eew = _get_eew(test)
    if eew is not None:
        emul = eew * lmul // sew
    else:
        emul = lmul
    nf = _get_nf(test)
    if emul * nf > 8:
        return

    # Generate with LMUL=2 and vl=vlmax, masked with v0=1 pattern
    description = f"cp_custom_ffLS_update_vl ({test}, lmul=2, vl=vlmax, masked)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=lmul,
            additional_no_overlap=[['vd', 'v0']],
        )
        writeTest(description, test, data, sew=sew, lmul=lmul, vl="vlmax", maskval="ones")
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass  # overlap constraints unsolvable for segmented instructions
