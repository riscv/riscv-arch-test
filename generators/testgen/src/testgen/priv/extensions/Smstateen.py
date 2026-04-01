##################################
# Smstateen.py
#
# Smstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test, gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses  (cross priv_mode_u, csr, csrrw)
#   → From U-mode, try CSRRW to each mstateenN CSR; these should trap.
# ---------------------------------------------------------------------------


def _generate_csr_illegal_accesses(test_data: TestData) -> list[str]:
    coverpoint = "cp_csr_illegal_accesses"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "Attempt CSRRW to mstateenN CSRs from U-mode (should trap)",
        )
    )

    temp_reg, val_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    # mstateen0..3 (and high halves on RV32)
    csrs_base = ["mstateen0", "mstateen1", "mstateen2", "mstateen3"]
    lines.extend(_enter_umode(test_data, temp_reg))

    for csr in csrs_base:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"{csr}_csrrw_umode", coverpoint, covergroup),
                f"\tCSRRW(x{val_reg}, {csr}, x{val_reg})  # illegal from U-mode",
                "\tnop",
            ]
        )

    lines.extend(
        [
            "#ifdef XLEN32",
        ]
    )
    for csr in ["mstateen0h", "mstateen1h", "mstateen2h", "mstateen3h"]:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"{csr}_csrrw_umode", coverpoint, covergroup),
                f"\tCSRRW(x{val_reg}, {csr}, x{val_reg})  # illegal from U-mode",
                "\tnop",
            ]
        )
    lines.append("#endif")

    lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones  (cross csr, csrrw, csr_walk)
#   → CSRRW each mstateenN with a walking-1 and walking-0 pattern.
#   For RV64 the walk is over rs1_val; for RV32 over the CSR value read back.
#   We use csr_walk_test() from csr.py which already handles this.
# ---------------------------------------------------------------------------


def _generate_walking_ones(test_data: TestData) -> list[str]:
    coverpoint = "cp_walking_ones"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns written to each mstateenN CSR via CSRRW",
        )
    )

    # csr_walk_test() allocates its own registers internally via test_data.
    # We only need save_reg ourselves to preserve the original CSR value.
    save_reg = test_data.int_regs.get_registers(1, exclude_regs=[0])[0]

    csrs_base = ["mstateen0", "mstateen1", "mstateen2", "mstateen3"]

    for csr in csrs_base:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"{csr}_walk", coverpoint, covergroup),
                f"\tCSRR(x{save_reg}, {csr})   # save original value",
            ]
        )
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))
        lines.extend(
            [
                f"\tCSRW({csr}, x{save_reg})   # restore original value",
            ]
        )

    lines.extend(["#ifdef XLEN32"])
    for csr in ["mstateen0h", "mstateen1h", "mstateen2h", "mstateen3h"]:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"{csr}_walk", coverpoint, covergroup),
                f"\tCSRR(x{save_reg}, {csr})   # save original value",
            ]
        )
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))
        lines.extend(
            [
                f"\tCSRW({csr}, x{save_reg})   # restore original value",
            ]
        )
    lines.append("#endif")

    test_data.int_regs.return_registers([save_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_ro_zero  (cross misa_F, csrrs, mstateen0_fcsr_bit)
#   bins of interest: misa_F=F_set AND mstateen0_fcsr_bit=fcsr_zero
#   → With F in misa but mstateen0.FCSR=0, CSRRS on fcsr should read zero.
#   ignore_bins cover the other combinations so only the enabled bin matters.
# ---------------------------------------------------------------------------


def _generate_fcsr_ro_zero(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_ro_zero"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "With mstateen0.FCSR=0 and F present, CSRRS on fcsr should return zero",
        )
    )

    temp_reg, save_mstateen, save_fcsr = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_fcsr}, fcsr)            # save fcsr",
            "",
            "\t# Clear mstateen0 FCSR bit (bit 0)",
            f"\tLI(x{temp_reg}, 1)",
            f"\tCSRC(mstateen0, x{temp_reg})        # mstateen0.FCSR = 0",
            "",
            test_data.add_testcase("csrrs_fcsr_mstateen_fcsr_zero", coverpoint, covergroup),
            f"\tCSRRS(x{temp_reg}, fcsr, x0)        # read fcsr with mstateen0.FCSR=0",
            gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
            gen_csr_read_sigupd(temp_reg, "fcsr", test_data),
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(fcsr, x{save_fcsr})            # restore fcsr",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_fcsr])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr  (cross misa_F, mstateen0_fcsr_bit, csrrw, fscr_csr)
#   Active bin: misa_F=F_set, mstateen0_fcsr_bit=fcsr_one, csrrw present, fscr_csr=fcsr
#   → With mstateen0.FCSR=1 and F present, CSRRW to fcsr works normally.
# ---------------------------------------------------------------------------


