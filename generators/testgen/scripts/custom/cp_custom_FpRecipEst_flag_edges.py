# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_FpRecipEst_flag_edges

Confirm all FP flags are correctly set for reciprocal estimate (vfrec7.v).
14 edge bins per SEW covering negative/positive subnormals, normals, zeros,
infinities, qNaN, and sNaN.

NOTE: Template uses ins.current.vs1 but vfrec7.v is VVM unary (source=vs2).
The template may need fixing to use vs2_val. We load data into vs2 regardless.
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

# Per-SEW edge values matching the template bins exactly.
# RVVI ALIAS BUG WORKAROUND: fsflagsi writes CSR 001 (fflags) but NOT
# CSR 003 (fcsr). The template reads fcsr, so stale flags from the previous
# vfrec7 persist in the RVVI CSR mirror. To work around this, after each
# flag-setting vfrec7, we insert a "spacer" vfrec7(-inf) which writes
# CSR 003=0 (no flags), clearing the stale value for the next real test.
# Flag-setting inputs: ±0 (DZ), ±sub_tiny (OF|NX). All others: no flags.
#
# Spacer values per SEW (negative infinity):
_SPACER = {16: 0xFC00, 32: 0xFF800000, 64: 0xFFF0000000000000}

# Test order: real test, then spacer if it set flags.
# Each tuple: (hex_value, description, sets_flags)
EDGES = {
    16: [
        (0xFC00, "neg_inf", False),
        (0x8001, "neg_sub_tiny", True),
        (0x83FF, "neg_sub_big", False),
        (0xBC00, "neg_norm_small", False),
        (0xFBFF, "neg_norm_big", False),
        (0x8000, "neg_zero", True),
        (0x7C00, "pos_inf", False),
        (0x0001, "pos_sub_tiny", True),
        (0x03FF, "pos_sub_big", False),
        (0x3C00, "pos_norm_small", False),
        (0x7BFF, "pos_norm_big", False),
        (0x0000, "pos_zero", True),
        (0x7E00, "qNaN", False),
        (0x7D00, "sNaN", False),
    ],
    32: [
        (0xFF800000, "neg_inf", False),
        (0x80000001, "neg_sub_tiny", True),
        (0x807FFFFF, "neg_sub_big", False),
        (0xBF800000, "neg_norm_small", False),
        (0xFF7FFFFF, "neg_norm_big", False),
        (0x80000000, "neg_zero", True),
        (0x7F800000, "pos_inf", False),
        (0x00000001, "pos_sub_tiny", True),
        (0x007FFFFF, "pos_sub_big", False),
        (0x3F800000, "pos_norm_small", False),
        (0x7F7FFFFF, "pos_norm_big", False),
        (0x00000000, "pos_zero", True),
        (0x7FC00000, "qNaN", False),
        (0x7FA00000, "sNaN", False),
    ],
    64: [
        (0xFFF0000000000000, "neg_inf", False),
        (0x8000000000000001, "neg_sub_tiny", True),
        (0x800FFFFFFFFFFFFF, "neg_sub_big", False),
        (0xBFF0000000000000, "neg_norm_small", False),
        (0xFFEFFFFFFFFFFFFF, "neg_norm_big", False),
        (0x8000000000000000, "neg_zero", True),
        (0x7FF0000000000000, "pos_inf", False),
        (0x0000000000000001, "pos_sub_tiny", True),
        (0x000FFFFFFFFFFFFF, "pos_sub_big", False),
        (0x3FF0000000000000, "pos_norm_small", False),
        (0x7FEFFFFFFFFFFFFF, "pos_norm_big", False),
        (0x0000000000000000, "pos_zero", True),
        (0x7FF8000000000000, "qNaN", False),
        (0x7FF0000000000001, "sNaN", False),
    ],
}


def _emit_test(test, sew, val, desc):
    """Emit one vfrec7 test case."""
    label = f"custom_recip_edge_{desc}_sew{sew}"
    registerCustomData(label, [val], element_size=sew)
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs2_val_pointer=label,
    )
    writeTest(f"cp_custom_FpRecipEst_flag_edges ({desc})", test, data,
              sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


@register("cp_custom_FpRecipEst_flag_edges")
def make(test, sew):
    if sew > common.flen:
        return

    spacer_val = _SPACER[sew]
    edges = EDGES.get(sew, [])
    for val, desc, sets_flags in edges:
        _emit_test(test, sew, val, desc)
        if sets_flags:
            # Insert spacer: vfrec7(-inf) writes CSR 003=0, clearing stale fcsr
            _emit_test(test, sew, spacer_val, f"spacer_after_{desc}")
