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
5. misa extension disable: same as SsstrictSm, from M-mode.

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

_SAFE_REGS: list[int] = list(range(7, 32))  # x7 .. x31


# ── CSR skip set (S-mode) ─────────────────────────────────────────────────

_S_CSR_SKIP: frozenset[int] = frozenset(
    [0x180]  # satp — skip: TLB flush / address-translation mode change
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

    # Switch to S-mode
    lines.extend(
        [
            "",
            "# Switch to supervisor mode for CSR sweep",
            "\tRVTEST_GOTO_LOWER_MODE Smode",
            "",
        ]
    )

    # CSR_BATCH_SIZE CSRs per S-mode session. At each boundary we return to
    # M-mode and re-enter S-mode so that every split file is self-contained:
    # each file starts with RVTEST_GOTO_LOWER_MODE Smode and ends with
    # RVTEST_GOTO_LOWER_MODE Mmode, regardless of where the splitter cuts.
    CSR_BATCH_SIZE = 50

    all_csrs = [a for a in range(4096) if a not in _S_CSR_SKIP]
    for idx, csr_addr in enumerate(all_csrs):
        # At every batch boundary (except the first): return to M-mode,
        # emit a blank line (the splitter cuts here), then re-enter S-mode.
        if idx > 0 and idx % CSR_BATCH_SIZE == 0:
            lines.extend(
                [
                    "\tRVTEST_GOTO_LOWER_MODE Mmode",
                    "",  # blank line — splitter cuts here
                    "\tRVTEST_GOTO_LOWER_MODE Smode",
                ]
            )
        elif idx > 0 and idx % 10 == 0:
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
            "",
        ]
    )

    return lines


# ── Shadow CSR writes (M-mode writes, S-mode shadow verification) ─────────


