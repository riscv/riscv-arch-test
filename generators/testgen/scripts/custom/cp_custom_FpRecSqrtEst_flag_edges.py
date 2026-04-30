# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecSqrtEst_flag_edges

Confirm all FP flags are correctly set for reciprocal sqrt estimate (vfrsqrt7.v).
Exercises 8 FP edge-case inputs with fflags clear before execution.
Cross: std_vec x vs1_0_reciprocal_sqrt_edges x fp_flags_clear
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
)

# RVVI ALIAS BUG WORKAROUND: fsflagsi writes CSR 001 (fflags) but NOT
# CSR 003 (fcsr). The template reads fcsr, so stale flags persist in the
# RVVI mirror. After each flag-setting vfrsqrt7, insert a spacer using
# pos_inf (vfrsqrt7(+inf)=+0, no flags → writes CSR 003=0).
# Flag-setting inputs: neg_finite(NV), neg_inf(NV), neg_zero(DZ),
#                      pos_zero(DZ), sNaN(NV).
_SPACER_LABEL = "vs_corner_f_posinfinity_emul1"

# (data label, description, sets_flags)
EDGE_CASES = [
    ("vs_corner_f_neg1_emul1", "neg_finite (-1.0)", True),
    ("vs_corner_f_neginfinity_emul1", "neg_inf (-Inf)", True),
    ("vs_corner_f_neg0_emul1", "neg_zero (-0.0)", True),
    ("vs_corner_f_pos0_emul1", "pos_zero (+0.0)", True),
    ("vs_corner_f_posinfinity_emul1", "pos_inf (+Inf)", False),
    ("vs_corner_f_pos1_emul1", "pos_finite (+1.0)", False),
    ("vs_corner_f_canonicalQNaN_emul1", "qNaN (canonical)", False),
    ("vs_corner_f_sNaN_payload1_emul1", "sNaN", True),
]


def _emit(test, sew, label, desc):
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs2_val_pointer=label,
    )
    writeTest(f"cp_custom_FpRecSqrtEst_flag_edges ({desc})", test, data,
              sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


@register("cp_custom_FpRecSqrtEst_flag_edges")
def make(test, sew):
    if sew > common.flen:
        return

    for label, desc, sets_flags in EDGE_CASES:
        _emit(test, sew, label, desc)
        if sets_flags:
            _emit(test, sew, _SPACER_LABEL, f"spacer_after_{desc}")
