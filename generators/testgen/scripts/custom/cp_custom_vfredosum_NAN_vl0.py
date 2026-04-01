# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfredosum_NAN_vl0

Confirm that if there are no active elements (vl=0), vs1[0] is simply
copied over and does not canonicalize NaN.

Template cross: fp_flags_clear × vtype_prev_vill_clear × vl_zero ×
                vstart_zero × vs1_0_qNAN (iff no trap)

We need: vl=0, vstart=0, vs1[0]=qNaN, fflags clear, vill clear.

Strategy: Two-test approach to work around writeTest(vl=0) preventing
data loading. Test 1 loads qNaN into a pinned vs1 register with vl=1.
Test 2 runs with vl=0 — vs1 retains qNaN from test 1 because vle
loads 0 elements and doesn't overwrite the register.
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

# qNaN values per SEW
QNAN = {
    16: 0x7E00,
    32: 0x7FC00000,
    64: 0x7FF8000000000000,
}

# Pin vs1 to a fixed register so test 2 retains data from test 1
VS1_REG = 8


@register("cp_custom_vfredosum_NAN_vl0")
def make(test, sew):
    if sew > common.flen:
        return

    # For widening reductions (vfwredosum), vs1 is read at 2*SEW
    is_widening = test.startswith("vfw")
    vs1_sew = sew * 2 if is_widening else sew

    qnan = QNAN.get(vs1_sew)
    if qnan is None:
        return

    label = f"custom_redosum_qnan_sew{vs1_sew}"
    registerCustomData(label, [qnan], element_size=vs1_sew)

    # Test 1: Load qNaN into vs1=v8 with vl=1 (populates vector register)
    description = f"cp_custom_vfredosum_NAN_vl0 setup ({test}, vl=1, vs1[0]=qNaN)"
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs1=VS1_REG, vs1_val_pointer=label,
    )
    writeTest(description, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()

    # Test 2: Run with vl=0 — vs1=v8 retains qNaN from test 1
    # The framework generates vle loads with vl=0 (loading nothing),
    # so v8 keeps its qNaN value. Coverage cross fires on this instruction.
    description = f"cp_custom_vfredosum_NAN_vl0 ({test}, vl=0, vs1[0]=qNaN retained)"
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs1=VS1_REG, vs1_val_pointer=label,
    )
    writeTest(description, test, data, sew=sew, lmul=1, vl=0)
    incrementBasetestCount()
    vsAddressCount()