def _generate_shadow_csr(test_data: TestData) -> list[str]:
    """cp_shadow_m / cp_shadow_s — mstatus/mie/mip shadow relationship.

    Writes all-ones and all-zeros to mstatus/mie/mip from M-mode, then
    reads the S-mode shadow registers sstatus/sie/sip from S-mode.
    Only writes the S-mode-visible bitfields to avoid DUT matching issues
    with implementation-specific M-mode-only fields.
    """
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_shadow_m / cp_shadow_s",
            "Write mstatus/mie/mip from M-mode (all 0s / all 1s),\n"
            "then read sstatus/sie/sip from S-mode to cover the shadow relationship.",
        )
    )

    # Write to M-mode shadow CSRs from M-mode
    lines.append("")
    lines.append("# cp_shadow_m: write mstatus/mie/mip from M-mode")
    for csr_name, csr_addr in [("mstatus", "0x300"), ("mie", "0x304"), ("mip", "0x344")]:
        r1 = _SAFE_REGS[0]  # x7, always safe
        lines.extend(
            [
                f"\t{test_data.add_testcase(f'{csr_name}_ones', 'cp_shadow_m', covergroup)}",
                f"\tli x{r1}, -1",
                f"\tcsrrw x0, {csr_addr}, x{r1}",  # write all-ones
                f"\t{test_data.add_testcase(f'{csr_name}_zeros', 'cp_shadow_m', covergroup)}",
                f"\tcsrrw x0, {csr_addr}, x0",  # write all-zeros
            ]
        )

    # Switch to S-mode to read shadow registers
    lines.extend(
        [
            "",
            "# cp_shadow_s: read sstatus/sie/sip from S-mode",
            "\tRVTEST_GOTO_LOWER_MODE Smode",
        ]
    )
    for csr_name, csr_addr in [("sstatus", "0x100"), ("sie", "0x104"), ("sip", "0x144")]:
        r1, r2, r3 = sample(_SAFE_REGS, 3)
        lines.extend(
            [
                f"\t{test_data.add_testcase(f'{csr_name}_ones', 'cp_shadow_s', covergroup)}",
                f"\tli x{r2}, -1",
                f"\tcsrrw x{r3}, {csr_addr}, x{r2}",  # write all-ones
                f"\t{test_data.add_testcase(f'{csr_name}_zeros', 'cp_shadow_s', covergroup)}",
                f"\tcsrrw x{r3}, {csr_addr}, x0",  # write all-zeros
                f"\tcsrrw x0, {csr_addr}, x{r1}",  # restore (r1=0 after INIT_REGS)
            ]
        )

    # Return to M-mode
    lines.extend(
        [
            "",
            "\tRVTEST_GOTO_LOWER_MODE Mmode",
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
        ("Reserved op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Reserved op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        ("Reserved op31", "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
    ]:
        _emit_raw_words(lines, cmt, tmpl)

    _emit_raw_words(lines, "cp_load funct3", "RRRRRRRRRRRR00000111001110000011")
    _emit_raw_words(lines, "cp_fload funct3", "RRRRRRRRRRRR00000001001110000111")
    _emit_raw_words(lines, "cp_fence_cbo funct3", "RRRRRRRRRRRRRRRRREEERRRRR0001111")
    _emit_raw_words(lines, "cp_cbo_immediate (rs1=0)", "EEEEEEEEEEEE00000010000000001111")
    _emit_raw_words(lines, "cp_cbo_rd", "00000000000RRRRRR010EEEEE0001111")
    _emit_raw_words(lines, "cp_store funct3 (rs1=0)", "RRRRRRRRRRRR00000100RRRRR0100011")
    _emit_raw_words(lines, "cp_fstore funct3 (rs1=0)", "RRRRRRRRRRRR00000001RRRRR0100111")
    _emit_raw_words(lines, "cp_Itype funct3[2:1]=01", "EEEEEEEEEEEERRRRRE01001110010011")
    _emit_raw_words(lines, "cp_Itypef3", "RRRRRRRRRRRRRRRRREEE001110010011")
    _emit_raw_words(lines, "cp_aes64ks1i rnum", "0011000EEEEERRRRR001001110010011")
    _emit_raw_words(lines, "cp_IWtype funct3", "RRRRRRRRRRRRRRRRREEE001110011011")
    _emit_raw_words(lines, "cp_IWshift", "EEEEEEERRRRRRRRRRE01001110011011")
    _emit_raw_words(lines, "cp_atomic_funct3 (rs1=0)", "RRRRRRRRRRRR00000000001110101111")
    _emit_raw_words(lines, "cp_atomic_funct7 (rs1=0)", "EEEEERRRRRRR00000000001110101111")
    _emit_raw_words(lines, "cp_lrsc", "00010RREEEEE00000000001110101111")
    _emit_raw_words(lines, "cp_rtype", "EEEEEEERRRRRRRRRREEE001110110011")
    _emit_raw_words(lines, "cp_rwtype", "EEEEEEERRRRRRRRRREEE001110111011")
    _emit_raw_words(lines, "cp_ftype", "EEEEERRRRRRRRRRRREEE001111010011")
    _emit_raw_words(lines, "cp_fsqrt", "0101100EEEEERRRRR000011111010011")
    _emit_raw_words(lines, "cp_fclass", "1110000EEEEERRRRR001001111010011")
    _emit_raw_words(lines, "cp_fcvtif", "1100000EEE00RRRRR000001111010011")
    _emit_raw_words(lines, "cp_fcvtif_fmt", "11000EE000EERRRRR000001111010011")
    _emit_raw_words(lines, "cp_fcvtfi", "1101000EEER00RRRR000001111010011")
    _emit_raw_words(lines, "cp_fcvtfi_fmt", "11010EE000EERRRRR000001111010011")
    _emit_raw_words(lines, "cp_fcvtff", "0100000EEER00RRRR000001111010011")
    _emit_raw_words(lines, "cp_fcvtff_fmt", "01000EEEEEEERRRRR000001111010011")
    _emit_raw_words(lines, "cp_fmvif", "11100EEEEEEERRRRR000001111010011")
    _emit_raw_words(lines, "cp_fmvfi", "11110EEEEEEERRRRR000001111010011")
    _emit_raw_words(lines, "cp_fmvp", "10110EERRRRRRRRRR000001111010011")
    _emit_raw_words(lines, "cp_fcvtmodwdfrm", "110000101000RRRRREEE001111010011")
    _emit_raw_words(lines, "cp_branch2", "RRRRRRRRRRRRRRRRR010RRRRR1100011")
    _emit_raw_words(lines, "cp_branch3", "RRRRRRRRRRRRRRRRR011RRRRR1100011")
    _emit_raw_words(lines, "cp_jalr0", "RRRRRRRRRRRRRRRRREE1001111100111")
    _emit_raw_words(lines, "cp_jalr1", "RRRRRRRRRRRRRRRRR010001111100111")
    _emit_raw_words(lines, "cp_jalr2", "RRRRRRRRRRRRRRRRR100001111100111")
    _emit_raw_words(lines, "cp_jalr3", "RRRRRRRRRRRRRRRRR110001111100111")
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
            # Valid privileged instructions that execute without trapping:
            "0001001XXXXXXXXXX000000001110011",  # SFENCE.VMA
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
        lines,
        "cp_privileged_rd",
        "00000000000000000000EEEEE1110011",
        exclusion=["00000000000000000000000001110011"],
    )
    _emit_raw_words(
        lines,
        "cp_privileged_rs2",
        "000000000000EEEEE000000001110011",
        exclusion=["00000000000000000000000001110011"],
    )
    _emit_raw_words(lines, "cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11")
    _emit_raw_words(lines, "cp_reserved_fence_fm", "EEEE00000000RRRRR000RRRRR0001111")
    _emit_raw_words(lines, "cp_reserved_fence_rs1", "00001111111100001000RRRRE0001111")
    _emit_raw_words(lines, "cp_reserved_fence_rd", "000011111111RRRRE000000010001111")

    lines.append(comment_banner("cp_upperreg", "x16-x31 — trap when E extension active"))
    for cmt, tmpl in [
        ("upperreg_rs1_add", "0000000000011EEEE000001111010011"),
        ("upperreg_rs2_add", "00000001EEEE00001000001111010011"),
        ("upperreg_rd_add", "000000000001000010001EEEE0110011"),
        ("upperreg_rs1_mul", "0000001000011EEEE000001111010011"),
        ("upperreg_rs2_mul", "00000011EEEE00001000001111010011"),
        ("upperreg_rd_mul", "000000100001000010001EEEE0110011"),
        ("upperreg_rs1_fadd-s", "0000000000011EEEE000001111010011"),
        ("upperreg_rs2_fadd-s", "00000001EEEE00001000001111010011"),
        ("upperreg_rd_fadd-s", "000000000001000010001EEEE1010011"),
        ("upperreg_imm_rs1_addi0", "0000000000001EEEE000001111010011"),
        ("upperreg_imm_rs1_addi1", "1111111111111EEEE000001111010011"),
        ("upperreg_imm_rd_addi0", "000000000000000010001EEEE0010011"),
        ("upperreg_imm_rd_addi1", "111111111111000010001EEEE0010011"),
        ("upperreg_fmv_x_w_rs1", "1110000000001EEEE000001111010011"),
        ("upperreg_fmv_x_w_rd", "111000000000000010001EEEE1010011"),
        ("upperreg_fmv_w_x_rs1", "1111000000001EEEE000001111010011"),
        ("upperreg_fmv_w_x_rd", "111100000000000010001EEEE1010011"),
    ]:
        _emit_raw_words(lines, cmt, tmpl)

    _emit_raw_words(lines, "cp_amocas_odd", "00101RRRRRRR00000000RRRRE0101111")
    return lines


# ── Compressed instruction sweep ──────────────────────────────────────────


def _generate_compressed_instr(test_data: TestData) -> list[str]:
    """cp_illegal_compressed_instruction — all 16-bit quadrant sweeps."""
    covergroup = "SsstrictS_comp_instr_cg"
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
            "011XXXXXXXXXXX00",  # c.ld (RV64) — base holds garbage → load fault
            "111XXXXXXXXXXX00",  # c.sd (RV64) — same → store fault
            "10000XXXXXXXXX00",  # c.lbu
            "100010XXXXXXXX00",  # c.lh
            "100011XXX0XXXX00",  # c.lhu
            "10010XXXXXXXXX00",  # c.sb
            "10011XXXXXXXXX00",  # c.sh
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
            "001XXXXXXXXXXX01",  # c.jal (RV32 only) / reserved
            "010X00001XXXXX01",  # c.li x1 (ra)
            "010X00010XXXXX01",  # c.li x2 (sp) — FATAL
            "010X00011XXXXX01",  # c.li x3 (gp)
            "010X00100XXXXX01",  # c.li x4 (tp)
            "010X00101XXXXX01",  # c.li x5 (t0)
            "010X00110XXXXX01",  # c.li x6 (t1)
            "011X00010XXXXX01",  # c.addi16sp
            "011X00001XXXXX01",  # c.lui x1
            "011X00011XXXXX01",  # c.lui x3
            "011X00100XXXXX01",  # c.lui x4
            "011X00101XXXXX01",  # c.lui x5
            "011X00110XXXXX01",  # c.lui x6
            "000X00001XXXXX01",  # c.addi x1
            "000X00010XXXXX01",  # c.addi x2
            "000X00011XXXXX01",  # c.addi x3
            "000X00100XXXXX01",  # c.addi x4
            "000X00101XXXXX01",  # c.addi x5
            "000X00110XXXXX01",  # c.addi x6
        ],
    )
    _emit_raw_words(
        lines,
        "compressed10",
        "EEEEEEEEEEEEEE10",
        length=16,
        exclusion=[
            "1000XXXXX0000010",  # c.jr rs1!=0 — random jump
            "1001XXXXX0000010",  # c.jalr/c.ebreak space
            "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp — bad address
            "X10XXXXXXXXXXX10",  # c.lwsp/c.swsp — bad address
            "1001000000000010",  # c.ebreak
            "011XXXXXXXXXXX10",  # c.ldsp — legal load via sp
            "111XXXXXXXXXXX10",  # c.sdsp — store fault
            "100100001XXXXX10",  # c.add x1
            "100100010XXXXX10",  # c.add x2 (sp) — FATAL
            "100100011XXXXX10",  # c.add x3
            "100100100XXXXX10",  # c.add x4
            "100100101XXXXX10",  # c.add x5
            "100100110XXXXX10",  # c.add x6
            "100000001XXXXX10",  # c.mv x1
            "100000010XXXXX10",  # c.mv x2 (sp) — FATAL
            "100000011XXXXX10",  # c.mv x3
            "100000100XXXXX10",  # c.mv x4
            "100000101XXXXX10",  # c.mv x5
            "100000110XXXXX10",  # c.mv x6
            "000X00001XXXXX10",  # c.slli x1
            "000X00010XXXXX10",  # c.slli x2 (sp) — FATAL
            "000X00011XXXXX10",  # c.slli x3
            "000X00100XXXXX10",  # c.slli x4
            "000X00101XXXXX10",  # c.slli x5
            "000X00110XXXXX10",  # c.slli x6
        ],
    )

    lines.append("")
    return lines


