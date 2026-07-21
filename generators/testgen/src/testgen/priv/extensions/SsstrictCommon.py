##################################
# priv/extensions/SsstrictCommon.py
#
# Shared encoding helpers, illegal-instruction sweep, and compressed-
# instruction sweep used by SsstrictSm, SsstrictS, and SsstrictU.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared infrastructure for the Ssstrict test generators.

A Ssstrict suite checks that reserved/illegal instruction encodings and CSR
accesses trap as expected from a given privilege mode. The mode-specific
generators (SsstrictSm/S/U) each call ``generate_ssstrict_suite`` with a suite
name, privilege mode, and the set of CSR addresses to skip; covergroup names
and per-mode setup are derived from those.

Instruction encodings are expanded from template strings (see ``_gen_encodings``)
and emitted as raw ``.word``/``.hword`` directives. Operand registers come from
the standard integer allocator (``test_data.int_regs``), which has already
reserved the framework's signature/data/temp/link registers, so any register it
hands out is safe to clobber. One register is reserved per template as a scratch
base pointing at mapped memory; load/store/atomic templates use it as rs1 (the
'B' field) so their accesses always land in the scratch region.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from random import randint, seed

from testgen.asm.helpers import comment_banner, reproducible_hash
from testgen.data.registers import IntegerRegisterFile
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# Number of CSR addresses per CSR-sweep chunk. Each CSR contributes 5 testcases
# (read / write-ones / write-zeros / set / clear), so this keeps each chunk well
# under TESTCASES_PER_PRIV_FILE while giving the splitter enough boundaries.
CSRS_PER_CHUNK = 100

# Maximum number of encoding words per chunk. Large templates (e.g. the 14-E-bit
# compressed quadrants = 16384 encodings) are split into several chunks so no
# single block becomes an oversized, unsplittable file. Kept below
# TESTCASES_PER_PRIV_FILE so the splitter can still pack a few chunks per file.
MAX_WORDS_PER_CHUNK = 3000


@dataclass(frozen=True)
class RawSweep:
    comment: str
    template: str
    length: int = 32
    exclusion: tuple[str, ...] = ()


SetupFn = Callable[[list[str], TestData, int], None]


USER_CUSTOM_CSR_RANGES = (range(0x800, 0x900), range(0xCC0, 0xD00))
S_CUSTOM_CSR_RANGES = (range(0x5C0, 0x600), range(0x9C0, 0xA00), range(0xDC0, 0xE00))
H_CUSTOM_CSR_RANGES = (range(0x6C0, 0x700), range(0xAC0, 0xB00), range(0xEC0, 0xF00))
M_CUSTOM_CSR_RANGES = (range(0x7C0, 0x800), range(0xBC0, 0xC00))
M_PRIV_CSR_RANGES = (range(0x300, 0x400), range(0x700, 0x800), range(0xB00, 0xC00), range(0xF00, 0x1000))


def csr_range_set(*ranges: range) -> set[int]:
    return {csr for csr_range in ranges for csr in csr_range}


# ── Global exclusion lists ────────────────────────────────────────────────

# Privileged/SYSTEM instruction exclusions shared by all modes.
PRIVILEGED_000_EXCLUSIONS: tuple[str, ...] = (
    "1XXX11XXXXXX00000000000001110011",  # custom system
    "00X10000001000000000000001110011",  # mret/sret
    "00000000000000000000000001110011",  # ecall
    "00010000010100000000000001110011",  # wfi
    "01110000001000000000000001110011",  # MNRET (Smrnmi)
)


# ── Encoding helpers ──────────────────────────────────────────────────────


def _excluded(encoding: str, patterns: Sequence[str]) -> bool:
    """True if `encoding` matches any pattern, where 'X' in a pattern is a wildcard."""
    return any(all(p in ("X", c) for p, c in zip(pattern, encoding)) for pattern in patterns)


