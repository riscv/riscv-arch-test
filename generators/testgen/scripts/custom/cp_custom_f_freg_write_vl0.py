# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_f_freg_write_vl0

Confirm that f-reg writing instructions (vfmv.f.s) successfully write
even when vl=0. Per the RISC-V V spec, instructions that write an x or f
register do so even when vstart >= vl, including when vl=0.

Bins: 1 — just need to show fd changes with vl=0.
Cross: std_vec x fd_changed_value x mstatus_prev_clean
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

    # Test 1: vl=0 — per spec, vfmv.f.s writes fd even when vl=0.
    # This is the primary goal of cp_custom_f_freg_write_vl0.
    description = "cp_custom_f_freg_write_vl0 (vl=0, fd should still be written)"
    instruction_data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs2_val_pointer="vs_corner_f_pos1_emul1",
    )
    writeTest(description, test, instruction_data,
              sew=sew, lmul=1, vl=0)
    incrementBasetestCount()
    vsAddressCount()

    # Test 2: vl=1 — hits std_vec (requires vl!=0) and fd_changed_value.
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
