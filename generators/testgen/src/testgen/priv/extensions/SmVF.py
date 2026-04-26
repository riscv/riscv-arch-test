##################################
# priv/extensions/SmVF.py
#
# SmVF privileged test generator: vector FP × mstatus.{FS,VS} (machine mode).
# Drives the SmVF_cg covergroup defined in coverpoints/priv/SmVF_coverage.svh.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmVF privileged test generator (vector FP / mstatus.FS state)."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "SmVF_cg"

_FS_MASK = 3 << 13
_VS_MASK = 3 << 9


def _set_fs_vs(fs: int, vs: int, temp_reg: int) -> list[str]:
    return [
        f"LI(x{temp_reg}, {_FS_MASK | _VS_MASK})",
        f"CSRC(mstatus, x{temp_reg})  # clear FS/VS",
        f"LI(x{temp_reg}, {(fs << 13) | (vs << 9)})",
        f"CSRS(mstatus, x{temp_reg})  # FS={fs} VS={vs}",
    ]


def _vector_setup(temp_reg: int) -> list[str]:
    return [
        f"vsetivli x{temp_reg}, 1, e32, m1, tu, mu",
        "csrw vstart, x0",
    ]


def _gen_state_tests(test_data: TestData, temp_reg: int, fp_temp_reg: int) -> list[str]:
    lines: list[str] = [
        comment_banner(
            "SmVF state-affecting / nonaffecting",
            "Run vector FP under FS=Initial(1) and FS=Clean(2) with VS=Dirty.",
        )
    ]
    for fs in (1, 2):
        lines.append(f"\n# --- FS={fs} ---")
        # Setup with FS=Dirty + VS=Dirty so we can prep regs.
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.extend(
            [
                f"LI(x{temp_reg}, 0x3f800000)",
                f"fmv.w.x f{fp_temp_reg}, x{temp_reg}",
                f"vfmv.v.f v1, f{fp_temp_reg}",  # v1 = 1.0 (nonzero)
                "vmv.v.i v2, 0",                  # v2 = 0
                "csrwi fflags, 0",
            ]
        )

        # vfmv.f.s (state_affecting_register) with v2=0 (vs1=0) and v1=1.0 (vs1!=0)
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfmv_f_s_v2_fs{fs}", "cp_vectorfp_mstatus_fs_state_affecting_register", _CG),
                f"vfmv.f.s f{fp_temp_reg}, v2",
                "nop",
            ]
        )
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfmv_f_s_v1_fs{fs}", "cp_vectorfp_mstatus_fs_state_affecting_register", _CG),
                f"vfmv.f.s f{fp_temp_reg}, v1",
                "nop",
            ]
        )

        # state_affecting_csr: vfdiv 1.0/0.0 -> raises DZ (fflags modified=true).
        # IMPORTANT: clear fflags BEFORE setting FS=Initial/Clean so the csrwi
        # doesn't transition FS to Dirty and break SAMPLE_BEFORE FS state.
        lines.append("csrwi fflags, 0")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfdiv_dz_fs{fs}", "cp_vectorfp_mstatus_fs_state_affecting_csr", _CG),
                "vfdiv.vv v3, v1, v2",
                "nop",
            ]
        )
        # state_affecting_csr with fflags_modified=false: vfadd 1.0+0 (no exception)
        lines.append("csrwi fflags, 0")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_clean_fs{fs}", "cp_vectorfp_mstatus_fs_state_affecting_csr", _CG),
                "vfadd.vv v3, v1, v2",
                "nop",
            ]
        )

        # state_nonaffecting cross: 4 combos of (vs1_zero, vs2_zero)
        # Order matters: csrwi fflags transitions FS to Dirty, so it must come
        # BEFORE _set_fs_vs (which restores FS=Initial/Clean) for SAMPLE_BEFORE
        # to see Initial/Clean. v1 is also refreshed before _set_fs_vs (vmv.v.x
        # to a vector reg doesn't dirty FS).
        # We need v1 = nonzero and v4 = zero immediately before each test, with
        # FS=Initial/Clean.
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                f"LI(x{temp_reg}, 0x123456789abcdef)",  # nonzero
                "vmv.v.i v4, 0",  # v4 = 0
            ]
        )
        # (vs1=0, vs2=0): vfadd v3, v4, v2  (vs2=v4=0, vs1=v2=0)
        lines.append("csrwi fflags, 0")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_zz_fs{fs}", "cp_vectorfp_mstatus_fs_state_nonaffecting", _CG),
                "vfadd.vv v3, v4, v2",
                "nop",
            ]
        )
        # (vs1=0, vs2!=0): vfadd v3, v1, v2  (vs2=v1=nz, vs1=v2=0)
        lines.append("csrwi fflags, 0")
        lines.append(f"vmv.v.x v1, x{temp_reg}  # refresh v1=nonzero")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_nz_fs{fs}", "cp_vectorfp_mstatus_fs_state_nonaffecting", _CG),
                "vfadd.vv v3, v1, v2",
                "nop",
            ]
        )
        # (vs1!=0, vs2=0): vfadd v3, v4, v1  (vs2=v4=0, vs1=v1=nz)
        lines.append("csrwi fflags, 0")
        lines.append(f"vmv.v.x v1, x{temp_reg}  # refresh v1=nonzero")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_zn_fs{fs}", "cp_vectorfp_mstatus_fs_state_nonaffecting", _CG),
                "vfadd.vv v3, v4, v1",
                "nop",
            ]
        )
        # (vs1!=0, vs2!=0): vfadd v3, v1, v1  (vs2=v1=nz, vs1=v1=nz)
        lines.append("csrwi fflags, 0")
        lines.append(f"vmv.v.x v1, x{temp_reg}  # refresh v1=nonzero")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_nn_fs{fs}", "cp_vectorfp_mstatus_fs_state_nonaffecting", _CG),
                "vfadd.vv v3, v1, v1",
                "nop",
            ]
        )

    return lines


def _gen_fs_off_trap(test_data: TestData, temp_reg: int) -> list[str]:
    lines: list[str] = [
        comment_banner(
            "cp_vectorfp_mstatus_fs_off",
            "FS=Off, VS!=Off: vector FP arithmetic must trap; cover all (vs1,vs2) zero combos.",
        )
    ]
    # Prep v1=1.0, v2=0, v4=0 with FS=dirty
    lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    fp_temp = test_data.float_regs.get_register()
    lines.extend(
        [
            f"LI(x{temp_reg}, 0x3f800000)",
            f"fmv.w.x f{fp_temp}, x{temp_reg}",
            f"vfmv.v.f v1, f{fp_temp}",
            "vmv.v.i v2, 0",
            "vmv.v.i v4, 0",
        ]
    )
    test_data.float_regs.return_registers([fp_temp])
    combos = [
        ("zz", "v4", "v2"),
        ("nz", "v1", "v2"),
        ("zn", "v4", "v1"),
        ("nn", "v1", "v1"),
    ]
    for tag, a, b in combos:
        # FS=Off, VS=Dirty
        lines.extend(_set_fs_vs(fs=0, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_off_{tag}", "cp_vectorfp_mstatus_fs_off", _CG),
                f"vfadd.vv v3, {a}, {b}  # traps",
                "nop",
            ]
        )
    # restore FS=Dirty
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
    """Generate SmVF tests."""
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])
    fp_temp_reg = test_data.float_regs.get_register()

    lines: list[str] = []
    lines.extend(_gen_state_tests(test_data, temp_reg, fp_temp_reg))
    lines.extend(_gen_fs_off_trap(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg])
    test_data.float_regs.return_registers([fp_temp_reg])
    return lines
