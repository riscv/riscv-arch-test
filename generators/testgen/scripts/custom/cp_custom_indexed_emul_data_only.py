# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_indexed_emul_data_only

Verify EMUL*NFIELDS <= 8 constraint applies to data register group only.
Test at LMUL*NFIELDS = 8 boundary.

Template has 3 crosses:
- cp_custom_indexed_emul_data_only_lmul1_nf8: LMUL=1, NF=8 (nf field=7)
- cp_custom_indexed_emul_data_only_lmul2_nf4: LMUL=2, NF=4 (nf field=3)
- cp_custom_indexed_emul_data_only_lmul4_nf2: LMUL=4, NF=2 (nf field=1)

The nf field is encoded in the instruction bits [31:29].
Segmented indexed instructions have names like vluxseg2ei8.v where the
segment count is in the name. We need to match the right instruction
to the right LMUL.
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

import re

def _get_nfields(instruction):
    """Extract NFIELDS from segmented instruction name (e.g., vluxseg4ei8.v → 4)."""
    m = re.search(r'seg(\d+)', instruction)
    return int(m.group(1)) if m else 1


@register("cp_custom_indexed_emul_data_only")
def make(test, sew):
    nf = _get_nfields(test)

    # Test each LMUL*NFIELDS = 8 boundary case
    targets = {8: 1, 4: 2, 2: 4}  # nf → lmul

    if nf in targets:
        lmul = targets[nf]
        description = f"cp_custom_indexed_emul_data_only ({test}, lmul={lmul}, nf={nf})"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=lmul,
            )
            writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass  # overlap constraints unsolvable for this instruction/sew/lmul combo
