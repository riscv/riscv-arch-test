##################################
# priv/extensions/VFCommon.py
#
# Shared vector floating-point test generation for Sm_VF (M-mode, mstatus.FS), S_VF (S-mode,
# sstatus.FS) and U_VF (U-mode, sstatus.FS or mstatus.FS through T-SBI).
# Vector floating-point interactions with xstatus.FS state transitions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating vector-FP × xstatus.FS state tests in M-, S- and U-mode."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import STATUS_CSR, gen_status_read_sigupd, set_status_fields

# vfadd.vv operand patterns as (vs2_reg, vs1_reg, name), covering the 4 vs1_zero x vs2_zero
# combinations. v1 and v4 hold 1.0; v2 holds 0.
_VFADD_PATTERNS = [
    ("v2", "v2", "vs1_0_vs2_0"),  # both zero
    ("v1", "v2", "vs1_0_vs2_n"),  # vs1=0, vs2!=0
    ("v2", "v1", "vs1_n_vs2_0"),  # vs1!=0, vs2=0
    ("v1", "v4", "vs1_n_vs2_n"),  # both nonzero
]


def _vector_setup(temp_reg: int) -> list[str]:
    return [
        f"vsetivli x{temp_reg}, 4, e32, m1, tu, mu  # vill=0, vl=4",
        "csrw vstart, x0",
    ]


def _load_v_zero_one(temp_reg: int) -> list[str]:
    """Load v1=ones (1.0f), v2=zeros, v4=ones, v5=ones — under FS=Dirty before any FS state change."""
    lines = []
    lines.append(f"LI(x{temp_reg}, 0x3f800000)  # 1.0f")
    lines.append(f"fmv.w.x f1, x{temp_reg}")
    lines.append(f"vsetvli x{temp_reg}, x0, e32, m1, ta, ma  # vl = VLMAX so the fills cover whole registers")
    lines.append("vfmv.v.f v1, f1   # v1 = 1.0 in each lane")
    lines.append("vmv.v.i v2, 0     # v2 = 0")
    lines.append("vfmv.v.f v4, f1   # v4 = 1.0")
    lines.append("vfmv.v.f v5, f1   # v5 = 1.0")
    lines.extend(_vector_setup(temp_reg))
    return lines


def _gen_fs_state_affecting_register(test_data: TestData, temp_reg: int, covergroup: str, priv: str) -> list[str]:
    """cp_vectorfp_xstatus_fs_state_affecting_register: vfmv.f.s with FS=Initial/Clean/Dirty."""
    status = STATUS_CSR[priv]
    coverpoint = f"cp_vectorfp_{status}_fs_state_affecting_register"
    lines = [
        comment_banner(coverpoint, "vfmv.f.s under FS=Initial(1)/Clean(2)/Dirty(3); should leave FS=Dirty"),
    ]
    for fs in (1, 2, 3):
        lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
        lines.extend(_load_v_zero_one(temp_reg))
        lines.extend(set_status_fields(temp_reg, priv, fs=fs, vs=3))
        lines.append(test_data.add_testcase(f"vfmv_f_s_fs{fs}", coverpoint, covergroup))
        lines.append("vfmv.f.s f1, v2")
        lines.append(gen_status_read_sigupd(temp_reg, test_data, priv))
    return lines


def _gen_fs_state_affecting_csr(test_data: TestData, temp_reg: int, covergroup: str, priv: str) -> list[str]:
    """cp_vectorfp_xstatus_fs_state_affecting_csr: vector-FP arith that raises fflags."""
    status = STATUS_CSR[priv]
    coverpoint = f"cp_vectorfp_{status}_fs_state_affecting_csr"
    lines = [
        comment_banner(
            coverpoint,
            "vfdiv.vv 1.0/0.0 (DZ), vfadd.vv inf + -inf (NV) and vmflt.vv with a NaN operand (NV)"
            " under FS=Initial/Clean/Dirty; must leave FS=Dirty",
        ),
    ]
    for fs in (1, 2, 3):
        for trial in range(3):
            lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
            lines.extend(_load_v_zero_one(temp_reg))
            lines.append(
                "csrwi fcsr, 0  # clear fcsr (fflags+frm) under FS=Dirty; clearing fflags alone leaves fcsr stale in some traces"
            )
            lines.extend(set_status_fields(temp_reg, priv, fs=fs, vs=3))
            lines.append(test_data.add_testcase(f"vfdiv_vv_fs{fs}_t{trial}", coverpoint, covergroup))
            lines.append("vfdiv.vv v3, v1, v2  # 1.0/0.0 -> +inf, DZ flag")
            # xstatus first: reading fflags may itself dirty FS on a conservative DUT
            lines.append(gen_status_read_sigupd(temp_reg, test_data, priv))
            lines.append(write_sigupd(None, test_data, "fflags"))
    # vfadd inf + -inf raises NV
    for fs in (1, 2, 3):
        lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
        lines.extend(_load_v_zero_one(temp_reg))
        # build +inf in v6 by 1.0/0.0 first under FS=Dirty
        lines.append("vfdiv.vv v6, v1, v2  # v6 = +inf")
        lines.append(f"LI(x{temp_reg}, 0xff800000)  # -inf")
        lines.append(f"fmv.w.x f2, x{temp_reg}")
        lines.append("vfmv.v.f v7, f2  # v7 = -inf")
        lines.append("csrwi fcsr, 0  # clear fcsr (fflags+frm) under FS=Dirty")
        lines.extend(set_status_fields(temp_reg, priv, fs=fs, vs=3))
        lines.append(test_data.add_testcase(f"vfadd_inf_minf_fs{fs}", coverpoint, covergroup))
        lines.append("vfadd.vv v3, v6, v7  # inf + -inf -> NV flag")
        lines.append(gen_status_read_sigupd(temp_reg, test_data, priv))
        lines.append(write_sigupd(None, test_data, "fflags"))
    # Mask-producing compare: writes no FP register, only fflags (NV for any NaN operand)
    for fs in (1, 2, 3):
        lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
        lines.extend(_load_v_zero_one(temp_reg))
        lines.append(f"LI(x{temp_reg}, 0x7fc00000)  # quiet NaN")
        lines.append(f"fmv.w.x f2, x{temp_reg}")
        lines.append("vfmv.v.f v6, f2  # v6 = quiet NaN")
        lines.append("csrwi fcsr, 0  # clear fcsr (fflags+frm) under FS=Dirty")
        lines.extend(set_status_fields(temp_reg, priv, fs=fs, vs=3))
        lines.append(test_data.add_testcase(f"vmflt_nan_fs{fs}", coverpoint, covergroup))
        lines.append("vmflt.vv v8, v6, v1  # quiet NaN operand -> NV flag")
        lines.append(gen_status_read_sigupd(temp_reg, test_data, priv))
        lines.append(write_sigupd(None, test_data, "fflags"))
    return lines


