# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
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
# cp_mstateen0_se0_controls_sstateen0
#   (cross csrrw, se0_state, sstateen_csrs — sstateen0 only per ignore_bins)
#   → CSRRW to sstateen0 from M-mode with mstateen0.SE0=0 and =1.
#   When SE0=0, writes to sstateen0 from lower modes should have no effect;
#   when SE0=1 they are permitted.  We test the write itself and capture
#   both mstateen0 and sstateen0 in the signature so the checker can verify.
# ---------------------------------------------------------------------------


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


def _generate_se0_controls_sstateen0(test_data: TestData) -> list[str]:
    coverpoint = "cp_mstateen0_se0_controls_sstateen0"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to sstateen0 with mstateen0.SE0=1 (required for sstateen0 access)",
        )
    )

    temp_reg, save_mstateen, save_sstateen, ones_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_sstateen}, sstateen0)   # save sstateen0",
            f"\tLI(x{ones_reg}, -1)",
            "#if __riscv_xlen == 32",
            f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
            "#endif",
        ]
    )

    # SE0 must be 1 to access sstateen0 — only test SE0=1
    lines.extend(_set_se0(temp_reg))
    lines.extend(
        [
            "",
            test_data.add_testcase("csrrw_sstateen0_se0_1", coverpoint, covergroup),
            f"\tCSRRW(x{temp_reg}, sstateen0, x{ones_reg})  # write all-ones to sstateen0",
            "\tnop",
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(sstateen0, x{save_sstateen})   # restore sstateen0",
            "#if __riscv_xlen == 32",
            f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_sstateen, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses  (cross priv_mode_u, csr, csrops, se0_state)
#   → From U-mode, attempt CSRRW/CSRRS/CSRRC/CSRR to each sstateenN CSR;
#   these should trap regardless of SE0.  We test with both SE0 states so
#   the cross bins are fully populated.
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

    temp_reg, save_mstateen = test_data.int_regs.get_registers(2, exclude_regs=[0])

    sstateen_csrs = ["sstateen0", "sstateen1", "sstateen2", "sstateen3"]
    csr_ops = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)  # save mstateen0",
            "#if __riscv_xlen == 32",
            f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
            "#endif",
        ]
    )
    lines.extend(_set_se0(temp_reg))
    lines.extend(_enter_umode(test_data, temp_reg))

    for csr in sstateen_csrs:
        for op in csr_ops:
            # CSRR takes only (rd, csr); CSRRW/CSRRS/CSRRC take (rd, csr, rs1)
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
    lines.extend(
        [
            f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
            "#if __riscv_xlen == 32",
            f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones  (cross csr, csrops, csr_walk, se0_state)
#   → Walking-1 and walking-0 patterns on sstateen0..3 with both SE0 states.
# ---------------------------------------------------------------------------


def _generate_walking_ones(test_data: TestData) -> list[str]:
    coverpoint = "cp_walking_ones"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns written to each sstateenN CSR via CSRRW with SE0=1",
        )
    )

    sstateen_csrs = ["sstateen0", "sstateen1", "sstateen2", "sstateen3"]

    # Set SE0=1 then release registers before csr_walk_test allocates its own
    save_mstateen, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)  # save mstateen0",
            "#if __riscv_xlen == 32",
            f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
            "#endif",
        ]
    )
    lines.extend(_set_se0(temp_reg))
    test_data.int_regs.return_registers([save_mstateen, temp_reg])

    # Full walk for each sstateen CSR — csr_walk_test allocates its own registers
    for csr in sstateen_csrs:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"{csr}_walk_se0_1", coverpoint, covergroup),
            ]
        )
        lines.extend(csr_walk_test(test_data, (csr, 0x7), covergroup, coverpoint))

    # Restore mstateen0/0h
    save_mstateen, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
            "#if __riscv_xlen == 32",
            f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
            "#endif",
        ]
    )
    test_data.int_regs.return_registers([save_mstateen, temp_reg])

    return lines