def _gen_encodings(
    int_regs: IntegerRegisterFile,
    scratch_base: int,
    template: str,
    length: int = 32,
    exclusion: Sequence[str] | None = None,
) -> list[str]:
    """Expand a template string into every matching instruction encoding (MSB-first).

    Template characters:
      '0'/'1' — fixed bit
      'R'     — random bit
      'E'     — exhaustive bit (every combination of the E bits is enumerated)
      'B'     — scratch-base field; rs1 of memory templates, set to scratch_base

    Fully-'R' register fields (rs1/rs2/rd of 32-bit templates) are replaced with
    distinct allocator registers, so a load never self-clobbers its base. The
    scratch base is reserved out of the pool, so no field can collide with it.
    Encodings matching any `exclusion` pattern are dropped.
    """
    exclusion = exclusion or ()
    # Fill the rs1 base field, if present, before enumerating (it is constant).
    template = template.replace("BBBBB", f"{scratch_base:05b}")

    # Start indices of the 5-bit register fields (rs2, rs1, rd) that are fully random.
    reg_fields = [(7, 12), (12, 17), (20, 25)] if length == 32 else []
    random_fields = [start for start, end in reg_fields if all(c == "R" for c in template[start:end])]

    ebits = template.count("E")
    results: list[str] = []
    for combo in range(2**ebits):
        ebit = iter(f"{combo:0{ebits}b}")
        instr = [str(randint(0, 1)) if c == "R" else next(ebit) if c == "E" else c for c in template]

        regs = int_regs.get_registers(len(random_fields))
        for start, reg in zip(random_fields, regs):
            instr[start : start + 5] = f"{reg:05b}"
        int_regs.return_registers(regs)

        encoding = "".join(instr)
        if not _excluded(encoding, exclusion):
            results.append(encoding)
    return results


def _scratch_setup(lines: list[str], test_data: TestData, scratch_base: int) -> None:
    """Per-chunk setup: point the scratch base register at the scratch region.

    Each chunk may begin a fresh split file, so it must re-establish the scratch
    base. Memory templates use this register as rs1, so it is the only one that
    must hold a valid mapped address before the encodings run. FP/vector state
    (mstatus.FS/VS) is already enabled by RVTEST_BEGIN in every file.
    """
    lines += [
        "",
        f"\t# x{scratch_base} = scratch base pointer",
        "\tnop",
        "\tnop",
        f"\tla x{scratch_base}, scratch",
        "",
    ]


def _finalize_chunk(test_data: TestData, lines: list[str], test_chunks: list[TestChunk]) -> None:
    """Set code + trap-based sigupd_count on the active chunk, end it, and collect it.

    Every counted testcase (each illegal encoding word and each CSR op) traps and
    writes 4 signature words (mstatus/mcause/mepc/mtval), so the per-file
    signature region is sized from 4 * num_testcases.
    """
    tc = test_data.test_chunk
    assert tc is not None, "No active test chunk to finalize"
    tc.code.extend(lines)
    tc.sigupd_count = 4 * tc.num_testcases
    test_chunks.append(test_data.end_test_chunk())


def _emit_raw_words(
    test_data: TestData,
    test_chunks: list[TestChunk],
    comment: str,
    template: str,
    length: int = 32,
    exclusion: Sequence[str] | None = None,
    setup: SetupFn | None = None,
    label: tuple[str, str, str] | None = None,
    section_header: str | None = None,
    split_name: str | None = None,
) -> None:
    """Emit a template's encodings as one or more self-contained .word/.hword chunks.

    Each chunk re-runs `setup` so it is valid wherever the file splitter places
    it. `label` and `section_header` are attached to the first chunk only.
    Templates over MAX_WORDS_PER_CHUNK encodings are split across chunks so no
    single block produces an oversized file.
    """
    seed(reproducible_hash(template))  # reproducible register/immediate choices per template
    directive = ".word" if length == 32 else ".hword"
    # Reserve one register as the scratch base; the rest of the pool stays
    # available for the encodings and per-chunk setup.
    # Exclude x12-x15: partially-fixed rd fields (011RR/011RE) land there, and a
    # legal lr/sc/amocas writing its own base register turns later legal memory
    # encodings into access faults, whose slow-handler +8 mepc adjustment skips
    # the following sweep word entirely (lost coverage on RV64).
    scratch_base = test_data.int_regs.get_register(exclude_regs=[12, 13, 14, 15])
    encodings = _gen_encodings(test_data.int_regs, scratch_base, template, length, exclusion)
    if not encodings:
        test_data.int_regs.return_register(scratch_base)
        return

    total = len(encodings)
    for grp_start in range(0, total, MAX_WORDS_PER_CHUNK):
        group = encodings[grp_start : grp_start + MAX_WORDS_PER_CHUNK]
        tc = test_data.begin_test_chunk(split_name)
        if section_header is not None and grp_start == 0:
            tc.section_header = section_header
        lines: list[str] = []
        if setup is not None:
            setup(lines, test_data, scratch_base)
        if label is not None and grp_start == 0:
            bin_name, coverpoint, covergroup = label
            lines.append(f"\t{test_data.add_testcase(bin_name, coverpoint, covergroup)}")
        lines.append("")
        if length == 32:
            lines.append("\t.balign 4")
        part = f" part {grp_start // MAX_WORDS_PER_CHUNK}" if total > MAX_WORDS_PER_CHUNK else ""
        lines.append(f"# {comment}{part}  ({len(group)} of {total} encodings) template {template}")
        for enc in group:
            lines.append(f"\t{directive} 0b{enc}")
        tc.num_testcases += len(group)
        _finalize_chunk(test_data, lines, test_chunks)
    test_data.int_regs.return_register(scratch_base)


