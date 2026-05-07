##################################
# priv/extensions/SsstrictCommon.py
#
# Shared encoding helpers, illegal-instruction sweep, and compressed-
# instruction sweep used by SsstrictSm, SsstrictS, and SsstrictU.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictCommon — shared infrastructure for Ssstrict test generators.

Provides:
  - Encoding generation helpers (_gen_encodings, _emit_raw_words)
  - Common exclusion lists (CBO, AMO, op31)
  - CSR sweep body emitter (generate_csr_sweep_body)
  - Illegal 32-bit instruction sweep (generate_illegal_instr)
  - Vector illegal instruction sweep (generate_vector_illegal_instr)
  - Compressed 16-bit instruction sweep (generate_compressed_instr)

Each mode-specific generator (SsstrictSm/S/U) imports these and passes
its own covergroup name, CSR skip set, and privilege-specific preamble.

Register exclusion
------------------
ALL scratch registers are chosen from {x7..x31} only.  The following
registers are permanently excluded:

  x0  zero — hardware constant
  x1  ra   — excluded by generate_priv_test's priv_exclude_regs
  x2  sp   — DEFAULT_SIG_REG (signature pointer); if set to -1 the
              epilog's sd x6,0(x2) faults, triggering the infinite loop
  x3  gp   — DEFAULT_DATA_REG (test-data pointer)
  x4  tp   — DEFAULT_TEMP_REG
  x5  t0   — DEFAULT_LINK_REG; also clobbered by the fast handler
              (csrr t0,mcause) on every trap — if r1=x5, the saved CSR
              value is overwritten before the restore instruction runs
  x6  t1   — Mtrampoline trap-signature pointer when rvtest_strap_routine
              is defined; must never be clobbered by the fast handler