def _gen_fs_state_nonaffecting(test_data: TestData, temp_reg: int, covergroup: str, priv: str) -> list[str]:
    """cp_vectorfp_xstatus_fs_state_nonaffecting: vfadd.vv with various vs1/vs2 patterns under FS=Initial/Clean/Dirty."""
    status = STATUS_CSR[priv]
    coverpoint = f"cp_vectorfp_{status}_fs_state_nonaffecting"
    lines = [
        comment_banner(
            coverpoint, "vfadd.vv under FS=Initial/Clean/Dirty across all 4 vs1_zero × vs2_zero combinations"
        ),
    ]
    for fs in (1, 2, 3):
        for vs2_reg, vs1_reg, name in _VFADD_PATTERNS:
            lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
            lines.extend(_load_v_zero_one(temp_reg))
            lines.append("csrwi fcsr, 0  # clear fcsr under FS=Dirty")
            lines.extend(set_status_fields(temp_reg, priv, fs=fs, vs=3))
            lines.append(test_data.add_testcase(f"vfadd_{name}_fs{fs}", coverpoint, covergroup))
            # vfadd.vv vd, vs2, vs1  — operand order: result = vs2 + vs1
            lines.append(f"vfadd.vv v3, {vs2_reg}, {vs1_reg}")
            # All four patterns are exact, so no flag may be raised: that is the evidence
            # no FP state moved. FS is not committed; it may legally stay or go dirty.
            lines.append(write_sigupd(None, test_data, "fflags"))
    return lines


def _gen_fs_off(test_data: TestData, temp_reg: int, covergroup: str, priv: str) -> list[str]:
    """cp_vectorfp_xstatus_fs_off: vector-FP arith with FS=Off must trap, across vs1/vs2 patterns."""
    status = STATUS_CSR[priv]
    coverpoint = f"cp_vectorfp_{status}_fs_off"
    lines = [
        comment_banner(
            coverpoint, "vfadd.vv with FS=Off (VS=Dirty) -> illegal-instruction trap; cover all vs1/vs2 patterns"
        ),
    ]
    for vs2_reg, vs1_reg, name in _VFADD_PATTERNS:
        lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
        lines.extend(_load_v_zero_one(temp_reg))
        lines.extend(set_status_fields(temp_reg, priv, fs=0, vs=3))
        lines.append(test_data.add_testcase(f"vfadd_{name}_fs_off", coverpoint, covergroup))
        lines.append(f"vfadd.vv v3, {vs2_reg}, {vs1_reg}  # traps: FS=Off")
    lines.extend(set_status_fields(temp_reg, priv, fs=3, vs=3))
    return lines


def gen_vf_tests(test_data: TestData, priv: str, covergroup: str) -> list[TestChunk]:
    """Generate vector-FP × xstatus.FS tests in privilege mode priv ("M", "S" or "U")."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("VF")
    temp_reg = test_data.int_regs.get_register()

    tc.code.extend(_gen_fs_state_affecting_register(test_data, temp_reg, covergroup, priv))
    tc.code.extend(_gen_fs_state_affecting_csr(test_data, temp_reg, covergroup, priv))
    tc.code.extend(_gen_fs_state_nonaffecting(test_data, temp_reg, covergroup, priv))
    tc.code.extend(_gen_fs_off(test_data, temp_reg, covergroup, priv))

    test_data.int_regs.return_registers([temp_reg])
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
