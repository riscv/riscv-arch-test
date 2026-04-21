# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfp_NaN_input

Confirm that NaN inputs set the proper flags.
Cross: std_vec × vfp_NaN_input_fp_flags_clear × vs2_element0_sqNAN

Template bins on vs2[0] being qNaN or sNaN, with fflags clear before.
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
    vfloattypes,
)

# qNaN and sNaN values per SEW, matching template bins exactly
NAN_VALUES = {
    16: [
        (0x7E00, "qNaN"),
        (0x7D00, "sNaN"),
    ],
    32: [
        (0x7FC00000, "qNaN"),
        (0x7FA00000, "sNaN"),
    ],
    64: [
        (0x7FF8000000000000, "qNaN"),
        (0x7FF0000000000001, "sNaN"),
    ],
}


@register("cp_custom_vfp_NaN_input")
def make(test, sew):
    if sew > common.flen:
        return

    if test not in vfloattypes:
        return

    # Emit sNaN first (before any FP op dirties fflags) to avoid the
    # fsflagsi/fcsr RVVI stale-CSR bug.  Then qNaN second.
    nans = NAN_VALUES.get(sew, [])
    for val, desc in reversed(nans):
        label = f"custom_nan_{desc}_sew{sew}"
        registerCustomData(label, [val], element_size=sew)
        description = f"cp_custom_vfp_NaN_input ({desc}, {test})"
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label,
            additional_no_overlap=[['vs2', 'vs1']],
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1)
        incrementBasetestCount()
        vsAddressCount()
