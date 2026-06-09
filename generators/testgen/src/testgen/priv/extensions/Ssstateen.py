# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CSR_OPS = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]


def _enter_umode(test_data: TestData, temp_reg: int) -> list[str]:
    """Drop to U-mode via RVTEST macro."""
    return [
        "\tRVTEST_GOTO_LOWER_MODE Umode  # enter U-mode",
    ]


def _enter_smode(test_data: TestData, temp_reg: int) -> list[str]:
    """Drop to S-mode via RVTEST macro."""
    return [
        "\tRVTEST_GOTO_LOWER_MODE Smode  # enter S-mode",
    ]


def _return_mmode(test_data: TestData, temp_reg: int) -> list[str]:
    """Return to M-mode via RVTEST macro."""
    return [
        "\tRVTEST_GOTO_MMODE  # return to M-mode",
    ]


def _set_se0(temp_reg: int) -> list[str]:
    """Emit instructions to set SE0=1 in mstateen0/mstateen0h."""
    return [
        "#if __riscv_xlen == 64",
        f"\tLI(x{temp_reg}, 0x8000000000000000)  # SE0 = bit 63 of mstateen0",
        f"\tCSRS(mstateen0, x{temp_reg})          # set SE0=1",
        "#else",
        f"\tLI(x{temp_reg}, 0x80000000)           # SE0 = bit 31 of mstateen0h",
        f"\tCSRS(mstateen0h, x{temp_reg})          # set SE0=1",
        "#endif",
    ]


def _clear_se0(temp_reg: int) -> list[str]:
    """Emit instructions to clear SE0=0 in mstateen0/mstateen0h."""
    return [
        "#if __riscv_xlen == 64",
        f"\tLI(x{temp_reg}, 0x8000000000000000)  # SE0 = bit 63 of mstateen0",
        f"\tCSRC(mstateen0, x{temp_reg})          # clear SE0=0",
        "#else",
        f"\tLI(x{temp_reg}, 0x80000000)           # SE0 = bit 31 of mstateen0h",
        f"\tCSRC(mstateen0h, x{temp_reg})          # clear SE0=0",
        "#endif",
    ]


def _save_mstateen(save_reg: int, save_regh: int) -> list[str]:
    """Save mstateen0 (and mstateen0h on RV32) into separate registers."""
    return [
        f"\tCSRR(x{save_reg}, mstateen0)          # save mstateen0",
        "#if __riscv_xlen == 32",
        f"\tCSRR(x{save_regh}, mstateen0h)         # save mstateen0h on RV32",
        "#endif",
    ]


def _restore_mstateen(save_reg: int, save_regh: int) -> list[str]:
    """Restore mstateen0 (and mstateen0h on RV32) from separate registers."""
    return [
        f"\tCSRW(mstateen0, x{save_reg})           # restore mstateen0",
        "#if __riscv_xlen == 32",
        f"\tCSRW(mstateen0h, x{save_regh})          # restore mstateen0h on RV32",
        "#endif",
    ]


# ---------------------------------------------------------------------------
# cp_mstateen0_se0_zero_controls_sstateen0
#   Cross: csrops × priv_mode_s × se0_zero × sstateen_csrs
#   Must run from S-mode (priv_mode_s), not M-mode.
# ---------------------------------------------------------------------------


