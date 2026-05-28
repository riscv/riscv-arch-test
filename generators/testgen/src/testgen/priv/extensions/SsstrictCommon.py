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
  - CSR sweep body emitter (generate_csr_sweep_body)
  - Illegal 32-bit instruction sweep (generate_illegal_instr)
  - Vector illegal instruction sweep (generate_vector_illegal_instr)
  - Compressed 16-bit instruction sweep (generate_compressed_instr)

Each mode-specific generator (SsstrictSm/S/U) imports these and passes
its own covergroup name, CSR skip set, and privilege-specific preamble.

Register exclusion
------------------
ALL working registers (register operands in generated encodings) are chosen
from {x7..x31} only.  The following
registers are permanently excluded:

  x0  zero — hardware constant
  x1  ra   — excluded by generate_priv_test's priv_exclude_regs
  x2  sp   — DEFAULT_SIG_REG (signature pointer); NEVER used as rd
              if set to -1 the epilog's sd x6,0(x2) faults, triggering the
              infinite loop; additionally, x2 must never be clobbered as a
              destination register in any encoding to protect the signature area
  x3  gp   — DEFAULT_DATA_REG (test-data pointer)
  x4  tp   — DEFAULT_TEMP_REG
  x5  t0   — DEFAULT_LINK_REG; also clobbered by the fast handler
              (csrr t0,mcause) on every trap — if r1=x5, the saved CSR
              value is overwritten before the restore instruction runs
  x6  t1   — Mtrampoline trap-signature pointer when rvtest_strap_routine
              is defined; must never be clobbered by the fast handler

Register initialization strategy
---------------------------------
_emit_reg_init() pre-loads ALL safe registers (x7-x31) with the address
of the scratch region before each encoding block.  This means:
  - Whichever safe register _gen_encodings picks for rs1 in a load/store,
    it already points to scratch — no need to hardcode rs1 in templates.
  - Load/store offsets are zeroed so accesses land exactly at scratch,
    not at some random offset that could be outside the mapped region.
  - rd is never assigned x8 (SCRATCH_BASE_REG) to prevent clobbering the
    scratch pointer, which would cascade to subsequent instructions.
  - rs1 != rd is enforced for loads to prevent self-clobbering.
  - All register fields are fully randomized for maximum test robustness.
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