def _generate_fcsr(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to fcsr with mstateen0.FCSR=1 (enabled) and F extension present",
        )
    )

    ones_reg, save_mstateen, save_fcsr, temp_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_fcsr}, fcsr)            # save fcsr",
            "",
            "\t# Set mstateen0 FCSR bit (bit 0) = 1",
            f"\tLI(x{temp_reg}, 1)",
            f"\tCSRS(mstateen0, x{temp_reg})        # mstateen0.FCSR = 1",
            f"\tLI(x{ones_reg}, -1)",
            "",
            test_data.add_testcase("csrrw_fcsr_mstateen_fcsr_one", coverpoint, covergroup),
            f"\tCSRRW(x{temp_reg}, fcsr, x{ones_reg})  # write all-ones to fcsr",
            gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
            gen_csr_read_sigupd(temp_reg, "fcsr", test_data),
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(fcsr, x{save_fcsr})            # restore fcsr",
        ]
    )

    test_data.int_regs.return_registers([ones_reg, save_mstateen, save_fcsr, temp_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower  (cross priv_mode_s_u, misa_F, mstateen0_fcsr_bit, csrrw, fcsr_lower_mode_csrs)
#   → From S/U-mode, CSRRW to frm/fflags/fcsr with both mstateen0.FCSR states.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to frm/fflags/fcsr from S/U-mode with mstateen0.FCSR enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])
    fp_csrs = ["frm", "fflags", "fcsr"]

    for fcsr_bit in [0, 1]:
        bit_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_fn in [("smode", _enter_smode), ("umode", _enter_umode)]:
            lines.extend(
                [
                    "",
                    f"\t# mstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"\tCSRR(x{save_mstateen}, mstateen0)",
                    f"\tLI(x{temp_reg}, 1)",
                    f"\t{bit_action}(mstateen0, x{temp_reg})  # set FCSR bit to {fcsr_bit}",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for csr in fp_csrs:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"csrrw_{csr}_fcsr{fcsr_bit}_{mode_label}", coverpoint, covergroup),
                        f"\tCSRR(x{save_reg}, {csr})",
                        f"\tCSRRW(x{temp_reg}, {csr}, x{save_reg})  # csrrw {csr} from {mode_label}",
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            lines.extend(
                [
                    f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
                ]
            )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower_fp_instrs  (cross priv_mode_s_u, misa_F, mstateen0_fcsr_bit, fp_instrs)
#   → From S/U-mode, execute FP instructions with mstateen0.FCSR=0 and =1.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower_fp_instrs"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "FP instructions from S/U-mode with mstateen0.FCSR enabled and disabled",
        )
    )

    temp_reg, save_mstateen, scratch_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    fp_instrs = [
        "fadd.s f0, f1, f2",
        "flw f0, 0(x{scratch})",
        "fcvt.w.s x{temp}, f0",
        "fcvt.s.w f0, x0",
        "fmv.x.w x{temp}, f0",
        "fmv.w.x f0, x{temp}",
        "fclass.s x{temp}, f0",
    ]

    lines.extend(
        [
            f"\tLA(x{scratch_reg}, scratch)  # scratch memory pointer",
        ]
    )

    for fcsr_bit in [0, 1]:
        bit_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_fn in [("smode", _enter_smode), ("umode", _enter_umode)]:
            lines.extend(
                [
                    "",
                    f"\t# mstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"\tCSRR(x{save_mstateen}, mstateen0)",
                    f"\tLI(x{temp_reg}, 1)",
                    f"\t{bit_action}(mstateen0, x{temp_reg})  # FCSR bit = {fcsr_bit}",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for insn_template in fp_instrs:
                insn = insn_template.replace("{temp}", str(temp_reg)).replace("{scratch}", str(scratch_reg))
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{insn_template.split()[0]}_fcsr{fcsr_bit}_{mode_label}", coverpoint, covergroup
                        ),
                        f"\t{insn}  # fp instr from {mode_label} with mstateen0.FCSR={fcsr_bit}",
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            lines.extend(
                [
                    f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
                ]
            )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, scratch_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt  (cross csrrw, jvt_csr, jvt_state)
#   → CSRRW to jvt with mstateen0.JVT bit=0 and =1.
# ---------------------------------------------------------------------------


def _generate_jvt(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to jvt CSR with mstateen0.JVT bit enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_jvt, ones_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    # mstateen0 bit for JVT — bit 2 per the Smstateen spec
    JVT_BIT = 2

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_jvt}, jvt)              # save jvt",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )

    for jvt_state in [0, 1]:
        bit_action = "CSRC" if jvt_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.JVT={jvt_state}",
                f"\tLI(x{temp_reg}, {1 << JVT_BIT})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "",
                test_data.add_testcase(f"csrrw_jvt_state{jvt_state}", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, jvt, x{ones_reg})  # write to jvt",
                gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
                gen_csr_read_sigupd(temp_reg, "jvt", test_data),
            ]
        )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(jvt, x{save_jvt})              # restore jvt",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_jvt, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt_lower_mode  (cross priv_mode_s_u, csrrw, jvt_csr, jvt_state)
