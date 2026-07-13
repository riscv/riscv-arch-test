# Smstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Smstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MSTATEEN_CSRS_64 = ["mstateen0", "mstateen1", "mstateen2", "mstateen3"]
MSTATEEN_CSRS_H = ["mstateen0h", "mstateen1h", "mstateen2h", "mstateen3h"]

CSR_OPS = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]


# RVTEST mode-switch macros, emitted as plain assembly (see other priv generators).
GOTO_UMODE = "RVTEST_GOTO_LOWER_MODE Umode  # enter U-mode"
GOTO_SMODE = "RVTEST_GOTO_LOWER_MODE Smode  # enter S-mode"
GOTO_MMODE = "RVTEST_GOTO_MMODE  # return to M-mode"
IN_MMODE = f"{INDENT}# already in M-mode"  # M-mode is the default; just a marker comment

# Mode dispatch for the priv_mode_m_maybes_u coverpoints. Each entry is
# (label, line that switches into the mode, whether an S_SUPPORTED guard is needed).
# GOTO_MMODE returns from any lower mode. Lower-mode-only coverpoints slice [1:].
_MODES_MUS = [
    ("mmode", IN_MMODE, False),
    ("umode", GOTO_UMODE, False),
    ("smode", GOTO_SMODE, True),
]


def _csr_insn(op: str, rd: int, csr: str, rs1: int) -> str:
    """Emit a single CSR instruction line. CSRR is read-only and only takes (rd, csr)."""
    if op == "CSRR":
        return f"{op}(x{rd}, {csr})"
    return f"{op}(x{rd}, {csr}, x{rs1})"


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses
#   Cross: priv_mode_s_u × mstateen_csrs × csrops
#   All CSR ops to mstateenN CSRs from U-mode AND S-mode — must trap.
# ---------------------------------------------------------------------------


def _generate_csr_illegal_accesses(test_data: TestData) -> list[str]:
    coverpoint = "cp_csr_illegal_accesses"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "All CSR ops to mstateenN CSRs from U-mode and S-mode — must trap (M-only CSRs)",
        )
    ]

    temp_reg = test_data.int_regs.get_register()

    # ── U-mode ──────────────────────────────────────────────────────────────
    lines.append(GOTO_UMODE)

    for csr in MSTATEEN_CSRS_64:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "nop",
                ]
            )

    lines.append("#if __riscv_xlen == 32")
    for csr in MSTATEEN_CSRS_H:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "nop",
                ]
            )
    lines.append("#endif  // __riscv_xlen == 32")

    lines.append(GOTO_MMODE)

    # ── S-mode ──────────────────────────────────────────────────────────────
    lines.append("#ifdef S_SUPPORTED")
    lines.append(GOTO_SMODE)

    for csr in MSTATEEN_CSRS_64:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_smode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "nop",
                ]
            )

    lines.append("#if __riscv_xlen == 32")
    for csr in MSTATEEN_CSRS_H:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_smode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "nop",
                ]
            )
    lines.append("#endif  // __riscv_xlen == 32")

    lines.append(GOTO_MMODE)
    lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: mstateen_walk_csrs × csrops × csr_walk
#   mstateen_walk_csrs = mstateen0 always, mstateen0h on RV32 only.
# ---------------------------------------------------------------------------


def _generate_walking_ones(test_data: TestData) -> list[str]:
    coverpoint = "cp_walking_ones"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns on mstateen0 (+ mstateen0h on RV32) from M-mode",
        )
    ]

    # The walk mask selects which bits are checked against the signature (csr_walk_test
    # walks every bit position regardless). It mirrors mstateen0's writable high-word
    # bits on RV64: SE0(63)|ENVCFG(62)|CSRIND(60)|AIA(59)|IMSIC(58)|CONTEXT(57)|P1P13(56)|
    # SRMCFG(55), plus FCSR(1)|JVT(2) in the low word. On RV32 mstateen0 is the low word
    # (0x6) and those high bits live in mstateen0h (0xDF800000).
    lines.extend(
        [
            "",
            test_data.add_testcase("mstateen0_walk", coverpoint, covergroup),
        ]
    )
    lines.extend(csr_walk_test(test_data, ("mstateen0", 0xDF80000000000006), covergroup, coverpoint))

    # mstateen0h — RV32 only
    lines.append("#if __riscv_xlen == 32")
    lines.extend(
        [
            "",
            test_data.add_testcase("mstateen0h_walk", coverpoint, covergroup),
        ]
    )
    lines.extend(csr_walk_test(test_data, ("mstateen0h", 0xDF800000), covergroup, coverpoint))
    lines.append("#endif  // __riscv_xlen == 32")

    return lines


