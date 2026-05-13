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

For (1) and (2): vs2 holds the index offset into memory.  Coverage reads
vs2 element 0 via get_vr_element_zero which uses the current SEW.  The
loadVecReg sanitization (vand + vrem) clears the MSB, so we override vs2
element 0 *after* sanitization using vmv.v.i in pre_test_lines.

For (3): vs2[0] = 0xFFFFFFFF_00000000 (top-32 ones, bottom-32 zeros).
On XLEN=32 the hardware truncates the 64-bit index to 32 bits, giving a
zero offset (safe memory access).  We reload vs2 from custom data after
sanitization because vmv.s.x can only provide XLEN-wide values.
"""

import vector_testgen_common as common
from coverpoint_registry import register
from vector_testgen_common import (
    getBaseSuiteTestCount,
    incrementBasetestCount,
    randomizeVectorInstructionData,
    registerCustomData,
    vsAddressCount,
    writeTest,
)


def _get_vs2_reg(data: list) -> int:
    """Extract the vs2 register number from randomized instruction data."""
    return int(data[0]["vs2"]["reg"])


def _get_rs1_reg(data: list) -> int:
    """Extract the rs1 register number from randomized instruction data."""
    return int(data[1]["rs1"]["reg"])


@register("cp_custom_ls_indexed")
def make(test: str, sew: int) -> None:
    # Part 1: zero-extended SEW=8 index (VlsCustom8 only)
    if sew == 8:
        description = f"cp_custom_ls_indexed_zero_extended_sew8 ({test}, vs2[0]=0xFF)"
        try:
            data = randomizeVectorInstructionData(
                test,
                sew,
                getBaseSuiteTestCount(),
                lmul=1,
            )
            vs2 = _get_vs2_reg(data)
            # Override vs2[0] to all-1s after loadVecReg sanitization.
            # At SEW=8, vmv.v.i with -1 writes 0xFF to element 0.
            pre_lines = [f"vmv.v.i v{vs2}, -1"]
            writeTest(description, test, data, sew=sew, lmul=1, vl=1, pre_test_lines=pre_lines)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass

    # Part 2: zero-extended SEW=16 index (VlsCustom16 only)
    elif sew == 16:
        description = f"cp_custom_ls_indexed_zero_extended_sew16 ({test}, vs2[0]=0xFFFF)"
        try:
            data = randomizeVectorInstructionData(
                test,
                sew,
                getBaseSuiteTestCount(),
                lmul=1,
            )
            vs2 = _get_vs2_reg(data)
            # At SEW=16, vmv.v.i with -1 writes 0xFFFF to element 0.
            pre_lines = [f"vmv.v.i v{vs2}, -1"]
            writeTest(description, test, data, sew=sew, lmul=1, vl=1, pre_test_lines=pre_lines)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass

    # Part 3: truncated on XLEN32 (VlsCustom64 only)
    elif sew == 64 and common.xlen == 32:
        label = "custom_idx_trunc_sew64"
        # top-32 ones, bottom-32 zeros → truncated to 32 bits → offset 0
        registerCustomData(label, [0xFFFFFFFF00000000], element_size=64)
        description = f"cp_custom_ls_indexed_truncated ({test}, vs2[0] top 32 set)"
        try:
            data = randomizeVectorInstructionData(
                test,
                sew,
                getBaseSuiteTestCount(),
                lmul=1,
                vs2_val_pointer=label,
            )
            vs2 = _get_vs2_reg(data)
            # {s0} is allocated by writeTest (pre_test_scratch_regs=1) — avoids
            # collision with rs1/sigReg, including post-switch sigReg.
            # Reload vs2 from custom data after sanitization.
            pre_lines = [
                f"la x{{s0}}, {label}",
                f"vle64.v v{vs2}, (x{{s0}})",
            ]
            writeTest(description, test, data, sew=sew, lmul=1, vl=1, pre_test_lines=pre_lines, pre_test_scratch_regs=1)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass

    # Part 4: basic test for remaining extensions (VlsCustom32, VlsCustom64 on rv64)
    # to cover cp_asm_count and std_vec bins
    else:
        description = f"cp_custom_ls_indexed_basic ({test}, sew={sew})"
        try:
            data = randomizeVectorInstructionData(
                test,
                sew,
                getBaseSuiteTestCount(),
                lmul=1,
            )
            writeTest(description, test, data, sew=sew, lmul=1, vl=1)
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass
