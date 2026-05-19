# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecipEst_edges

Confirm all possible 7-bit significand inputs to vfrec7.v produce correct
results. The template bins on the 7 MSBs of the significand field of vs2[0].
We iterate all 128 combinations (0..127) embedded in a positive normal value.

Bit positions per SEW:
  SEW16: bits [9:3]
  SEW32: bits [22:16]
  SEW64: bits [51:45]
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


def _make_value(sew, sig_7bit):
    """Build a positive normal FP value with the given 7-bit significand MSBs."""
    if sew == 16:
        # half: sign(1) exp(5) sig(10), normal exp=1 (biased=16)
        # bits[9:3] = sig_7bit
        return (0b0_10000 << 10) | (sig_7bit << 3)
    elif sew == 32:
        # float: sign(1) exp(8) sig(23), normal exp=1 (biased=128)
        # bits[22:16] = sig_7bit
        return (0b0_10000000 << 23) | (sig_7bit << 16)
    elif sew == 64:
        # double: sign(1) exp(11) sig(52), normal exp=1 (biased=1024)
        # bits[51:45] = sig_7bit
        return (0b0_10000000000 << 52) | (sig_7bit << 45)
    return 0


@register("cp_custom_FpRecipEst_edges")
def make(test, sew):
    if sew > common.flen:
        return

    for i in range(128):
        val = _make_value(sew, i)
        label = f"custom_recip_sig_{i:03d}_sew{sew}"
        registerCustomData(label, [val], element_size=sew)
        description = f"cp_custom_FpRecipEst_edges (sig={i:03d})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