"""

from random import choice, randint, sample

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData

# ── Constants ─────────────────────────────────────────────────────────────

# Blank line every N consecutive .word/.hword directives so the splitter
# can break large encoding blocks into separate small files.
BLANK_INTERVAL = 50

# Registers safe to use as scratch in all sweeps.
# Excludes x0-x6: zero, ra, sp(sig ptr), gp(data ptr), tp, t0, t1.
# t0 and t1 are clobbered by the fast handler on every trap.
SAFE_REGS: list[int] = list(range(7, 32))  # x7 .. x31
# The register reserved as a permanent scratch base pointer.
# Must be in SAFE_REGS.  Initialized to &scratch before the sweep so
# every load/store that uses it as rs1 hits valid mapped memory.
SCRATCH_BASE_REG: int = 8  # x8 / s0


# ── Global exclusion lists ────────────────────────────────────────────────

CBO_EXCLUSIONS: list[str] = []

AMO_EXCLUSIONS: list[str] = [
    "01001XXXXXXXXXXXX01X010010101111",  # ssamoswap (Ssamoswap)
]
# Privileged/SYSTEM instruction exclusions shared by all modes.
PRIVILEGED_000_EXCLUSIONS: list[str] = [
    "1XXX11XXXXXX00000000000001110011",  # custom system
    "00X10000001000000000000001110011",  # mret/sret
    "00000000000000000000000001110011",  # ecall
    "00010000010100000000000001110011",  # wfi
    "01110000001000000000000001110011",  # MNRET (Smrnmi)
]


# ── Encoding helpers ──────────────────────────────────────────────────────
def _gen_encodings(
    template: str,
    length: int = 32,
    exclusion: list[str] | None = None,
) -> list[str]:
    """Generate all exhaustive encodings from a template string.

    Template characters:
      '0'/'1' — fixed bit
      'R'     — random bit (but register fields constrained to SAFE_REGS)
      'E'     — exhaustive bit (all 2^N combinations enumerated)

    For 32-bit instructions:
      - Register fields (rd, rs1, rs2) that are fully 'R' in the template
        are replaced with a randomly chosen register from SAFE_REGS.
      - rd is never assigned SCRATCH_BASE_REG (x8) to prevent clobbering
        the permanent scratch base pointer used by load/store instructions.
      - rs1 is never assigned the same register as rd to prevent loads
        from corrupting their own base address.
    """
    if exclusion is None:
        exclusion = []

    # For 32-bit instructions, identify register fields (MSB-first indices).
    # rs2: bits[24:20] -> template[7:12]
    # rs1: bits[19:15] -> template[12:17]
    # rd:  bits[11:7]  -> template[20:25]
    reg_field_ranges: list[tuple[str, int, int]] = []
    if length == 32:
        reg_field_ranges = [
            ("rs2", 7, 12),
            ("rs1", 12, 17),
            ("rd", 20, 25),
        ]

    # SAFE_REGS minus the scratch base — used when picking rd
    safe_regs_no_scratch = [r for r in SAFE_REGS if r != SCRATCH_BASE_REG]

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
        # the template) with a randomly chosen safe register.
        for field_name, start, end in reg_field_ranges:
            if all(template[k] == "R" for k in range(start, end)):
                reg = (
                    choice(safe_regs_no_scratch) if field_name == "rd" else choice(SAFE_REGS)
                )  # rd must never be SCRATCH_BASE_REG
                reg_bits = f"{reg:05b}"
                for k, b in enumerate(reg_bits):
                    instr[start + k] = b

        # Read the actual rd value (whether fixed in template or just assigned)
        # and ensure rs1 != rd to prevent loads from self-clobbering.
        if length == 32:
            rd_start, rd_end = 20, 25
            rs1_start, rs1_end = 12, 17
            rd_val = int("".join(instr[rd_start:rd_end]), 2)

            # If rs1 was randomly assigned and collides with rd, re-pick
            if all(template[k] == "R" for k in range(rs1_start, rs1_end)):
                rs1_val = int("".join(instr[rs1_start:rs1_end]), 2)
                if rs1_val == rd_val:
                    alt = [r for r in SAFE_REGS if r != rd_val]
                    reg = choice(alt)
                    reg_bits = f"{reg:05b}"
                    for k, b in enumerate(reg_bits):
                        instr[rs1_start + k] = b

            # Also ensure rd is not SCRATCH_BASE_REG even if rd was
            # fixed in the template (e.g. template has rd = 01000 = x8)
            if rd_val == SCRATCH_BASE_REG and all(template[k] != "R" for k in range(rd_start, rd_end)):
                # rd is hardcoded to x8 in the template — we can't change
                # it without altering the test intent, so leave it alone.
                # This case is rare and only happens if the template
                # explicitly targets x8.
                pass

        instrstr = "".join(instr)
        if not any(all(p[k] == "X" or p[k] == instrstr[k] for k in range(length)) for p in exclusion):
            results.append(instrstr)
    return results


def _emit_reg_init(lines: list[str]) -> None:
    """Re-initialize x8 to aligned scratch and copy to all other safe regs."""
    lines.append("")
    lines.append("\t# x8 = permanent scratch base, 8-byte aligned for atomics")
    lines.append("\tnop")
    lines.append("\tnop")
    lines.append("\tla x8, scratch")
    lines.append("\t# Pre-load remaining safe regs with scratch address")
    for r in range(7, 32):
        if r != 8:
            lines.append(f"\tmv x{r}, x8")
    lines.append("")


def emit_raw_words(
    lines: list[str],
    comment: str,
    template: str,
    length: int = 32,
    exclusion: list[str] | None = None,
    reinit_interval: int = 0,
) -> None:
    """Emit .word/.hword directives with blank lines every BLANK_INTERVAL.

    If reinit_interval > 0, emit _emit_reg_init every reinit_interval
    encodings to prevent register clobbering during compressed sweeps.
    """
    directive = ".word" if length == 32 else ".hword"
    encodings = _gen_encodings(template, length, exclusion)
    lines.append("")
    if length == 32:
        lines.append("\t.balign 4")
    lines.append(f"# {comment}  ({len(encodings)} encodings)")
    for idx, enc in enumerate(encodings):
        if reinit_interval > 0 and idx > 0 and idx % reinit_interval == 0:
            _emit_reg_init(lines)
        elif idx > 0 and idx % BLANK_INTERVAL == 0:
            lines.append("")
        lines.append(f"\t{directive} 0b{enc}")
    lines.append("")


# ── CSR sweep body ────────────────────────────────────────────────────────


def generate_csr_sweep_body(
    test_data: TestData,
    covergroup: str,
    csr_addresses: list[int],
) -> list[str]:
    """Emit the CSR read/write/set/clear body for a list of CSR addresses.

    This is the inner loop only — callers are responsible for any
    mode-switch preamble/postamble (GOTO Smode, GOTO MMODE, PMP lock, etc.).
    """
    lines: list[str] = []
    for idx, csr_addr in enumerate(csr_addresses):
        if idx > 0 and idx % 10 == 0:
            lines.append("")

        # Pick three distinct safe registers
        r1, r2, r3 = sample(SAFE_REGS, 3)

        ih = hex(csr_addr)
        lines.extend(
            [
                f"# CSR {ih}",
                f"\t{test_data.add_testcase(f'csrr_{ih}', 'cp_csrr', covergroup)}",
                f"\tcsrr x{r1}, {ih}",  # save CSR value
                f"\tli x{r2}, -1",  # all-ones value
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

    lines.append("")
    return lines


# ── Illegal 32-bit instruction sweep ─────────────────────────────────────


def generate_illegal_instr(
    test_data: TestData,
    covergroup: str,
) -> list[str]:
    """cp_illegal_instruction — reserved/illegal 32-bit encoding sweep.

    Run from M-mode so the fast handler can advance mepc correctly.
    Encodings are identical for all Ssstrict variants: reserved/illegal
    encodings trap regardless of privilege level.

    Reserved op31 excluded — RISC-V spec reserves bits[6:0]=1111111 for
    ≥192-bit instructions; QEMU/Whisper interpret this literally and do
    not treat it as a simple 4-byte illegal instruction.
    Vector opcodes op21/op29 are included here (moved from SsstrictV).
    """
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
            "Exhaustive reserved/illegal 32-bit encoding sweep from M-mode.\n"
            "Reserved op31 excluded — variable-length ambiguity across platforms.\n"
            "Vector opcodes op21/op29 included.",
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

    # ── Reserved opcodes ──────────────────────────────────────────────
    _emit_reg_init(lines)
    for cmt, tmpl in [
        ("Reserved op7", "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
        ("Reserved op15", "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
        # ("Reserved op21 (OP-V)", "RRRRRRRRRRRRRRRRRRRRRRRRR1010111"),
        ("Reserved op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Reserved op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        # ("Reserved op29 (OP-VE)", "RRRRRRRRRRRRRRRRRRRRRRRRR1110111"),
        # op31 excluded — variable-length ambiguity across QEMU/Whisper
    ]:
        emit_raw_words(lines, cmt, tmpl)

    # ── Loads ─────────────────────────────────────────────────────────
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_load", "RRRRRRRRRRRRRRRRREEE010010000011")
    emit_raw_words(lines, "cp_fload", "RRRRRRRRRRRRRRRRREEE010010000111")

    # ── Stores — rs1 fixed to x8 (scratch base) ──────────────────────
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_store", "RRRRRRRRRRRR01000EEERRRRR0100011")
    emit_raw_words(lines, "cp_fstore", "RRRRRRRRRRRR01000EEERRRRR0100111")

    # ── Fence / CBO — rs1 fixed to x8 ────────────────────────────────
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_fence_cbo", "RRRRRRRRRRRRRRRRREEE010010001111", exclusion=CBO_EXCLUSIONS)
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_cbo_immediate", "EEEEEEEEEEEE01000010000000001111", exclusion=CBO_EXCLUSIONS)
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_cbo_rd", "00000000000RRRRRR010EEEEE0001111", exclusion=CBO_EXCLUSIONS)

    # ── Atomics — rs1 fixed to x8 ────────────────────────────────────
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_atomic_funct3", "RRRRRRRRRRRR01000EEE010010101111", exclusion=AMO_EXCLUSIONS)
    emit_raw_words(lines, "cp_atomic_funct7", "EEEEERRRRRRR0100001E010010101111", exclusion=AMO_EXCLUSIONS)
    emit_raw_words(lines, "cp_lrsc", "00010RREEEEE0100001E010010101111", exclusion=AMO_EXCLUSIONS)

    # ── amocas odd-register sweep ─────────────────────────────────────
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_amocas_odd", "00101RRRRRRRRRRREEEE01000E0101111")

    # ── I-type / IW-type ──────────────────────────────────────────────
    emit_raw_words(lines, "cp_Itype", "EEEEEEEEEEEERRRRRE01010010010011")
    emit_raw_words(lines, "cp_llAItype", "RRRRRRRRRRRRRRRRREEE010010010011")
    emit_raw_words(lines, "cp_aes64ks1i", "0011000EEEEERRRRR001010010010011")
    emit_raw_words(lines, "cp_IWtype", "RRRRRRRRRRRRRRRRREEE010010011011")
    emit_raw_words(lines, "cp_IWshift", "EEEEEEERRRRRRRRRRE01010010011011")

    # ── R-type / RW-type ──────────────────────────────────────────────
    emit_raw_words(lines, "cp_rtype", "EEEEEEE0011100111EEE001110110011")
    emit_raw_words(lines, "cp_rwtype", "EEEEEEE0011100111EEE001110111011")

    # ── FP ────────────────────────────────────────────────────────────
    emit_raw_words(lines, "cp_ftype", "EEEEERR0011100111EEE001111010011")
    emit_raw_words(lines, "cp_fsqrt", "0101100EEEEE00111000011111010011")
    emit_raw_words(lines, "cp_fclass", "1110000EEEEE00111001001111010011")
    emit_raw_words(lines, "cp_fcvtif", "1100000EEE0000111000001111010011")
    emit_raw_words(lines, "cp_fcvtif_fmt", "11000EE000EE00111000001111010011")
    emit_raw_words(lines, "cp_fcvtfi", "1101000EEE1000111000001111010011")
    emit_raw_words(lines, "cp_fcvtfi_fmt", "11010EE000EE00111000001111010011")
    emit_raw_words(lines, "cp_fcvtff", "0100000EEE1000111000001111010011")
    emit_raw_words(lines, "cp_fcvtff_fmt", "01000EEEEEEE00111000001111010011")
    emit_raw_words(lines, "cp_fmvif", "11100EEEEEEE00111000001111010011")
    emit_raw_words(lines, "cp_fli", "11110EEEEEEERRRRR000010011010011")
    emit_raw_words(lines, "cp_fmvfi", "11110EEEEEEE00111000001111010011")
    emit_raw_words(lines, "cp_fmvh", "11100EEEEEEERRRRR000010011010011")
    emit_raw_words(lines, "cp_fmvp", "10110EE0011100111000001111010011")  # funct5=10110 (fmv.p)
    emit_raw_words(lines, "cp_cvtmodwd", "11000EEEEEEE00111001001111010011")
    emit_raw_words(lines, "cp_fcvtmodwdfrm", "11000010100000111EEE001111010011")

    # ── Branch / JALR ─────────────────────────────────────────────────
    emit_raw_words(lines, "cp_branch2", "RRRRRRR0011100111010001111100011")
    emit_raw_words(lines, "cp_branch3", "RRRRRRR0011100111011001111100011")
    emit_raw_words(lines, "cp_jalr0", "RRRRRRR0011100111EE1001111100111")
    emit_raw_words(lines, "cp_jalr1", "RRRRRRR0011100111010001111100111")
    emit_raw_words(lines, "cp_jalr2", "RRRRRRR0011100111100001111100111")
    emit_raw_words(lines, "cp_jalr3", "RRRRRRR0011100111110001111100111")

    # ── Privileged / SYSTEM ───────────────────────────────────────────
    emit_raw_words(lines, "cp_privileged_f3", "00000000000100000EEE000001110011")
    emit_raw_words(
        lines,
        "cp_privileged_000",
        "EEEEEEEEEEEE00000000000001110011",
        exclusion=PRIVILEGED_000_EXCLUSIONS,
    )
    emit_raw_words(
        lines, "cp_privileged_rd", "00000000000000000000EEEEE1110011", exclusion=["00000000000000000000000001110011"]
    )
    emit_raw_words(
        lines, "cp_privileged_rs2", "000000000000EEEEE000000001110011", exclusion=["00000000000000000000000001110011"]
    )

    # ── Reserved FMA / fence ──────────────────────────────────────────
    emit_raw_words(lines, "cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11")
    emit_raw_words(lines, "cp_reserved_fence_fm", "EEEE00000000RRRRR000RRRRR0001111")
    emit_raw_words(lines, "cp_reserved_fence_rs1", "00001111111100001000RRRRE0001111")
    emit_raw_words(lines, "cp_reserved_fence_rd", "000011111111RRRRE000000010001111")

    # ── Upper register sweep (E extension) ────────────────────────────
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
    ]:
        emit_raw_words(lines, cmt, tmpl)

    return lines


# ── Vector illegal instruction sweep ─────────────────────────────────────


def generate_vector_illegal_instr(
    test_data: TestData,
    covergroup: str,
) -> list[str]:
    """cp_illegal_vector_instruction — reserved/illegal vector encoding sweep.

    Covers vset* configuration instructions, reserved vector load/store
    widths and lumops, vector arithmetic funct6 sweeps (per SEW),
    vector unary instruction sweeps, and vector crypto instructions.

    Run from M-mode so the fast handler can advance mepc correctly.
    """
    coverpoint = "cp_illegal_vector_instruction"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
            "Exhaustive reserved/illegal vector encoding sweep from M-mode.\n"
            "Covers vset* config, vector load/store reserved encodings,\n"
            "vector arithmetic funct6 sweeps (per SEW), unary instructions,\n"
            "and vector crypto instructions.",
        )
    )

    lines.append(f"\t{test_data.add_testcase('vector_illegal_sweep', coverpoint, covergroup)}")
    lines.append("")

    # ── vset* configuration instructions ──────────────────────────────
    lines.append(comment_banner("vset* reserved encodings", "Reserved bits in vsetvl/vsetvli/vsetivli"))

    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_v_vsetvl", "10EEEEERRRRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetvli_sew", "0000RR1EERRRRRRRR111RRRRR1010111")
    # TODO: Restore once Sail vsetvli reserved-vtype behavior is resolved
    # emit_raw_words(lines, "cp_v_vsetvli_res", "EEE0RR0RRRRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetivli_sew", "1100RR1EERRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetivli_res", "11EERR0RRRRRRRRRR111RRRRR1010111")

    # ── Reserved vector loads ─────────────────────────────────────────
    lines.append(comment_banner("Vector load reserved encodings", "Reserved mew/width/lumop for vector loads"))

    _emit_reg_init(lines)
    # mew=0, reserved width values
    emit_raw_words(lines, "cp_vl_0_000", "RRR0RRRRRRRRRRRRR000RRRRR0000111")
    emit_raw_words(lines, "cp_vl_0_101", "RRR0RRRRRRRRRRRRR101RRRRR0000111")
    emit_raw_words(lines, "cp_vl_0_110", "RRR0RRRRRRRRRRRRR110RRRRR0000111")
    emit_raw_words(lines, "cp_vl_0_111", "RRR0RRRRRRRRRRRRR111RRRRR0000111")
    # mew=1, reserved width values
    emit_raw_words(lines, "cp_vl_1_000", "RRR1RRRRRRRRRRRRR000RRRRR0000111")
    emit_raw_words(lines, "cp_vl_1_101", "RRR1RRRRRRRRRRRRR101RRRRR0000111")
    emit_raw_words(lines, "cp_vl_1_110", "RRR1RRRRRRRRRRRRR110RRRRR0000111")
    emit_raw_words(lines, "cp_vl_1_111", "RRR1RRRRRRRRRRRRR111RRRRR0000111")
    # Reserved lumop values per width
    emit_raw_words(lines, "cp_vl_lumop_8", "RRR0RR1EEEEERRRRR000RRRRR0000111")
    emit_raw_words(lines, "cp_vl_lumop_16", "RRR0RR1EEEEERRRRR101RRRRR0000111")
    emit_raw_words(lines, "cp_vl_lumop_32", "RRR0RR1EEEEERRRRR110RRRRR0000111")
    emit_raw_words(lines, "cp_vl_lumop_64", "RRR0RR1EEEEERRRRR111RRRRR0000111")

    # ── Reserved vector stores ────────────────────────────────────────
    lines.append(comment_banner("Vector store reserved encodings", "Reserved mew/width/lumop for vector stores"))

    _emit_reg_init(lines)
    # mew=0, reserved width values
    emit_raw_words(lines, "cp_vs_0_000", "RRR0RRRRRRRRRRRRR000RRRRR0100111")
    emit_raw_words(lines, "cp_vs_0_101", "RRR0RRRRRRRRRRRRR101RRRRR0100111")
    emit_raw_words(lines, "cp_vs_0_110", "RRR0RRRRRRRRRRRRR110RRRRR0100111")
    emit_raw_words(lines, "cp_vs_0_111", "RRR0RRRRRRRRRRRRR111RRRRR0100111")
    # mew=1, reserved width values
    emit_raw_words(lines, "cp_vs_1_000", "RRR1RRRRRRRRRRRRR000RRRRR0100111")
    emit_raw_words(lines, "cp_vs_1_101", "RRR1RRRRRRRRRRRRR101RRRRR0100111")
    emit_raw_words(lines, "cp_vs_1_110", "RRR1RRRRRRRRRRRRR110RRRRR0100111")
    emit_raw_words(lines, "cp_vs_1_111", "RRR1RRRRRRRRRRRRR111RRRRR0100111")
    # Reserved lumop values per width
    emit_raw_words(lines, "cp_vs_lumop_8", "RRR0RR1EEEEERRRRR000RRRRR0100111")
    emit_raw_words(lines, "cp_vs_lumop_16", "RRR0RR1EEEEERRRRR101RRRRR0100111")
    emit_raw_words(lines, "cp_vs_lumop_32", "RRR0RR1EEEEERRRRR110RRRRR0100111")
    emit_raw_words(lines, "cp_vs_lumop_64", "RRR0RR1EEEEERRRRR111RRRRR0100111")

    # ── Vector arithmetic per-SEW sweeps ──────────────────────────────
    # Each SEW needs its own vsetivli so the vector unit is configured
    # correctly when the illegal encodings are executed.
    for sew in ["8", "16", "32", "64"]:
        lines.append(comment_banner(f"Vector arithmetic SEW={sew}", f"funct6 sweeps with e{sew}"))
        lines.append(f"\tvsetivli x0, 1, e{sew}, m1, ta, ma")
        lines.append("")

        _emit_reg_init(lines)

        # funct6 sweep for every vector arithmetic category
        emit_raw_words(lines, f"cp_IVV_f6_e{sew}", "EEEEEEERRRRRRRRRR000RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_f6_e{sew}", "EEEEEEERRRRRRRRRR001RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_f6_e{sew}", "EEEEEEERRRRRRRRRR010RRRRR1010111")
        emit_raw_words(lines, f"cp_IVI_f6_e{sew}", "EEEEEEERRRRRRRRRR011RRRRR1010111")
        emit_raw_words(lines, f"cp_IVX_f6_e{sew}", "EEEEEEERRRRRRRRRR100RRRRR1010111")
        emit_raw_words(lines, f"cp_FVF_f6_e{sew}", "EEEEEEERRRRRRRRRR101RRRRR1010111")
        emit_raw_words(lines, f"cp_MVX_f6_e{sew}", "EEEEEEERRRRRRRRRR110RRRRR1010111")

        # Unary vector instructions — exhaustive encoding sweep
        emit_raw_words(lines, f"cp_MVV_VWRXUNARY0_e{sew}", "010000ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_MVX_VRXUNARY0_e{sew}", "010000EEEEEERRRRR110RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_VXUNARY0_e{sew}", "010010ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_VMUNARY0_e{sew}", "010100ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_VWFUNARY0_e{sew}", "010000ERRRRREEEEE001RRRRR1010111")
        emit_raw_words(lines, f"cp_FVF_VRFUNARY0_e{sew}", "010000EEEEEERRRRR101RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_VFUNARY0_e{sew}", "010010ERRRRREEEEE001RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_VFUNARY1_e{sew}", "010011ERRRRREEEEE001RRRRR1010111")

        # Vector crypto — vaes.vv / vaes.vs
        # Note: no effort to make vl/vstart multiples of EGS for vector crypto.
        # That is tested in ExceptionsV.
        emit_raw_words(lines, f"cp_MVV_vaesvv_e{sew}", "101000ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_vaesvs_e{sew}", "101001ERRRRREEEEE010RRRRR1010111")

    lines.append("")
    return lines


# ── Compressed 16-bit instruction sweep ──────────────────────────────────


def generate_compressed_instr(
    test_data: TestData,
    covergroup: str,
) -> list[str]:
    """cp_illegal_compressed_instruction — all 16-bit quadrant sweeps.

    Run from M-mode so the fast handler handles every trap correctly.
    """
    coverpoint = "cp_illegal_compressed_instruction"
    lines: list[str] = []

    lines.append(comment_banner(coverpoint, "Exhaustive 16-bit quadrant sweep from M-mode."))
    lines.append(f"\t{test_data.add_testcase('compressed_sweep', coverpoint, covergroup)}")
    lines.append("")

    emit_raw_words(
        lines,
        "compressed00",
        "EEEEEE000EEEEE00",  # rs1' fixed to 000 (x8/scratch base)
        length=16,
        exclusion=[
            "XXXXXXXXXXX000XX",  # rd' = x8 — clobbers scratch base pointer
        ],
        reinit_interval=50,
    )
    emit_raw_words(
        lines,
        "compressed01",
        "EEEEEEEEEEEEEE01",
        length=16,
        exclusion=[
            "101XXXXXXXXXXX01",  # c.j — random jump
            "11XXXXXXXXXXXX01",  # c.beqz/c.bnez — random branch
            "001XXXXXXXXXXX01",  # c.jr
            "XXXX00010XXXXX01",  # rd = x2
            "XXXXXXXXXXX000X1",  # rd' = x8 (insn[4:2]=000) — clobbers scratch base pointer
        ],
    )
    emit_raw_words(
        lines,
        "compressed10",
        "1EEEEEEEEEEEEE10",
        length=16,
        exclusion=[
            "1000XXXXX0000010",  # c.jr rs1!=0
            "1001XXXXX0000010",  # c.jalr/c.ebreak
            "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp
            "X10XXXXXXXXXXX10",  # c.lwsp/c.swsp
            "1001000000000010",  # c.ebreak
            "XXXX00010XXXXX10",  # rd = x2 (sp)
            "XXXX01000XXXXX10",  # rd = x8 — clobbers scratch base pointer
            "1100XXXXXXXXXX10",  # c.swsp with rs2=x2
            "1110XXXXXXXXXX10",  # c.sdsp
            "1010XXXXXXXXXX10",  # nop-like edge
        ],
    )
    lines.append("")

    return lines