# ---------------------------------------------------------------------------
# Bit-controlled feature coverpoints
#   cp_envcfg, cp_imsic, cp_aia, cp_context, cp_p1p13, cp_srmcfg, cp_ctr
#
#   Each of these crosses csrops × <feature>_csr(s) × <feature>_state ×
#   priv_mode_m_maybes_u: a single mstateen0 control bit gates a small set of
#   S-mode CSRs, and the cross must be hit from M-, U-, and S-mode with the
#   control bit both set and cleared. They differ only in the control-bit
#   position and the gated CSR list.
# ---------------------------------------------------------------------------


def _generate_bit_controlled(
    test_data: TestData,
    *,
    coverpoint: str,
    bit: int,
    bit_name: str,
    banner: str,
    csrs: list[str],
    csrs_rv32: list[str] | None = None,
) -> list[str]:
    """Generate M/U/S-mode CSR-op tests for a single mstateen0 control bit.

    The control bit lives at `bit` in mstateen0 on RV64 and at `bit - 32` in mstateen0h
    on RV32. For each control-bit state (cleared, set) and each of M-, U-, and S-mode,
    every CSR in `csrs` is exercised with every op in CSR_OPS.

    Args:
        csrs: CSRs to access. When `csrs_rv32` is given, those are used instead on RV32
            (e.g. the AIA high-half registers sieh/siph in place of sie/sip).
    """
    covergroup = "Smstateen_cg"
    lines = [comment_banner(coverpoint, banner)]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    mask_64 = f"{1 << bit:#x}"
    mask_32 = f"{1 << (bit - 32):#x}"

    def emit_ops(op_csrs: list[str], state: int, mode_label: str) -> list[str]:
        out: list[str] = []
        for csr in op_csrs:
            for op in CSR_OPS:
                out.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{csr}_{op.lower()}_{bit_name}{state}_{mode_label}", coverpoint, covergroup
                        ),
                        _csr_insn(op, temp_reg, csr, ones_reg),
                        "nop",
                    ]
                )
        return out

    lines.append(f"LI(x{ones_reg}, -1)")

    for state in (0, 1):
        bit_action = "CSRS" if state else "CSRC"
        lines.extend(
            [
                "",
                f"{INDENT}# mstateen0.{bit_name} = {state} (bit {bit})",
                "#if __riscv_xlen == 64",
                f"LI(x{temp_reg}, {mask_64})",
                f"{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"LI(x{temp_reg}, {mask_32})",
                f"{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )

        for mode_label, enter_line, needs_guard in _MODES_MUS:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.append(enter_line)
            if csrs_rv32 is None:
                lines.extend(emit_ops(csrs, state, mode_label))
            else:
                lines.append("#if __riscv_xlen == 64")
                lines.extend(emit_ops(csrs, state, mode_label))
                lines.append("#else  // RV32")
                lines.extend(emit_ops(csrs_rv32, state, mode_label))
                lines.append("#endif  // __riscv_xlen")
            lines.append(GOTO_MMODE)
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt_access
#   Cross: priv_mode_maybes_u (S-mode + U-mode) × csrops × jvt_csr × jvt_state
#   The covergroup cross samples U/S-mode only — there is no M-mode jvt cross,
#   so M-mode jvt access is intentionally not exercised here.
# ---------------------------------------------------------------------------


def _generate_jvt(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt_access"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on jvt from U/S-mode with mstateen0.jvt (bit 2) disabled and enabled",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    JVT_BIT_MASK = 1 << 2

    lines.append(f"LI(x{ones_reg}, -1)")

    # Lower modes only (U + S); the cp_jvt_access cross does not sample M-mode.
    for mode_label, enter_line, needs_guard in _MODES_MUS[1:]:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "CSRC" if state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"{INDENT}# mstateen0.jvt = {state}, {mode_label}",
                    f"LI(x{temp_reg}, {JVT_BIT_MASK})",
                    f"{bit_action}(mstateen0, x{temp_reg})",
                ]
            )
            lines.append(enter_line)
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"jvt_{op.lower()}_jvt{state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        _csr_insn(op, temp_reg, "jvt", ones_reg),
                        "nop",
                    ]
                )
            lines.append(GOTO_MMODE)
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_ro_zero
#   Cross: misa_F × csrops × mstateen0_fcsr_bit
#   Exercises the ignore_bins-covered path where fcsr reads as zero
#   when misa.F is set but mstateen0.fcsr (bit 1) is clear.
# ---------------------------------------------------------------------------


