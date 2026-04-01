# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfclass_onehot

Confirm all 10 classify cases are correctly handled by vfclass.v.
The template checks that vd[0] (stored in vs1_val since vfclass is VVM
with result in vd) equals each of the 10 one-hot bit patterns.

The 10 classes (RISC-V spec Table):
  bit 0: -inf
  bit 1: -normal
  bit 2: -subnormal
  bit 3: -0
  bit 4: +0
  bit 5: +subnormal
  bit 6: +normal
  bit 7: +inf
  bit 8: sNaN
  bit 9: qNaN

We provide vs2 inputs that produce each classification.
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

# Input values per SEW that produce each of the 10 vfclass results
CLASSIFY_INPUTS = {
    16: [
        (0xFC00, "neg_inf"),       # bit 0
        (0xBC00, "neg_normal"),    # bit 1
        (0x8001, "neg_subnormal"), # bit 2
        (0x8000, "neg_zero"),      # bit 3
        (0x0000, "pos_zero"),      # bit 4
        (0x0001, "pos_subnormal"), # bit 5
        (0x3C00, "pos_normal"),    # bit 6
        (0x7C00, "pos_inf"),       # bit 7
        (0x7D01, "sNaN"),          # bit 8
        (0x7E00, "qNaN"),          # bit 9
    ],
    32: [
        (0xFF800000, "neg_inf"),
        (0xBF800000, "neg_normal"),
        (0x80000001, "neg_subnormal"),
        (0x80000000, "neg_zero"),
        (0x00000000, "pos_zero"),
        (0x00000001, "pos_subnormal"),
        (0x3F800000, "pos_normal"),
        (0x7F800000, "pos_inf"),
        (0x7F800001, "sNaN"),
        (0x7FC00000, "qNaN"),
    ],
    64: [
        (0xFFF0000000000000, "neg_inf"),
        (0xBFF0000000000000, "neg_normal"),
        (0x8000000000000001, "neg_subnormal"),
        (0x8000000000000000, "neg_zero"),
        (0x0000000000000000, "pos_zero"),
        (0x0000000000000001, "pos_subnormal"),
        (0x3FF0000000000000, "pos_normal"),
        (0x7FF0000000000000, "pos_inf"),
        (0x7FF0000000000001, "sNaN"),
        (0x7FF8000000000000, "qNaN"),
    ],
}


@register("cp_custom_vfclass_onehot")
def make(test, sew):
    if sew > common.flen:
        return

    inputs = CLASSIFY_INPUTS.get(sew, [])
    for val, desc in inputs:
        label = f"custom_vfclass_{desc}_sew{sew}"
        registerCustomData(label, [val], element_size=sew)
        description = f"cp_custom_vfclass_onehot ({desc})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