def _emit_raw_sweeps(
    test_data: TestData,
    test_chunks: list[TestChunk],
    sweeps: Sequence[RawSweep],
    *,
    setup: SetupFn | None = None,
    label: tuple[str, str, str] | None = None,
    section_header: str | None = None,
    split_name: str | None = None,
) -> None:
    next_label = label
    next_header = section_header
    next_split_name = split_name
    for sweep in sweeps:
        _emit_raw_words(
            test_data,
            test_chunks,
            sweep.comment,
            sweep.template,
            length=sweep.length,
            exclusion=sweep.exclusion or None,
            setup=setup,
            label=next_label,
            section_header=next_header,
            split_name=next_split_name,
        )
        next_label = None
        next_header = None
        next_split_name = None


# ── CSR sweep body ────────────────────────────────────────────────────────


def _generate_csr_sweep_body(
    test_data: TestData,
    covergroup: str,
    csr_addresses: list[int],
    chunk_preamble: list[str] | None = None,
    section_header: str | None = None,
) -> list[TestChunk]:
    """Emit the CSR read/write/set/clear sweep as self-contained chunks.

    CSRs are batched CSRS_PER_CHUNK per chunk. `chunk_preamble` is prepended to
    every chunk so each is valid as the first body of a split file;
    `section_header` is attached to the first chunk only.
    """
    test_chunks: list[TestChunk] = []
    for batch_start in range(0, len(csr_addresses), CSRS_PER_CHUNK):
        batch = csr_addresses[batch_start : batch_start + CSRS_PER_CHUNK]
        tc = test_data.begin_test_chunk("CSR")
        if section_header is not None and batch_start == 0:
            tc.section_header = section_header
        lines: list[str] = []
        if chunk_preamble:
            lines.extend(chunk_preamble)
        for idx, csr_addr in enumerate(batch):
            if idx > 0 and idx % 10 == 0:
                lines.append("")

            r1, r2, r3 = test_data.int_regs.get_registers(3)

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
                    "",
                ]
            )
            test_data.int_regs.return_registers([r1, r2, r3])
        _finalize_chunk(test_data, lines, test_chunks)
    return test_chunks


# ── Illegal 32-bit instruction sweep ─────────────────────────────────────