AMO_EXCLUSIONS: list[str] = [
    "01001XXXXXXXXXXXXXXXXXXXX0101111",  # ssamoswap (Ssamoswap)
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

    # SAFE_REGS minus scratch base (x8) and signature pointer (x2)
    # x2 is the signature pointer and must never be clobbered as rd
    safe_regs_no_scratch = [r for r in SAFE_REGS if r not in (SCRATCH_BASE_REG, 2)]

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
    """Re-initialize x8 to aligned scratch and copy to all other safe regs.

    Every safe register (x7-x31) is loaded with the scratch address so
    that whichever register _gen_encodings picks for rs1 in a load/store,
    it already points to valid mapped memory.
    """
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


def _emit_vector_init(lines: list[str]) -> None:
    """Re-initialize GPRs and enable vector extension state (mstatus.VS)."""
    _emit_reg_init(lines)
    lines.append("\t# Enable vector extension: mstatus.VS = 11 (Initial/Dirty)")
    lines.append("\tli t2, 0x00000600  # VS field bitmask [14:13]")
    lines.append("\tcsrs mstatus, t2")
    lines.append("\t# Set vl=0 so valid vector loads/stores are no-ops")
    lines.append("\tvsetivli x0, 0, e8, m1, ta, ma")
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

    All register fields (rs1, rs2, rd) are fully randomized from SAFE_REGS.
    _emit_reg_init() pre-loads every safe register with the scratch address,
    so whichever register is picked as rs1 for loads/stores, it already
    points to valid mapped memory.  rd is constrained to never be x8
    (SCRATCH_BASE_REG) to keep the scratch pointer intact.

    Load/store offsets are zeroed so accesses land exactly at scratch,
    avoiding writes to random addresses outside the scratch region.
    """
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
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
    # All fields fully random (constrained to SAFE_REGS by _gen_encodings)
    _emit_reg_init(lines)
    for cmt, tmpl in [
        ("Reserved op7", "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
        ("Reserved op15", "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
        ("Reserved op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Reserved op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        ("Reserved op31", "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
    ]:
        emit_raw_words(lines, cmt, tmpl)

    # ── Loads — rs1=x8 (scratch), rd=x12-x15 (randomized), offset=0 ──
    # I-type: imm[11:0]=0 | rs1=01000 | funct3=EEE | rd=011RR | opcode
    # rs1 fixed to x8 (scratch base), rd sweeps x12-x15 via RR bits,
    # offset zeroed so load accesses exactly scratch.
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_load", "00000000000001000EEE011RR0000011")
    emit_raw_words(lines, "cp_fload", "00000000000001000EEE011RR0000111")

    # ── Stores — rs1=x8 (scratch), rs2=RRRRR (randomized), offset=0 ──
    # S-type: imm[11:5]=0 | rs2=RRRRR | rs1=01000 | funct3=EEE | imm[4:0]=0 | opcode
    # rs1 fixed to x8, offset zeroed, rs2 value irrelevant for trap testing.
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_store", "0000000RRRRR01000EEE000000100011")
    emit_raw_words(lines, "cp_fstore", "0000000RRRRR01000EEE000000100111")

    # ── Fence / CBO — rs1=x8, rd=00000, offset=0 ──────────────────────
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_fence_cbo", "00000000000001000EEE000000001111")
    # CBO immediate sweep: rs1=x8, rd=00000 (CBO has no rd)
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_cbo_immediate", "EEEEEEEEEEEE01000010000000001111")
    # CBO rd sweep: rs1=x8, rd=EEEEE (swept x0-x31) offset=0
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_cbo_rd", "00000000000001000010EEEEE0001111")

    # ── Atomics — rs1=x8, rd=011RR (x12-x15) ────────────────────────
    # AMO: funct5 | aq | rl | rs2 | rs1=01000 | funct3 | rd=011RR (x12-x15) | opcode
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_atomic_funct3", "RRRRRRRRRRRR01000EEE011RR0101111", exclusion=AMO_EXCLUSIONS)
    emit_raw_words(lines, "cp_atomic_funct7", "EEEEERRRRRRR0100001E011RR0101111", exclusion=AMO_EXCLUSIONS)
    emit_raw_words(lines, "cp_lrsc", "00010RREEEEE0100001E011RR0101111", exclusion=AMO_EXCLUSIONS)

    # ── amocas odd-register sweep — rs1=x8, rs2=RRRRe (even+odd), rd=011RE={x12-x15} ──
    _emit_reg_init(lines)
    emit_raw_words(lines, "cp_amocas_odd", "00101RRRRRRE01000EEE011RE0101111")

    # ── I-type / IW-type — all registers randomized ───────────────────
    emit_raw_words(lines, "cp_Itype", "EEEEEEEEEEEERRRRRE01RRRRR0010011")
    emit_raw_words(lines, "cp_llAItype", "RRRRRRRRRRRRRRRRREEERRRRR0010011")
    emit_raw_words(lines, "cp_aes64ks1i", "0011000EEEEERRRRR001RRRRR0010011")
    emit_raw_words(lines, "cp_IWtype", "RRRRRRRRRRRRRRRRREEERRRRR0011011")
    emit_raw_words(lines, "cp_IWshift", "EEEEEEERRRRRRRRRRE01RRRRR0011011")

    # ── R-type / RW-type — all registers randomized ───────────────────
    emit_raw_words(lines, "cp_rtype", "EEEEEEERRRRRRRRRREEERRRRR0110011")
    emit_raw_words(lines, "cp_rwtype", "EEEEEEERRRRRRRRRREEERRRRR0111011")

    # ── FP — all registers randomized ─────────────────────────────────
    emit_raw_words(lines, "cp_ftype", "EEEEERRRRRRRRRRRREEERRRRR1010011")
    emit_raw_words(lines, "cp_fsqrt", "0101100EEEEERRRRRRRRRRRRR1010011")
    emit_raw_words(lines, "cp_fclass", "1110000EEEEERRRRR001RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtif", "1100000EEE00RRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtif_fmt", "11000EE000EERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtfi", "1101000EEER00RRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtfi_fmt", "11010EE000EERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtff", "0100000EEER00RRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtff_fmt", "01000EEEEEEERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fmvif", "11100EEEEEEERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fli", "11110EEEEEEERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fmvfi", "11110EEEEEEERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fmvh", "11100EEEEEEERRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_fmvp", "10110EERRRRRRRRRR000RRRRR1010011")
    emit_raw_words(lines, "cp_cvtmodwd", "11000EEEEEEERRRRR001RRRRR1010011")
    emit_raw_words(lines, "cp_fcvtmodwdfrm", "110000101000RRRRREEERRRRR1010011")

    # ── Branch / JALR — all registers randomized ──────────────────────
    emit_raw_words(lines, "cp_branch2", "RRRRRRRRRRRRRRRRR010RRRRR1100011")  # branches have no rd
    emit_raw_words(lines, "cp_branch3", "RRRRRRRRRRRRRRRRR011RRRRR1100011")  # branches have no rd
    emit_raw_words(lines, "cp_jalr0", "RRRRRRRRRRRRRRRRREE1RRRRR1100111")
    emit_raw_words(lines, "cp_jalr1", "RRRRRRRRRRRRRRRRR010RRRRR1100111")
    emit_raw_words(lines, "cp_jalr2", "RRRRRRRRRRRRRRRRR100RRRRR1100111")
    emit_raw_words(lines, "cp_jalr3", "RRRRRRRRRRRRRRRRR110RRRRR1100111")

    # ── Privileged / SYSTEM ───────────────────────────────────────────
    emit_raw_words(lines, "cp_privileged_f3", "00000000000100000EEE000001110011")
    emit_raw_words(
        lines,
        "cp_privileged_000",
        "EEEEEEEEEEEE00000000000001110011",
        exclusion=PRIVILEGED_000_EXCLUSIONS,
    )
    emit_raw_words(
        lines,
        "cp_privileged_rd",
        "00000000000000000000EEEEE1110011",
        exclusion=[
            "00000000000000000000000001110011",  # exclude ecall
            "XXXXXXXXXXXXXXXXXXXX00010XXXXXXX",  # exclude rd=x2 (sp)
            "XXXXXXXXXXXXXXXXXXXX01000XXXXXXX",  # exclude rd=x8 (scratch base)
        ],
    )
    emit_raw_words(
        lines,
        "cp_privileged_rs2",
        "000000000000EEEEE000000001110011",
        exclusion=["00000000000000000000000001110011"],
    )

    # ── Reserved FMA / fence ──────────────────────────────────────────
    emit_raw_words(lines, "cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11")
    emit_raw_words(lines, "cp_reserved_fence_fm", "EEEE00000000RRRRR000RRRRR0001111")
    emit_raw_words(
        lines,
        "cp_reserved_fence_rs1",
        "00001111111100001000RRRRE0001111",
        exclusion=[
            "XXXXXXXXXXXXXXXXXXXX00010XXXXXXX",  # exclude rd=x2 (sp)
            "XXXXXXXXXXXXXXXXXXXX01000XXXXXXX",  # exclude rd=x8 (scratch base)
        ],
    )
    emit_raw_words(lines, "cp_reserved_fence_rd", "000011111111RRRRE000000010001111")

    # ── Upper register sweep (E extension) ────────────────────────────
    lines.append(comment_banner("cp_upperreg", "x16-x31 — trap when E extension active"))
    for cmt, tmpl in [
        ("cp_upperreg_rs1_add", "0000000000011EEEE000000010110011"),
        ("cp_upperreg_rs2_add", "00000001EEEE00001000011100110011"),
        ("cp_upperreg_rd_add", "000000000001000010001EEEE0110011"),
        ("cp_upperreg_rs1_mul", "0000001000011EEEE000000010110011"),
        ("cp_upperreg_rs2_mul", "00000011EEEE00001000011100110011"),
        ("cp_upperreg_rd_mul", "000000100001000010001EEEE0110011"),
        ("cp_upperreg_rs1_fadd-s", "0000000000011EEEE000000011010011"),
        ("cp_upperreg_rs2_fadd-s", "00000001EEEE00001000011101010011"),
        ("cp_upperreg_rd_fadd-s", "000000000001000010001EEEE1010011"),
        ("cp_upperreg_imm_rs1_addi0", "0000000000001EEEE000011100010011"),
        ("cp_upperreg_imm_rs1_addi1", "1111111111111EEEE000011100010011"),
        ("cp_upperreg_imm_rd_addi0", "000000000000000010001EEEE0010011"),
        ("cp_upperreg_imm_rd_addi1", "111111111111000010001EEEE0010011"),
        ("cp_upperreg_fmv_x_w_rs1", "1110000000001EEEE000000011010011"),
        ("cp_upperreg_fmv_x_w_rd", "111000000000000010001EEEE1010011"),
        ("cp_upperreg_fmv_w_x_rs1", "1111000000001EEEE000011101010011"),
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

    All register fields randomized; _emit_reg_init pre-loads scratch.
    Vector load/store rs1 randomized (all safe regs hold scratch address).
    """
    coverpoint = "cp_illegal_vector_instruction"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
            "Exhaustive reserved/illegal vector encoding sweep from M-mode.\n"
            "All register fields randomized; _emit_reg_init pre-loads scratch.",
        )
    )

    lines.append(f"\t{test_data.add_testcase('vector_illegal_sweep', coverpoint, covergroup)}")
    lines.append("")

    # ── vset* configuration instructions ──────────────────────────────
    lines.append(comment_banner("vset* reserved encodings", "Reserved bits in vsetvl/vsetvli/vsetivli"))

    _emit_vector_init(lines)
    emit_raw_words(lines, "cp_v_vsetvl", "10EEEEERRRRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetvli_sew", "0000RR1EERRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetvli_res", "EEE0RR0RRRRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetivli_sew", "1100RR1EERRRRRRRR111RRRRR1010111")
    emit_raw_words(lines, "cp_v_vsetivli_res", "11EERR0RRRRRRRRRR111RRRRR1010111")

    # ── Reserved vector loads ─────────────────────────────────────────
    # rs1 randomized — all safe regs pre-loaded with scratch address.
    # For lumop templates, mop fixed to 00 (unit-stride) so the lumop
    # E bits are interpreted as lumop, not as a stride register.
    lines.append(comment_banner("Vector load reserved encodings", "Reserved mew/width/lumop for vector loads"))

    _emit_vector_init(lines)
    # mew=0, reserved width values — rs1=x8, vd=011RR
    emit_raw_words(lines, "cp_vl_0_000", "RRR0RRRRRRRR01000000011RR0000111")
    emit_raw_words(lines, "cp_vl_0_101", "RRR0RRRRRRRR01000101011RR0000111")
    emit_raw_words(lines, "cp_vl_0_110", "RRR0RRRRRRRR01000110011RR0000111")
    emit_raw_words(lines, "cp_vl_0_111", "RRR0RRRRRRRR01000111011RR0000111")
    # mew=1, reserved width values — rs1=x8, vd=011RR
    emit_raw_words(lines, "cp_vl_1_000", "RRR1RRRRRRRR01000000011RR0000111")
    emit_raw_words(lines, "cp_vl_1_101", "RRR1RRRRRRRR01000101011RR0000111")
    emit_raw_words(lines, "cp_vl_1_110", "RRR1RRRRRRRR01000110011RR0000111")
    emit_raw_words(lines, "cp_vl_1_111", "RRR1RRRRRRRR01000111011RR0000111")
    # lumop sweep — mop=00, vm=1, rs1=x8, vd=011RR
    emit_raw_words(lines, "cp_vl_lumop_8", "RRR0001EEEEE01000000011RR0000111")
    emit_raw_words(lines, "cp_vl_lumop_16", "RRR0001EEEEE01000101011RR0000111")
    emit_raw_words(lines, "cp_vl_lumop_32", "RRR0001EEEEE01000110011RR0000111")
    emit_raw_words(lines, "cp_vl_lumop_64", "RRR0001EEEEE01000111011RR0000111")

    # ── Reserved vector stores ────────────────────────────────────────
    lines.append(comment_banner("Vector store reserved encodings", "Reserved mew/width/lumop for vector stores"))

    _emit_vector_init(lines)
    # mew=0, reserved width values — rs1=x8, vs3=011RR
    emit_raw_words(lines, "cp_vs_0_000", "RRR0RRRRRRRR01000000011RR0100111")
    emit_raw_words(lines, "cp_vs_0_101", "RRR0RRRRRRRR01000101011RR0100111")
    emit_raw_words(lines, "cp_vs_0_110", "RRR0RRRRRRRR01000110011RR0100111")
    emit_raw_words(lines, "cp_vs_0_111", "RRR0RRRRRRRR01000111011RR0100111")
    # mew=1, reserved width values — rs1=x8, vs3=011RR
    emit_raw_words(lines, "cp_vs_1_000", "RRR1RRRRRRRR01000000011RR0100111")
    emit_raw_words(lines, "cp_vs_1_101", "RRR1RRRRRRRR01000101011RR0100111")
    emit_raw_words(lines, "cp_vs_1_110", "RRR1RRRRRRRR01000110011RR0100111")
    emit_raw_words(lines, "cp_vs_1_111", "RRR1RRRRRRRR01000111011RR0100111")
    # sumop sweep — mop=00, vm=1, rs1=x8, vs3=011RR
    emit_raw_words(lines, "cp_vs_lumop_8", "RRR0001EEEEE01000000011RR0100111")
    emit_raw_words(lines, "cp_vs_lumop_16", "RRR0001EEEEE01000101011RR0100111")
    emit_raw_words(lines, "cp_vs_lumop_32", "RRR0001EEEEE01000110011RR0100111")
    emit_raw_words(lines, "cp_vs_lumop_64", "RRR0001EEEEE01000111011RR0100111")

    # ── Vector arithmetic per-SEW sweeps ──────────────────────────────
    for sew in ["8", "16", "32", "64"]:
        lines.append(comment_banner(f"Vector arithmetic SEW={sew}", f"funct6 sweeps with e{sew}"))
        lines.append(f"\tvsetivli x0, 1, e{sew}, m1, ta, ma")
        lines.append("")

        _emit_vector_init(lines)

        emit_raw_words(lines, f"cp_IVV_f6_e{sew}", "EEEEEEERRRRRRRRRR000RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_f6_e{sew}", "EEEEEEERRRRRRRRRR001RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_f6_e{sew}", "EEEEEEERRRRRRRRRR010RRRRR1010111")
        emit_raw_words(lines, f"cp_IVI_f6_e{sew}", "EEEEEEERRRRRRRRRR011RRRRR1010111")
        emit_raw_words(lines, f"cp_IVX_f6_e{sew}", "EEEEEEERRRRRRRRRR100RRRRR1010111")
        emit_raw_words(lines, f"cp_FVF_f6_e{sew}", "EEEEEEERRRRRRRRRR101RRRRR1010111")
        emit_raw_words(lines, f"cp_MVX_f6_e{sew}", "EEEEEEERRRRRRRRRR110RRRRR1010111")

        emit_raw_words(lines, f"cp_MVV_VWRXUNARY0_e{sew}", "010000ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_MVX_VRXUNARY0_e{sew}", "010000EEEEEERRRRR110RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_VXUNARY0_e{sew}", "010010ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_MVV_VMUNARY0_e{sew}", "010100ERRRRREEEEE010RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_VWFUNARY0_e{sew}", "010000ERRRRREEEEE001RRRRR1010111")
        emit_raw_words(lines, f"cp_FVF_VRFUNARY0_e{sew}", "010000EEEEEERRRRR101RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_VFUNARY0_e{sew}", "010010ERRRRREEEEE001RRRRR1010111")
        emit_raw_words(lines, f"cp_FVV_VFUNARY1_e{sew}", "010011ERRRRREEEEE001RRRRR1010111")

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
    All register fields fully swept via E bits for maximum coverage.
    """
    coverpoint = "cp_illegal_compressed_instruction"
    lines: list[str] = []

    lines.append(comment_banner(coverpoint, "Exhaustive 16-bit quadrant sweep from M-mode."))
    lines.append(f"\t{test_data.add_testcase('compressed_sweep', coverpoint, covergroup)}")
    lines.append("")

    # Quadrant 00: covers c.addi4spn, c.lw, c.ld, c.flw, c.fld, c.sw, c.sd, c.fsw, c.fsd
    # All register fields (rd', rs1', rs2') swept exhaustively.
    # CRITICAL: offset bits are zeroed (bits[6:5]=00, bits[4:2]=000) to ensure
    # all load/store offsets are 0, so rs1 points exactly to scratch.
    # _emit_reg_init pre-loads all safe regs (x7-x31) with scratch, so
    # x8-x15 (the rs1' range) all point to valid memory.
    # rd' = x8 excluded to prevent clobbering the scratch pointer.
    # reinit_interval keeps registers fresh as valid loads clobber them.
    emit_raw_words(
        lines,
        "compressed00",
        "EEEEEEEEEEEEEE00",
        length=16,
        exclusion=[
            "XXXXXXXXXXX000XX",  # rd' = x8 — clobbers scratch base pointer
        ],
        reinit_interval=50,
    )

    # Quadrant 01: fully exhaustive
    # reinit_interval keeps registers fresh as valid loads/stores clobber them.
    emit_raw_words(
        lines,
        "compressed01",
        "EEEEEEEEEEEEEE01",
        length=16,
        exclusion=[
            "101XXXXXXXXXXX01",  # c.j — random jump
            "11XXXXXXXXXXXX01",  # c.beqz/c.bnez — random branch
            "001XXXXXXXXXXX01",  # c.jal (RV32) — random jump
            "XXXX00010XXXXX01",  # rd = x2 — clobbers signature pointer
            "XXXXXXXXXXX000X1",  # rd' = x8 — clobbers scratch base pointer
        ],
        reinit_interval=50,
    )

    # Quadrant 10: fully exhaustive except for c.jr/c.jalr/c.ebreak (random jump/trap)
    # reinit_interval keeps registers fresh as valid loads/stores clobber them.
    emit_raw_words(
        lines,
        "compressed10",
        "EEEEEEEEEEEEEE10",
        length=16,
        exclusion=[
            "1000XXXXX0000010",  # c.jr rs1!=0 — random jump
            "1001XXXXX0000010",  # c.jalr/c.ebreak — random jump or debug trap
            "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp — sp-relative, corrupts signature area
            "X10XXXXXXXXXXX10",  # c.lwsp/c.swsp — sp-relative, corrupts signature area
            "1001000000000010",  # c.ebreak — legal, tested elsewhere
            "XXXX00010XXXXX10",  # rd = x2 (sp) — clobbers signature pointer
            "XXXX01000XXXXX10",  # rd = x8 — clobbers scratch base pointer
            "1100XXXXXXXXXX10",  # c.swsp with rs2=x2 — stores sp to random address
            "1110XXXXXXXXXX10",  # c.sdsp/c.fswsp — sp-relative store
            "1010XXXXXXXXXX10",  # nop-like edge — unpredictable on some platforms
        ],
        reinit_interval=50,
    )
    lines.append("")

    return lines