# ── misa extension disable ────────────────────────────────────────────────


def _generate_misa_ext_disable(test_data: TestData) -> list[str]:
    """cp_misa_ext_disable — disable each misa bit, run representative instruction."""
    covergroup = "SsstrictS_scsr_cg"
    coverpoint = "cp_misa_ext_disable"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
            "Disable each MUTABLE_MISA_* bit, execute representative instruction\n"
            "(should raise illegal-instruction), then re-enable.\n"
            "Run from M-mode so the fast handler advances mepc correctly.",
        )
    )

    for ext, bit, instr in [
        ("A", 0, "amoswap.w x0, x0, (x0)"),
        ("C", 2, "c.addi x8, 0"),
        ("D", 3, "fadd.d f0, f1, f2"),
        ("F", 5, "fadd.s f0, f1, f2"),
        ("M", 12, "mul x7, x8, x9"),
    ]:
        lines.extend(
            [
                "",
                f"#ifdef MUTABLE_MISA_{ext}",
                f"\t{test_data.add_testcase(f'misa_{ext}', coverpoint, covergroup)}",
                f"\tli t2, {1 << bit:#010x}",  # t2=x7, safe
                "\tcsrc misa, t2",
                "\tnop",
                f"\t{instr}",
                "\tnop",
                "\tcsrs misa, t2",
                "#endif",
            ]
        )

    lines.extend(
        [
            "",
            "#ifdef MUTABLE_MISA_B",
            "\tli t2, 0x2",
            "\tcsrc misa, t2",
            f"\t{test_data.add_testcase('misa_B_zba', coverpoint, covergroup)}",
            "\tsh3add x8, x9, x10",
            "\tnop",
            f"\t{test_data.add_testcase('misa_B_zbb', coverpoint, covergroup)}",
            "\tandn x8, x9, x10",
            "\tnop",
            f"\t{test_data.add_testcase('misa_B_zbs', coverpoint, covergroup)}",
            "\tbext x8, x9, x10",
            "\tnop",
            "\tcsrs misa, t2",
            "#endif",
            "",
            "#ifdef MUTABLE_MISA_I",
            f"\t{test_data.add_testcase('misa_I_upperreg', coverpoint, covergroup)}",
            "\tli t2, 0x100",
            "\tcsrc misa, t2",
            "\t.word 0x01080833",  # add x16,x16,x16 — traps when E active
            "\tnop",
            "\tcsrs misa, t2",
            "#endif",
            "",
        ]
    )

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
    lines.extend(_generate_misa_ext_disable(test_data))
    return lines
