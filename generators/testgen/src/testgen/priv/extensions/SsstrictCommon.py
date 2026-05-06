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

# ── Global exclusion lists ────────────────────────────────────────────────

# CBO instructions — platform-dependent trap behaviour (access-fault vs
# illegal-instruction vs no-trap depending on Zicbom/Zicboz enablement).
# TODO: Restore these once CI for QEMU + Spike passes and all bugs identified
CBO_EXCLUSIONS: list[str] = [
    "000000000000XXXXX010XXXXX0001111",  # cbo.inval
    "000000000001XXXXX010XXXXX0001111",  # cbo.clean
    "000000000010XXXXX010XXXXX0001111",  # cbo.flush
    "000000000100XXXXX010XXXXX0001111",  # cbo.zero
    "000000000000XXXXX110XXXXX0001111",  # prefetch variants
]

# TODO: Restore these once CI for QEMU + Spike passes and all bugs identified
AMO_EXCLUSIONS: list[str] = [
    "00010XXXXXXXXXXXX01X010010101111",  # lr.w / lr.d
    "00011XXXXXXXXXXXX01X010010101111",  # sc.w / sc.d
    "00001XXXXXXXXXXXX01X010010101111",  # amoswap
    "00000XXXXXXXXXXXX01X010010101111",  # amoadd
    "00100XXXXXXXXXXXX01X010010101111",  # amoxor
    "01100XXXXXXXXXXXX01X010010101111",  # amoand
    "01000XXXXXXXXXXXX01X010010101111",  # amoor
    "10000XXXXXXXXXXXX01X010010101111",  # amomin
    "10100XXXXXXXXXXXX01X010010101111",  # amomax
    "11000XXXXXXXXXXXX01X010010101111",  # amominu
    "11100XXXXXXXXXXXX01X010010101111",  # amomaxu
    "00101XXXXXXXXXXXX01X010010101111",  # amocas (Zacas)
    "01001XXXXXXXXXXXX01X010010101111",  # ssamoswap (Ssamoswap)
]
# Privileged/SYSTEM instruction exclusions shared by all modes.
# TODO: Restore fences + URET once CI for QEMU + Spike passes and all bugs identified
PRIVILEGED_000_EXCLUSIONS: list[str] = [
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
    # "00000000001000000000000001110011",  # URET (deprecated)
]


# ── Encoding helpers ──────────────────────────────────────────────────────


# The register reserved as a permanent scratch base pointer.
# Must be in SAFE_REGS.  Initialized to &scratch before the sweep so
# every load/store that uses it as rs1 hits valid mapped memory.
SCRATCH_BASE_REG: int = 8  # x8 / s0


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