def _generate_se0_zero_controls_sstateen0(test_data: TestData) -> list[str]:
    coverpoint = "cp_mstateen0_se0_zero_controls_sstateen0"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSR ops to sstateen0 from S-mode with mstateen0.SE0=0 (should trap)",
        )
    )

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, ones_reg = test_data.int_regs.get_registers(
        5, exclude_regs=[0]
    )

    lines.extend(
        [
            f"\tCSRR(x{save_sstateen}, sstateen0)   # save sstateen0",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )
    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    lines.extend(_clear_se0(temp_reg))

    # Must sample from S-mode to hit priv_mode_s bin
    lines.extend(_enter_smode(test_data, temp_reg))

    for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
        insn = f"\t{op}(x{temp_reg}, sstateen0)" if op == "CSRR" else f"\t{op}(x{temp_reg}, sstateen0, x{ones_reg})"
        lines.extend(
            [
                "",
                test_data.add_testcase(f"sstateen0_{op.lower()}_se0_0_smode", coverpoint, covergroup),
                insn,
                "\tnop",
            ]
        )

    lines.extend(_return_mmode(test_data, temp_reg))
    lines.extend(["", f"\tCSRW(sstateen0, x{save_sstateen})   # restore sstateen0"])
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_mstateen0_se0_one_controls_sstateen0
#   Cross: csrops × priv_mode_s × se0_one × sstateen_csrs
#   Must run from S-mode (priv_mode_s).
# ---------------------------------------------------------------------------


def _generate_se0_one_controls_sstateen0(test_data: TestData) -> list[str]:
    coverpoint = "cp_mstateen0_se0_one_controls_sstateen0"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSR ops to sstateen0 from S-mode with mstateen0.SE0=1 (access permitted)",
        )
    )

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, ones_reg = test_data.int_regs.get_registers(
        5, exclude_regs=[0]
    )

    lines.extend(
        [
            f"\tCSRR(x{save_sstateen}, sstateen0)   # save sstateen0",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )
    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    lines.extend(_set_se0(temp_reg))

    # Must sample from S-mode to hit priv_mode_s bin
    lines.extend(_enter_smode(test_data, temp_reg))

    for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
        insn = f"\t{op}(x{temp_reg}, sstateen0)" if op == "CSRR" else f"\t{op}(x{temp_reg}, sstateen0, x{ones_reg})"
        lines.extend(
            [
                "",
                test_data.add_testcase(f"sstateen0_{op.lower()}_se0_1_smode", coverpoint, covergroup),
                insn,
                "\tnop",
            ]
        )

    lines.extend(_return_mmode(test_data, temp_reg))
    lines.extend(["", f"\tCSRW(sstateen0, x{save_sstateen})   # restore sstateen0"])
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses
#   Cross: priv_mode_u × sstateen_csrs × csrops × se0_one
#   U-mode only (unchanged).
# ---------------------------------------------------------------------------


def _generate_csr_illegal_accesses(test_data: TestData) -> list[str]:
    coverpoint = "cp_csr_illegal_accesses"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "Attempt CSR ops to sstateenN CSRs from U-mode with SE0=1 (should trap)",
        )
    )

    temp_reg, save_mstateen, save_mstatenh = test_data.int_regs.get_registers(3, exclude_regs=[0])

    sstateen_csrs = ["sstateen0", "sstateen1", "sstateen2", "sstateen3"]
    csr_ops = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]

    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    lines.extend(_set_se0(temp_reg))
    lines.extend(_enter_umode(test_data, temp_reg))

    for csr in sstateen_csrs:
        for op in csr_ops:
            if op == "CSRR":
                insn = f"\t{op}(x{temp_reg}, {csr})  # illegal from U-mode"
            else:
                insn = f"\t{op}(x{temp_reg}, {csr}, x{temp_reg})  # illegal from U-mode"
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode_se0_1", coverpoint, covergroup),
                    insn,
                    "\tnop",
                ]
            )

    lines.extend(_return_mmode(test_data, temp_reg))
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: priv_mode_s × sstateen_walk_csr × csrops × csr_walk × se0_one
#   Must run from S-mode with SE0=1. csr_walk_test covers csrw+csrs+csrc
#   internally (walking-1s uses CSRW+CSRS, walking-0s uses CSRW+CSRC).
# ---------------------------------------------------------------------------


