# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_ls_indexed

Contains 3 crosses:
1. cp_custom_ls_indexed_zero_extended_sew8: std_vec × vs2[0]=0xFF × sew=8
   - Confirm indexed instructions zero-extend (not sign-extend) 8-bit index
2. cp_custom_ls_indexed_zero_extended_sew16: std_vec × vs2[0]=0xFFFF × sew=16
   - Same for 16-bit index
3. cp_custom_ls_indexed_truncated (XLEN32 only): std_vec × sew=64 ×
   vs2[0] with top 32 bits set, bottom 32 bits zero
   - Confirm 64-bit index is truncated to XLEN=32

For (1) and (2): vs2 holds the index offset into memory. We need
vs2[0] = 0xFF or 0xFFFF (all ones in the EEW field).
For (3): vs2[0] = 0xFFFF0000_00000000 to show top bits are truncated.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    registerCustomData,
)


@register("cp_custom_ls_indexed")
def make(test, sew):
    # Part 1: zero-extended SEW=8 index
    if sew == 8:
        label = "custom_idx_ff_sew8"
        registerCustomData(label, [0xFF], element_size=8)
        description = f"cp_custom_ls_indexed_zero_extended_sew8 ({test}, vs2[0]=0xFF)"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=1,
                vs2_val_pointer=label,
            )
            writeTest(description, test, data, sew=sew, lmul=1, vl=1)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass

    # Part 2: zero-extended SEW=16 index
    if sew == 16:
        label = "custom_idx_ffff_sew16"
        registerCustomData(label, [0xFFFF], element_size=16)
        description = f"cp_custom_ls_indexed_zero_extended_sew16 ({test}, vs2[0]=0xFFFF)"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=1,
                vs2_val_pointer=label,
            )
            writeTest(description, test, data, sew=sew, lmul=1, vl=1)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass

    # Part 3: truncated on XLEN32 — sew=64, top bits set
    # Only meaningful on RV32 where XLEN=32
    if sew == 64 and common.xlen == 32:
        label = "custom_idx_trunc_sew64"
        registerCustomData(label, [0xFFFF000000000000], element_size=64)
        description = f"cp_custom_ls_indexed_truncated ({test}, vs2[0] top 32 set)"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=1,
                vs2_val_pointer=label,
            )
            writeTest(description, test, data, sew=sew, lmul=1, vl=1)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass
