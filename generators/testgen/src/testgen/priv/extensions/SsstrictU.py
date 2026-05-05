##################################
# priv/extensions/SsstrictU.py
#
# Ssstrict user-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from U-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictU — user-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.

Structure
---------
1. Switch to U-mode via RVTEST_GOTO_LOWER_MODE Umode.
2. CSR sweep from U-mode (user-privilege CSRs only: 0x000-0x0FF,
   0x400-0x4FF, 0xC00-0xCBF).
   - All S/H/M CSRs raise illegal-instruction from U-mode.
   - Custom and reserved ranges are skipped.
3. Return to M-mode, then run the illegal instruction and compressed
   sweeps (from M-mode so the fast handler handles every trap correctly).

Register exclusion for the CSR sweep
--------------------------------------
Same constraints as SsstrictSm — all scratch registers chosen from
{x7..x31} only.  x0-x6 are permanently excluded (see SsstrictSm.py for
the full rationale).
"""

from random import choice, randint, sample, seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

BLANK_INTERVAL = 50

_SAFE_REGS: list[int] = list(range(7, 32))  # x7 .. x31


# ── CSR skip set (U-mode) ─────────────────────────────────────────────────

# U-mode can only access CSRs with privilege bits[9:8]=00 (user-level):
#   0x000-0x0FF: user standard (all accessible)
#   0x400-0x4FF: user standard (performance counter shadows)
#   0x800-0x8FF: user custom2 — skip: undefined behaviour
#   0xC00-0xCBF: user read-only counters (cycle, time, instret, hpmcounterN)
#   0xCC0-0xCFF: user custom3 — skip
#
# All S/H/M CSRs (priv bits != 00) raise illegal-instruction from U-mode.
# Those are swept by SsstrictSm/S so we do not duplicate them here.

_U_CSR_SKIP: frozenset[int] = frozenset(
    list(range(0x100, 0x1000))  # everything above 0x0FF except user std1 and counters
    # Re-add the user-accessible ranges (we'll compute accessible positively below)
    # Actually use an exclusion approach: skip everything NOT user-privilege
)

# Build the accessible set positively: only CSRs with bits[9:8]=00
_U_CSR_ACCESSIBLE: frozenset[int] = frozenset(
    a
    for a in range(4096)
    if ((a >> 8) & 3) == 0  # user-privilege level
    and a not in range(0x800, 0x900)  # skip user custom2
    and a not in range(0xCC0, 0xD00)  # skip user custom3
)


# ── Encoding helpers (shared logic identical to SsstrictSm) ───────────────


SAFE_REGS = list(range(7, 32))  # x7 .. x31


def _gen_encodings(
    template: str,
    length: int = 32,
    exclusion: list[str] | None = None,
) -> list[str]:
    """Generate all exhaustive encodings from a template string."""
    if exclusion is None:
        exclusion = []

    # For 32-bit instructions, identify register fields (MSB-first indices).
    # rd: bits[11:7] -> template[20:25]
    # rs1: bits[19:15] -> template[12:17]
    # rs2: bits[24:20] -> template[7:12]
    reg_field_ranges = []
    if length == 32:
        reg_field_ranges = [(7, 12), (12, 17), (20, 25)]

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

        # Overwrite register fields that are fully random (all 'R' in
        # the template) with a randomly chosen safe register (x7..x31).
        for start, end in reg_field_ranges:
            if all(template[k] == "R" for k in range(start, end)):
                reg = choice(SAFE_REGS)
                reg_bits = f"{reg:05b}"
                for k, b in enumerate(reg_bits):
                    instr[start + k] = b

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


# ── U-mode CSR sweep ──────────────────────────────────────────────────────


def _generate_csr_tests_u(test_data: TestData) -> list[str]:
    """cp_csrr / cp_csrw_corners / cp_csrcs from U-mode.

    Switches to U-mode, sweeps all user-accessible CSRs, then returns
    to M-mode via ecall.
    """
    covergroup = "SsstrictU_ucsr_cg"
    lines: list[str] = []

    lines.append(
        comment_banner(
            "cp_csrr / cp_csrw_corners / cp_csrcs (U-mode)",
            "Read, write 0s/1s, set, clear every user-accessible CSR from U-mode.\n"
            "S/H/M CSRs all raise illegal-instruction from U-mode.\n"
            "Custom and reserved CSR ranges skipped.",
        )
    )

    # Switch to U-mode — no trailing blank so the splitter cannot cut between
    # this and the first CSR instruction.
    lines.extend(
        [
            "",
            "# Switch to user mode for CSR sweep",
            "\tRVTEST_GOTO_LOWER_MODE Umode",
        ]
    )

    # The U-mode CSR sweep stays in U-mode continuously from the opening
    # RVTEST_GOTO_LOWER_MODE Umode to the closing RVTEST_GOTO_MMODE.
    # No intra-sweep mode switches are emitted — same rationale as SsstrictS.py:
    # RVTEST_GOTO_MMODE is a no-op on some configs, so any intra-sweep
    # GOTO Umode would execute from U-mode, crashing identically.
    # All CSR accesses from U-mode either trap as illegal (handled by fast handler)
    # or execute silently — Mtrampoline is never fired, save area sp stays valid.
    all_csrs = sorted(_U_CSR_ACCESSIBLE)
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
                f"\tcsrrw x{r3}, {ih}, x{r2}",  # write all-ones (illegal for RO csrs)
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
            "# Return to machine mode after U-mode CSR sweep",
            "\tRVTEST_GOTO_MMODE",
            "",
        ]
    )

    return lines


# ── Illegal instruction sweep (M-mode, identical templates to SsstrictSm) ─


def _generate_illegal_instr(test_data: TestData) -> list[str]:
    """cp_illegal_instruction — reserved/illegal 32-bit encoding sweep.

    Run from M-mode so the fast handler can advance mepc correctly.
    """
    covergroup = "SsstrictU_instr_cg"
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

    lines.append("")
    lines.append("\t.align 4")  # force 4-byte alignment before the sweep
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

    _emit_raw_words(lines, "cp_load", "RRRRRRRRRRRRRRRRREEE010010000011")
    _emit_raw_words(
        lines,
        "cp_fload",
        "RRRRRRRRRRRRRRRRREEE010010000111",
        exclusion=[
            "110XXXXXXXXXXXX01XXXXXXXXXXXXXXX",  # c.beqz
            "111XXXXXXXXXXXX01XXXXXXXXXXXXXXX",  # c.bnez
            "101XXXXXXXXXXXX01XXXXXXXXXXXXXXX",  # c.j
            "001XXXXXXXXXXXX01XXXXXXXXXXXXXXX",  # c.jal (RV32 only)
            "1000XXXXXXXXX0000010XXXXXXXXXXXXXX",  # c.jr
            "1001XXXXXXXXX0000010XXXXXXXXXXXXXX",  # c.jalr
        ],
    )
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
    "SsstrictU",
    required_extensions=["Sm", "U", "Zicsr"],
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
def make_ssstrictu(test_data: TestData) -> list[str]:
    """SsstrictU — user-mode strict compliance tests."""
    seed(42)
    lines: list[str] = []
    lines.extend(_generate_csr_tests_u(test_data))
    lines.extend(_generate_illegal_instr(test_data))
    lines.extend(_generate_compressed_instr(test_data))
    return lines