#   → From S/U-mode, CSRRW to jvt with mstateen0.JVT=0 and =1.
# ---------------------------------------------------------------------------


def _generate_jvt_lower_mode(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt_lower_mode"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to jvt from S/U-mode with mstateen0.JVT enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_jvt = test_data.int_regs.get_registers(3, exclude_regs=[0])
    JVT_BIT = 2

    for jvt_state in [0, 1]:
        bit_action = "CSRC" if jvt_state == 0 else "CSRS"
        for mode_label, enter_fn in [("smode", _enter_smode), ("umode", _enter_umode)]:
            lines.extend(
                [
                    "",
                    f"\t# mstateen0.JVT={jvt_state}, {mode_label}",
                    f"\tCSRR(x{save_mstateen}, mstateen0)",
                    f"\tCSRR(x{save_jvt}, jvt)",
                    f"\tLI(x{temp_reg}, {1 << JVT_BIT})",
                    f"\t{bit_action}(mstateen0, x{temp_reg})",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"csrrw_jvt_state{jvt_state}_{mode_label}", coverpoint, covergroup),
                    f"\tCSRRW(x{temp_reg}, jvt, x{temp_reg})  # write jvt from {mode_label}",
                    "\tnop",
                ]
            )
            lines.extend(_return_mmode(test_data, temp_reg))
            lines.extend(
                [
                    f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
                    f"\tCSRW(jvt, x{save_jvt})             # restore jvt",
                ]
            )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_jvt])
    return lines


# ---------------------------------------------------------------------------
# cp_envcfg  (cross csrrw, senvcfg_csr, envcfg_state)
#   → CSRRW to senvcfg with mstateen0.ENVCFG (bit 63 on RV64, bit 31 on RV32hi) =0 and =1.
# ---------------------------------------------------------------------------


def _generate_envcfg(test_data: TestData) -> list[str]:
    coverpoint = "cp_envcfg"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to senvcfg with mstateen0.ENVCFG bit enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_senvcfg, ones_reg, bit_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_senvcfg}, senvcfg)      # save senvcfg",
            f"\tLI(x{ones_reg}, -1)",
            "#ifdef XLEN64",
            f"\tLI(x{bit_reg}, 0x4000000000000000)  # ENVCFG = bit 62",
            "#else",
            f"\tLI(x{bit_reg}, 0x40000000)          # ENVCFG = bit 30 of mstateen0h on RV32",
            "#endif",
        ]
    )

    for envcfg_state in [0, 1]:
        bit_action = "CSRC" if envcfg_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.ENVCFG={envcfg_state}",
                f"\t{bit_action}(mstateen0, x{bit_reg})  # set/clear ENVCFG bit",
                "",
                "\tRVTEST_GOTO_LOWER_MODE Smode",
                test_data.add_testcase(f"csrrw_senvcfg_state{envcfg_state}", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, senvcfg, x{ones_reg})  # write to senvcfg",
                "\tRVTEST_GOTO_MMODE",
                gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
                gen_csr_read_sigupd(temp_reg, "senvcfg", test_data),
            ]
        )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(senvcfg, x{save_senvcfg})      # restore senvcfg",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_senvcfg, ones_reg, bit_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_context  (cross csrrw, scontext_csr, context_state)
