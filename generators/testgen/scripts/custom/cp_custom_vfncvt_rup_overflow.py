# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfncvt_rup_overflow

Confirm overflow is recognized when narrowing with round-up mode (frm=RUP).
With SEW=32, source is 64-bit and dest is 32-bit single-precision.

Cross: std_vec x vtype_sew_32 x frm_rup x fflags_of

Only float-to-float narrowing (vfncvt.f.f.w, vfncvt.rod.f.f.w) can actually
produce fflags.OF with SEW=32, because:
- int64 max (~9.2e18) < float32 max (~3.4e38), so int-to-float can't overflow
- float-to-int overflow sets NV (invalid), not OF
Tests are generated for all instructions but coverage will only hit for
float-to-float variants.
"""

from coverpoint_registry import register
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    registerCustomData,
)

# 64-bit double values that exceed float32 max range (~3.4028235e38)
# These match the pattern from cp_custom_vfncvt_rod_overflow template:
#   pos_overflow: [64'h47F0000000000000 : 64'h7FEFFFFFFFFFFFFF]
#   neg_overflow: [64'hC7F0000000000000 : 64'hFFEFFFFFFFFFFFFF]
POS_OVERFLOW_F64 = 0x47F0000000000000  # ~3.50e+38 (just above float32 max)
NEG_OVERFLOW_F64 = 0xC7F0000000000000  # ~-3.50e+38

# Large 64-bit integer (won't overflow float32 but generates a test)
LARGE_INT64 = 0x0000000100000000  # 2^32

# Large float64 exceeding int32/uint32 range (for float-to-int instructions)
LARGE_FLOAT_FOR_INT = 0x41F0000000000000  # 2^32 as double

FLOAT_TO_FLOAT = {"vfncvt.f.f.w", "vfncvt.rod.f.f.w"}
INT_TO_FLOAT = {"vfncvt.f.x.w", "vfncvt.f.xu.w"}
FLOAT_TO_INT = {"vfncvt.xu.f.w", "vfncvt.x.f.w", "vfncvt.rtz.xu.f.w", "vfncvt.rtz.x.f.w"}

# Register custom data labels for 64-bit values that can't use vmv.v.x
DATA_LABELS = {
    "custom_pos_overflow_f64": POS_OVERFLOW_F64,
    "custom_neg_overflow_f64": NEG_OVERFLOW_F64,
    "custom_large_int64": LARGE_INT64,
    "custom_large_float_for_int": LARGE_FLOAT_FOR_INT,
}


@register("cp_custom_vfncvt_rup_overflow")
def make(test, sew):
    if sew != 32:
        return

    # Register all custom data labels so they appear in .data section
    for label, val in DATA_LABELS.items():
        registerCustomData(label, [val], element_size=64)

    if test in FLOAT_TO_FLOAT:
        # Source is 64-bit double; use value exceeding float32 range
        values = [
            ("custom_pos_overflow_f64", "positive overflow"),
            ("custom_neg_overflow_f64", "negative overflow"),
        ]
    elif test in INT_TO_FLOAT:
        # Source is 64-bit integer; can't truly overflow float32 but test anyway
        values = [("custom_large_int64", "large integer")]
    elif test in FLOAT_TO_INT:
        # Source is 64-bit double, dest is 32-bit integer; overflow sets NV not OF
        values = [("custom_large_float_for_int", "large float for int overflow")]
    else:
        return

    for label, desc in values:
        description = f"cp_custom_vfncvt_rup_overflow ({test}, {desc}, frm=RUP)"
        instruction_data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(
            description, test, instruction_data,
            sew=sew, lmul=1, vl=1, frm="rup",
        )
        incrementBasetestCount()
        vsAddressCount()
