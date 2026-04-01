# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecSqrtEst_edges

Confirm all possible 7-bit significand inputs to vfrsqrt7.v produce correct
results. The template bins on the 7 MSBs of the significand field of vs2[0].
We iterate all 128 combinations (0..127) embedded in a positive normal value.

Bit positions per SEW:
  SEW16: bits [10:4]
  SEW32: bits [23:17]
  SEW64: bits [52:46]
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


def _make_value(sew, lookup_7bit):
    """Build a positive normal FP value that puts lookup_7bit into the
    coverpoint extraction field (exponent LSB + top 6 mantissa bits).

    The coverpoint extracts bits[10:4] (SEW16), [23:17] (SEW32), [52:46] (SEW64).
    These span the exponent LSB and the 6 MSBs of the significand — the
    7-bit lookup key for vfrsqrt7.

    lookup_7bit[6] = exponent LSB → pick even or odd biased exponent.
    lookup_7bit[5:0] = top 6 mantissa bits.
    """
    exp_lsb = (lookup_7bit >> 6) & 1
    mant_top6 = lookup_7bit & 0x3F
    if sew == 16:
        # half: sign(1) exp(5) sig(10)
        # Use biased exp 16 (0b10000) for exp_lsb=0, 17 (0b10001) for exp_lsb=1
        exp = 0b10000 | exp_lsb
        return (exp << 10) | (mant_top6 << 4)
    elif sew == 32:
        # float: sign(1) exp(8) sig(23)
        exp = 0b10000000 | exp_lsb
        return (exp << 23) | (mant_top6 << 17)
    elif sew == 64:
        # double: sign(1) exp(11) sig(52)
        exp = 0b10000000000 | exp_lsb
        return (exp << 52) | (mant_top6 << 46)
    return 0


@register("cp_custom_FpRecSqrtEst_edges")
def make(test, sew):
    if sew > common.flen:
        return

    for i in range(128):
        val = _make_value(sew, i)
        label = f"custom_rsqrt_sig_{i:03d}_sew{sew}"
        registerCustomData(label, [val], element_size=sew)
        description = f"cp_custom_FpRecSqrtEst_edges (sig={i:03d})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
