# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_state

Spec: any vector FP instruction that modifies FP extension state (an f
register or an FP CSR) must set mstatus.FS to Dirty.

This coverpoint only checks the *setup* — that the instruction is exercised
while mstatus.FS is not already Dirty — so a lockstep reference model can
verify the FS=Dirty transition.  The setup sequence clears fflags and sets
mstatus.FS to Clean (10) right before the instruction executes (via
pre_instruction_lines), ensuring that register/vector loads in writeTest
don't re-dirty FS before the test instruction.
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

# Assembly lines to inject immediately before the test instruction.
# These force mstatus.FS = Clean (0b10) so the test instruction dirties it.
_FS_CLEAN_LINES: list[str] = [
    "li x6, 0x6000",                     # mstatus.FS mask (bits 14:13)
    "csrrc x0, mstatus, x6",             # clear FS -> Off
    "li x6, 0x4000",                     # FS=Clean (0b10)
    "csrrs x0, mstatus, x6",             # set FS=Clean
]


@register("cp_custom_vfp_state")
def make(test, sew):
    # V spec 3.4: SEW <= FLEN for FP instructions
    if sew > common.flen:
        return

    description = "cp_custom_vfp_state (FS=Clean pre-instruction)"

    instruction_data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs2_val_pointer="vs_corner_f_pos1_emul1",
    )
    writeTest(description, test, instruction_data,
              sew=sew, lmul=1, vl=1, clear_fflags=False,
              pre_instruction_lines=_FS_CLEAN_LINES)
    incrementBasetestCount()
    vsAddressCount()
