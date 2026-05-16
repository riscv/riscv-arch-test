##################################
# priv/extensions/SmVF.py
#
# SmVF privileged test generator.
# Vector floating-point interactions with mstatus.FS state transitions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmVF privileged test generator: vector-FP × mstatus.FS state."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "SmVF_cg"

_FS_MASK = 3 << 13  # mstatus.FS = bits [14:13]
_VS_MASK = 3 << 9  # mstatus.VS = bits [10:9]


def _set_fs_vs(fs: int, vs: int, temp_reg: int) -> list[str]:
    return [
        f"LI(x{temp_reg}, {_FS_MASK | _VS_MASK})",
        f"CSRC(mstatus, x{temp_reg})  # clear FS and VS",
        f"LI(x{temp_reg}, {(fs << 13) | (vs << 9)})",
        f"CSRS(mstatus, x{temp_reg})  # FS={fs}, VS={vs}",
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
    lines.append("vfmv.v.f v1, f1   # v1 = 1.0 in each lane")
    lines.append("vmv.v.i v2, 0     # v2 = 0")
    lines.append("vfmv.v.f v4, f1   # v4 = 1.0")
    lines.append("vfmv.v.f v5, f1   # v5 = 1.0")
    return lines


def _gen_fs_state_affecting_register(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vectorfp_mstatus_fs_state_affecting_register: vfmv.f.s with FS=Initial/Clean."""
    coverpoint = "cp_vectorfp_mstatus_fs_state_affecting_register"
    lines = [
        comment_banner(coverpoint, "vfmv.f.s under FS=Initial(1)/Clean(2); should set FS=Dirty"),
    ]
    for fs in (1, 2):
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.extend(_load_v_zero_one(temp_reg))
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.append(test_data.add_testcase(f"vfmv_f_s_fs{fs}", coverpoint, _CG))
        lines.append("vfmv.f.s f1, v2")
        lines.append("nop")
    return lines


def _gen_fs_state_affecting_csr(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vectorfp_mstatus_fs_state_affecting_csr: vector-FP arith that raises fflags."""
    coverpoint = "cp_vectorfp_mstatus_fs_state_affecting_csr"
    lines = [
        comment_banner(coverpoint, "vfdiv.vv 1.0/0.0 under FS=Initial/Clean; sets DZ in fflags"),
    ]
    for fs in (1, 2):
        for trial in range(3):
            lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
            lines.extend(_vector_setup(temp_reg))
            lines.extend(_load_v_zero_one(temp_reg))
            lines.append(
                "csrwi fcsr, 0  # clear fcsr (fflags+frm) under FS=Dirty; clearing fflags alone leaves fcsr stale in some traces"
            )
            lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
            lines.append(test_data.add_testcase(f"vfdiv_vv_fs{fs}_t{trial}", coverpoint, _CG))
            lines.append("vfdiv.vv v3, v1, v2  # 1.0/0.0 -> +inf, DZ flag")
            lines.append("nop")
    # Also exercise an exception with vfadd inf-inf and vfmul 0*inf
    for fs in (1, 2):
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.extend(_load_v_zero_one(temp_reg))
        # build +inf in v6 by 1.0/0.0 first under FS=Dirty
        lines.append("vfdiv.vv v6, v1, v2  # v6 = +inf")
        lines.append(f"LI(x{temp_reg}, 0xff800000)  # -inf")
        lines.append(f"fmv.w.x f2, x{temp_reg}")
        lines.append("vfmv.v.f v7, f2  # v7 = -inf")
        lines.append("csrwi fcsr, 0  # clear fcsr (fflags+frm) under FS=Dirty")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.append(test_data.add_testcase(f"vfadd_inf_minf_fs{fs}", coverpoint, _CG))
        lines.append("vfadd.vv v3, v6, v7  # inf + -inf -> NV flag")
        lines.append("nop")
    return lines


def _gen_fs_state_nonaffecting(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vectorfp_mstatus_fs_state_nonaffecting: vfadd.vv with various vs1/vs2 patterns under FS=Initial/Clean."""
    coverpoint = "cp_vectorfp_mstatus_fs_state_nonaffecting"
    lines = [
        comment_banner(coverpoint, "vfadd.vv under FS=Initial/Clean across all 4 vs1_zero × vs2_zero combinations"),
    ]
    # 4 combinations: (vs1_zero, vs2_zero)
    # vs1 = v1 (1.0 nonzero) vs v2 (0) ; vs2 likewise
    pattern_pairs = [
        ("v2", "v2", "vs1_0_vs2_0"),  # both zero
        ("v1", "v2", "vs1_n_vs2_0"),  # vs1!=0, vs2=0
        ("v2", "v1", "vs1_0_vs2_n"),  # vs1=0, vs2!=0
        ("v1", "v4", "vs1_n_vs2_n"),  # both nonzero
    ]
    for fs in (1, 2):
        for vs2_reg, vs1_reg, name in pattern_pairs:
            lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
            lines.extend(_vector_setup(temp_reg))
            lines.extend(_load_v_zero_one(temp_reg))
            lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
            lines.append(test_data.add_testcase(f"vfadd_{name}_fs{fs}", coverpoint, _CG))
            # vfadd.vv vd, vs2, vs1  — operand order: result = vs2 + vs1
            lines.append(f"vfadd.vv v3, {vs2_reg}, {vs1_reg}")
            lines.append("nop")
    return lines


def _gen_fs_off(test_data: TestData, temp_reg: int) -> list[str]:
    """cp_vectorfp_mstatus_fs_off: vector-FP arith with FS=Off must trap, across vs1/vs2 patterns."""
    coverpoint = "cp_vectorfp_mstatus_fs_off"
    lines = [
        comment_banner(
            coverpoint, "vfadd.vv with FS=Off (VS=Dirty) -> illegal-instruction trap; cover all vs1/vs2 patterns"
        ),
    ]
    pattern_pairs = [
        ("v2", "v2", "vs1_0_vs2_0"),
        ("v1", "v2", "vs1_n_vs2_0"),
        ("v2", "v1", "vs1_0_vs2_n"),
        ("v1", "v4", "vs1_n_vs2_n"),
    ]
    for vs2_reg, vs1_reg, name in pattern_pairs:
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.extend(_load_v_zero_one(temp_reg))
        lines.extend(_set_fs_vs(fs=0, vs=3, temp_reg=temp_reg))
        lines.append(test_data.add_testcase(f"vfadd_{name}_fs_off", coverpoint, _CG))
        lines.append(f"vfadd.vv v3, {vs2_reg}, {vs1_reg}  # traps: FS=Off")
        lines.append("nop")
    lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
    return lines


@add_priv_test_generator(
    "SmVF",
    required_extensions=["Sm", "I", "M", "V", "F", "Zicsr"],
    march_extensions=["I", "M", "F", "V", "Zicsr"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_smvf(test_data: TestData) -> list[str]:
    """Generate SmVF tests (vector-FP × mstatus.FS state)."""
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines: list[str] = []
    lines.extend(_gen_fs_state_affecting_register(test_data, temp_reg))
    lines.extend(_gen_fs_state_affecting_csr(test_data, temp_reg))
    lines.extend(_gen_fs_state_nonaffecting(test_data, temp_reg))
    lines.extend(_gen_fs_off(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg])
    return lines
