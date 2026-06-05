# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_vfredosum_NAN_vl0

Confirm that if there are no active elements (vl=0), vs1[0] is simply
copied over and does not canonicalize NaN.

Template cross: fp_flags_clear x vtype_prev_vill_clear x vl_zero x
                vstart_zero x vs1_0_qNAN (iff no trap)

We need: vl=0, vstart=0, vs1[0]=qNaN, fflags clear, vill clear.

writeTest(vl=0) now routes operand loads through the existing
load_unique_vtype save/restore path with AVL=1, so the operand vle
instructions populate vs1[0] with qNaN before the test vtype (vl=0)
is restored for the reduction itself.
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

QNAN = {
    16: 0x7E00,
    32: 0x7FC00000,
    64: 0x7FF8000000000000,
}


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

    description = f"cp_custom_vfredosum_NAN_vl0 ({test}, vl=0, vs1[0]=qNaN retained)"
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs1_val_pointer=label,
    )
    writeTest(description, test, data, sew=sew, lmul=1, vl=0)
    incrementBasetestCount()
    vsAddressCount()