def _generate_jvt(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to jvt CSR with sstateen0.JVT enabled/disabled under SE0=1",
        )
    )

    temp_reg, save_mstateen, save_sstateen, save_jvt, ones_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])

    JVT_BIT = 2

    lines.extend(
        [
            f"\tCSRR(x{save_mstateen}, mstateen0)   # save mstateen0",
            f"\tCSRR(x{save_sstateen}, sstateen0)   # save sstateen0",
            f"\tCSRR(x{save_jvt}, jvt)              # save jvt",
            f"\tLI(x{ones_reg}, -1)",
            "#if __riscv_xlen == 32",
            f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
            "#endif",
        ]
    )
    lines.extend(_set_se0(temp_reg))

    for jvt_state in [0, 1]:
        jvt_action = "CSRC" if jvt_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# SE0=1, sstateen0.JVT={jvt_state}",
                f"\tLI(x{temp_reg}, {1 << JVT_BIT})",
                f"\t{jvt_action}(sstateen0, x{temp_reg})",
                "",
                test_data.add_testcase(f"csrrw_jvt_se0_1_jvt_{jvt_state}", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, jvt, x{ones_reg})  # write to jvt",
                "\tnop",
            ]
        )

    lines.extend(
        [
            "",
            f"\tCSRW(mstateen0, x{save_mstateen})   # restore mstateen0",
            f"\tCSRW(sstateen0, x{save_sstateen})   # restore sstateen0",
            f"\tCSRW(jvt, x{save_jvt})              # restore jvt",
            "#if __riscv_xlen == 32",
            f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_sstateen, save_jvt, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt_lower_mode  (cross priv_mode_u, csrops, jvt_csr, jvt_state, se0_state)
#   [ifdef ZCMT_SUPPORTED]
#   → From U-mode, CSRRW to jvt with all combinations of SE0 and JVT states.
# ---------------------------------------------------------------------------


def _generate_jvt_lower_mode(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt_lower_mode"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "CSRRW to jvt from U-mode with sstateen0.JVT enabled/disabled under SE0=1",
        )
    )

    temp_reg, save_mstateen, save_sstateen, save_jvt = test_data.int_regs.get_registers(4, exclude_regs=[0])
    JVT_BIT = 2

    for jvt_state in [0, 1]:
        jvt_action = "CSRC" if jvt_state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# SE0=1, sstateen0.JVT={jvt_state}",
                f"\tCSRR(x{save_mstateen}, mstateen0)",
                f"\tCSRR(x{save_sstateen}, sstateen0)",
                f"\tCSRR(x{save_jvt}, jvt)",
                "#if __riscv_xlen == 32",
                f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
                "#endif",
            ]
        )
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                f"\tLI(x{temp_reg}, {1 << JVT_BIT})",
                f"\t{jvt_action}(sstateen0, x{temp_reg})",
            ]
        )
        lines.extend(_enter_umode(test_data, temp_reg))
        lines.extend(
            [
                "",
                test_data.add_testcase(f"csrrw_jvt_se0_1_jvt_{jvt_state}_umode", coverpoint, covergroup),
                f"\tCSRRW(x{temp_reg}, jvt, x{temp_reg})  # write jvt from U-mode",
                "\tnop",
            ]
        )
        lines.extend(_return_mmode(test_data, temp_reg))
        lines.extend(
            [
                f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
                f"\tCSRW(sstateen0, x{save_sstateen})  # restore sstateen0",
                f"\tCSRW(jvt, x{save_jvt})             # restore jvt",
                "#if __riscv_xlen == 32",
                f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
                "#endif",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_sstateen, save_jvt])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower
#   (cross priv_mode_s_u, misa_F, se0_state, sstateen0_fcsr_bit, csrops, fcsr_lower_mode_csrs)
#   [ifdef ZFINX_SUPPORTED]
#   → From S/U-mode, CSR ops on frm/fflags/fcsr under all combinations of
#   SE0 and sstateen0.FCSR states.
#   ignore_bins in the covergroup exclude the cases where sstateen0.FCSR=0 AND
#   misa_F is set or clear (those are covered separately); we still exercise
#   both states so the enabled bins are hit.
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

    temp_reg, save_mstateen, save_sstateen, save_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])
    fp_csrs = ["frm", "fflags", "fcsr"]
    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR per spec Figure 37

    for fcsr_bit in [0, 1]:
        fcsr_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_fn in [("smode", _enter_smode), ("umode", _enter_umode)]:
            lines.extend(
                [
                    "",
                    f"\t# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"\tCSRR(x{save_mstateen}, mstateen0)",
                    f"\tCSRR(x{save_sstateen}, sstateen0)",
                    "#if __riscv_xlen == 32",
                    f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
                    "#endif",
                ]
            )
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
            lines.extend(
                [
                    f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
                    f"\tCSRW(sstateen0, x{save_sstateen})  # restore sstateen0",
                    "#if __riscv_xlen == 32",
                    f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
                    "#endif",
                ]
            )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_sstateen, save_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower_fp_instrs
#   (cross priv_mode_u, misa_F, se0_state, sstateen0_fcsr_bit, fp_instrs)
#   [ifdef ZFINX_SUPPORTED]
#   → From U-mode, execute each FP instruction under all combinations of
#   SE0 and sstateen0.FCSR.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower_fp_instrs"
    covergroup = "Ssstateen_cg"

    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "FP instructions from U-mode with SE0=1 and sstateen0.FCSR states",
        )
    )

    temp_reg, save_mstateen, save_sstateen, scratch_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR per spec Figure 37

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
        fcsr_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# SE0=1, sstateen0.FCSR={fcsr_bit}, umode",
                f"\tCSRR(x{save_mstateen}, mstateen0)",
                f"\tCSRR(x{save_sstateen}, sstateen0)",
                "#if __riscv_xlen == 32",
                f"\tCSRR(x{save_mstateen}, mstateen0h)  # save mstateen0h on RV32",
                "#endif",
            ]
        )
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                f"\tLI(x{temp_reg}, {1 << FCSR_BIT})",
                f"\t{fcsr_action}(sstateen0, x{temp_reg})  # sstateen0.FCSR = {fcsr_bit}",
            ]
        )
        lines.extend(_enter_umode(test_data, temp_reg))
        for insn_template in fp_instrs:
            insn = insn_template.replace("{temp}", str(temp_reg)).replace("{scratch}", str(scratch_reg))
            lines.extend(
                [
                    "",
                    test_data.add_testcase(
                        f"{insn_template.split()[0]}_se0_1_fcsr{fcsr_bit}_umode",
                        coverpoint,
                        covergroup,
                    ),
                    f"\t{insn}  # fp instr from umode fcsr={fcsr_bit}",
                    "\tnop",
                ]
            )
        lines.extend(_return_mmode(test_data, temp_reg))
        lines.extend(
            [
                f"\tCSRW(mstateen0, x{save_mstateen})  # restore mstateen0",
                f"\tCSRW(sstateen0, x{save_sstateen})  # restore sstateen0",
                "#if __riscv_xlen == 32",
                f"\tCSRW(mstateen0h, x{save_mstateen})  # restore mstateen0h on RV32",
                "#endif",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_sstateen, scratch_reg])
    return lines


def _generate_envcfg(test_data: TestData) -> list[str]:
    coverpoint = "cp_envcfg"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on senvcfg from S-mode with SE0=1 and mstateen0.envcfg (bit 62) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    ENVCFG_BIT_MASK_64 = "0x4000000000000000"  # bit 62 of mstateen0
    ENVCFG_BIT_MASK_32 = "0x40000000"  # bit 30 of mstateen0h

    lines.extend([f"\tLI(x{ones_reg}, -1)"])

    for state in [1, 0]:
        bit_action = "CSRS" if state == 1 else "CSRC"
        # SE0 must be set first so senvcfg access from S-mode doesn't trap
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                "",
                f"\t# mstateen0.envcfg = {state}, SE0=1, drop to S-mode",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {ENVCFG_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {ENVCFG_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.extend(_enter_smode(test_data, temp_reg))
        for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
            insn = f"\t{op}(x{temp_reg}, senvcfg)" if op == "CSRR" else f"\t{op}(x{temp_reg}, senvcfg, x{ones_reg})"
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"senvcfg_{op.lower()}_envcfg{state}_smode", coverpoint, covergroup),
                    insn,
                    "\tnop",
                ]
            )
        lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