def _generate_walking_ones(test_data: TestData) -> list[str]:
    coverpoint = "cp_walking_ones"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns on sstateen0 from S-mode with SE0=1",
        )
    ]

    save_mstateen, save_mstatenh, temp_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    lines.extend(_set_se0(temp_reg))
    test_data.int_regs.return_registers([save_mstateen, save_mstatenh, temp_reg])

    # The walk itself must be sampled in S-mode so priv_mode_s bin is hit
    # We enter S-mode, perform the walk, then return to M-mode.
    # csr_walk_test emits CSRW+CSRS (walking-1s) and CSRW+CSRC (walking-0s),
    # satisfying the csrops cross (csrw, csrs, csrc all hit).
    lines.extend(
        [
            "",
            test_data.add_testcase("sstateen0_walk_se0_1_smode", coverpoint, covergroup),
        ]
    )

    # Enter S-mode before the walk
    save_mstateen, save_mstatenh, temp_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])
    lines.extend(_enter_smode(test_data, temp_reg))
    test_data.int_regs.return_registers([save_mstateen, save_mstatenh, temp_reg])

    lines.extend(csr_walk_test(test_data, ("sstateen0", 0x7), covergroup, coverpoint))

    save_mstateen, save_mstatenh, temp_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])
    lines.extend(_return_mmode(test_data, temp_reg))
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
    test_data.int_regs.return_registers([save_mstateen, save_mstatenh, temp_reg])

    return lines


# ---------------------------------------------------------------------------
# cp_jvt
#   Cross: priv_mode_maybes_u × csrops × jvt_csr × jvt_state × se0_one
#   priv_mode_maybes_u = S-mode + U-mode.
#   The old generator split this across _generate_jvt (M-mode) and
#   _generate_jvt_lower_mode (U-mode). Both are wrong/incomplete.
#   This single function covers S-mode and U-mode.
# ---------------------------------------------------------------------------