#   → CSRRW to scontext with mstateen0.CONTEXT bit enabled and disabled.
# ---------------------------------------------------------------------------


def _generate_context(test_data: TestData) -> list[str]:
    coverpoint = "cp_context"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to scontext with mstateen0.CONTEXT bit enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_scontext, ones_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    # mstateen0 CONTEXT bit — bit 57 per spec (Smstateen 1.0 Table 1)
    CONTEXT_BIT = 57

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)    # save mstateen0",
            f"\tCSRR(x{save_scontext}, scontext)     # save scontext",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )

    for ctx_state in [0, 1]:
        bit_action = "CSRC" if ctx_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.CONTEXT={ctx_state}",
                f"\tLI(x{temp_reg}, 1 << {CONTEXT_BIT})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "",
                test_data.add_testcase(f"csrrw_scontext_state{ctx_state}", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, scontext, x{ones_reg})  # write to scontext",
                gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
                gen_csr_read_sigupd(temp_reg, "scontext", test_data),
            ]
        )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})    # restore mstateen0",
            f"\tCSRW(scontext, x{save_scontext})     # restore scontext",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_scontext, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_p1p13  (cross csrrw, p1p13_state, hedeleg_csr)
#   → CSRRW to hedeleg with mstateen0.P1P13 bit enabled and disabled.
#   P1P13 guards access to hedeleg (and similar H-extension CSRs) from S-mode.
# ---------------------------------------------------------------------------


def _generate_p1p13(test_data: TestData) -> list[str]:
    coverpoint = "cp_p1p13"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to hedeleg with mstateen0.P1P13 bit enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_hedeleg, ones_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    # P1P13 is bit 60 in mstateen0 per Smstateen 1.0 spec
    P1P13_BIT = 56

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)    # save mstateen0",
            f"\tCSRR(x{save_hedeleg}, hedeleg)       # save hedeleg",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )

    for p1p13_state in [0, 1]:
        bit_action = "CSRC" if p1p13_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.P1P13={p1p13_state}",
                f"\tLI(x{temp_reg}, 1 << {P1P13_BIT})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "",
                test_data.add_testcase(f"csrrw_hedeleg_p1p13_{p1p13_state}", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, hedeleg, x{ones_reg})  # write to hedeleg",
                gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
                gen_csr_read_sigupd(temp_reg, "hedeleg", test_data),
            ]
        )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})    # restore mstateen0",
            f"\tCSRW(hedeleg, x{save_hedeleg})       # restore hedeleg",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_hedeleg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_srmcfg  (cross csrrw, srmcfg_csr, srmcfg_state)
#   → CSRRW to srmcfg with mstateen0.SRMCFG bit enabled and disabled.
# ---------------------------------------------------------------------------


def _generate_srmcfg(test_data: TestData) -> list[str]:
    coverpoint = "cp_srmcfg"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to srmcfg with mstateen0.SRMCFG bit enabled and disabled",
        )
    )

    temp_reg, save_mstateen, save_srmcfg, ones_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    # SRMCFG bit — bit 58 in mstateen0 per Smstateen spec
    SRMCFG_BIT = 55

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_srmcfg}, srmcfg)        # save srmcfg",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )

    for srmcfg_state in [0, 1]:
        bit_action = "CSRC" if srmcfg_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.SRMCFG={srmcfg_state}",
                f"\tLI(x{temp_reg}, 1 << {SRMCFG_BIT})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "",
                test_data.add_testcase(f"csrrw_srmcfg_state{srmcfg_state}", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, srmcfg, x{ones_reg})  # write to srmcfg",
                gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
                gen_csr_read_sigupd(temp_reg, "srmcfg", test_data),
            ]
        )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(srmcfg, x{save_srmcfg})        # restore srmcfg",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_srmcfg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ctr  (cross csrrw, ctr_csrs, ctr_state)