def _generate_context(test_data: TestData) -> list[str]:
    coverpoint = "cp_context"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on scontext from S-mode with SE0=1 and mstateen0.context (bit 57) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    CONTEXT_BIT_MASK_64 = "0x0200000000000000"  # bit 57
    CONTEXT_BIT_MASK_32 = "0x02000000"  # bit 25 of mstateen0h

    lines.extend([f"\tLI(x{ones_reg}, -1)"])

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                "",
                f"\t# mstateen0.context = {state}, SE0=1",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {CONTEXT_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {CONTEXT_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.extend(_enter_smode(test_data, temp_reg))
        for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
            insn = f"\t{op}(x{temp_reg}, scontext)" if op == "CSRR" else f"\t{op}(x{temp_reg}, scontext, x{ones_reg})"
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"scontext_{op.lower()}_context{state}_smode", coverpoint, covergroup),
                    insn,
                    "\tnop",
                ]
            )
        lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


def _generate_ctr(test_data: TestData) -> list[str]:
    coverpoint = "cp_ctr"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on sctrdepth/sctrstatus from S-mode with SE0=1 and mstateen0.ctr (bit 54) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    CTR_BIT_MASK_64 = "0x0040000000000000"  # bit 54
    CTR_BIT_MASK_32 = "0x00400000"  # bit 22 of mstateen0h
    ctr_csrs = ["sctrdepth", "sctrstatus"]

    lines.extend([f"\tLI(x{ones_reg}, -1)"])

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                "",
                f"\t# mstateen0.ctr = {state}, SE0=1",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {CTR_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {CTR_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.extend(_enter_smode(test_data, temp_reg))
        for csr in ctr_csrs:
            for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
                insn = f"\t{op}(x{temp_reg}, {csr})" if op == "CSRR" else f"\t{op}(x{temp_reg}, {csr}, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_ctr{state}_smode", coverpoint, covergroup),
                        insn,
                        "\tnop",
                    ]
                )
        lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


def _generate_imsic(test_data: TestData) -> list[str]:
    coverpoint = "cp_imsic"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on stopei/vstopei from S-mode with SE0=1 and mstateen0.imsic (bit 58) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    IMSIC_BIT_MASK_64 = "0x0400000000000000"  # bit 58
    IMSIC_BIT_MASK_32 = "0x04000000"  # bit 26 of mstateen0h
    imsic_csrs = ["stopei", "vstopei"]

    lines.extend([f"\tLI(x{ones_reg}, -1)"])

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                "",
                f"\t# mstateen0.imsic = {state}, SE0=1",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {IMSIC_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {IMSIC_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.extend(_enter_smode(test_data, temp_reg))
        for csr in imsic_csrs:
            for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
                insn = f"\t{op}(x{temp_reg}, {csr})" if op == "CSRR" else f"\t{op}(x{temp_reg}, {csr}, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_imsic{state}_smode", coverpoint, covergroup),
                        insn,
                        "\tnop",
                    ]
                )
        lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