def emit_raw_words(
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
    if length == 32:
        lines.append("\t.balign 4")  # ensure 4-byte alignment for .word blocks
    lines.append(f"# {comment}  ({len(encodings)} encodings)")
    for idx, enc in enumerate(encodings):
        if idx > 0 and idx % BLANK_INTERVAL == 0:
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

    Vector opcodes op21/op29 excluded — covered in SsstrictV.
    Reserved op31 excluded — RISC-V spec reserves bits[6:0]=1111111 for
    ≥192-bit instructions; QEMU/Whisper interpret this literally and do
    not treat it as a simple 4-byte illegal instruction.
    amocas_odd excluded — Zacas extension not in target profile; QEMU
    may not decode these, causing platform-dependent behaviour.
    """
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(
        comment_banner(
            coverpoint,
            "Exhaustive reserved/illegal 32-bit encoding sweep from M-mode.\n"
            "Vector opcodes op21/op29 excluded — covered in SsstrictV.\n"
            "Reserved op31 excluded — variable-length ambiguity across platforms.\n"
            "amocas_odd excluded — Zacas not in target extension set.",
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

    # x8 = permanent scratch base pointer (never used as rd).
    # All other safe regs also point to scratch so any surviving
    # base-address usage hits valid mapped memory.
    lines.append("")
    lines.append("\t# x8 = permanent scratch base (never clobbered as rd)")
    lines.append("\tla x8, scratch")
    lines.append("\t# Pre-load remaining safe regs with scratch address")
    for r in range(7, 32):
        if r != 8:
            lines.append(f"\tmv x{r}, x8")
    # Reserved opcodes (op31 excluded — variable-length ambiguity)
    for cmt, tmpl in [
        ("Reserved op7", "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
        ("Reserved op15", "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
        ("Reserved op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Reserved op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        # TODO: Restore these once CI for QEMU + Spike passes and all bugs identified
        #         # ("Reserved op31", "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
    ]:
        emit_raw_words(lines, cmt, tmpl)

    # Loads — rs1 is random (already constrained to safe regs, rd != rs1 != x8)
    emit_raw_words(lines, "cp_load", "RRRRRRRRRRRRRRRRREEE010010000011")
    emit_raw_words(lines, "cp_fload", "RRRRRRRRRRRRRRRRREEE010010000111")

    # Stores — rs1 fixed to x8 (scratch base)
    emit_raw_words(lines, "cp_store", "RRRRRRRRRRRR01000EEERRRRR0100011")
    emit_raw_words(lines, "cp_fstore", "RRRRRRRRRRRR01000EEERRRRR0100111")

    # Fence / CBO — rs1 fixed to x8
    emit_raw_words(lines, "cp_fence_cbo", "RRRRRRRRRRRRRRRRREEE010010001111", exclusion=CBO_EXCLUSIONS)
    emit_raw_words(lines, "cp_cbo_immediate", "EEEEEEEEEEEE01000010000000001111", exclusion=CBO_EXCLUSIONS)
    emit_raw_words(lines, "cp_cbo_rd", "00000000000RRRRRR010EEEEE0001111", exclusion=CBO_EXCLUSIONS)

    # Atomics — rs1 fixed to x8
    emit_raw_words(lines, "cp_atomic_funct3", "RRRRRRRRRRRR01000EEE010010101111", exclusion=AMO_EXCLUSIONS)
    emit_raw_words(lines, "cp_atomic_funct7", "EEEEERRRRRRR0100001E010010101111", exclusion=AMO_EXCLUSIONS)
    emit_raw_words(lines, "cp_lrsc", "00010RREEEEE0100001E010010101111", exclusion=AMO_EXCLUSIONS)
    # I-type / IW-type
    emit_raw_words(lines, "cp_Itype", "EEEEEEEEEEEERRRRRE01010010010011")
    emit_raw_words(lines, "cp_llAItype", "RRRRRRRRRRRRRRRRREEE010010010011")
    emit_raw_words(lines, "cp_aes64ks1i", "0011000EEEEERRRRR001010010010011")
    emit_raw_words(lines, "cp_IWtype", "RRRRRRRRRRRRRRRRREEE010010011011")
    emit_raw_words(lines, "cp_IWshift", "EEEEEEERRRRRRRRRRE01010010011011")

    # R-type / RW-type
    emit_raw_words(lines, "cp_rtype", "EEEEEEE0011100111EEE001110110011")
    emit_raw_words(lines, "cp_rwtype", "EEEEEEE0011100111EEE001110111011")

    # FP
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
    emit_raw_words(lines, "cp_fmvp", "11100EE0011100111000001111010011")
    emit_raw_words(lines, "cp_cvtmodwd", "11000EEEEEEE00111001001111010011")
    emit_raw_words(lines, "cp_fcvtmodwdfrm", "11000010100000111EEE001111010011")

    # Branch / JALR
    emit_raw_words(lines, "cp_branch2", "RRRRRRR0011100111010001111100011")
    emit_raw_words(lines, "cp_branch3", "RRRRRRR0011100111011001111100011")
    emit_raw_words(lines, "cp_jalr0", "RRRRRRR0011100111EE1001111100111")
    emit_raw_words(lines, "cp_jalr1", "RRRRRRR0011100111010001111100111")
    emit_raw_words(lines, "cp_jalr2", "RRRRRRR0011100111100001111100111")
    emit_raw_words(lines, "cp_jalr3", "RRRRRRR0011100111110001111100111")

    # TODO: Bring back cp_amocas_odd + Add all vector cps
    # Privileged / SYSTEM
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

    # Reserved FMA / fence
    emit_raw_words(lines, "cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11")
    emit_raw_words(lines, "cp_reserved_fence_fm", "EEEE00000000RRRRR000RRRRR0001111")
    emit_raw_words(lines, "cp_reserved_fence_rs1", "00001111111100001000RRRRE0001111")
    emit_raw_words(lines, "cp_reserved_fence_rd", "000011111111RRRRE000000010001111")

    # Upper register sweep (E extension)
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

    # TODO: Restore these, Put scratch in x8, and do load/store from x8
    emit_raw_words(
        lines,
        "compressed00",
        "EEEEEEEEEEEEEE00",
        length=16,
        exclusion=[
            "X01XXXXXXXXXXX00",  # c.fld/c.fsd — bad address
            "X10XXXXXXXXXXX00",  # c.lw/c.sw — bad address
            "10000XXXXXXXXX00",  # c.lbu, c.lh, c.lhu
            "10010XXXXXXXXX00",  # c.sb
            "10011XXXXXXXXX00",  # c.sh
            "XXXX00010XXXXX00",  # rd = x2
            "011XXXXXXXXXXX00",  # c.ld — garbage in regs + random mtval on fault
            "111XXXXXXXXXXX00",  # c.sd — store from uninitialised reg, bad address
        ],
    )
    emit_raw_words(
        lines,
        "compressed01",
        "EEEEEEEEEEEEEE01",
        length=16,
        exclusion=[
            "101XXXXXXXXXXX01",  # c.j — random jump - EXCLUDED
            "11XXXXXXXXXXXX01",  # c.beqz/c.bnez — random branch
            "001XXXXXXXXXXX01",  # c.jr
            # "XXXX00010XXXXX01",  # rd = x2 -  Bug resolved, nor x2 is not getting used as rd
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
            "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp - Interfere with x2 which is pointing to regular signature area
            "X10XXXXXXXXXXX10",  # c.lwsp/c.swsp — Interfere with x2 which is pointing to regular signature area
            "1001000000000010",  # c.ebreak
            # "XXXX00010XXXXX10",  # rd = x2 (sp) - Bug resolved, nor x2 is not getting used as rd
            "1100XXXXXXXXXX10",  # c.swsp with rs2=x2 (corrupts via store of sp) - Interfere with x2 which is pointing to regular signature area
            "1110XXXXXXXXXX10",  # c.lwsp rd=x2 alternate encoding guard - Interfere with x2 which is pointing to regular signature area
            "1010XXXXXXXXXX10",  # zero-length / nop-like edge in quadrant 2 - Will get the exact cause for this one
        ],
    )
    lines.append("")

    return lines
