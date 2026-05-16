# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_ls_indexed

Contains 1 cross + basic fallback:
1. cp_custom_ls_indexed_truncated (XLEN32 only): std_vec × sew=64 ×
   vs2[0] with top 32 bits set, bottom 32 bits zero
   - Confirm 64-bit index is truncated to XLEN=32

vs2[0] = 0xFFFFFFFF_00000000 (top-32 ones, bottom-32 zeros).
On XLEN=32 the hardware truncates the 64-bit index to 32 bits, giving a
zero offset (safe memory access).  We reload vs2 from custom data after
sanitization because vmv.s.x can only provide XLEN-wide values.

Negative-index (sew8=0xFF, sew16=0xFFFF) cases were removed: the spec
zero-extends index elements, so a "negative" element would produce a
huge unsigned offset and a bad memory access.  Index sanitization in
loadVecReg now uses vremu.vx so all indices stay in [0, 2*vlmax).
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
    # Part 3: truncated on XLEN32 (VlsCustom64 only)
    if sew == 64 and common.xlen == 32:
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