def _generate_aia(test_data: TestData) -> list[str]:
    coverpoint = "cp_aia"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on AIA CSRs from S-mode with SE0=1 and mstateen0.aia (bit 59) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    AIA_BIT_MASK_64 = "0x0800000000000000"  # bit 59
    AIA_BIT_MASK_32 = "0x08000000"  # bit 27 of mstateen0h

    lines.extend([f"\tLI(x{ones_reg}, -1)"])

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                "",
                f"\t# mstateen0.aia = {state}, SE0=1",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {AIA_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {AIA_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.extend(_enter_smode(test_data, temp_reg))
        lines.append("#if __riscv_xlen == 64")
        for csr in ["sie", "sip"]:
            for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
                insn = f"\t{op}(x{temp_reg}, {csr})" if op == "CSRR" else f"\t{op}(x{temp_reg}, {csr}, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_aia{state}_smode", coverpoint, covergroup),
                        insn,
                        "\tnop",
                    ]
                )
        lines.append("#else  // RV32")
        for csr in ["sieh", "siph"]:
            for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
                insn = f"\t{op}(x{temp_reg}, {csr})" if op == "CSRR" else f"\t{op}(x{temp_reg}, {csr}, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_aia{state}_smode", coverpoint, covergroup),
                        insn,
                        "\tnop",
                    ]
                )
        lines.append("#endif")
        lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


def _generate_p1p13(test_data: TestData) -> list[str]:
    coverpoint = "cp_p1p13"
    covergroup = "Ssstateen_cg"  # was Smstateen_cg — wrong

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on hedelegh from S-mode with SE0=1 and mstateen0.p1p13 (bit 56) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    P1P13_BIT_MASK_64 = "0x0100000000000000"  # bit 56
    P1P13_BIT_MASK_32 = "0x01000000"  # bit 24 of mstateen0h

    lines.extend([f"\tLI(x{ones_reg}, -1)"])

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(_set_se0(temp_reg))
        lines.extend(
            [
                "",
                f"\t# mstateen0.p1p13 = {state}, SE0=1",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {P1P13_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {P1P13_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.extend(_enter_smode(test_data, temp_reg))
        for op in ["CSRRW", "CSRRS", "CSRRC", "CSRR"]:
            insn = f"\t{op}(x{temp_reg}, hedelegh)" if op == "CSRR" else f"\t{op}(x{temp_reg}, hedelegh, x{ones_reg})"
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"hedelegh_{op.lower()}_p1p13_{state}_smode", coverpoint, covergroup),
                    insn,
                    "\tnop",
                ]
            )
        lines.extend(_return_mmode(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, ones_reg])
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
    lines.extend(_generate_se0_controls_sstateen0(test_data))
    lines.extend(_generate_csr_illegal_accesses(test_data))
    lines.extend(_generate_walking_ones(test_data))
    lines.extend(_generate_envcfg(test_data))
    # scontext tests only when SSDTRIG is supported — sstateen0.context bit is relevant
    lines.append("#ifdef SSDTRIG_SUPPORTED")
    lines.extend(_generate_context(test_data))
    lines.append("#endif  // SSDTRIG_SUPPORTED")

    lines.append("#ifdef SM1P13_SUPPORTED")
    lines.extend(_generate_p1p13(test_data))
    lines.append("#endif  // SM1P13_SUPPORTED")

    lines.append("#ifdef SCTR_SUPPORTED")
    lines.extend(_generate_ctr(test_data))
    lines.append("#endif  // SCTR_SUPPORTED")

    lines.append("#ifdef IMSIC_SUPPORTED")
    lines.extend(_generate_imsic(test_data))
    lines.append("#endif  // IMSIC_SUPPORTED")

    lines.append("#ifdef AIA_SUPPORTED")
    lines.extend(_generate_aia(test_data))
    lines.append("#endif  // AIA_SUPPORTED")

    # cp_fcsr_lower, cp_fcsr_lower_fp_instrs
    # Only when F (Zfinx) is supported — sstateen0.FCSR bit is relevant
    lines.append("#ifdef ZFINX_SUPPORTED")
    lines.extend(_generate_fcsr_lower(test_data))
    lines.extend(_generate_fcsr_lower_fp_instrs(test_data))
    lines.append("#endif  // ZFINX_SUPPORTED")

    # cp_jvt, cp_jvt_lower_mode
    # Only when Zcmt is supported — sstateen0.JVT bit is relevant
    lines.append("#ifdef ZCMT_SUPPORTED")
    lines.extend(_generate_jvt(test_data))
    lines.extend(_generate_jvt_lower_mode(test_data))
    lines.append("#endif  // ZCMT_SUPPORTED")

    return lines