def _generate_fcsr_ro_zero(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_ro_zero"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "misa.F set, mstateen0.fcsr (bit 1) clear — fcsr reads as zero (access-fault path)",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    FCSR_BIT_MASK = 1 << 1  # bit 1 of mstateen0

    lines.extend(
        [
            f"LI(x{ones_reg}, -1)",
            "",
            f"{INDENT}# Ensure misa.F is set (read misa, verify F bit, then proceed)",
            f"CSRR(x{temp_reg}, misa)",
            f"{INDENT}# bit 5 = F; test proceeds assuming F is present per MARCH",
            "",
            f"{INDENT}# Clear mstateen0.fcsr so fcsr reads zero",
            f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
            f"CSRC(mstateen0, x{temp_reg})",
        ]
    )

    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_ro_zero", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "nop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr
# ---------------------------------------------------------------------------


def _generate_fcsr(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "M-mode CSR ops on fcsr under misa.F set and mstateen0.fcsr (bit 1) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    FCSR_BIT_MASK = 1 << 1

    lines.append(f"LI(x{ones_reg}, -1)")

    lines.extend(
        [
            "",
            f"{INDENT}# mstateen0.fcsr = 1 (only meaningful state per ignore_bins)",
            f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
            f"CSRS(mstateen0, x{temp_reg})",
        ]
    )
    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_fcsr1", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "nop",
            ]
        )

    lines.extend(
        [
            "",
            f"{INDENT}# mstateen0.fcsr = 0",
            f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
            f"CSRC(mstateen0, x{temp_reg})",
        ]
    )
    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_fcsr0", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "nop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower
#   Cross: priv_mode_s_u × misa_F × mstateen0_fcsr_bit × csrops × fcsr_lower_mode_csrs
#   S-mode and U-mode only.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "S/U-mode CSR ops on frm/fflags/fcsr with mstateen0.fcsr (bit 1) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    FCSR_BIT_MASK = 1 << 1
    fp_csrs = ["frm", "fflags", "fcsr"]

    lines.append(f"LI(x{ones_reg}, -1)")

    # Lower modes only (U + S); these crosses do not sample M-mode.
    for mode_label, enter_line, needs_guard in _MODES_MUS[1:]:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "CSRC" if state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"{INDENT}# mstateen0.fcsr = {state}, {mode_label}",
                    f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
                    f"{bit_action}(mstateen0, x{temp_reg})",
                ]
            )
            lines.append(enter_line)
            for csr in fp_csrs:
                for op in CSR_OPS:
                    lines.extend(
                        [
                            "",
                            test_data.add_testcase(
                                f"{csr}_{op.lower()}_fcsr{state}_{mode_label}",
                                coverpoint,
                                covergroup,
                            ),
                            _csr_insn(op, temp_reg, csr, ones_reg),
                            "nop",
                        ]
                    )
            lines.append(GOTO_MMODE)
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower_fp_instrs
#   Cross: priv_mode_s_u × misa_F × mstateen0_fcsr_bit × fp_instrs
#   S-mode and U-mode only.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower_fp_instrs"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "FP instructions from U/S-mode with mstateen0.fcsr (bit 1) disabled and enabled",
        )
    ]

    temp_reg1, temp_reg2, temp_reg3 = test_data.int_regs.get_registers(3)
    FCSR_BIT_MASK = 1 << 1

    fp_instrs = [
        (f"fadd.s x{temp_reg1}, x{temp_reg2}, x{temp_reg3}", "fadd_s"),
        (f"fcvt.w.s x{temp_reg1}, x{temp_reg2}", "fcvt_w_s"),
        (f"fcvt.s.w x{temp_reg1}, x{temp_reg2}", "fcvt_s_w"),
        (f"fclass.s x{temp_reg1}, x{temp_reg2}", "fclass_s"),
    ]

    # Lower modes only (U + S); these crosses do not sample M-mode.
    for mode_label, enter_line, needs_guard in _MODES_MUS[1:]:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "CSRC" if state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"{INDENT}# mstateen0.fcsr = {state}, {mode_label}",
                    f"LI(x{temp_reg1}, {FCSR_BIT_MASK})",
                    f"{bit_action}(mstateen0, x{temp_reg1})",
                ]
            )
            lines.append(enter_line)
            for insn, label in fp_instrs:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{label}_fcsr{state}_{mode_label}", coverpoint, covergroup),
                        insn,
                        "nop",
                    ]
                )
            lines.append(GOTO_MMODE)
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg1, temp_reg2, temp_reg3])
    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["S", "Zicsr", "Smstateen"],
    march_extensions=["S", "Smstateen", "Zicsr", "Zcmt", "Zfinx"],
)
def make_smstateen(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Smstateen state-enable extension testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    # Unconditional coverpoints — required by all Smstateen targets
    tc.code.extend(_generate_csr_illegal_accesses(test_data))
    tc.code.extend(_generate_walking_ones(test_data))
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_envcfg",
            bit=62,
            bit_name="envcfg",
            banner="CSR ops on senvcfg from M/S/U-mode with mstateen0.envcfg (bit 62) enabled and disabled",
            csrs=["senvcfg"],
        )
    )

    # cp_imsic — only when IMSIC is present
    tc.code.append("#ifdef IMSIC_SUPPORTED")
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_imsic",
            bit=58,
            bit_name="imsic",
            banner="CSR ops on stopei/vstopei with mstateen0.imsic (bit 58) disabled and enabled — M/S/U-mode",
            csrs=["stopei", "vstopei"],
        )
    )
    tc.code.append("#endif  // IMSIC_SUPPORTED")

    # cp_aia — only when AIA is present
    tc.code.append("#ifdef AIA_SUPPORTED")
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_aia",
            bit=59,
            bit_name="aia",
            banner="CSR ops on AIA CSRs with mstateen0.aia (bit 59) disabled and enabled — M/S/U-mode",
            csrs=["sie", "sip"],
            csrs_rv32=["sieh", "siph"],
        )
    )
    tc.code.append("#endif  // AIA_SUPPORTED")

    # cp_jvt_access — only when Zcmt is present (covers S-mode and U-mode)
    tc.code.append("#ifdef ZCMT_SUPPORTED")
    tc.code.extend(_generate_jvt(test_data))
    tc.code.append("#endif  // ZCMT_SUPPORTED")

    # cp_context — only when Sdtrig is present
    tc.code.append("#ifdef SDTRIG_SUPPORTED")
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_context",
            bit=57,
            bit_name="context",
            banner="CSR ops on scontext with mstateen0.context (bit 57) disabled and enabled — M/S/U-mode",
            csrs=["scontext"],
        )
    )
    tc.code.append("#endif  // SDTRIG_SUPPORTED")

    # cp_p1p13 — only when Sm1p13 + Hypervisor present
    tc.code.append("#if defined(SM1P13_SUPPORTED) && defined(H_SUPPORTED)")
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_p1p13",
            bit=56,
            bit_name="p1p13",
            banner="CSR ops on hedelegh with mstateen0.p1p13 (bit 56) disabled and enabled — M/S/U-mode",
            csrs=["hedelegh"],
        )
    )
    tc.code.append("#endif  // SM1P13_SUPPORTED && H_SUPPORTED")

    # cp_srmcfg — only when Ssqosid is present
    tc.code.append("#ifdef SSQOSID_SUPPORTED")
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_srmcfg",
            bit=55,
            bit_name="srmcfg",
            banner="CSR ops on srmcfg with mstateen0.srmcfg (bit 55) disabled and enabled — M/S/U-mode",
            csrs=["srmcfg"],
        )
    )
    tc.code.append("#endif  // SSQOSID_SUPPORTED")

    # cp_ctr — only when Sctr is present
    tc.code.append("#ifdef SCTR_SUPPORTED")
    tc.code.extend(
        _generate_bit_controlled(
            test_data,
            coverpoint="cp_ctr",
            bit=54,
            bit_name="ctr",
            banner="CSR ops on sctrdepth/sctrstatus with mstateen0.ctr (bit 54) disabled and enabled — M/S/U-mode",
            csrs=["sctrdepth", "sctrstatus"],
        )
    )
    tc.code.append("#endif  // SCTR_SUPPORTED")

    # cp_fcsr, cp_fcsr_ro_zero, cp_fcsr_lower, cp_fcsr_lower_fp_instrs — only when Zfinx present
    tc.code.append("#ifdef ZFINX_SUPPORTED")
    tc.code.extend(_generate_fcsr_ro_zero(test_data))
    tc.code.extend(_generate_fcsr(test_data))
    tc.code.extend(_generate_fcsr_lower(test_data))
    tc.code.extend(_generate_fcsr_lower_fp_instrs(test_data))
    tc.code.append("#endif  // ZFINX_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
