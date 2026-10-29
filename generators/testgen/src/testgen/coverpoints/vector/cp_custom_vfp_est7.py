##################################
# cp_custom_vfp_est7.py
#
# nfotenos@g.hmc.edu October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Subnormal input and output coverpoints for vfrec7.v and vfrsqrt7.v.

cp_custom_FpRecipEst_subnorm
    Subnormal inputs with 0 or 1 leading zeros, normal inputs with a subnormal result, and
    subnormal inputs whose reciprocal overflows under every frm. The overflow result is +/-inf or
    the greatest finite value, depending on frm and sign.

cp_custom_FpRecSqrtEst_subnorm
    Positive subnormal inputs with each count of leading zeros.

The values come from the same ranges as the cp_custom_FpRec*Est_subnorm_sew{16,32,64}.sv bins.
"""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.random import random_range
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params

# SEW: (exponent bits, fraction bits)
FP_FORMATS = {16: (5, 10), 32: (8, 23), 64: (11, 52)}

# frm encodings 0-4
FRM_MODES = ("rne", "rtz", "rdn", "rup", "rmm")

# (bin name, lowest value, highest value, expected result)
FpClass = tuple[str, int, int, str]


def fp_pack(sew: int, sign: int, exp: int, frac: int) -> int:
    nf = FP_FORMATS[sew][1]
    return (sign << (sew - 1)) | (exp << nf) | frac


def _classes(
    sew: int, name: str, comment: str, exp: int, frac: tuple[int, int], signs: tuple[int, ...] = (0, 1)
) -> list[FpClass]:
    """One class per sign, with fractions frac[0]..frac[1] at exponent exp."""
    return [
        (f"{'neg' if s else 'pos'}_{name}", fp_pack(sew, s, exp, frac[0]), fp_pack(sew, s, exp, frac[1]), comment)
        for s in signs
    ]


def recip_classes(sew: int) -> list[FpClass]:
    ne, nf = FP_FORMATS[sew]
    bias = (1 << (ne - 1)) - 1
    fmax = (1 << nf) - 1
    return (
        _classes(sew, "sub_lz0", "normal result", 0, (1 << (nf - 1), fmax))
        + _classes(sew, "sub_lz1", "normal result", 0, (1 << (nf - 2), (1 << (nf - 1)) - 1))
        + _classes(sew, "norm_subres1", "subnormal result", 2 * bias - 1, (0, fmax))
        + _classes(sew, "norm_subres2", "subnormal result", 2 * bias, (0, fmax))
    )


def recip_overflow_classes(sew: int) -> list[FpClass]:
    """Subnormals with two or more leading zeros, whose reciprocal overflows."""
    nf = FP_FORMATS[sew][1]
    return _classes(sew, "sub_ovf", "+/-inf or +/-greatest finite by frm; OF, NX", 0, (1, (1 << (nf - 2)) - 1))


def rsqrt_classes(sew: int) -> list[FpClass]:
    nf = FP_FORMATS[sew][1]
    return [
        cls
        for lz in range(nf)
        for cls in _classes(sew, f"sub_lz{lz}", "", 0, (1 << (nf - 1 - lz), (1 << (nf - lz)) - 1), (0,))
    ]


def _class_tests(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    classes: list[FpClass],
    frm: int | None = None,
) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None
    lmul = get_base_lmul(instr_name, instr_type, sew)
    test_chunks = []
    for name, lo, hi, comment in classes:
        bin_name = name if frm is None else f"{name}_{FRM_MODES[frm]}"
        label = f"{coverpoint}_{bin_name}"
        val = random_range(lo, hi)
        test_data.register_vector_data(label, sew, elements=[val])
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, vs2_val_pointer=label, csr_frm_val=frm
        )
        desc = f"{coverpoint} ({name}{': ' + comment if comment else ''}, vs2[0] = {val:#x})"
        test_chunks.append(
            format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        )
        return_testcase_registers(test_data, params)
    return test_chunks


def _sew_supported(test_data: TestData) -> bool:
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    return test_data.config.sew in FP_FORMATS and test_data.config.sew <= test_data.config.flen


@add_coverpoint_generator("cp_custom_FpRecipEst_subnorm")
def cp_custom_fp_recip_est_subnorm(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """vfrec7.v subnormal inputs and outputs, and overflowing subnormal inputs under every frm."""
    if not _sew_supported(test_data):
        return []
    sew = test_data.config.sew
    assert sew is not None
    test_chunks = _class_tests(instr_name, instr_type, coverpoint, test_data, recip_classes(sew))
    for frm in range(len(FRM_MODES)):
        test_chunks += _class_tests(instr_name, instr_type, coverpoint, test_data, recip_overflow_classes(sew), frm)
    return test_chunks


@add_coverpoint_generator("cp_custom_FpRecSqrtEst_subnorm")
def cp_custom_fp_recsqrt_est_subnorm(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """vfrsqrt7.v positive subnormal inputs with each count of leading zeros."""
    if not _sew_supported(test_data):
        return []
    sew = test_data.config.sew
    assert sew is not None
    return _class_tests(instr_name, instr_type, coverpoint, test_data, rsqrt_classes(sew))
