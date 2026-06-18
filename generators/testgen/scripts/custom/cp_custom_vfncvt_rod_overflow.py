# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfncvt_rod_overflow

Verify that vfncvt.rod.f.f.w correctly saturates to the destination format's
largest finite value (not infinity) when the source exceeds the dest range.

Template cross: std_vec × rod_vtype_sew_32 × rod_vs2_exceeds_f32_range
  - SEW=32 only (narrowing: 64-bit double → 32-bit float)
  - vs2[0] must be a finite double exceeding float32 max range
  - Two bins: pos_overflow and neg_overflow
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

# 64-bit double values exceeding float32 max (~3.4028235e38)
POS_OVERFLOW_F64 = 0x47F0000000000000  # ~3.50e+38
NEG_OVERFLOW_F64 = 0xC7F0000000000000  # ~-3.50e+38


@register("cp_custom_vfncvt_rod_overflow")
def make(test, sew):
    # Only SEW=32 (destination is 32-bit, source is 64-bit)
    if sew != 32:
        return

    values = [
        (POS_OVERFLOW_F64, "positive_overflow"),
        (NEG_OVERFLOW_F64, "negative_overflow"),
    ]

    for val, desc in values:
        label = f"custom_rod_overflow_{desc}"
        registerCustomData(label, [val], element_size=64)
        description = f"cp_custom_vfncvt_rod_overflow ({desc})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