def _generate_illegal_instr(
    test_data: TestData,
    covergroup: str,
) -> list[TestChunk]:
    """cp_illegal_instruction — reserved/illegal 32-bit encoding sweep.

    Each encoding block becomes a self-contained chunk that re-runs
    _scratch_setup (reload the scratch base) so it is valid in any split file.
    """
    coverpoint = "cp_illegal_instruction"
    test_chunks: list[TestChunk] = []
    # Only the first chunk carries the coverpoint testcase label and section banner.
    label: tuple[str, str, str] | None = ("illegal_instr_sweep", coverpoint, covergroup)
    section_header: str | None = comment_banner(coverpoint)
    split_name = "IllegalInstr"

    scalar_sweeps = [
        [
            RawSweep("Reserved op7", "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
            RawSweep("Reserved op15", "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
            RawSweep("Reserved op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
            RawSweep("Reserved op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
            RawSweep("Reserved op31", "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
        ],
        [
            RawSweep("cp_load", "000000000000BBBBBEEE011RR0000011"),
            RawSweep("cp_fload", "000000000000BBBBBEEE011RR0000111"),
            RawSweep("cp_store", "0000000RRRRRBBBBBEEE000000100011"),
            RawSweep("cp_fstore", "0000000RRRRRBBBBBEEE000000100111"),
        ],
        [
            RawSweep("cp_fence_cbo", "000000000000BBBBBEEE000000001111"),
            RawSweep("cp_cbo_immediate", "EEEEEEEEEEEEBBBBB010000000001111"),
            RawSweep("cp_cbo_rd", "000000000000BBBBB010EEEEE0001111"),
        ],
        [
            RawSweep(
                "cp_atomic_funct3",
                "RRRRRRRRRRRRBBBBBEEE011RR0101111",
                exclusion=("01001XXXXXXX0100001XXXXXX0101111",),
            ),
            RawSweep(
                "cp_atomic_funct7",
                "EEEEERRRRRRRBBBBB01E011RR0101111",
                exclusion=("01001XXXXXXXXXXXX01XXXXXX0101111",),
            ),
            RawSweep("cp_lrsc", "00010RREEEEEBBBBB01E011RR0101111"),
            RawSweep("cp_amocas_odd", "00101RRRRRREBBBBBEEE011RE0101111"),
        ],
        [
            RawSweep("cp_Itype", "EEEEEEEEEEEERRRRRE01RRRRR0010011"),
            RawSweep("cp_llAItype", "RRRRRRRRRRRRRRRRREEERRRRR0010011"),
            RawSweep("cp_aes64ks1i", "0011000EEEEERRRRR001RRRRR0010011"),
            RawSweep("cp_IWtype", "RRRRRRRRRRRRRRRRREEERRRRR0011011"),
            RawSweep("cp_IWshift", "EEEEEEERRRRRRRRRRE01RRRRR0011011"),
            RawSweep("cp_rtype", "EEEEEEERRRRRRRRRREEERRRRR0110011"),
            RawSweep("cp_rwtype", "EEEEEEERRRRRRRRRREEERRRRR0111011"),
        ],
        [
            RawSweep("cp_ftype", "EEEEERRRRRRRRRRRREEERRRRR1010011"),
            RawSweep("cp_fsqrt", "0101100EEEEERRRRRRRRRRRRR1010011"),
            RawSweep("cp_fclass", "1110000EEEEERRRRR001RRRRR1010011"),
            RawSweep("cp_fcvtif", "1100000EEE00RRRRR000RRRRR1010011"),
            RawSweep("cp_fcvtif_fmt", "11000EE000EERRRRR000RRRRR1010011"),
            RawSweep("cp_fcvtfi", "1101000EEER00RRRR000RRRRR1010011"),
            RawSweep("cp_fcvtfi_fmt", "11010EE000EERRRRR000RRRRR1010011"),
            RawSweep("cp_fcvtff", "0100000EEER00RRRR000RRRRR1010011"),
            RawSweep("cp_fcvtff_fmt", "01000EEEEEEERRRRR000RRRRR1010011"),
            RawSweep("cp_fmvif", "11100EEEEEEERRRRR000RRRRR1010011"),
            RawSweep("cp_fli", "11110EEEEEEERRRRR000RRRRR1010011"),
            RawSweep("cp_fmvfi", "11110EEEEEEERRRRR000RRRRR1010011"),
            RawSweep("cp_fmvh", "11100EEEEEEERRRRR000RRRRR1010011"),
            RawSweep("cp_fmvp", "10110EERRRRRRRRRR000RRRRR1010011"),
            RawSweep("cp_cvtmodwd", "11000EEEEEEERRRRR001RRRRR1010011"),
            RawSweep("cp_fcvtmodwdfrm", "110000101000RRRRREEERRRRR1010011"),
        ],
        [
            RawSweep("cp_branch2", "RRRRRRRRRRRRRRRRR010RRRRR1100011"),
            RawSweep("cp_branch3", "RRRRRRRRRRRRRRRRR011RRRRR1100011"),
            RawSweep("cp_jalr0", "RRRRRRRRRRRRRRRRREE1RRRRR1100111"),
            RawSweep("cp_jalr1", "RRRRRRRRRRRRRRRRR010RRRRR1100111"),
            RawSweep("cp_jalr2", "RRRRRRRRRRRRRRRRR100RRRRR1100111"),
            RawSweep("cp_jalr3", "RRRRRRRRRRRRRRRRR110RRRRR1100111"),
        ],
        [
            RawSweep(
                "cp_privileged_f3",
                "00000000000100000EEE000001110011",
                # funct3=000 is ebreak: legal, traps as breakpoint (cause 3), and the
                # slow handler's +8 sepc adjustment would skip the funct3=001 word.
                # The funct3=000 cross bin is amply covered by the privileged_000 sweep.
                exclusion=("00000000000100000000000001110011",),
            ),
            RawSweep(
                "cp_privileged_000",
                "EEEEEEEEEEEE00000000000001110011",
                exclusion=PRIVILEGED_000_EXCLUSIONS,
            ),
            RawSweep(
                "cp_privileged_rd",
                "00000000000000000000EEEEE1110011",
                exclusion=PRIVILEGED_000_EXCLUSIONS,
            ),
            RawSweep(
                "cp_privileged_rd",
                "RRRRRRRRRRRR00000000EEEEE1110011",
                exclusion=PRIVILEGED_000_EXCLUSIONS,
            ),
            RawSweep(
                "cp_privileged_rs2", "000000000000EEEEE000000001110011", exclusion=("00000000000000000000000001110011",)
            ),
        ],
        [
            RawSweep("cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11"),
            RawSweep("cp_reserved_fence_fm", "EEEE00000000RRRRR000RRRRR0001111"),
            RawSweep(
                "cp_reserved_fence_rs1",
                "00001111111100001000RRRRE0001111",
                exclusion=("XXXXXXXXXXXXXXXXXXXX00010XXXXXXX", "XXXXXXXXXXXXXXXXXXXX01000XXXXXXX"),
            ),
            RawSweep("cp_reserved_fence_rd", "000011111111RRRRE000000010001111"),
        ],
    ]
    for sweep_group in scalar_sweeps:
        _emit_raw_sweeps(
            test_data,
            test_chunks,
            sweep_group,
            setup=_scratch_setup,
            label=label,
            section_header=section_header,
            split_name=split_name,
        )
        label = None
        section_header = None

    # ── Upper register sweep (E extension) ── x16-x31 trap when E active ──
    upperreg_header: str | None = comment_banner("cp_upperreg", "x16-x31 — trap when E extension active")
    _emit_raw_sweeps(
        test_data,
        test_chunks,
        [
            RawSweep("cp_upperreg_rs1_add", "0000000000011EEEE000000010110011"),
            RawSweep("cp_upperreg_rs2_add", "00000001EEEE00001000011100110011"),
            RawSweep("cp_upperreg_rd_add", "000000000001000010001EEEE0110011"),
            RawSweep("cp_upperreg_rs1_mul", "0000001000011EEEE000000010110011"),
            RawSweep("cp_upperreg_rs2_mul", "00000011EEEE00001000011100110011"),
            RawSweep("cp_upperreg_rd_mul", "000000100001000010001EEEE0110011"),
            RawSweep("cp_upperreg_rs1_fadd-s", "0000000000011EEEE000000011010011"),
            RawSweep("cp_upperreg_rs2_fadd-s", "00000001EEEE00001000011101010011"),
            RawSweep("cp_upperreg_rd_fadd-s", "000000000001000010001EEEE1010011"),
            RawSweep("cp_upperreg_imm_rs1_addi0", "0000000000001EEEE000011100010011"),
            RawSweep("cp_upperreg_imm_rs1_addi1", "1111111111111EEEE000011100010011"),
            RawSweep("cp_upperreg_imm_rd_addi0", "000000000000000010001EEEE0010011"),
            RawSweep("cp_upperreg_imm_rd_addi1", "111111111111000010001EEEE0010011"),
            RawSweep("cp_upperreg_fmv_x_w_rs1", "1110000000001EEEE000000011010011"),
            RawSweep("cp_upperreg_fmv_x_w_rd", "111000000000000010001EEEE1010011"),
            RawSweep("cp_upperreg_fmv_w_x_rs1", "1111000000001EEEE000011101010011"),
            RawSweep("cp_upperreg_fmv_w_x_rd", "111100000000000010001EEEE1010011"),
        ],
        setup=_scratch_setup,
        section_header=upperreg_header,
    )

    return test_chunks


# ── Vector illegal instruction sweep ─────────────────────────────────────


def _vector_setup(sew: str = "8", avl: int = 0) -> SetupFn:
    """Per-chunk setup factory for vector blocks: reload scratch base + set vl/vtype.

    mstatus.VS is already enabled by RVTEST_BEGIN; only vl/vtype must be set so
    any legal vector load/store among the swept encodings behaves predictably
    (avl=0 makes them no-ops).
    """

    def setup(lines: list[str], test_data: TestData, scratch_base: int) -> None:
        _scratch_setup(lines, test_data, scratch_base)
        lines.append(f"\tvsetivli x0, {avl}, e{sew}, m1, ta, ma")
        lines.append("")

    return setup


def _generate_vector_illegal_instr(
    test_data: TestData,
    covergroup: str,
) -> list[TestChunk]:
    """cp_illegal_vector_instruction — reserved/illegal vector encoding sweep.

    Each encoding block becomes a self-contained chunk that re-runs the vector
    setup (reload the scratch base + the right vsetivli for the block) so it is
    valid in any split file.
    """
    coverpoint = "cp_illegal_vector_instruction"
    test_chunks: list[TestChunk] = []
    # Only the first chunk carries the coverpoint testcase label.
    label: tuple[str, str, str] | None = ("vector_illegal_sweep", coverpoint, covergroup)

    # ── vset* configuration instructions ──────────────────────────────
    vset_header = comment_banner(
        coverpoint,
        "Exhaustive reserved/illegal vector encoding sweep.",
    ) + comment_banner("vset* reserved encodings", "Reserved bits in vsetvl/vsetvli/vsetivli")
    _emit_raw_sweeps(
        test_data,
        test_chunks,
        [
            RawSweep("cp_v_vsetvl", "10EEEEERRRRRRRRRR111RRRRR1010111"),
            RawSweep("cp_v_vsetvli_sew", "0000RR1EERRRRRRRR111RRRRR1010111"),
            RawSweep("cp_v_vsetvli_res", "0EEERR0RRRRRRRRRR111RRRRR1010111"),
            RawSweep("cp_v_vsetivli_sew", "1100RR1EERRRRRRRR111RRRRR1010111"),
            RawSweep("cp_v_vsetivli_res", "11EERR0RRRRRRRRRR111RRRRR1010111"),
        ],
        setup=_vector_setup(),
        label=label,
        section_header=vset_header,
        split_name="VectorInstr",
    )

    # ── Reserved vector loads ── rs1 is the scratch base (B field) ──
    # For lumop templates, mop is fixed to 00 (unit-stride) so the lumop E bits
    # are interpreted as lumop, not as a stride register.
    _emit_raw_sweeps(
        test_data,
        test_chunks,
        [
            RawSweep("cp_vl_0_000", "RRRERRRRRRRRBBBBBEEE011RR0000111"),
            RawSweep("cp_vl_lumop_8", "RRR000REEEEEBBBBB000011RR0000111"),
            RawSweep("cp_vl_lumop_16", "RRR000REEEEEBBBBB101011RR0000111"),
            RawSweep("cp_vl_lumop_32", "RRR000REEEEEBBBBB110011RR0000111"),
            RawSweep("cp_vl_lumop_64", "RRR000REEEEEBBBBB111011RR0000111"),
        ],
        setup=_vector_setup(),
        section_header=comment_banner("Vector load reserved encodings", "Reserved mew/width/lumop for vector loads"),
    )

    # ── Reserved vector stores ────────────────────────────────────────
    _emit_raw_sweeps(
        test_data,
        test_chunks,
        [
            RawSweep("cp_vl_0_000", "RRRERRRRRRRRBBBBBEEE011RR0100111"),
            RawSweep("cp_vl_sumop_8", "RRR000REEEEEBBBBB000011RR0100111"),
            RawSweep("cp_vl_sumop_16", "RRR000REEEEEBBBBB101011RR0100111"),
            RawSweep("cp_vl_sumop_32", "RRR000REEEEEBBBBB110011RR0100111"),
            RawSweep("cp_vl_sumop_64", "RRR000REEEEEBBBBB111011RR0100111"),
        ],
        setup=_vector_setup(),
        section_header=comment_banner("Vector store reserved encodings", "Reserved mew/width/lumop for vector stores"),
    )

    # ── Vector arithmetic per-SEW sweeps ──────────────────────────────
    for sew in ["8", "16", "32", "64"]:
        sew_header: str | None = comment_banner(f"Vector arithmetic SEW={sew}", f"funct6 sweeps with e{sew}")
        _emit_raw_sweeps(
            test_data,
            test_chunks,
            [
                RawSweep(f"cp_IVV_f6_e{sew}", "EEEEEEERRRRRRRRRR000RRRRR1010111"),
                RawSweep(f"cp_FVV_f6_e{sew}", "EEEEEEERRRRRRRRRR001RRRRR1010111"),
                RawSweep(f"cp_MVV_f6_e{sew}", "EEEEEEERRRRRRRRRR010RRRRR1010111"),
                RawSweep(f"cp_IVI_f6_e{sew}", "EEEEEEERRRRRRRRRR011RRRRR1010111"),
                RawSweep(f"cp_IVX_f6_e{sew}", "EEEEEEERRRRRRRRRR100RRRRR1010111"),
                RawSweep(f"cp_FVF_f6_e{sew}", "EEEEEEERRRRRRRRRR101RRRRR1010111"),
                RawSweep(f"cp_MVX_f6_e{sew}", "EEEEEEERRRRRRRRRR110RRRRR1010111"),
                RawSweep(f"cp_MVV_VWRXUNARY0_e{sew}", "010000ERRRRREEEEE010RRRRR1010111"),
                RawSweep(f"cp_MVX_VRXUNARY0_e{sew}", "010000EEEEEERRRRR110RRRRR1010111"),
                RawSweep(f"cp_MVV_VXUNARY0_e{sew}", "010010ERRRRREEEEE010RRRRR1010111"),
                RawSweep(f"cp_MVV_VMUNARY0_e{sew}", "010100ERRRRREEEEE010RRRRR1010111"),
                RawSweep(f"cp_FVV_VWFUNARY0_e{sew}", "010000ERRRRREEEEE001RRRRR1010111"),
                RawSweep(f"cp_FVF_VRFUNARY0_e{sew}", "010000EEEEEERRRRR101RRRRR1010111"),
                RawSweep(f"cp_FVV_VFUNARY0_e{sew}", "010010ERRRRREEEEE001RRRRR1010111"),
                RawSweep(f"cp_FVV_VFUNARY1_e{sew}", "010011ERRRRREEEEE001RRRRR1010111"),
                RawSweep(f"cp_vopve_e{sew}", "EEEEEEERRRRRRRRRREEERRRRR1110111"),
                RawSweep(f"cp_MVV_vaesvv_e{sew}", "101000ERRRRREEEEE010RRRRR1110111"),
                RawSweep(f"cp_MVV_vaesvs_e{sew}", "101001ERRRRREEEEE010RRRRR1110111"),
            ],
            setup=_vector_setup(sew, avl=1),
            section_header=sew_header,
        )

    return test_chunks


# ── Compressed 16-bit instruction sweep ──────────────────────────────────


def _generate_compressed_instr(
    test_data: TestData,
    covergroup: str,
) -> list[TestChunk]:
    """cp_illegal_compressed_instruction — exhaustive 16-bit quadrant sweeps.

    Compressed encodings need no scratch setup; sp-relative and jump/branch
    encodings are excluded so no chunk corrupts the signature area.
    """
    coverpoint = "cp_illegal_compressed_instruction"
    test_chunks: list[TestChunk] = []
    compressed_sweeps = [
        # Quadrant 00: Exclude loads and stores that could cause exceptions for bad addresses
        RawSweep(
            "compressed00",
            "EEEEEEEEEEEEEE00",
            length=16,
            exclusion=(
                "001XXXXXXXXXXX00",  # c.fld
                "010XXXXXXXXXXX00",  # c.lw
                "011XXXXXXXXXXX00",  # c.flw/c.ld
                "100000XXXXXXXX00",  # c.lbu
                "100001XXXXXXXX00",  # c.lh/lhu
                "100010XXXXXXXX00",  # c.sb
                "100011XXX0XXXX00",  # c.sh
                "101XXXXXXXXXXX00",  # c.fsd
                "110XXXXXXXXXXX00",  # c.sw
                "111XXXXXXXXXXX00",  # c.fsw/c.sd
            ),
        ),
        # Quadrant 01: exclude jumps and branches that could go to unknown places.
        # Avoid clobbering signature pointer in x2
        RawSweep(
            "compressed01",
            "EEEEEEEEEEEEEE01",
            length=16,
            exclusion=(
                "101XXXXXXXXXXX01",  # c.j — random jump
                "11XXXXXXXXXXXX01",  # c.beqz/c.bnez — random branch
                "001XXXXXXXXXXX01",  # c.jal (RV32) — random jump
                "0XXX00010XXXXX01",  # rd = x2 — clobbers signature pointer
            ),
        ),
        # Quadrant 10:
        RawSweep(
            "compressed10",
            "EEEEEEEEEEEEEE10",
            length=16,
            exclusion=(
                "1000XXXXX0000010",  # c.jr rs1!=0 — random jump
                "1001XXXXX0000010",  # c.jalr/c.ebreak — random jump or debug trap
                "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp — sp-relative, corrupts signature area
                "X10XXXXXXXXXXX10",  # c.lwsp/c.swsp — sp-relative, corrupts signature area
                "011XXXXXXXXXXX10",  # c.ldsp/c.flwsp — sp-relative store
                "1001000000000010",  # c.ebreak — legal, tested elsewhere
                "0X0X00010XXXXX10",  # CI with rd = x2 (sp) — clobbers signature pointer
                "100X00010XXXXX10",  # CR with rd = x2 (sp) — clobbers signature pointer
                "1100XXXXXXXXXX10",  # c.swsp with rs2=x2 — stores sp to random address
                "111XXXXXXXXXXX10",  # c.sdsp/c.fswsp — sp-relative store
                "1010XXXXXXXXXX10",  # nop-like edge — unpredictable on some platforms
            ),
        ),
        RawSweep("illegal_c_jr", "1000000000000010", length=16),
    ]
    _emit_raw_sweeps(
        test_data,
        test_chunks,
        compressed_sweeps,
        label=("compressed_sweep", coverpoint, covergroup),
        section_header=comment_banner(coverpoint, "Exhaustive 16-bit quadrant sweep."),
        split_name="CompressedInstr",
    )

    return test_chunks


# ── Suite assembly ─────────────────────────────────────────────────────────

_MODE_LABEL = {"M": "M-mode", "S": "S-mode", "U": "U-mode"}

# M-mode only: lock PMP region 0 (TOR RWX) before each CSR chunk so PMP CSR
# reads do not corrupt config regardless of which split file the chunk lands in.
_M_MODE_PMP_LOCK = [
    "# Lock PMP region 0 (TOR RWX) so PMP CSR reads do not corrupt config",
    "\tli x10, 0x8F",
    "\tcsrw pmpcfg0, x10",
    "",
]


def _generate_csr_sweep(test_data: TestData, suite: str, priv_mode: str, csr_skip: frozenset[int]) -> list[TestChunk]:
    """CSR read/write/set/clear sweep, with covergroup and setup derived from priv mode.

    The covergroup is ``{suite}_{m,s,u}csr_cg``. M-mode prepends the PMP lock to
    every chunk. ``csr_skip`` holds the suite's excluded CSRs (higher-privilege,
    custom, and reserved addresses), documented at its definition site.
    """
    label = _MODE_LABEL[priv_mode]
    covergroup = f"{suite}_{priv_mode.lower()}csr_cg"
    all_csrs = [a for a in range(4096) if a not in csr_skip]
    preamble = _M_MODE_PMP_LOCK if priv_mode == "M" else None
    section_header = comment_banner(
        f"cp_csrr / cp_csrw_corners / cp_csrcs ({label})",
        f"Read, write 0s/1s, set, clear every swept CSR from {label}.\n"
        "Higher-privilege, custom, and reserved CSRs are excluded via the\n"
        "suite's skip set (architecturally-known traps add no coverage).",
    )
    return _generate_csr_sweep_body(
        test_data, covergroup, all_csrs, chunk_preamble=preamble, section_header=section_header
    )


def generate_ssstrict_suite(
    test_data: TestData,
    suite: str,
    priv_mode: str,
    csr_skip: frozenset[int],
) -> list[TestChunk]:
    """Assemble a full Ssstrict suite for ``priv_mode`` ("M"/"S"/"U").

    All covergroup names are derived from ``suite`` and ``priv_mode``; the only
    suite-specific input is the CSR skip set.
    """
    seed(42)
    instr_covergroup = f"{suite}_instr_cg"
    compressed_covergroup = f"{suite}_comp_instr_cg"
    test_chunks: list[TestChunk] = []
    test_chunks.extend(_generate_csr_sweep(test_data, suite, priv_mode, csr_skip))
    test_chunks.extend(_generate_illegal_instr(test_data, instr_covergroup))
    test_chunks.extend(_generate_compressed_instr(test_data, compressed_covergroup))
    test_chunks.extend(_generate_vector_illegal_instr(test_data, instr_covergroup))
    return test_chunks
