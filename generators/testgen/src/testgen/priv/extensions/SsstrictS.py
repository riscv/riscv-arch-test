##################################
# priv/extensions/SsstrictS.py
#
# Ssstrict supervisor-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from S-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictS — supervisor-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.

Structure
---------
1. Switch to S-mode via RVTEST_GOTO_LOWER_MODE Smode.
2. CSR sweep from S-mode (all non-skipped CSRs).
   - S-mode CSRs (priv=01) are accessible and exercise S-mode CSR coverage.
   - M-mode CSRs (priv=11) raise illegal-instruction from S-mode.
   - H-mode CSRs (priv=10) are SKIPPED: in HS-mode (S with H extension)
     they would be accessible, so behaviour is config-dependent.
   - satp (0x180) is SKIPPED: reading/writing satp flushes the TLB and
     changes address-translation mode, causing unpredictable side effects.
3. Shadow CSR writes: write mstatus/mie/mip from M-mode, then read
   sstatus/sie/sip from S-mode to cover the M<->S shadow relationship.
4. Return to M-mode via ecall, then run the illegal instruction and
   compressed sweeps (same encoding templates as SsstrictSm, from M-mode
   so the fast handler can advance mepc correctly for every trap).

Register exclusion for the CSR sweep
--------------------------------------
Same constraints as SsstrictSm — all scratch registers chosen from
{x7..x31} only.  x0-x6 are permanently excluded (see SsstrictSm.py for
the full rationale).
"""

from random import randint, sample, seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

BLANK_INTERVAL = 50

# x0-x6 excluded: framework-reserved (x0=zero, x1=ra, x2=sp/trap-count, x3=data-ptr,
# x4=temp, x5=link, x6=T1).  x2 in particular must never be used as rd: it holds the
# stack pointer and trap-count metadata written by the trap handler.
_SAFE_REGS: list[int] = list(range(7, 32))  # x7..x31 only


# ── CSR skip set (S-mode) ─────────────────────────────────────────────────

_S_CSR_SKIP: frozenset[int] = frozenset(
    [0x180]        # satp  — skip: TLB flush / address-translation mode change
    + [0x104]      # sie   — skip: all-ones write enables S-mode interrupts; covered in shadow test
    + [0x144]      # sip   — skip: all-ones write asserts SSIP software interrupt; covered in shadow test
    + list(range(0x200, 0x300))  # H-mode std0 — skip: accessible from HS-mode
    + list(range(0x600, 0x700))  # H-mode std1 — skip: HS-mode ambiguity
    + list(range(0xA00, 0xB00))  # H-mode std2 — skip: HS-mode ambiguity
    + list(range(0xE00, 0xF00))  # H-mode std3 — skip: HS-mode ambiguity
    + list(range(0x5C0, 0x600))  # S-mode custom1
    + list(range(0x6C0, 0x700))  # H-mode custom1
    + list(range(0x9C0, 0xA00))  # S-mode custom2
    + list(range(0xAC0, 0xB00))  # H-mode custom2
    + list(range(0x800, 0x900))  # user custom2
    + list(range(0xCC0, 0xD00))  # user custom3
    + list(range(0xDC0, 0xE00))  # S-mode custom3
    + list(range(0xEC0, 0xF00))  # H-mode custom3
)


# ── Encoding helpers (shared logic identical to SsstrictSm) ───────────────


def _gen_encodings(
    template: str,
    length: int = 32,
    exclusion: list[str] | None = None,
) -> list[str]:
    """Generate all exhaustive encodings from a template string."""
    if exclusion is None:
        exclusion = []
    ebits = template.count("E")
    results: list[str] = []
    for j in range(2**ebits):
        instr = ["0"] * length
        e = ebits - 1
        for i in range(length):
            if template[i] == "R":
                instr[i] = str(randint(0, 1))
            elif template[i] == "E":
                instr[i] = str((j >> e) & 1)
                e -= 1
            else:
                instr[i] = template[i]
        instrstr = "".join(instr)
        if not any(all(p[k] == "X" or p[k] == instrstr[k] for k in range(length)) for p in exclusion):
            results.append(instrstr)
    return results


def _emit_raw_words(
    lines: list[str],
    comment: str,
    template: str,
    length: int = 32,
    exclusion: list[str] | None = None,
) -> None:
    """Emit .word/.hword directives with blank lines every BLANK_INTERVAL."""
    directive = ".word" if length == 32 else ".hword"
    encodings = _gen_encodings(template, length, exclusion)
    lines.append("")
    lines.append(f"# {comment}  ({len(encodings)} encodings)")
    for idx, enc in enumerate(encodings):
        if idx > 0 and idx % BLANK_INTERVAL == 0:
            lines.append("")
        lines.append(f"\t{directive} 0b{enc}")
    lines.append("")


# ── S-mode CSR sweep ──────────────────────────────────────────────────────


def _generate_csr_tests_s(test_data: TestData) -> list[str]:
    """cp_csrr / cp_csrw_corners / cp_csrcs from S-mode.

    Switches to S-mode, sweeps all non-skipped CSRs, then returns to
    M-mode via ecall so subsequent sections can use the fast handler.
    """
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_csrr / cp_csrw_corners / cp_csrcs (S-mode)",
            "Read, write 0s/1s, set, clear every non-skipped CSR from S-mode.\n"
            "M-mode CSRs raise illegal-instruction from S-mode.\n"
            "H-mode CSRs skipped — accessible from HS-mode (config-dependent).\n"
            "satp skipped — TLB flush / address-translation side effects.",
        )
    )

    # Switch to S-mode — no trailing blank so the splitter cannot cut between
    # this and the first CSR instruction.  Every file that contains sweep code
    # must have the GOTO Smode either preceding it (in a prior file) or as its
    # own first executable line.
    lines.extend(
        [
            "",
            "# Switch to supervisor mode for CSR sweep",
            "\tRVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    # The S-mode CSR sweep stays in S-mode continuously from the opening
    # RVTEST_GOTO_LOWER_MODE Smode (above) to the closing RVTEST_GOTO_LOWER_MODE Mmode
    # (below).  No intra-sweep mode switches are emitted.
    #
    # Why no batch boundaries with GOTO Mmode/Smode pairs:
    # RVTEST_GOTO_LOWER_MODE Mmode is a preprocessor no-op on some configs
    # (including RV32 sail-rv32-max) — it generates zero machine code.  Emitting
    # it inside the sweep therefore leaves us in S-mode.  GOTO Smode then executes
    # from S-mode: its first instruction is an M-mode CSR read that traps as
    # illegal.  The fast handler advances mepc+4, skipping only that instruction,
    # and execution falls into the middle of the macro with a corrupt register
    # value.  The subsequent lw using that register hits an invalid address,
    # producing a load-access-fault.  Mtrampoline (not the fast handler) catches
    # it, saves S-mode sp=0 into the framework save area, and later rtn_fm_mmode
    # restores sp=0 → epilog store-access-fault → infinite fetch-fault loop.
    #
    # Safe split-file invariant (no GOTO pairs needed):
    # The only instructions in the sweep body are csrr / li / csrrw / csrrs /
    # csrrc — all either trap as illegal (M-mode CSRs from S-mode, handled by
    # the fast handler) or execute silently (S/U-mode CSRs from S-mode).
    # Neither path fires Mtrampoline.  Therefore the framework save area is never
    # written during the sweep, and it retains the valid M-mode sp written by the
    # GOTO Smode that opened the sweep (either at the start of this function for
    # the first file that contains the sweep opening, or by the previous file's
    # setup for subsequent files).  When RVTEST_CODE_END's ecall fires from
    # S-mode, rtn_fm_mmode restores that valid sp and the epilog succeeds.
    #
    # Blank lines every 10 CSRs give the splitter enough cut points without any
    # mode-switch instructions at the boundaries.
    all_csrs = [a for a in range(4096) if a not in _S_CSR_SKIP]
    for idx, csr_addr in enumerate(all_csrs):
        if idx > 0 and idx % 10 == 0:
            lines.append("")

        r1, r2, r3 = sample(_SAFE_REGS, 3)
        ih = hex(csr_addr)
        lines.extend(
            [
                f"# CSR {ih}",
                f"\t{test_data.add_testcase(f'csrr_{ih}', 'cp_csrr', covergroup)}",
                f"\tcsrr x{r1}, {ih}",  # save CSR value
                f"\tli x{r2}, -1",  # all-ones
                f"\t{test_data.add_testcase(f'csrw_ones_{ih}', 'cp_csrw_corners', covergroup)}",
                f"\tcsrrw x{r3}, {ih}, x{r2}",  # write all-ones
                f"\t{test_data.add_testcase(f'csrw_zeros_{ih}', 'cp_csrw_corners', covergroup)}",
                f"\tcsrrw x{r3}, {ih}, x0",  # write all-zeros
                f"\t{test_data.add_testcase(f'csrrs_{ih}', 'cp_csrcs', covergroup)}",
                f"\tcsrrs x{r3}, {ih}, x{r2}",  # set all bits
                f"\t{test_data.add_testcase(f'csrrc_{ih}', 'cp_csrcs', covergroup)}",
                f"\tcsrrc x{r3}, {ih}, x{r2}",  # clear all bits
                f"\tcsrrw x{r3}, {ih}, x{r1}",  # restore
            ]
        )

    # Final return to M-mode after last batch
    lines.extend(
        [
            "",
            "# Return to machine mode after S-mode CSR sweep",
            "\tRVTEST_GOTO_LOWER_MODE Mmode",
            "\tcsrw    mie, x0",
            "",
        ]
    )

    return lines


# ── Shadow CSR writes (M-mode writes, S-mode shadow verification) ─────────


def _generate_shadow_csr(test_data: TestData) -> list[str]:
    """cp_shadow_m / cp_shadow_s — mstatus/mie/mip shadow relationship.

    Writes all-ones and all-zeros to mstatus/mie from M-mode (mip skipped —
    writing MSIP/SSIP with MIE potentially enabled can fire spurious interrupts),
    then reads the S-mode shadow registers sstatus/sie/sip from S-mode.

    Safety invariants:
      M-mode: mie is cleared before any mstatus write so a transient MIE=1
              in mstatus cannot cause interrupt delivery.  Originals for both
              mstatus and mie are saved via csrr and fully restored afterward.
      S-mode: each shadow CSR is saved (csrr), corner-tested, then restored
              (csrw) before the next CSR is touched.  Ordering sstatus → sie →
              sip ensures sstatus.SIE=original(0) whenever sie or sip carry a
              transient all-ones value, so no interrupt can be delivered.
    """
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_shadow_m / cp_shadow_s",
            "Write mstatus/mie from M-mode (all 0s / all 1s),\n"
            "then read sstatus/sie/sip from S-mode to cover the shadow relationship.\n"
            "mip skipped in M-mode section (MSIP/SSIP write unsafe while MIE may be 1).",
        )
    )

    # Fixed registers for M-mode section (no random sampling — we need specific slots).
    r_sv_mstatus = _SAFE_REGS[0]  # x7 — saved mstatus original
    r_sv_mie = _SAFE_REGS[1]      # x8 — saved mie original
    r_scratch = _SAFE_REGS[2]     # x9 — scratch: li -1, csrrw discard destination

    lines.extend(
        [
            "",
            "# cp_shadow_m: write mstatus/mie from M-mode (originals saved and restored)",
            f"\tcsrr x{r_sv_mstatus}, 0x300",   # save mstatus original
            f"\tcsrr x{r_sv_mie}, 0x304",        # save mie original
            # Disable M-mode interrupts before any mstatus write.  A transient
            # MIE=1 written into mstatus is harmless when mie=0 (no source enabled).
            f"\tcsrw 0x304, x0",                 # mie = 0
        ]
    )

    # Test mstatus corner values (mie=0 throughout).
    # After writing all-zeros to mstatus, mstatus.MIE=0 — exploit this to make
    # the mie all-ones write safe: do NOT restore mstatus until after mie tests.
    lines.extend(
        [
            f"\t{test_data.add_testcase('mstatus_ones', 'cp_shadow_m', covergroup)}",
            f"\tli x{r_scratch}, -1",
            f"\tcsrrw x{r_scratch}, 0x300, x{r_scratch}",  # write all-ones (mie=0, safe)
            f"\t{test_data.add_testcase('mstatus_zeros', 'cp_shadow_m', covergroup)}",
            f"\tcsrrw x{r_scratch}, 0x300, x0",             # write all-zeros → mstatus.MIE=0
        ]
    )

    # Test mie corner values while mstatus.MIE=0 (mstatus still holds all-zeros
    # from the line above).  Writing all-ones to mie (MTIE=1) with MIE=0 in
    # mstatus cannot deliver a machine-timer interrupt even if MTIP=1.
    lines.extend(
        [
            f"\t{test_data.add_testcase('mie_ones', 'cp_shadow_m', covergroup)}",
            f"\tli x{r_scratch}, -1",
            f"\tcsrrw x{r_scratch}, 0x304, x{r_scratch}",  # write all-ones (MIE=0, safe)
            f"\t{test_data.add_testcase('mie_zeros', 'cp_shadow_m', covergroup)}",
            f"\tcsrrw x{r_scratch}, 0x304, x0",             # write all-zeros
            # Restore mie first (mstatus.MIE still 0 → no interrupt during restore).
            # Then restore mstatus (mie is now original → safe even if MIE=1 restored).
            f"\tcsrw 0x304, x{r_sv_mie}",                   # restore mie original
            f"\tcsrw 0x300, x{r_sv_mstatus}",               # restore mstatus original
        ]
    )

    # Fixed registers for S-mode section.
    r_sv = _SAFE_REGS[0]    # x7 — saved CSR original for current iteration
    r_ones = _SAFE_REGS[1]  # x8 — all-ones constant, loaded once
    r_rd = _SAFE_REGS[2]    # x9 — csrrw destination (result discarded)

    lines.extend(
        [
            "",
            "# cp_shadow_s: write/read sstatus/sie/sip from S-mode",
            "# Each CSR is saved (csrr), corner-tested, then fully restored (csrw)",
            "# before the next CSR is touched — prevents spurious interrupt delivery.",
            "\tRVTEST_GOTO_LOWER_MODE Smode",
            f"\tli x{r_ones}, -1",  # load -1 once, reuse for all three CSRs
        ]
    )

    # Ordering: sstatus → sie → sip.
    # When writing all-ones to sie, sstatus.SIE=original(0) → no delivery.
    # When writing all-ones to sip, sstatus.SIE=original(0) → no delivery.
    for csr_name, csr_addr in [("sstatus", "0x100"), ("sie", "0x104"), ("sip", "0x144")]:
        lines.extend(
            [
                f"\tcsrr x{r_sv}, {csr_addr}",                         # save original
                f"\t{test_data.add_testcase(f'{csr_name}_ones', 'cp_shadow_s', covergroup)}",
                f"\tcsrrw x{r_rd}, {csr_addr}, x{r_ones}",             # write all-ones
                f"\t{test_data.add_testcase(f'{csr_name}_zeros', 'cp_shadow_s', covergroup)}",
                f"\tcsrrw x{r_rd}, {csr_addr}, x0",                    # write all-zeros
                f"\tcsrw {csr_addr}, x{r_sv}",                         # restore original
            ]
        )

    # Return to M-mode
    lines.extend(
        [
            "",
            "\tRVTEST_GOTO_LOWER_MODE Mmode",
            "\tcsrw    mie, x0",  # re-disable interrupts after Mtrampoline ecall return
            "",
        ]
    )

    return lines


# ── Illegal instruction sweep (M-mode, identical templates to SsstrictSm) ─


def _generate_illegal_instr(test_data: TestData) -> list[str]:
    """cp_illegal_instruction — reserved/illegal 32-bit encoding sweep.

    Run from M-mode so the fast handler can advance mepc correctly.
    Encodings are identical to SsstrictSm: these are reserved/illegal
    regardless of privilege mode.
    """
    covergroup = "SsstrictS_instr_cg"
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
            "Exhaustive reserved/illegal 32-bit encoding sweep from M-mode.\n"
            "Illegal encodings trap regardless of privilege level.\n"
            "Vector opcodes op21/op29 excluded — covered in SsstrictV.",
        )
    )

    lines.extend(
        [
            "",
            "# Enable FP (mstatus.FS=01)",
            "\tli t2, 1",  # t2=x7, safe
            "\tslli t3, t2, 13",  # t3=x28
            "\tcsrs mstatus, t3",
            "",
        ]
    )

    lines.append(f"\t{test_data.add_testcase('illegal_instr_sweep', coverpoint, covergroup)}")
    lines.append("")

    for cmt, tmpl in [
        ("Reserved op7", "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
        ("Reserved op15", "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
        ("Reserved op21", "RRRRRRRRRRRRRRRRRRRRRRRRR1010111"),
        ("Reserved op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Reserved op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        ("Reserved op29", "RRRRRRRRRRRRRRRRRRRRRRRRR1110111"),
        ("Reserved op31", "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
    ]:
        _emit_raw_words(lines, cmt, tmpl)

    _emit_raw_words(lines, "cp_load", "RRRRRRRRRRRRRRRRREEE010010000011")
    _emit_raw_words(lines, "cp_fload", "RRRRRRRRRRRRRRRRREEE010010000111")
    _emit_raw_words(lines, "cp_fence_cbo", "RRRRRRRRRRRRRRRRREEE010010001111")
    _emit_raw_words(lines, "cp_cbo_immediate", "EEEEEEEEEEEE00000010000000001111")
    _emit_raw_words(lines, "cp_cbo_rd", "00000000000RRRRRR010EEEEE0001111")
    _emit_raw_words(lines, "cp_store", "RRRRRRRRRRRR00000EEERRRRR0100011")
    _emit_raw_words(lines, "cp_fstore", "RRRRRRRRRRRR00000EEERRRRR0100111")
    _emit_raw_words(lines, "cp_Itype", "EEEEEEEEEEEERRRRRE01010010010011")
    _emit_raw_words(lines, "cp_llAItype", "RRRRRRRRRRRRRRRRREEE010010010011")
    _emit_raw_words(lines, "cp_aes64ks1i", "0011000EEEEERRRRR001010010010011")
    _emit_raw_words(lines, "cp_IWtype", "RRRRRRRRRRRRRRRRREEE010010011011")
    _emit_raw_words(lines, "cp_IWshift", "EEEEEEERRRRRRRRRRE01010010011011")
    _emit_raw_words(lines, "cp_atomic_funct3", "RRRRRRRRRRRR00000EEE010010101111")
    _emit_raw_words(lines, "cp_atomic_funct7", "EEEEERRRRRRR0000001E010010101111")
    _emit_raw_words(lines, "cp_lrsc", "00010RREEEEE0000001E010010101111")
    _emit_raw_words(lines, "cp_rtype", "EEEEEEE0011100111EEE001110110011")
    _emit_raw_words(lines, "cp_rwtype", "EEEEEEE0011100111EEE001110111011")
    _emit_raw_words(lines, "cp_ftype", "EEEEERR0011100111EEE001111010011")
    _emit_raw_words(lines, "cp_fsqrt", "0101100EEEEE00111000011111010011")
    _emit_raw_words(lines, "cp_fclass", "1110000EEEEE00111001001111010011")
    _emit_raw_words(lines, "cp_fcvtif", "1100000EEE0000111000001111010011")
    _emit_raw_words(lines, "cp_fcvtif_fmt", "11000EE000EE00111000001111010011")
    _emit_raw_words(lines, "cp_fcvtfi", "1101000EEE1000111000001111010011")
    _emit_raw_words(lines, "cp_fcvtfi_fmt", "11010EE000EE00111000001111010011")
    _emit_raw_words(lines, "cp_fcvtff", "0100000EEE1000111000001111010011")
    _emit_raw_words(lines, "cp_fcvtff_fmt", "01000EEEEEEE00111000001111010011")
    _emit_raw_words(lines, "cp_fmvif", "11100EEEEEEE00111000001111010011")
    _emit_raw_words(lines, "cp_fli", "11110EEEEEEERRRRR000010011010011")
    _emit_raw_words(lines, "cp_fmvfi", "11110EEEEEEE00111000001111010011")
    _emit_raw_words(lines, "cp_fmvh", "11100EEEEEEERRRRR000010011010011")
    _emit_raw_words(lines, "cp_fmvp", "11100EE0011100111000001111010011")
    _emit_raw_words(lines, "cp_cvtmodwd", "11000EEEEEEE00111001001111010011")
    _emit_raw_words(lines, "cp_fcvtmodwdfrm", "11000010100000111EEE001111010011")
    _emit_raw_words(lines, "cp_branch2", "RRRRRRR0011100111010001111100011")
    _emit_raw_words(lines, "cp_branch3", "RRRRRRR0011100111011001111100011")
    _emit_raw_words(lines, "cp_jalr0", "RRRRRRR0011100111EE1001111100111")
    _emit_raw_words(lines, "cp_jalr1", "RRRRRRR0011100111010001111100111")
    _emit_raw_words(lines, "cp_jalr2", "RRRRRRR0011100111100001111100111")
    _emit_raw_words(lines, "cp_jalr3", "RRRRRRR0011100111110001111100111")
    _emit_raw_words(lines, "cp_privileged_f3", "00000000000100000EEE000001110011")
    _emit_raw_words(
        lines,
        "cp_privileged_000",
        "EEEEEEEEEEEE00000000000001110011",
        exclusion=[
            "1XXX11XXXXXX00000000000001110011",  # custom system
            "00X10000001000000000000001110011",  # mret/sret
            "00000000000000000000000001110011",  # ecall
            "00010000010100000000000001110011",  # wfi
            # Valid privileged instructions that execute without trapping
            # on implementations with Sv39/Svinval/H-extension:
            "0001001XXXXXXXXXX000000001110011",  # SFENCE.VMA (any rs1,rs2)
            "0001011XXXXXXXXXX000000001110011",  # SINVAL.VMA (Svinval)
            "00011000000000000000000001110011",  # SFENCE.W.INVAL
            "00011000000100000000000001110011",  # SFENCE.INVAL.IR
            "0010001XXXXXXXXXX000000001110011",  # HFENCE.BVMA
            "1010001XXXXXXXXXX000000001110011",  # HFENCE.GVMA
            "01110000001000000000000001110011",  # MNRET (Smrnmi)
            "00000000001000000000000001110011",  # URET (deprecated)
        ],
    )
    _emit_raw_words(
        lines, "cp_privileged_rd", "00000000000000000000EEEEE1110011", exclusion=["00000000000000000000000001110011"]
    )
    _emit_raw_words(
        lines, "cp_privileged_rs2", "000000000000EEEEE000000001110011", exclusion=["00000000000000000000000001110011"]
    )
    _emit_raw_words(lines, "cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11")
    _emit_raw_words(lines, "cp_reserved_fence_fm", "EEEE00000000RRRRR000RRRRR0001111")
    _emit_raw_words(lines, "cp_reserved_fence_rs1", "00001111111100001000RRRRE0001111")
    _emit_raw_words(lines, "cp_reserved_fence_rd", "000011111111RRRRE000000010001111")

    lines.append(comment_banner("cp_upperreg", "x16-x31 — trap when E extension active"))
    for cmt, tmpl in [
        ("cp_upperreg_rs1_add", "0000000000011EEEE000000010110011"),
        ("cp_upperreg_rs2_add", "00000001EEEE00001000001100110011"),
        ("cp_upperreg_rd_add", "000000000001000010001EEEE0110011"),
        ("cp_upperreg_rs1_mul", "0000001000011EEEE000000010110011"),
        ("cp_upperreg_rs2_mul", "00000011EEEE00001000001100110011"),
        ("cp_upperreg_rd_mul", "000000100001000010001EEEE0110011"),
        ("cp_upperreg_rs1_fadd-s", "0000000000011EEEE000000011010011"),
        ("cp_upperreg_rs2_fadd-s", "00000001EEEE00001000000101010011"),
        ("cp_upperreg_rd_fadd-s", "000000000001000010001EEEE1010011"),
        ("cp_upperreg_imm_rs1_addi0", "0000000000001EEEE000000010010011"),
        ("cp_upperreg_imm_rs1_addi1", "1111111111111EEEE000000010010011"),
        ("cp_upperreg_imm_rd_addi0", "000000000000000010001EEEE0010011"),
        ("cp_upperreg_imm_rd_addi1", "111111111111000010001EEEE0010011"),
        ("cp_upperreg_fmv_x_w_rs1", "1110000000001EEEE000000011010011"),
        ("cp_upperreg_fmv_x_w_rd", "111000000000000010001EEEE1010011"),
        ("cp_upperreg_fmv_w_x_rs1", "1111000000001EEEE000000011010011"),
        ("cp_upperreg_fmv_w_x_rd", "111100000000000010001EEEE1010011"),
        ("cp_amocas_odd", "00101RRRRRRRRRRREEEE0100E0101111"),
    ]:
        _emit_raw_words(lines, cmt, tmpl)

    _emit_raw_words(lines, "cp_amocas_odd", "00101RRRRRRR00000000RRRRE0101111")
    return lines


# ── Compressed instruction sweep ──────────────────────────────────────────


def _generate_compressed_instr(test_data: TestData) -> list[str]:
    """cp_illegal_compressed_instruction — all 16-bit quadrant sweeps."""
    covergroup = "SsstrictSm_comp_instr_cg"
    coverpoint = "cp_illegal_compressed_instruction"
    lines: list[str] = []

    lines.append(comment_banner(coverpoint, "Exhaustive 16-bit quadrant sweep from M-mode."))
    lines.append(f"\t{test_data.add_testcase('compressed_sweep', coverpoint, covergroup)}")
    lines.append("")

    _emit_raw_words(
        lines,
        "compressed00",
        "EEEEEEEEEEEEEE00",
        length=16,
        exclusion=[
            "X01XXXXXXXXXXX00",  # c.fld/c.fsd — bad address
            "X10XXXXXXXXXXX00",  # c.lw/c.sw — bad address
            "10000XXXXXXXXX00",  # c.lbu , c.lh, c.lhu
            "10010XXXXXXXXX00",  # c.sb: bits[15:11]=10010, bit10=imm[5] varies
            "10011XXXXXXXXX00",  # c.sh: bits[15:11]=10011, bit10 varies
            "XXXX00010XXXXX00",  # rd = x2
            "011XXXXXXXXXXX00",  # c.ld — garbage in regs + random mtval on fault
            "111XXXXXXXXXXX00",  # c.sd — store from uninitialised reg, bad address
        ],
    )
    _emit_raw_words(
        lines,
        "compressed01",
        "EEEEEEEEEEEEEE01",
        length=16,
        exclusion=[
            "101XXXXXXXXXXX01",  # c.j — random jump
            "11XXXXXXXXXXXX01",  # c.beqz/c.bnez — random branch
            "001XXXXXXXXXXX01",  # c.jr
            "XXXX00010XXXXX01",  # rd = x2
        ],
    )
    _emit_raw_words(
        lines,
        "compressed10",
        "1EEEEEEEEEEEEE10",
        length=16,
        exclusion=[
            "1000XXXXX0000010",  # c.jr rs1!=0
            "1001XXXXX0000010",  # c.jalr/c.ebreak
            "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp
            "X10XXXXXXXXXXX10",  # c.lwsp/c.swsp — bad address
            "1001000000000010",  # c.ebreak
            "XXXX00010XXXXX10",  # rd = x2 (sp)
            "1100XXXXXXXXXX10",  # c.swsp with rs2=x2 (corrupts via store of sp)
            "1110XXXXXXXXXX10",  # c.lwsp rd=x2 alternate encoding guard
            "1010XXXXXXXXXX10",  # zero-length / nop-like edge in quadrant 2
        ],
    )
    lines.append("")

    return lines


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictS",
    required_extensions=["Sm", "S", "Zicsr"],
    march_extensions=[
        # Zcf excluded — RV32-only.
        # Vector excluded — covered by SsstrictV.
        # Zbc/Zacas/Zcb excluded: not in non-max configs, not supported by GCC < 14.
        "I",
        "M",
        "A",
        "F",
        "D",
        "C",
        "Zicsr",
        "Zba",
        "Zbb",
        "Zbs",
        "Zca",
        "Zcd",
    ],
)
def make_ssstrictss(test_data: TestData) -> list[str]:
    """SsstrictS — supervisor-mode strict compliance tests."""
    seed(42)
    lines: list[str] = []
    lines.extend(_generate_csr_tests_s(test_data))
    lines.extend(_generate_shadow_csr(test_data))
    lines.extend(_generate_illegal_instr(test_data))
    lines.extend(_generate_compressed_instr(test_data))
    return lines