def _generate_jvt(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSR ops on jvt from S/U-mode with sstateen0.JVT enabled/disabled under SE0=1",
        )
    )

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_jvt, ones_reg = test_data.int_regs.get_registers(
        6, exclude_regs=[0]
    )

    JVT_BIT = 2
    csr_ops = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]

    # priv_mode_maybes_u = S-mode + U-mode
    modes = [
        ("smode", _enter_smode),
        ("umode", _enter_umode),
    ]

    for mode_label, enter_fn in modes:
        if mode_label == "smode":
            lines.append("#ifdef S_SUPPORTED")
        for jvt_state in [0, 1]:
            jvt_action = "CSRC" if jvt_state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"\t# SE0=1, sstateen0.JVT={jvt_state}, {mode_label}",
                    f"\tCSRR(x{save_sstateen}, sstateen0)  # save sstateen0",
                    f"\tCSRR(x{save_jvt}, jvt)             # save jvt",
                    f"\tLI(x{ones_reg}, -1)",
                ]
            )
            lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
            lines.extend(_set_se0(temp_reg))
            lines.extend(
                [
                    f"\tLI(x{temp_reg}, {1 << JVT_BIT})",
                    f"\t{jvt_action}(sstateen0, x{temp_reg})  # sstateen0.JVT = {jvt_state}",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for op in csr_ops:
                insn = f"\t{op}(x{temp_reg}, jvt)" if op == "CSRR" else f"\t{op}(x{temp_reg}, jvt, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{op.lower()}_jvt_se0_1_jvt_{jvt_state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        insn,
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            lines.extend(
                [
                    f"\tCSRW(sstateen0, x{save_sstateen})  # restore sstateen0",
                    f"\tCSRW(jvt, x{save_jvt})             # restore jvt",
                ]
            )
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
        if mode_label == "smode":
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_jvt, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower
#   Cross: priv_mode_maybes_u × misa_F × se0_one × sstateen0_fcsr_bit × csrops × fcsr_lower_mode_csrs
#   priv_mode_maybes_u = S-mode + U-mode (unchanged from original).
# ---------------------------------------------------------------------------


def _generate_fcsr_lower(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSR ops on frm/fflags/fcsr from S/U-mode with SE0=1 and sstateen0.FCSR states",
        )
    )

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_reg = test_data.int_regs.get_registers(
        5, exclude_regs=[0]
    )
    fp_csrs = ["frm", "fflags", "fcsr"]
    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR

    for fcsr_bit in [0, 1]:
        fcsr_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_fn in [("smode", _enter_smode), ("umode", _enter_umode)]:
            if mode_label == "smode":
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(
                [
                    "",
                    f"\t# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"\tCSRR(x{save_sstateen}, sstateen0)",
                ]
            )
            lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
            lines.extend(_set_se0(temp_reg))
            lines.extend(
                [
                    f"\tLI(x{temp_reg}, {1 << FCSR_BIT})",
                    f"\t{fcsr_action}(sstateen0, x{temp_reg})  # sstateen0.FCSR = {fcsr_bit}",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for csr in fp_csrs:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"csrrw_{csr}_se0_1_fcsr{fcsr_bit}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        f"\tCSRR(x{save_reg}, {csr})",
                        f"\tCSRRW(x{temp_reg}, {csr}, x{save_reg})  # csrrw {csr} from {mode_label}",
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            lines.extend([f"\tCSRW(sstateen0, x{save_sstateen})  # restore sstateen0"])
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
            if mode_label == "smode":
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_fp_instrs
#   Cross: priv_mode_maybes_u × misa_F × se0_one × sstateen0_fcsr_bit × fp_instrs
#   priv_mode_maybes_u = S-mode + U-mode.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_fp_instrs"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "FP instructions from S/U-mode with SE0=1 and sstateen0.FCSR states",
        )
    )

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, scratch_reg = test_data.int_regs.get_registers(
        5, exclude_regs=[0]
    )

    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR

    fp_instrs = [
        ("fadd.s f0, f1, f2", "fadd_s"),
        ("flw f0, 0(x{scratch})", "flw"),
        ("fcvt.w.s x{temp}, f0", "fcvt_w_s"),
        ("fcvt.s.w f0, x0", "fcvt_s_w"),
        ("fmv.x.w x{temp}, f0", "fmv_x_w"),
        ("fmv.w.x f0, x{temp}", "fmv_w_x"),
        ("fclass.s x{temp}, f0", "fclass_s"),
    ]

    lines.extend([f"\tLA(x{scratch_reg}, scratch)  # scratch memory pointer"])

    for fcsr_bit in [0, 1]:
        fcsr_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_fn in [("smode", _enter_smode), ("umode", _enter_umode)]:
            if mode_label == "smode":
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(
                [
                    "",
                    f"\t# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"\tCSRR(x{save_sstateen}, sstateen0)",
                ]
            )
            lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
            lines.extend(_set_se0(temp_reg))
            lines.extend(
                [
                    f"\tLI(x{temp_reg}, {1 << FCSR_BIT})",
                    f"\t{fcsr_action}(sstateen0, x{temp_reg})  # sstateen0.FCSR = {fcsr_bit}",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for insn_template, label in fp_instrs:
                insn = insn_template.replace("{temp}", str(temp_reg)).replace("{scratch}", str(scratch_reg))
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{label}_se0_1_fcsr{fcsr_bit}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        f"\t{insn}  # fp instr from {mode_label} fcsr={fcsr_bit}",
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            lines.extend([f"\tCSRW(sstateen0, x{save_sstateen})  # restore sstateen0"])
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
            if mode_label == "smode":
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, scratch_reg])
    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Ssstateen",
    required_extensions=["S", "Zicsr", "Smstateen", "Ssstateen"],
    march_extensions=["Ssstateen", "Smstateen", "Zicsr", "Zcmt"],
)
def make_ssstateen(test_data: TestData) -> list[str]:
    """Generate tests for Ssstateen state-enable extension testsuite."""
    lines: list[str] = []

    # Unconditional coverpoints — required by all Ssstateen targets
    lines.extend(_generate_se0_zero_controls_sstateen0(test_data))
    lines.extend(_generate_se0_one_controls_sstateen0(test_data))
    lines.extend(_generate_csr_illegal_accesses(test_data))
    lines.extend(_generate_walking_ones(test_data))

    # cp_fcsr_lower, cp_fcsr_fp_instrs — only when F (Zfinx) is supported
    lines.append("#ifdef ZFINX_SUPPORTED")
    lines.extend(_generate_fcsr_lower(test_data))
    lines.extend(_generate_fcsr_lower_fp_instrs(test_data))
    lines.append("#endif  // ZFINX_SUPPORTED")

    # cp_jvt — only when Zcmt is supported (covers both S-mode and U-mode)
    lines.append("#ifdef ZCMT_SUPPORTED")
    lines.extend(_generate_jvt(test_data))
    lines.append("#endif  // ZCMT_SUPPORTED")

    return lines
