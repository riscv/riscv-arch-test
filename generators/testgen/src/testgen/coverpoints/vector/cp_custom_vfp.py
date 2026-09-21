##################################
# cp_custom_vfp.py
#
# rwolk@hmc.edu September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.tsbi import tsbi_call
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import PresetMask
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction, format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import get_base_lmul, get_legal_lmuls
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_vfp_NaN_input")
def cp_custom_vfp_NaN_input(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test both types of NaN inputs"""
    NAN_VALUES = {
        16: {
            "qNaN": 0x7E00,
            "sNaN": 0x7D00,
        },
        32: {
            "qNaN": 0x7FC00000,
            "sNaN": 0x7FA00000,
        },
        64: {
            "qNaN": 0x7FF8000000000000,
            "sNaN": 0x7FF0000000000001,
        },
    }

    assert test_data.config.sew is not None, "SEW must be provided for vector tests"

    if test_data.config.sew > test_data.config.flen:
        return []

    lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    test_chunks = []
    for nan_type in ["sNaN", "qNaN"]:  # Due problems with the trace, we need to emit sNaN first
        label = f"cp_custom_vfp_NaN_input_{nan_type}"

        instr_type_config = get_instruction_type_config(instr_type)
        assert instr_type_config.vector_data is not None, "Vector data must be provided for vector instructions"
        eew = test_data.config.sew * 2 if "vs2" in instr_type_config.vector_data.widened_regs else test_data.config.sew

        val = NAN_VALUES[eew][nan_type]
        test_data.register_vector_data(label, eew, elements=[val])

        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, vs2_val_pointer=label, additional_no_overlap={("vs2", "vs1")}
        )
        desc = f"NaN Input: {nan_type}"
        bin_name = nan_type

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


_POS_ONE = {16: 0x3C00, 32: 0x3F800000, 64: 0x3FF0000000000000}


@add_coverpoint_generator("cp_custom_vfp_state")
def cp_custom_vfp_state(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Any vector FP instruction that writes to an f register must set mstatus.FS to Dirty.

    This only checks the setup: the instruction is exercised while mstatus.FS is Clean, so a
    lockstep reference model can verify the FS=Dirty transition. mstatus.FS is forced to Clean
    immediately before the test instruction, after any setup code (register loads, etc.) has run.
    """
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    label = "cp_custom_vfp_state_pos1"
    test_data.register_vector_data(label, sew, elements=[_POS_ONE[sew]])
    params = generate_random_vector_params(test_data, instr_name, instr_type, 1, vs2_val_pointer=label)

    tc = test_data.begin_test_chunk()
    label_line = test_data.add_testcase("", coverpoint)
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

    reg = params.temp_reg
    force_fs_clean = "\n".join(
        [
            "# Clear mstatus.fs",
            f"li x{reg}, 0x6000",
            tsbi_call(f"csrc mstatus, x{reg}"),
            "# Set mstatus.fs = clean",
            f"li x{reg}, 0x4000",
            tsbi_call(f"csrs mstatus, x{reg}"),
        ]
    )

    tc.code.extend([f"# {coverpoint} (FS=Clean pre-instruction)", setup, force_fs_clean, label_line, test, check])
    tc = test_data.end_test_chunk()
    return_testcase_registers(test_data, params)

    return [tc]


_NCVT_FLOAT_TO_FLOAT = {"vfncvt.f.f.w", "vfncvt.rod.f.f.w"}
_NCVT_INT_TO_FLOAT = {"vfncvt.f.x.w", "vfncvt.f.xu.w"}
_NCVT_FLOAT_TO_INT = {"vfncvt.xu.f.w", "vfncvt.x.f.w", "vfncvt.rtz.xu.f.w", "vfncvt.rtz.x.f.w"}

# 64-bit double values exceeding float32 max range (~3.4028235e38)
_NCVT_POS_OVERFLOW_F64 = 0x47F0000000000000
_NCVT_NEG_OVERFLOW_F64 = 0xC7F0000000000000
_NCVT_LARGE_INT64 = 0x0000000100000000  # 2^32, doesn't overflow float32 but exercises the path
_NCVT_LARGE_FLOAT_FOR_INT = 0x41F0000000000000  # 2^32 as a double, exceeds int32/uint32 range

# 32-bit single precision values exceeding bf16 range
_NCVT_POS_OVERFLOW_F32 = 0x7F7FF800
_NCVT_NEG_OVERFLOW_F32 = 0xFF7FF800


@add_coverpoint_generator("cp_custom_vfncvt_rup_overflow")
def cp_custom_vfncvt_rup_overflow(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Confirm overflow is recognized when narrowing with round-up (frm=RUP), at SEW=32: source is
    64-bit, destination is 32-bit single-precision.

    Only the float-to-float narrowing variants can actually set fflags.OF here: int64 can't exceed
    the float32 range, and float-to-int overflow sets NV rather than OF. Every variant still gets a
    test so coverage stays uniform, even though only float-to-float can hit the OF bin.
    """
    if test_data.config.sew != 32 and not ("bf16" in instr_name and test_data.config.sew == 16):
        return []

    if instr_name in _NCVT_FLOAT_TO_FLOAT:
        values = [(_NCVT_POS_OVERFLOW_F64, "positive_overflow"), (_NCVT_NEG_OVERFLOW_F64, "negative_overflow")]
    elif instr_name in _NCVT_INT_TO_FLOAT:
        values = [(_NCVT_LARGE_INT64, "large_integer")]
    elif instr_name in _NCVT_FLOAT_TO_INT:
        values = [(_NCVT_LARGE_FLOAT_FOR_INT, "large_float_for_int")]
    elif instr_name == "vfncvtbf16.f.f.w":
        values = [(_NCVT_POS_OVERFLOW_F32, "positive_overflow"), (_NCVT_NEG_OVERFLOW_F32, "negative_overflow")]
    else:
        raise ValueError("Unsupported Instruction for cp_custom_vfncvt_rup_overflow")

    test_chunks = []
    for val, bin_name in values:
        label = f"cp_custom_vfncvt_rup_overflow_{bin_name}"
        test_data.register_vector_data(label, 64, elements=[val])
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, 1, vs2_val_pointer=label, csr_frm_val=3
        )
        desc = f"cp_custom_vfncvt_rup_overflow ({bin_name}, frm=RUP)"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_custom_vfncvt_rod_overflow")
def cp_custom_vfncvt_rod_overflow(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Confirm vfncvt.rod.f.f.w saturates to the destination format's largest finite value (not
    infinity) when the source exceeds the destination range. SEW=32 only: narrowing 64-bit double
    to 32-bit float.
    """
    if test_data.config.sew != 32:
        return []

    test_chunks = []
    for val, bin_name in [(_NCVT_POS_OVERFLOW_F64, "positive_overflow"), (_NCVT_NEG_OVERFLOW_F64, "negative_overflow")]:
        label = f"cp_custom_vfncvt_rod_overflow_{bin_name}"
        test_data.register_vector_data(label, 64, elements=[val])
        params = generate_random_vector_params(test_data, instr_name, instr_type, 1, vs2_val_pointer=label)
        desc = f"cp_custom_vfncvt_rod_overflow ({bin_name})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


def _make_rsqrt_estimate_value(sew: int, lookup_7bit: int) -> int:
    """
    Build a positive normal FP value that puts lookup_7bit into the field vfrsqrt7's coverpoint
    extracts: the exponent LSB and the 6 MSBs of the significand (bits [10:4]/[23:17]/[52:46] for
    SEW 16/32/64).
    """
    exp_lsb = (lookup_7bit >> 6) & 1
    mant_top6 = lookup_7bit & 0x3F
    if sew == 16:
        # half: sign(1) exp(5) sig(10)
        # Use biased exp 16 (0b10000) for exp_lsb=0, 17 (0b10001) for exp_lsb=1
        return ((0b10000 | exp_lsb) << 10) | (mant_top6 << 4)
    elif sew == 32:
        # float: sign(1) exp(8) sig(23)
        return ((0b10000000 | exp_lsb) << 23) | (mant_top6 << 17)
    elif sew == 64:
        # double: sign(1) exp(11) sig(52)
        return ((0b10000000000 | exp_lsb) << 52) | (mant_top6 << 46)

    raise ValueError(f"Unsupported SEW {sew} for rsqrt_estimate_value")


@add_coverpoint_generator("cp_custom_FpRecSqrtEst_edges")
def cp_custom_fp_recsqrt_est_edges(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Confirm all 128 possible 7-bit significand lookups into vfrsqrt7.v produce correct results."""
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    lmul = get_base_lmul(instr_name, instr_type, sew)
    test_chunks = []
    for i in range(128):
        label = f"cp_custom_FpRecSqrtEst_edges_sig{i:03d}"
        test_data.register_vector_data(label, sew, elements=[_make_rsqrt_estimate_value(sew, i)])
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs2_val_pointer=label)
        desc = f"cp_custom_FpRecSqrtEst_edges (sig={i:03d})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"sig{i:03d}", coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


def _make_recip_estimate_value(sew: int, sig_7bit: int) -> int:
    """
    Build a positive normal FP value with the given 7-bit significand MSBs, matching the field
    vfrec7's coverpoint extracts (bits [9:3]/[22:16]/[51:45] for SEW 16/32/64).
    """
    if sew == 16:
        return (0b0_10000 << 10) | (sig_7bit << 3)
    elif sew == 32:
        return (0b0_10000000 << 23) | (sig_7bit << 16)
    else:
        return (0b0_10000000000 << 52) | (sig_7bit << 45)


@add_coverpoint_generator("cp_custom_FpRecipEst_edges")
def cp_custom_fp_recip_est_edges(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Confirm all 128 possible 7-bit significand lookups into vfrec7.v produce correct results."""
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    lmul = get_base_lmul(instr_name, instr_type, sew)
    test_chunks = []
    for i in range(128):
        label = f"cp_custom_FpRecipEst_edges_sig{i:03d}"
        test_data.register_vector_data(label, sew, elements=[_make_recip_estimate_value(sew, i)])
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs2_val_pointer=label)
        desc = f"cp_custom_FpRecipEst_edges (sig={i:03d})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"sig{i:03d}", coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


_RSQRT_FLAG_EDGES = [
    ("neg_finite (-1.0)", {16: 0xBC00, 32: 0xBF800000, 64: 0xBFF0000000000000}, True),
    ("neg_inf (-Inf)", {16: 0xFC00, 32: 0xFF800000, 64: 0xFFF0000000000000}, True),
    ("neg_zero (-0.0)", {16: 0x8000, 32: 0x80000000, 64: 0x8000000000000000}, True),
    ("pos_zero (+0.0)", {16: 0x0000, 32: 0x00000000, 64: 0x0000000000000000}, True),
    ("pos_inf (+Inf)", {16: 0x7C00, 32: 0x7F800000, 64: 0x7FF0000000000000}, False),
    ("pos_finite (+1.0)", {16: 0x3C00, 32: 0x3F800000, 64: 0x3FF0000000000000}, False),
    ("qNaN (canonical)", {16: 0x7E00, 32: 0x7FC00000, 64: 0x7FF8000000000000}, False),
    ("sNaN", {16: 0x7D01, 32: 0x7F800001, 64: 0x7FF0000000000001}, True),
]
_RSQRT_FLAG_SPACER = {16: 0x7C00, 32: 0x7F800000, 64: 0x7FF0000000000000}  # +inf


@add_coverpoint_generator("cp_custom_FpRecSqrtEst_flag_edges")
def cp_custom_fp_recsqrt_est_flag_edges(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Confirm all FP flags are correctly set for vfrsqrt7.v across its FP edge-case inputs."""
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    lmul = get_base_lmul(instr_name, instr_type, sew)
    spacer_label = "cp_custom_FpRecSqrtEst_flag_edges_spacer"
    test_data.register_vector_data(spacer_label, sew, elements=[_RSQRT_FLAG_SPACER[sew]])

    test_chunks = []
    for desc, values, sets_flags in _RSQRT_FLAG_EDGES:
        bin_name = desc.split()[0]
        label = f"cp_custom_FpRecSqrtEst_flag_edges_{bin_name}"
        test_data.register_vector_data(label, sew, elements=[values[sew]])
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs2_val_pointer=label)
        tc = format_single_testcase(
            instr_name,
            instr_type,
            test_data,
            params,
            f"cp_custom_FpRecSqrtEst_flag_edges ({desc})",
            bin_name,
            coverpoint,
        )
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

        # RVVI CSR mirror workaround: the check reads fcsr, so stale flags from a previous flag-setting
        # vfrsqrt7/vfrec7 persist unless cleared. A spacer with a no-flags input (vfrsqrt7(+inf)=+0,
        # vfrec7(-inf)=+0) follows every flag-setting input so each test starts from fflags=0.
        if sets_flags:
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul, vs2_val_pointer=spacer_label
            )
            tc = format_single_testcase(
                instr_name,
                instr_type,
                test_data,
                params,
                f"cp_custom_FpRecSqrtEst_flag_edges (spacer after {desc})",
                f"{bin_name}_spacer",
                coverpoint,
            )
            return_testcase_registers(test_data, params)
            test_chunks.append(tc)

    return test_chunks


# Per-SEW edge values matching the template bins exactly. Flag-setting inputs are ±0 (DZ) and
# ±tiny subnormal (OF|NX); everything else sets no flags. See cp_custom_FpRecSqrtEst_flag_edges
# for why a spacer follows every flag-setting input.
_RECIP_FLAG_EDGES = {
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
_RECIP_FLAG_SPACER = {16: 0xFC00, 32: 0xFF800000, 64: 0xFFF0000000000000}  # -inf


@add_coverpoint_generator("cp_custom_FpRecipEst_flag_edges")
def cp_custom_fp_recip_est_flag_edges(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Confirm all FP flags are correctly set for vfrec7.v across its FP edge-case inputs."""
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    lmul = get_base_lmul(instr_name, instr_type, sew)
    spacer_label = "cp_custom_FpRecSqrtEst_flag_edges_spacer"
    test_data.register_vector_data(spacer_label, sew, elements=[_RECIP_FLAG_SPACER[sew]])

    test_chunks = []
    for val, bin_name, sets_flags in _RECIP_FLAG_EDGES.get(sew, []):
        label = f"cp_custom_FpRecipEst_flag_edges_{bin_name}"
        test_data.register_vector_data(label, sew, elements=[val])
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs2_val_pointer=label)
        tc = format_single_testcase(
            instr_name,
            instr_type,
            test_data,
            params,
            f"cp_custom_FpRecipEst_flag_edges ({bin_name})",
            bin_name,
            coverpoint,
        )
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

        # Work around for limitations in the sail trace
        if sets_flags:
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul, vs2_val_pointer=spacer_label
            )
            tc = format_single_testcase(
                instr_name,
                instr_type,
                test_data,
                params,
                f"cp_custom_FpRecipEst_flag_edges (spacer after {bin_name})",
                f"{bin_name}_spacer",
                coverpoint,
            )
            return_testcase_registers(test_data, params)
            test_chunks.append(tc)

    return test_chunks


# Input values per SEW that produce each of vfclass.v's 10 one-hot classifications.
_CLASSIFY_INPUTS = {
    16: [
        (0xFC00, "neg_inf"),
        (0xBC00, "neg_normal"),
        (0x8001, "neg_subnormal"),
        (0x8000, "neg_zero"),
        (0x0000, "pos_zero"),
        (0x0001, "pos_subnormal"),
        (0x3C00, "pos_normal"),
        (0x7C00, "pos_inf"),
        (0x7D01, "sNaN"),
        (0x7E00, "qNaN"),
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


@add_coverpoint_generator("cp_custom_vfclass_onehot")
def cp_custom_vfclass_onehot(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Confirm all 10 classify cases (RISC-V spec vfclass.v result bits) are correctly handled."""
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    lmul = get_base_lmul(instr_name, instr_type, sew)
    test_chunks = []
    for val, bin_name in _CLASSIFY_INPUTS.get(sew, []):
        label = f"cp_custom_vfclass_onehot_{bin_name}"
        test_data.register_vector_data(label, sew, elements=[val])
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs2_val_pointer=label)
        desc = f"cp_custom_vfclass_onehot ({bin_name})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


_REDOSUM_MAX_NORM = {16: 0x7BFF, 32: 0x7F7FFFFF, 64: 0x7FEFFFFFFFFFFFFF}
_REDOSUM_NEG_MAX_NORM = {16: 0xFBFF, 32: 0xFF7FFFFF, 64: 0xFFEFFFFFFFFFFFFF}


@add_coverpoint_generator("cp_custom_vfredosum_ordered_sum")
def cp_custom_vfredosum_ordered_sum(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Confirm vfredosum.vs sums in order: maxNorm + (-maxNorm) + small == small, not 0 as an unordered
    (catastrophic-cancellation) sum would give. Needs vl >= 2 and lmul = 2 so the reduction walks
    two elements.
    """
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    vs1_label = "cp_custom_vfredosum_ordered_sum_maxnorm"
    test_data.register_vector_data(vs1_label, sew, elements=[_REDOSUM_MAX_NORM[sew]])

    vs2_label = "cp_custom_vfredosum_ordered_sum_negmaxnorm_small"
    test_data.register_vector_data(vs2_label, sew, elements=[_REDOSUM_NEG_MAX_NORM[sew], _POS_ONE[sew]])

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=2,
        vl=2,
        suite="length",
        vs1_val_pointer=vs1_label,
        vs2_val_pointer=vs2_label,
    )
    desc = "cp_custom_vfredosum_ordered_sum (maxNorm + (-maxNorm) + small)"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, "ordered_sum", coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]


_REDOSUM_QNAN = {16: 0x7E00, 32: 0x7FC00000, 64: 0x7FF8000000000000}


@add_coverpoint_generator("cp_custom_vfredosum_NAN_vl0")
def cp_custom_vfredosum_nan_vl0(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Confirm that with vl=0, vs1[0] is passed through untouched and not canonicalized, even a qNaN."""
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew
    if sew > test_data.config.flen:
        return []

    type_config = get_instruction_type_config(instr_type)
    assert type_config.vector_data is not None, "Vector data must be provided for all vector instruction types"
    vs1_sew = sew * 2 if "vs1" in type_config.vector_data.widened_regs else sew

    qnan = _REDOSUM_QNAN.get(vs1_sew)
    if qnan is None:
        raise ValueError(f"Unsupported SEW {sew} for cp_custom_vfredosum_NAN_vl0")

    label = f"cp_custom_vfredosum_NAN_vl0_sew{vs1_sew}"
    test_data.register_vector_data(label, vs1_sew, elements=[qnan])

    params = generate_random_vector_params(test_data, instr_name, instr_type, 1, vl=0, vs1_val_pointer=label)
    desc = f"cp_custom_vfredosum_NAN_vl0 ({instr_name}, vl=0, vs1[0]=qNaN retained)"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, "vl0_qnan", coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_fmv_sf_vd_all_lmul")
def cp_custom_fmv_sf_vd_all_lmul(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Confirm vfmv.s.f ignores LMUL for the destination register: LMUL=1 exercises all 32 vd values,
    every other legal LMUL exercises vd=v1. vd is a scalar register for this instruction, so it
    always occupies exactly one physical register regardless of LMUL.
    """
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew

    if sew > test_data.config.flen:
        return []

    test_chunks = []
    for exponent in get_legal_lmuls(sew):
        lmul = 2.0**exponent

        # TODO: Come back to this coverpoint definition. It seems flawed
        # LMUL=1: all 32 regs (covers vd_all_regs cross). Others: just vd=1 (covers LMUL cross).
        vd_values = range(32) if lmul == 1.0 else [1]

        for vd in vd_values:
            test_data.vec_regs.allocate_operand("vd", vd, 1)
            params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vd=vd)
            desc = f"cp_custom_fmv_sf_vd_all_lmul (vd=v{vd}, lmul={lmul})"
            bin_name = f"vd{vd}_lmul{lmul}"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            return_testcase_registers(test_data, params)
            test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_custom_fmv_fs_vs2_all_lmul")
def cp_custom_fmv_fs_vs2_all_lmul(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Confirm vfmv.f.s ignores LMUL for the source register: LMUL=1 exercises all 32 vs2 values, every
    other legal LMUL exercises vs2=v1. vs2 is a scalar register for this instruction, so it always
    occupies exactly one physical register regardless of LMUL.
    """
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew

    test_chunks = []
    for exponent in get_legal_lmuls(sew):
        lmul = 2.0**exponent

        # TODO: Come back to this coverpoint and get better coverage of what actually matters
        vs2_values = range(32) if lmul == 1 else [1]

        for vs2 in vs2_values:
            test_data.vec_regs.allocate_operand("vs2", vs2, 1)
            params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs2=vs2)
            desc = f"cp_custom_fmv_fs_vs2_all_lmul (vs2=v{vs2}, lmul={lmul})"
            bin_name = f"vs2{vs2}_lmul{lmul}"
            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            return_testcase_registers(test_data, params)
            test_chunks.append(tc)

    return test_chunks


##################################
# cp_custom_vfp_flags / cp_custom_vfp_flags_inactive_not_set
##################################


@add_coverpoint_generator("cp_custom_vfp_flags")
def cp_custom_vfp_flags(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """VFP flags currently has no generation as it is covered by other test generation"""

    # Currently this coverpoint is disabled
    return []


_VFP_FLAGS_TV: dict[int, dict[str, int]] = {
    16: {
        "NV": 0x7D01,
        "DZ": 0x0000,
        "OF": 0x7BFF,
        "UF": 0x0080,
        "NX": 0x3C01,
        "NX2": 0x3C02,
        "ONE": 0x3C00,
        "THREE": 0x4200,
    },
    32: {
        "NV": 0x7F800001,
        "DZ": 0x00000000,
        "OF": 0x7F7FFFFF,
        "UF": 0x00800001,
        "NX": 0x3F800001,
        "NX2": 0x3F800002,
        "ONE": 0x3F800000,
        "THREE": 0x40400000,
    },
    64: {
        "NV": 0x7FF0000000000001,
        "DZ": 0x0000000000000000,
        "OF": 0x7FEFFFFFFFFFFFFF,
        "UF": 0x0010000000000001,
        "NX": 0x3FF0000000000001,
        "NX2": 0x3FF0000000000002,
        "ONE": 0x3FF0000000000000,
        "THREE": 0x4008000000000000,
    },
}


@add_coverpoint_generator("cp_custom_vfp_flags_inactive_not_set")
def cp_custom_vfp_flags_inactive_not_set(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Confirm a masked-off element does not get its flags set: vfrsqrt7.v(0.0) would set DZ if active,
    so mask it off and confirm fflags stays clean.
    """
    assert test_data.config.sew is not None, "SEW must be provided for vector tests"
    sew = test_data.config.sew

    if sew > test_data.config.flen:
        return []

    if instr_name != "vfrsqrt7.v":
        raise ValueError("cp_custom_vfp_flags_inactive_not_set is only defined for vfrsqrt7.v")

    t = _VFP_FLAGS_TV[sew]
    spacer_label = f"custom_flag_one_sew{sew}"
    test_data.register_vector_data(spacer_label, sew, elements=[t["ONE"]])
    spacer_params = generate_random_vector_params(test_data, instr_name, instr_type, 1, vs2_val_pointer=spacer_label)
    spacer = format_single_testcase(
        instr_name,
        instr_type,
        test_data,
        spacer_params,
        "cp_custom_vfp_flags_inactive_not_set spacer (clears stale fcsr)",
        "spacer",
        coverpoint,
    )
    return_testcase_registers(test_data, spacer_params)

    zero_label = f"custom_flag_zero_sew{sew}"
    test_data.register_vector_data(zero_label, sew, elements=[0])
    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        1,
        masked=True,
        vs2_val_pointer=zero_label,
        maskval=PresetMask.ZEROS,
        additional_no_overlap={("vs2", "v0"), ("vd", "v0")},
    )
    tc = format_single_testcase(
        instr_name,
        instr_type,
        test_data,
        params,
        "cp_custom_vfp_flags_inactive_not_set (vfrsqrt7.v vs2=0, masked)",
        "masked",
        coverpoint,
    )
    return_testcase_registers(test_data, params)

    return [spacer, tc]
