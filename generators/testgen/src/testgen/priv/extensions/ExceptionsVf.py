##################################
# priv/extensions/ExceptionsVf.py
#
# ExceptionsVf privileged test generator.
# Vector floating-point interactions with mstatus.{FS,VS}.
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsVf privileged test generator: vector FP × mstatus.{FS,VS}."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsVf_cg"

_FS_MASK = 3 << 13  # mstatus.FS = bits [14:13]
_VS_MASK = 3 << 9  # mstatus.VS = bits [10:9]


def _set_fs_vs(fs: int, vs: int, temp_reg: int) -> list[str]:
    """Force mstatus.FS=fs and mstatus.VS=vs (each in 0..3)."""
    return [
        f"LI(x{temp_reg}, {_FS_MASK | _VS_MASK})",
        f"CSRC(mstatus, x{temp_reg})  # clear FS and VS",
        f"LI(x{temp_reg}, {(fs << 13) | (vs << 9)})",
        f"CSRS(mstatus, x{temp_reg})  # FS={fs}, VS={vs}",
    ]


def _vector_setup(temp_reg: int) -> list[str]:
    """Configure a legal vtype/vl (SEW=32, LMUL=1, vl=1) and clear vstart."""
    return [
        f"vsetivli x{temp_reg}, 1, e32, m1, tu, mu  # vill=0, vl=1",
        "csrw vstart, x0",
    ]


def _seed_misa(temp_reg: int) -> list[str]:
    # Sail only emits misa to the rvvi trace when an instruction touches it,
    # so any coverpoint that reads misa needs an explicit access first.
    return [f"csrr x{temp_reg}, misa  # seed misa into rvvi trace"]


def _gen_vs_off_trap(test_data: TestData, temp_reg: int) -> list[str]:
    coverpoint = "cp_mstatus_vs_off"
    lines = [
        comment_banner(coverpoint, "VS=Off, FS=non-Off: vector FP must trap (illegal-instruction)"),
    ]
    lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    lines.extend(_seed_misa(temp_reg))
    lines.extend(
        [
            f"LI(x{temp_reg}, {_VS_MASK})",
            f"CSRC(mstatus, x{temp_reg})  # VS=Off (FS stays non-Off)",
            test_data.add_testcase("vfadd_vv_vs_off", coverpoint, _CG),
            "vfadd.vv v8, v16, v24  # traps: VS=Off",
            "nop",
            f"LI(x{temp_reg}, {3 << 9})",
            f"CSRS(mstatus, x{temp_reg})  # restore VS=Dirty",
        ]
    )
    return lines


def _gen_fs_off_trap(test_data: TestData, temp_reg: int) -> list[str]:
    coverpoint = "cp_mstatus_fs_off"
    lines = [
        comment_banner(coverpoint, "FS=Off, VS=non-Off: vector FP must trap (illegal-instruction)"),
    ]
    lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
    lines.extend(_vector_setup(temp_reg))
    lines.extend(_seed_misa(temp_reg))
    lines.extend(
        [
            f"LI(x{temp_reg}, {_FS_MASK})",
            f"CSRC(mstatus, x{temp_reg})  # FS=Off (VS stays Dirty)",
            test_data.add_testcase("vfadd_vv_fs_off", coverpoint, _CG),
            "vfadd.vv v8, v16, v24  # traps: FS=Off",
            "nop",
            f"LI(x{temp_reg}, {3 << 13})",
            f"CSRS(mstatus, x{temp_reg})  # restore FS=Dirty",
        ]
    )
    return lines


def _gen_fs_state_tests(test_data: TestData, temp_reg: int, fp_temp_reg: int) -> list[str]:
    coverpoint = "cp_vectorfp_mstatus_fs_state"
    lines = [
        comment_banner(
            coverpoint,
            "Sample vector-FP instructions under each non-Off FS state\n"
            "(1=Initial, 2=Clean, 3=Dirty). The spec permits a legal\n"
            "always-dirty implementation, so we cannot directly observe an\n"
            "FS state-transition in coverage; signature comparison between\n"
            "models catches divergence on transitioning impls. Three\n"
            "instruction classes are exercised per FS state:\n"
            "  vfmv.f.s    -- writes f-reg (would-be 'state-affecting register')\n"
            "  vfdiv.vv    -- raises DZ in fflags (would-be 'state-affecting csr')\n"
            "  vfadd.vv 0,0 -- 'nonaffecting' (no observable coverpoint; see header)",
        ),
    ]

    fs_names = {1: "initial", 2: "clean", 3: "dirty"}
    for fs, name in fs_names.items():
        lines.append(f"\n# --- FS={name} ({fs}) ---")
        # Setup with FS=Dirty + VS=Dirty so we can prep fp/vector data and clear fflags
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.extend(_vector_setup(temp_reg))
        lines.extend(
            [
                f"LI(x{temp_reg}, 0x3f800000)  # 1.0f bit pattern",
                f"fmv.w.x f{fp_temp_reg}, x{temp_reg}",
                f"vfmv.v.f v1, f{fp_temp_reg}        # v1 = {{1.0,...}}",
                "vmv.v.i v2, 0                  # v2 = 0",
                "csrwi fflags, 0",
            ]
        )

        # Drop FS to target state (keep VS=Dirty), then sample insns
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(_seed_misa(temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfmv_f_s_fs{fs}", coverpoint, _CG),
                f"vfmv.f.s f{fp_temp_reg}, v2  # writes f-reg",
                "nop",
            ]
        )

        # On a transitioning impl, vfmv.f.s may have set FS=Dirty. Re-arm to target.
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfdiv_vv_fs{fs}", coverpoint, _CG),
                "vfdiv.vv v3, v1, v2  # 1.0/0.0 -> DZ in fflags",
                "nop",
            ]
        )

        # Re-prep v1=0 for nonaffecting case (needs FS=Dirty to be safe with vmv)
        lines.extend(_set_fs_vs(fs=3, vs=3, temp_reg=temp_reg))
        lines.append("vmv.v.i v1, 0  # v1 = 0 for nonaffecting case")
        lines.extend(_set_fs_vs(fs=fs, vs=3, temp_reg=temp_reg))
        lines.extend(
            [
                test_data.add_testcase(f"vfadd_vv_zero_fs{fs}", coverpoint, _CG),
                "vfadd.vv v3, v1, v2  # vs1=vs2=0; nonaffecting (no coverpoint)",
                "nop",
            ]
        )

    return lines


@add_priv_test_generator(
    "ExceptionsVf",
    required_extensions=["Sm", "I", "M", "V", "F", "Zicsr"],
    march_extensions=["I", "M", "F", "V", "Zicsr"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_exceptionsvf(test_data: TestData) -> list[str]:
    """Generate ExceptionsVf tests (vector FP × mstatus.{FS,VS})."""
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])
    fp_temp_reg = test_data.float_regs.get_register()

    lines: list[str] = []
    lines.extend(_gen_vs_off_trap(test_data, temp_reg))
    lines.extend(_gen_fs_off_trap(test_data, temp_reg))
    lines.extend(_gen_fs_state_tests(test_data, temp_reg, fp_temp_reg))

    test_data.int_regs.return_registers([temp_reg])
    test_data.float_regs.return_registers([fp_temp_reg])
    return lines