#   → CSRRW to sctrdepth and sctrstatus with mstateen0.CTR bit enabled and disabled.
# ---------------------------------------------------------------------------


def _generate_ctr(test_data: TestData) -> list[str]:
    coverpoint = "cp_ctr"
    covergroup = "Smstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to sctrdepth/sctrstatus with mstateen0.CTR bit enabled and disabled",
        )
    )

    temp_reg, save_mstateen, ones_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    # CTR bit — bit 54 in mstateen0 (Smstateen spec, Table 1)
    CTR_BIT = 54
    ctr_csrs = ["sctrdepth", "sctrstatus"]

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tLI(x{ones_reg}, -1)",
        ]
    )

    for ctr_state in [0, 1]:
        bit_action = "CSRC" if ctr_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.CTR={ctr_state}",
                f"\tLI(x{temp_reg}, 1 << {CTR_BIT})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
            ]
        )
        for csr in ctr_csrs:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"csrrw_{csr}_ctr{ctr_state}", coverpoint, covergroup),
                    f"\tCSRRW(x{temp_reg}, {csr}, x{ones_reg})  # write to {csr}",
                    "\tnop",
                    gen_csr_read_sigupd(temp_reg, "mstateen0", test_data),
                    gen_csr_read_sigupd(temp_reg, csr, test_data),
                ]
            )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["Sm", "Zicsr", "Smstateen"],
    march_extensions=["Smstateen", "Zicsr", "Zcmt"],
)
def make_smstateen(test_data: TestData) -> list[str]:
    """Generate tests for Smstateen state-enable extension testsuite."""
    lines: list[str] = []

    # Unconditional coverpoints — required by all Smstateen targets
    lines.extend(_generate_csr_illegal_accesses(test_data))
    lines.extend(_generate_walking_ones(test_data))
    lines.extend(_generate_envcfg(test_data))

    # cp_fcsr, cp_fcsr_ro_zero, cp_fcsr_lower, cp_fcsr_lower_fp_instrs
    # Only when F (Zfinx) is supported — mstateen0.FCSR bit is relevant
    lines.append("#ifdef ZFINX_SUPPORTED")
    lines.extend(_generate_fcsr_ro_zero(test_data))
    lines.extend(_generate_fcsr(test_data))
    lines.extend(_generate_fcsr_lower(test_data))
    lines.extend(_generate_fcsr_lower_fp_instrs(test_data))
    lines.append("#endif  // ZFINX_SUPPORTED")

    # cp_jvt, cp_jvt_lower_mode
    # Only when Zcmt is supported — mstateen0.JVT bit is relevant
    lines.append("#ifdef ZCMT_SUPPORTED")
    lines.extend(_generate_jvt(test_data))
    lines.extend(_generate_jvt_lower_mode(test_data))
    lines.append("#endif  // ZCMT_SUPPORTED")

    # cp_context
    # Only when Sdtrig (debug trigger) is supported — mstateen0.CONTEXT bit is relevant
    lines.append("#ifdef SDTRIG_SUPPORTED")
    lines.extend(_generate_context(test_data))
    lines.append("#endif  // SDTRIG_SUPPORTED")

    # cp_p1p13
    # Only when Sm1p13 and Hypervisor extension are supported — guards hedeleg access
    lines.append("#ifdef SM1P13_SUPPORTED")
    lines.extend(_generate_p1p13(test_data))
    lines.append("#endif  // SM1P13_SUPPORTED")

    # cp_srmcfg
    # Only when Ssqosid is supported — mstateen0.SRMCFG bit is relevant
    lines.append("#ifdef SSQOSID_SUPPORTED")
    lines.extend(_generate_srmcfg(test_data))
    lines.append("#endif  // SSQOSID_SUPPORTED")

    # cp_ctr
    # Only when Sctr (control transfer records) is supported
    lines.append("#ifdef SCTR_SUPPORTED")
    lines.extend(_generate_ctr(test_data))
    lines.append("#endif  // SCTR_SUPPORTED")

    return lines
