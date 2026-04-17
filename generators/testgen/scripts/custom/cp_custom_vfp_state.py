# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_state

Tests vector FP state transitions — fd register changes and vfsqrt flag
setting — both with mstatus.vs previously clean, to verify that the
processor correctly dirties mstatus when FP state changes.

Cross 1: std_vec x fd_changed_value x mstatus_prev_clean
Cross 2: std_vec x vfp_state_vfsqrt_flag_set x mstatus_prev_clean x fp_flags_clear
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


@register("cp_custom_vfp_state")
def make(test, sew):
    # Skip SEW > FLEN: V spec Section 3.4 requires SEW <= FLEN for FP instructions
    if sew > common.flen:
        return

    # vl=1 — hits std_vec (requires vl!=0) and fd_changed_value.
    # Note: mstatus_prev_clean (mstatus.vs==0) cannot be satisfied because
    # VS=Off traps on all vector instructions. See coverage_issues/ for details.
    description = "cp_custom_vfp_state (vl=1, std_vec + fd_changed)"
    instruction_data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs2_val_pointer="vs_corner_f_pos1_emul1",
    )
    writeTest(description, test, instruction_data,
              sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()
