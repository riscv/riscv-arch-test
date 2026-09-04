##################################
# priv/extensions/ZpmCommon.py
#
# Pointer masking (Ssnpm/Smmpm/Smnpm) shared test generators.
# Author :  Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared pointer-masking extension test infrastructure.
Common code for Ssnpm (S->U), Smmpm (M-mode), SmnpmS (M->S), SmnpmU (M->U)
test generators.
"""

from __future__ import annotations

from dataclasses import dataclass

from testgen.asm.csr import gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData

# ── Constants ──────────────────────────────────────────────────────────────

UPPER_PATTERNS: list[int] = [
    0x0000,  # no tag: masking is a no-op, the control case
    0x0001,  # bit 48   -- stripped by PMLEN=16 only
    0x0100,  # bit 56   -- stripped by PMLEN=16 only
    0x0200,  # bit 57   -- stripped by PMLEN=16 and PMLEN=7
    0x8000,  # bit 63   -- stripped by PMLEN=16 and PMLEN=7
    0xFFFF,  # bits 63:48 -- fully stripped by PMLEN=16, partially by PMLEN=7
    0xFE00,  # bits 63:57 -- exactly the PMLEN=7 window
    0xFF00,  # bits 63:56 -- fully stripped by PMLEN=16, partially by PMLEN=7
]

PMM_CONFIGS: list[tuple[int, int, str]] = [
    (0b00, 0, "pmm00"),
    (0b10, 7, "pmm10"),
    (0b11, 16, "pmm11"),
]

VALUE_OLD: int = 0xABCD_1234_ABCD_1234
VALUE_NEW: int = 0xA5A5_A5A5_A5A5_A5A5
SENTINEL: int = 0x1BAD_0BAD_1BAD_0BAD

_MSTATUS_MXR = 1 << 19
_MSTATUS_SUM = 1 << 18
_MSTATUS_FS_DIRTY = 3 << 13
_MSTATUS_VS_DIRTY = 3 << 9

CP_MASKING = "cp_pmlen_masking"
CP_MISALIGN = "cp_pmlen_misaligned_word"
CP_MXR = "cp_pmm_mxr"
CP_JALR = "cp_pmm_jalr"
CP_FAULT = "cp_hardware_csr_writes_fault"
CP_CSR = "cp_pm_csr_software_access"
CP_UXL_CLEAR = "cp_pmm_uxl_clear"
CP_SXL_CLEAR = "cp_pmm_sxl_clear"
CP_MPRV_MPP_M = "cp_pm_mprv_mpp_m"
CP_MPRV_MPP_U_S = "cp_pm_mprv_mpp_u_s"
CP_MPRV_MPP_U_NO_S = "cp_pm_mprv_mpp_u_no_s"

# envcfg (menvcfg/senvcfg) field positions shared by every mode-entry prelude
# that needs to grant cbo.*/prefetch.*/Zicfiss permission to the next lower
# privilege level.
_ENVCFG_CBIE_SHIFT = 4
_ENVCFG_CBCFE_SHIFT = 6
_ENVCFG_CBZE_SHIFT = 7
_ENVCFG_SSE_BIT = 1 << 3

READS: list[str] = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]
WRITES: list[tuple[str, str]] = [("sb", "lbu"), ("sh", "lhu"), ("sw", "lw"), ("sd", "ld")]
AMO_OPS = ["swap", "add", "xor", "and", "or", "min", "max", "minu", "maxu"]
RV64A_AMOS: list[tuple[str, str]] = [(f"amo{op}.{w}", "lw" if w == "w" else "ld") for op in AMO_OPS for w in ("w", "d")]
ZABHA_AMOS: list[tuple[str, str]] = [
    (f"amo{op}.{w}", "lbu" if w == "b" else "lhu") for op in AMO_OPS for w in ("b", "h")
]
ZACAS_AMOS: list[str] = ["amocas.w", "amocas.d", "amocas.q"]
FP_READS: list[tuple[str, str, str]] = [
    ("flw", "F_SUPPORTED", "fmv.w.x"),
    ("fld", "D_SUPPORTED", "fmv.d.x"),
]  # TODO :Add flq & fsq when Q is supported.
FP_WRITES: list[tuple[str, str, str, str]] = [
    ("fsw", "lw", "F_SUPPORTED", "fmv.w.x"),
    ("fsd", "ld", "D_SUPPORTED", "fmv.d.x"),
]
ZCA_READS_CL: list[str] = ["c.lw", "c.ld"]
ZCA_WRITES_CS: list[tuple[str, str]] = [("c.sw", "lw"), ("c.sd", "ld")]
ZCA_READS_SP: list[str] = ["c.lwsp", "c.ldsp"]
ZCA_WRITES_SP: list[tuple[str, str]] = [("c.swsp", "lw"), ("c.sdsp", "ld")]

ZICBOM_OPS: list[str] = ["cbo.clean", "cbo.flush", "cbo.inval"]
ZICBOP_OPS: list[str] = ["prefetch.r", "prefetch.w", "prefetch.i"]
ZICFISS_AMOS: list[
    tuple[str, str, int]
] = []  # TODO : Add all zicfiss instructions including amo and push, pop instructions.

VEC_READS: list[tuple[str, int, str]] = [
    ("vle8.v", 8, "vle8.v v2, (x{a})"),
    ("vle16.v", 16, "vle16.v v2, (x{a})"),
    ("vle32.v", 32, "vle32.v v2, (x{a})"),
    ("vle64.v", 64, "vle64.v v2, (x{a})"),
    ("vle8ff.v", 8, "vle8ff.v v2, (x{a})"),
    ("vle16ff.v", 16, "vle16ff.v v2, (x{a})"),
    ("vle32ff.v", 32, "vle32ff.v v2, (x{a})"),
    ("vle64ff.v", 64, "vle64ff.v v2, (x{a})"),
    ("vlse32.v", 32, "vlse32.v v2, (x{a}), x0"),
    ("vlse64.v", 64, "vlse64.v v2, (x{a}), x0"),
    ("vluxei32.v", 32, "vluxei32.v v2, (x{a}), v4"),
    ("vluxei64.v", 64, "vluxei64.v v2, (x{a}), v4"),
    ("vloxei32.v", 32, "vloxei32.v v2, (x{a}), v4"),
    ("vloxei64.v", 64, "vloxei64.v v2, (x{a}), v4"),
    ("vl1r.v", 64, "vl1r.v v2, (x{a})"),
    ("vlseg2e32.v", 32, "vlseg2e32.v v2, (x{a})"),
]
VEC_WRITES: list[tuple[str, int, str, str]] = [
    ("vse8.v", 8, "vse8.v v2, (x{a})", "lbu"),
    ("vse16.v", 16, "vse16.v v2, (x{a})", "lhu"),
    ("vse32.v", 32, "vse32.v v2, (x{a})", "lw"),
    ("vse64.v", 64, "vse64.v v2, (x{a})", "ld"),
    ("vsse32.v", 32, "vsse32.v v2, (x{a}), x0", "lw"),
    ("vsse64.v", 64, "vsse64.v v2, (x{a}), x0", "ld"),
    ("vsuxei32.v", 32, "vsuxei32.v v2, (x{a}), v4", "lw"),
    ("vsuxei64.v", 64, "vsuxei64.v v2, (x{a}), v4", "ld"),
    ("vsoxei32.v", 32, "vsoxei32.v v2, (x{a}), v4", "lw"),
    ("vsoxei64.v", 64, "vsoxei64.v v2, (x{a}), v4", "ld"),
    ("vs1r.v", 64, "vs1r.v v2, (x{a})", "ld"),
    ("vsseg2e32.v", 32, "vsseg2e32.v v2, (x{a})", "lw"),
]

# ── Page-table constants (Sv39/Sv48/Sv57) ─────────────────────────────────

_NONLEAF_PERMS = "PTE_V"  # non-leaf PTEs must have ONLY V set
_LEAF_PERMS_U = "PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V"  # U-accessible data page
_LEAF_PERMS_S = "PTE_D | PTE_A | PTE_W | PTE_R | PTE_V"  # S-accessible only (no U)

LEVELS_BELOW_ROOT: dict[str, int] = {"sv39": 2, "sv48": 3, "sv57": 4}
IDENTITY_VPN_SHIFT: dict[str, int] = {"sv39": 30, "sv48": 39, "sv57": 48}

HIGH_VA: dict[str, int] = {
    "sv39": 0xFFFF_FFC0_0000_0000,
    "sv48": 0xFFFF_8000_0000_0000,
    # sv57 reuses sv48's boundary rather than its own tighter one (bit 56
    # only, 0xFF00...) because that value leaves bit 47 = 0, breaking the
    # PMLEN=16 round trip; this one keeps bits 63:47 all set to 1.
    "sv57": 0xFFFF_8000_0000_0000,
}

MODES: list[str] = ["bare", "sv39", "sv48", "sv57"]
MODE_GUARDS: dict[str, str | None] = {m: None if m == "bare" else f"{m.upper()}_SUPPORTED" for m in MODES}

# ── MPRV pass (Smmpm-specific) ──────────

_MSTATUS_MPRV = 1 << 17
_MSTATUS_MPP_SHIFT = 11
_MPP_M, _MPP_S, _MPP_U = 0b11, 0b01, 0b00

# PMM field bit position (common across mseccfg/menvcfg/senvcfg)
_PMM_FIELD_SHIFT = 32

# Limited upper patterns for MPRV testing (per testplan)
_MPRV_UPPER_PATTERNS: list[int] = [0x0000, 0x0001, 0x0200]


# ── Config / Regs ──────────────────────────────────────────────────────────
@dataclass
class Regs:
    base: int
    a: int
    data: int
    chk: int
    tmp: int
    tmp2: int
    fp: int
    fp_c: int
    dest_pair: int  # for amocas.q (register pair)
    source_pair: int  # for amocas.q (register pair)


# ── Register allocation helpers ─────────────────────────────────────────────


def alloc_pm_regs_paired(td: TestData) -> Regs:
    """chk/data are reserved as aligned pairs (get_register_pair) for amocas.q,
    which implicitly reads/writes rd+1/rs2+1; those halves double as tmp/tmp2,
    always reloaded before use. `a` is pinned to x8-x15 since it's rs1 in
    forced c.lw/c.ld/c.sw/c.sd, whose 3-bit field can't encode x6.
    """
    chk = td.int_regs.get_register_pair()
    data = td.int_regs.get_register_pair()
    tmp = chk + 1
    tmp2 = data + 1
    a = td.int_regs.get_registers(1, reg_range=list(range(8, 16)))[0]
    base = td.int_regs.get_registers(1)[0]
    fp, fp_c = (
        td.float_regs.get_register(),
        td.float_regs.get_register(reg_range=list(range(8, 16))),
    )
    return Regs(
        base=base,
        a=a,
        data=data,
        chk=chk,
        tmp=tmp,
        tmp2=tmp2,
        fp=fp,
        fp_c=fp_c,
        dest_pair=chk,
        source_pair=data,
    )


def alloc_pm_regs_wide(td: TestData) -> Regs:
    """Same reasoning as alloc_pm_regs_paired"""
    chk = td.int_regs.get_register_pair()
    data = td.int_regs.get_register_pair()
    tmp = chk + 1
    tmp2 = data + 1
    a = td.int_regs.get_registers(1, reg_range=list(range(8, 16)))[0]
    base = td.int_regs.get_registers(1)[0]
    fp, fp_c = td.float_regs.get_register(), td.float_regs.get_register(reg_range=list(range(8, 16)))
    return Regs(
        base=base,
        a=a,
        data=data,
        chk=chk,
        tmp=tmp,
        tmp2=tmp2,
        fp=fp,
        fp_c=fp_c,
        dest_pair=chk,
        source_pair=data,
    )


def free_pm_regs(td: TestData, regs: Regs) -> None:
    """Return every register a probe module borrows. dest_pair/source_pair are
    reserved as register pairs; tmp/tmp2 alias their +1 halves rather than
    being separately reserved, so returning the two pairs already releases
    tmp/tmp2.
    """
    td.int_regs.return_register_pair(regs.dest_pair)
    td.int_regs.return_register_pair(regs.source_pair)
    td.int_regs.return_registers([regs.base, regs.a])
    td.float_regs.return_registers([regs.fp, regs.fp_c])


# ── Assembly Helpers ───────────────────────────────────────────────────────


def _fixed(instr: str) -> list[str]:
    """
    Wraps it in `.option norvc` so the assembler cannot silently substitute
    a compressed (16-bit) encoding,
    This keeps the emitted instruction matching the exact mnemonic the
    test ID/coverpoint was built from.
    """
    return [".option push", ".option norvc", instr, ".option pop"]


def _fixed_block(body: list[str]) -> list[str]:
    return [".option push", ".option norvc", *body, ".option pop"]


def _tid(prefix: str, upper: int, mnemonic: str) -> str:
    return f"{prefix}_up{upper:04X}_{mnemonic.replace('.', '_')}"


# ── Factoring helpers (PMM / FS+VS / JALR pad / data pages) ────────────────


def set_pmm_field(csr: str, shift: int, val: int, pmlen: int, tmp: int) -> list[str]:
    """Clear then set the 2-bit PMM field in *csr* at *shift*."""
    mask = 0b11 << shift
    lines = [
        f"# {csr}.PMM={val:#04b} PMLEN={pmlen}",
        f"LI(x{tmp}, {hex(mask)})",
        f"csrc {csr}, x{tmp}",
    ]
    if val:
        lines += [
            f"LI(x{tmp}, {hex(val << shift)})",
            f"csrs {csr}, x{tmp}",
        ]
    return lines


def enable_fp_vector_state(
    regs: Regs,
    extra_bits: int = 0,
    extra_comment: str | None = None,
) -> list[str]:
    """Enable FS/VS dirty so FP and vector probes are legal.

    *extra_bits* is ORed into the same mstatus write (e.g. SUM for Ssnpm).
    *extra_comment* replaces the default one-line comment when supplied.
    """
    bits = _MSTATUS_FS_DIRTY | _MSTATUS_VS_DIRTY | extra_bits
    if extra_comment is not None:
        comment = extra_comment
    else:
        comment = "# FP and vector state must be enabled for the FP/vector probes to be legal."
    return [
        "",
        comment,
        f"LI(x{regs.tmp}, {hex(bits)})",
        f"csrs mstatus, x{regs.tmp}",
    ]


def jalr_pad_asm(regs: Regs) -> list[str]:
    return [
        "j pm_jalr_pad_end",
        "pm_jalr_pad:",
        f"addi x{regs.chk}, x{regs.chk}, 1",
        "jr ra",
        "pm_jalr_pad_end:",
        "RVTEST_GOTO_MMODE",
        "",
    ]


def data_page(label: str, value: int = VALUE_OLD) -> list[str]:
    """One 4 KiB page containing a single dword seed."""
    return [
        ".p2align 12",
        f"{label}: .dword {hex(value)}",
        ".zero 4088",
    ]


def data_pm_lo_page() -> list[str]:
    return data_page("pm_lo_page")


def data_pm_hi_page() -> list[str]:
    return data_page("pm_hi_page")


def data_slvl_tables(mode: str, label_prefix: str = "rvtest_slvl") -> list[str]:
    """Zero-filled page-table pages for the given satp mode."""
    lines: list[str] = []
    for i in range(LEVELS_BELOW_ROOT[mode]):
        lines += [".p2align 12", f"{label_prefix}{i}_pg_tbl: .zero 4096"]
    return lines


def pass_g_csr_writes(
    prefix: str,
    pmlen: int,
    td: TestData,
    regs: Regs,
    cg: str,
    csrs: list[str],
) -> list[str]:
    """CSR writes must not be pointer-masked (shared by Smmpm / SmnpmS)."""
    lines = [comment_banner(f"{prefix}: CSR writes must not be pointer-masked")]
    pattern = ((1 << pmlen) - 1) << (64 - pmlen) | 0x1234_5678
    for csr in csrs:
        lines += [
            f"csrr x{regs.tmp}, {csr} # save the csr's value before clobbering it",
            f"LI(x{regs.chk}, {hex(pattern)})",
            td.add_testcase(f"{prefix}_csrw_{csr}", CP_CSR, cg),
            gen_csr_write_sigupd(regs.chk, csr, td),
            f"csrw {csr}, x{regs.tmp} # restore before any later trap needs this CSR",
        ]
    return lines


# ── MPRV pass (Smmpm-specific) ─────────


def _mprv_img_tables(mode: str) -> list[str]:
    """Top-down ordered labels for the MPRV pass's dedicated page tables
    (rvtest_mprv_slvl*_pg_tbl_<mode>, allocated in mprv_data_section()).
    Matches the ordering build_data_only_u_map_asm / _walk_asm expect:
    tables[0] is the table one level below the framework root, tables[-1]
    is the table that directly holds the 4 KiB leaf PTEs.
    """
    return [f"rvtest_mprv_slvl{i}_pg_tbl_{mode}" for i in range(LEVELS_BELOW_ROOT[mode] - 1, -1, -1)]


def set_mprv(enable: bool, mpp: int, tmp: int) -> list[str]:
    if enable:
        return [
            f"LI(x{tmp}, {hex(0b11 << _MSTATUS_MPP_SHIFT)})",
            f"csrc mstatus, x{tmp}",
            f"LI(x{tmp}, {hex((mpp << _MSTATUS_MPP_SHIFT) | _MSTATUS_MPRV)})",
            f"csrs mstatus, x{tmp}",
        ]
    return [
        f"LI(x{tmp}, {hex(_MSTATUS_MPRV)})",
        f"csrc mstatus, x{tmp}",
    ]


def set_sum(enable: bool, tmp: int) -> list[str]:
    op = "csrs" if enable else "csrc"
    return [
        f"# mstatus.SUM = {int(enable)}",
        f"LI(x{tmp}, {hex(_MSTATUS_SUM)})",
        f"{op} mstatus, x{tmp}",
    ]


def mprv_data_section() -> list[str]:
    lines = [
        ".pushsection .data",
        *data_pm_lo_page(),
        *data_page("mprv_page"),
    ]
    for mode, guard in [
        ("sv39", "SV39_SUPPORTED"),
        ("sv48", "SV48_SUPPORTED"),
        ("sv57", "SV57_SUPPORTED"),
    ]:
        lines.append(f"#ifdef {guard}")
        for level in range(LEVELS_BELOW_ROOT[mode]):
            lines += [
                ".p2align 12",
                f"rvtest_mprv_slvl{level}_pg_tbl_{mode}: .zero 4096",
            ]
        lines.append(f"#endif // {guard}")
    lines.append(".popsection")
    return lines


def build_data_only_u_map_asm(mode: str, img_tables: list[str], td: TestData) -> list[str]:
    """Split the 2 MiB region containing rvtest_code_begin into 4 KiB leaves,
    granting PTE_U only to the U-accessible data range (rvtest_data_begin..
    end_signature). Unlike build_finegrained_text_map_asm, no code range is
    ever marked U -- callers (Smmpm's MPRV pass) fetch only from M-mode,
    which is never translated, so only the data page's permission bit matters.

    Only 6 int registers are available, so the loop keeps just three live
    across iterations -- current VA, leaf PTE slot pointer, and the loop
    counter -- and reloads the data-range bounds with LA each pass instead
    of holding them in dedicated registers.
    """
    (r0,) = td.int_regs.get_registers(1)
    lines = [f"# {mode.upper()}: 4 KiB mapping of the test image; PTE_U only on data range"]
    # Walk the non-leaf PTEs from the framework root down to img_tables[0].
    lines += [f"LA(x{r0}, rvtest_code_begin)"]
    lines += _walk_asm(mode, img_tables, f"x{r0}", td)

    r1, r6, s0, s1, s2 = td.int_regs.get_registers(5)
    lines += [
        # Recompute the 2 MiB-aligned base of the image; this is the VA the
        # leaf-fill loop below walks forward from, 4 KiB at a time.
        f"LA(x{r0}, rvtest_code_begin)",
        f"srli x{r0}, x{r0}, 21",
        f"slli x{r0}, x{r0}, 21                  # x{r0} = 2 MiB-aligned base of the image",
        # r1 walks the 512 consecutive leaf PTE slots in img_tables[-1].
        f"LA(x{r1}, {img_tables[-1]})",
        f"li   x{r6}, 512",
        "1:",
        # Default leaf perms with no PTE_U.
        f"li   x{s0}, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V)",
        # pm_lo_page
        f"LA(x{s1}, pm_lo_page)",
        f"sub  x{s1}, x{r0}, x{s1}",
        f"li   x{s2}, 4096",
        f"bltu x{s1}, x{s2}, 2f",
        # mprv_page
        f"LA(x{s1}, mprv_page)",
        f"sub  x{s1}, x{r0}, x{s1}",
        f"li   x{s2}, 4096",
        f"bltu x{s1}, x{s2}, 2f",
        # framework data range
        f"LA(x{s1}, rvtest_data_begin)",
        f"LA(x{s2}, end_signature)",
        f"LA(x{s2}, end_signature)",
        f"sub  x{s2}, x{s2}, x{s1}",
        f"sub  x{s1}, x{r0}, x{s1}",
        "2:",
        f"ori  x{s0}, x{s0}, PTE_U",
        "3:",
        # Pack the PPN + perms into the PTE and store it, then advance to the
        # next leaf slot and the next 4 KiB page.
        f"srli x{s1}, x{r0}, 12",
        f"slli x{s1}, x{s1}, 10",
        f"or   x{s1}, x{s1}, x{s0}",
        f"sd   x{s1}, 0(x{r1})",
        f"addi x{r1}, x{r1}, 8",
        f"lui  x{s1}, 1",
        f"add  x{r0}, x{r0}, x{s1}",
        f"addi x{r6}, x{r6}, -1",
        f"bnez x{r6}, 1b",
    ]
    td.int_regs.return_registers([r0, r1, r6, s0, s1, s2])
    return lines


# ── envcfg (menvcfg/senvcfg) setup helper ──────────────────────────────────


def enable_envcfg_cbo_sse(regs: Regs, csr: str = "menvcfg") -> list[str]:
    """Grant the next-lower privilege level permission to run cbo.*/
    prefetch.* and the Zicfiss shadow-stack atomics.

    Pass the *envcfg CSR that actually gates the mode the probes run in:
    - "menvcfg" when the probes run in S-mode with no lower level to cascade
      through (SmnpmS, and M-mode-only Smmpm doesn't need this at all).
    - "senvcfg" when the probes run in U-mode; the caller is responsible for
      first cascading the same fields through menvcfg down to senvcfg
      (Ssnpm).
    """
    cbo_fields = (0b11 << _ENVCFG_CBIE_SHIFT) | (1 << _ENVCFG_CBCFE_SHIFT) | (1 << _ENVCFG_CBZE_SHIFT) | _ENVCFG_SSE_BIT
    return [
        f"# {csr}: let the probes run cbo.*/prefetch.* (CBIE=11, CBCFE=1, CBZE=1)",
        "# and the Zicfiss shadow-stack atomics (SSE=1)",
        f"LI(x{regs.tmp}, {hex(cbo_fields)})",
        f"csrs {csr}, x{regs.tmp}",
    ]


def enable_cascaded_envcfg_cbo_sse(regs: Regs) -> list[str]:
    """Grant U-mode permission to run cbo.*/prefetch.* and the Zicfiss
    shadow-stack atomics, cascading the grant through menvcfg down to senvcfg.
    Used when the probes run in U-mode under an M-mode-configured PMM
    ( SmnpmU)
    """
    cbo_fields = (0b11 << _ENVCFG_CBIE_SHIFT) | (1 << _ENVCFG_CBCFE_SHIFT) | (1 << _ENVCFG_CBZE_SHIFT) | _ENVCFG_SSE_BIT
    return [
        "# Let U-mode run cbo.*/prefetch.* (CBIE=11, CBCFE=1, CBZE=1) and the Zicfiss",
        "# shadow-stack atomics (SSE=1). menvcfg gates senvcfg, so both are written.",
        f"LI(x{regs.tmp}, {hex(_ENVCFG_SSE_BIT)})",
        f"csrs menvcfg, x{regs.tmp}",
        f"LI(x{regs.tmp}, {hex(cbo_fields)})",
        f"csrs senvcfg, x{regs.tmp}",
    ]


# ── Page-table helpers (ported verbatim, previously missing from ZpmCommon) ─


def _pte_chain_asm(mode: str, va: int, leaf_label: str, leaf_perms: str = _LEAF_PERMS_U) -> list[str]:
    """Walk a fresh chain from the root down to a 4 KiB leaf mapping ``va``.
    This walks root -> slvl(top-1) -> ... -> slvl0 -> leaf across multiple PTE_SETUP calls
    """
    top = LEVELS_BELOW_ROOT[mode]
    macro = f"PTE_SETUP_{mode.upper()}"
    lines = [f"# {mode.upper()}: map {hex(va)} -> {leaf_label}"]
    for level in range(top, 0, -1):
        lines.append(f"{macro}(rvtest_slvl{level - 1}_pg_tbl, ({_NONLEAF_PERMS}), {hex(va)}, LEVEL{level})")
    lines.append(f"{macro}({leaf_label}, ({leaf_perms}), {hex(va)}, LEVEL0)")
    return lines


def _nonleaf_asm(parent: str, child: str, shift: int, va_reg: str, td: TestData) -> list[str]:
    """parent[VPN(va, shift)] = child, valid but not a leaf."""
    t1, t2, t3 = td.int_regs.get_registers(3)
    lines = [
        f"srli x{t1}, {va_reg}, {shift}",
        f"andi x{t1}, x{t1}, 0x1FF",
        f"slli x{t1}, x{t1}, 3",
        f"LA(x{t2}, {parent})",
        f"add  x{t2}, x{t2}, x{t1}",
        f"LA(x{t3}, {child})",
        f"srli x{t3}, x{t3}, 12",
        f"slli x{t3}, x{t3}, 10",
        f"ori  x{t3}, x{t3}, ({_NONLEAF_PERMS})",
        f"sd   x{t3}, 0(x{t2})",
    ]
    td.int_regs.return_registers([t1, t2, t3])
    return lines


def _walk_asm(mode: str, tables: list[str], va_reg: str, td: TestData) -> list[str]:
    """Install non-leaf entries from the framework root down to tables[0]."""
    top = LEVELS_BELOW_ROOT[mode]
    shifts = [12 + 9 * k for k in range(top, 0, -1)]
    chain = ["rvtest_Sroot_pg_tbl", *tables]
    lines: list[str] = []
    for parent, child, shift in zip(chain, chain[1:], shifts):
        lines += _nonleaf_asm(parent, child, shift, va_reg, td)
    return lines


def build_finegrained_text_map_asm(mode: str, img_tables: list[str], td: TestData) -> list[str]:
    """Split the 2 MiB region containing rvtest_code_begin into 4 KiB leaves,
    granting PTE_U to:
    1. U-mode-executable text (pm_utext_begin..end)
    2. U-accessible framework data range (rvtest_data_begin..end_signature)
    3. PM data pages (pm_lo_page and pm_hi_page for non-bare modes)

    The S-mode trap handler, which lives outside that bracket in the same
    2 MiB region, is left without PTE_U so S-mode can still fetch it.
    """
    (r0,) = td.int_regs.get_registers(1)
    lines = [
        f"# {mode.upper()}: 4 KiB mapping of the test image; PTE_U on test code, framework data, and PM data pages"
    ]
    lines += [f"LA(x{r0}, rvtest_code_begin)"]
    lines += _walk_asm(mode, img_tables, f"x{r0}", td)

    r1, r6, s0, s1, s2 = td.int_regs.get_registers(5)
    lines += [
        f"LA(x{r0}, rvtest_code_begin)",
        f"srli x{r0}, x{r0}, 21",
        f"slli x{r0}, x{r0}, 21                  # x{r0} = 2 MiB-aligned base of the image",
        f"LA(x{r1}, {img_tables[-1]})",
        f"li   x{r6}, 512",
        "1:",
        f"li   x{s0}, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V)",
        # Check the U-executable text range first; bounds reloaded fresh
        # rather than held in dedicated registers (6-register budget).
        f"LA(x{s1}, pm_utext_begin)",
        f"LA(x{s2}, pm_utext_end)",
        f"sub  x{s2}, x{s2}, x{s1}                  # x{s2} = size of the U-executable text",
        f"sub  x{s1}, x{r0}, x{s1}                  # x{s1} = offset from text begin",
        f"bltu x{s1}, x{s2}, 2f                  # inside the code segment -> U-accessible",
        # Check PM data pages: pm_lo_page
        f"LA(x{s1}, pm_lo_page)",
        f"sub  x{s1}, x{r0}, x{s1}                  # x{s1} = offset from pm_lo_page",
        f"li   x{s2}, 4096                     # x{s2} = size of pm_lo_page",
        f"bltu x{s1}, x{s2}, 2f                # within pm_lo_page -> U-accessible",
    ]

    # For non-bare modes, also check pm_hi_page
    if mode != "bare":
        lines += [
            f"LA(x{s1}, pm_hi_page)",
            f"sub  x{s1}, x{r0}, x{s1}                  # x{s1} = offset from pm_hi_page",
            f"li   x{s2}, 4096                     # x{s2} = size of pm_hi_page",
            f"bltu x{s1}, x{s2}, 2f                # within pm_hi_page -> U-accessible",
        ]

    # Not in text or PM range -- check the U-accessible framework data range.
    lines += [
        f"LA(x{s1}, rvtest_data_begin)",
        f"LA(x{s2}, end_signature)",
        f"sub  x{s2}, x{s2}, x{s1}                  # x{s2} = size of the U-accessible data",
        f"sub  x{s1}, x{r0}, x{s1}                  # x{s1} = offset from data begin",
        f"bgeu x{s1}, x{s2}, 3f                  # outside the data segment -> keep U clear",
        "2:",
        f"ori  x{s0}, x{s0}, PTE_U",
        "3:",
        f"srli x{s1}, x{r0}, 12",
        f"slli x{s1}, x{s1}, 10",
        f"or   x{s1}, x{s1}, x{s0}",
        f"sd   x{s1}, 0(x{r1})",
        f"addi x{r1}, x{r1}, 8",
        f"lui  x{s1}, 1",
        f"add  x{r0}, x{r0}, x{s1}",
        f"addi x{r6}, x{r6}, -1",
        f"bnez x{r6}, 1b",
    ]
    td.int_regs.return_registers([r0, r1, r6, s0, s1, s2])
    return lines


# ── Probe Primitives ───────────────────────────────────────────────────────
# Every probe below takes an explicit `cg` (covergroup) argument. Callers
# must pass their own extension's covergroup name.


def _seed(regs: Regs) -> list[str]:
    return [f"LI(x{regs.data}, {hex(VALUE_OLD)})", f"sd x{regs.data}, 0(x{regs.base})"]


def _sentinel(regs: Regs) -> list[str]:
    return [f"LI(x{regs.chk}, {hex(SENTINEL)})"]


def _probe_load(mn: str, tid: str, td: TestData, regs: Regs, cp: str, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        td.add_testcase(tid, cp, cg),
        *_fixed(f"{mn} x{regs.chk}, 0(x{regs.a})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_store(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cp: str, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        td.add_testcase(tid, cp, cg),
        *_fixed(f"{mn} x{regs.data}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_amo(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} x{regs.chk}, x{regs.data}, (x{regs.a})"),  # capture old value
        write_sigupd(regs.chk, td),  # sigupd the AMO result
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),  # then the memory read-back
    ]


def _probe_zacas(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    """ZACAS probe: handles amocas.w/d (single registers) and amocas.q (register pairs)."""
    if mn == "amocas.q":
        dest_lo, dest_hi = regs.dest_pair, regs.tmp
        src_lo, src_hi = regs.source_pair, regs.tmp2
        return [
            *_seed(regs),
            f"sd x0, 8(x{regs.base})   # seed high dword of the 128-bit comparand",
            f"LI(x{dest_lo}, {hex(VALUE_OLD)})   # comparand.lo matches the seeded value",
            f"LI(x{dest_hi}, 0)                  # comparand.hi matches the seeded value",
            f"LI(x{src_lo}, {hex(VALUE_NEW)})",
            f"LI(x{src_hi}, {hex(VALUE_NEW)})",
            td.add_testcase(tid, CP_MASKING, cg),
            *_fixed(f"{mn} x{dest_lo}, x{src_lo}, (x{regs.a})"),
            *_fixed(f"ld x{dest_lo}, 0(x{regs.base})"),
            *_fixed(f"ld x{dest_hi}, 8(x{regs.base})"),
            write_sigupd(dest_lo, td),
            write_sigupd(dest_hi, td),
        ]

    dest_reg, src_reg = regs.chk, regs.data
    return [
        *_seed(regs),
        f"LI(x{dest_reg}, {hex(VALUE_OLD)})   # comparand matches the seeded value",
        f"LI(x{src_reg}, {hex(VALUE_NEW)})",
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} x{dest_reg}, x{src_reg}, (x{regs.a})"),
        *_fixed(f"ld x{dest_reg}, 0(x{regs.base})"),
        write_sigupd(dest_reg, td),
    ]


def _probe_fp_load(mn: str, mv: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"{mv} f{regs.fp}, x{regs.chk}   # poison the FP destination",
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} f{regs.fp}, 0(x{regs.a})"),
        write_sigupd(regs.fp, td, "float"),
    ]


def _probe_fp_store(mn: str, readback: str, mv: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        f"{mv} f{regs.fp}, x{regs.data}",
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} f{regs.fp}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_load_cl(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        td.add_testcase(tid, CP_MASKING, cg),
        f"{mn} x{regs.chk}, 0(x{regs.a})",
        write_sigupd(regs.chk, td),
    ]


def _probe_c_store_cs(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        td.add_testcase(tid, CP_MASKING, cg),
        f"{mn} x{regs.data}, 0(x{regs.a})",
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_load_sp(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        f"{mn} x{regs.chk}, 0(sp)",
        f"mv sp, x{regs.tmp}",
        write_sigupd(regs.chk, td),
    ]


def _probe_c_store_sp(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        f"{mn} x{regs.data}, 0(sp)",
        f"mv sp, x{regs.tmp}",
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_cd_load_sp(tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"fmv.d.x f{regs.fp_c}, x{regs.chk}",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        f"c.fldsp f{regs.fp_c}, 0(sp)",
        f"mv sp, x{regs.tmp}",
        write_sigupd(regs.fp_c, td, "float"),
    ]


def _probe_cd_store_sp(tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        f"fmv.d.x f{regs.fp_c}, x{regs.data}",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        f"c.fsdsp f{regs.fp_c}, 0(sp)",
        f"mv sp, x{regs.tmp}",
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_cbo(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} 0(x{regs.a})"),
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _vset(sew: int, regs: Regs) -> list[str]:
    return [
        "csrw vstart, x0",
        f"vsetivli x{regs.tmp}, 2, e{sew}, m1, ta, ma",
        "vmv.v.i v4, 0   # zero index vector: indexed probes address the base itself",
    ]


def _probe_vec_load(mn: str, sew: int, template: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        *_fixed_block(
            [
                *_vset(sew, regs),
                f"vmv.v.x v2, x{regs.chk}   # poison the destination vector",
                td.add_testcase(tid, CP_MASKING, cg),
                template.format(a=regs.a),
                f"vmv.x.s x{regs.chk}, v2",
                "csrw vstart, x0",
            ]
        ),
        write_sigupd(regs.chk, td),
    ]


def _probe_vec_store(
    mn: str, sew: int, template: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str
) -> list[str]:
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        *_fixed_block(
            [
                *_vset(sew, regs),
                f"vmv.v.x v2, x{regs.data}",
                td.add_testcase(tid, CP_MASKING, cg),
                template.format(a=regs.a),
                "csrw vstart, x0",
            ]
        ),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_zicfiss(mn: str, readback: str, funct3: int, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    """Zicfiss shadow-stack AMO through a tagged pointer (kept for parity;
    ZICFISS_AMOS is currently empty across all four extensions, TODO : Add them"""
    return [
        *_seed(regs),
        f"LI(x{regs.data}, {hex(VALUE_NEW)})",
        *_sentinel(regs),
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(
            f".insn r 0x2f, {funct3:#x}, 0x24, x{regs.chk}, x{regs.a}, x{regs.data}"
            f"   # {mn} x{regs.chk}, x{regs.data}, (x{regs.a})"
        ),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


# ── Mode-specific address loading helpers ──────────────────────────────────


def _load_base(mode: str, region: str, regs: Regs) -> list[str]:
    if region == "hi":
        return [
            f"# upper-half VA base: masking must sign extend to reproduce {hex(HIGH_VA[mode])}",
            f"LI(x{regs.base}, {hex(HIGH_VA[mode])})",
        ]
    return [f"LA(x{regs.base}, pm_lo_page)"]


def _tag_address(upper: int, regs: Regs, byte_offset: int = 0) -> list[str]:
    lines = [
        f"# tagged pointer: bits 63:48 = 0x{upper:04X}",
        f"LI(x{regs.tmp}, {hex(upper << 48)})",
        f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
    ]
    if byte_offset:
        lines.append(f"addi x{regs.a}, x{regs.a}, {byte_offset}   # force a misaligned effective address")
    return lines


# ── Common Pass Implementations ────────────────────────────────────────────


def pass_a_all_instructions(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    lines = []
    for upper in UPPER_PATTERNS:
        lines.append(comment_banner(f"{prefix} {CP_MASKING}: tag 0x{upper:04X} -- full instruction sweep"))
        lines += [f"LI(x{regs.tmp}, {hex(upper << 48)})", f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]

        for mn in READS:
            lines += _probe_load(mn, _tid(prefix, upper, mn), td, regs, CP_MASKING, cg)
        for mn, rb in WRITES:
            lines += _probe_store(mn, rb, _tid(prefix, upper, mn), td, regs, CP_MASKING, cg)

        lines.append("#ifdef ZAAMO_SUPPORTED")
        for mn, rb in RV64A_AMOS:
            lines += _probe_amo(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#ifdef ZABHA_SUPPORTED")
        for mn, rb in ZABHA_AMOS:
            lines += _probe_amo(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#endif // ZABHA_SUPPORTED")
        lines.append("#ifdef ZACAS_SUPPORTED")
        for mn in ZACAS_AMOS:
            lines += _probe_zacas(mn, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#endif // ZACAS_SUPPORTED")
        lines.append("#endif // ZAAMO_SUPPORTED")

        for mn, guard, mv in FP_READS:
            lines.append(f"#ifdef {guard}")
            lines += _probe_fp_load(mn, mv, _tid(prefix, upper, mn), td, regs, cg)
            lines.append(f"#endif // {guard}")
        for mn, rb, guard, mv in FP_WRITES:
            lines.append(f"#ifdef {guard}")
            lines += _probe_fp_store(mn, rb, mv, _tid(prefix, upper, mn), td, regs, cg)
            lines.append(f"#endif // {guard}")

        lines.append("#ifdef ZCA_SUPPORTED")
        for mn in ZCA_READS_CL:
            lines += _probe_c_load_cl(mn, _tid(prefix, upper, mn), td, regs, cg)
        for mn, rb in ZCA_WRITES_CS:
            lines += _probe_c_store_cs(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        for mn in ZCA_READS_SP:
            lines += _probe_c_load_sp(mn, _tid(prefix, upper, mn), td, regs, cg)
        for mn, rb in ZCA_WRITES_SP:
            lines += _probe_c_store_sp(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#ifdef ZCD_SUPPORTED")
        lines += _probe_cd_load_sp(_tid(prefix, upper, "c.fldsp"), td, regs, cg)
        lines += _probe_cd_store_sp(_tid(prefix, upper, "c.fsdsp"), td, regs, cg)
        lines.append("#endif // ZCD_SUPPORTED")
        lines.append("#endif // ZCA_SUPPORTED")

        lines.append("#ifdef ZICFISS_SUPPORTED")
        for mn, rb, f3 in ZICFISS_AMOS:
            lines += _probe_zicfiss(mn, rb, f3, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#endif // ZICFISS_SUPPORTED")

        lines.append("#ifdef ZICBOZ_SUPPORTED")
        lines += _probe_cbo("cbo.zero", _tid(prefix, upper, "cbo.zero"), td, regs, cg)
        lines.append("#endif // ZICBOZ_SUPPORTED")

        lines.append("#ifdef ZICBOM_SUPPORTED")
        for mn in ZICBOM_OPS:
            lines += _probe_cbo(mn, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#endif // ZICBOM_SUPPORTED")

        lines.append("#ifdef ZICBOP_SUPPORTED")
        for mn in ZICBOP_OPS:
            lines += _probe_cbo(mn, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#endif // ZICBOP_SUPPORTED")

        lines.append("#ifdef ZVL32B_SUPPORTED")
        for mn, sew, template in VEC_READS:
            lines += _probe_vec_load(mn, sew, template, _tid(prefix, upper, mn), td, regs, cg)
        for mn, sew, template, rb in VEC_WRITES:
            lines += _probe_vec_store(mn, sew, template, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines.append("#endif // ZVL32B_SUPPORTED")
    return lines


def pass_c_misaligned(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    lines = [comment_banner(f"{prefix}: misaligned word accesses through a tagged pointer")]
    for upper in UPPER_PATTERNS:
        lines += [
            f"LI(x{regs.tmp}, {hex(upper << 48)})",
            f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
            f"addi x{regs.a}, x{regs.a}, 1   # force a misaligned effective address",
        ]
        lines += _probe_load("lw", _tid(f"{prefix}_mis", upper, "lw"), td, regs, CP_MISALIGN, cg)
        lines += _probe_store("sw", "lw", _tid(f"{prefix}_mis", upper, "sw"), td, regs, CP_MISALIGN, cg)
    return lines


def set_mxr(enable: bool, tmp: int, status_csr: str = "sstatus") -> list[str]:
    """MXR gates pointer masking off entirely when set in priv modes below M"""
    op = "csrs" if enable else "csrc"
    return [f"# {status_csr}.MXR = {int(enable)}", f"LI(x{tmp}, {hex(_MSTATUS_MXR)})", f"{op} {status_csr}, x{tmp}"]


def pass_d_mxr(
    cfg: object | None,
    prefix: str,
    td: TestData,
    regs: Regs,
    cg: str,
    goto_target_mode: str = "RVTEST_GOTO_LOWER_MODE Umode",
    status_csr: str = "sstatus",
) -> list[str]:
    """sw/lw with MXR set. MXR suppresses masking, so tagged pointers must fault."""
    lines = [comment_banner(f"{prefix}: {status_csr}.MXR=1 suppresses pointer masking")]
    lines += ["RVTEST_GOTO_MMODE", *set_mxr(True, regs.tmp, status_csr)]
    if goto_target_mode:
        lines.append(goto_target_mode)
    lines += [f"LA(x{regs.base}, pm_lo_page)"]
    for upper in UPPER_PATTERNS:
        lines += [f"LI(x{regs.tmp}, {hex(upper << 48)})", f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]
        lines += _probe_load("lw", _tid(f"{prefix}_mxr", upper, "lw"), td, regs, CP_MXR, cg)
        lines += _probe_store("sw", "lw", _tid(f"{prefix}_mxr", upper, "sw"), td, regs, CP_MXR, cg)
    return lines


def pass_e_jalr(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str, mxr: int = 0) -> list[str]:
    lines = [comment_banner(f"{prefix}: JALR through a tagged pointer, MXR={mxr} (fetch is never masked)")]
    lines.append(f"LA(x{regs.base}, pm_jalr_pad)")
    for upper in UPPER_PATTERNS:
        lines += [f"LI(x{regs.tmp}, {hex(upper << 48)})", f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]
        lines += [
            f"li x{regs.chk}, 0   # the pad sets this to 1 if the fetch succeeded",
            td.add_testcase(_tid(f"{prefix}_mxr{mxr}", upper, "jalr"), CP_JALR, cg),
            *_fixed(f"jalr ra, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
    lines += [f"LA(x{regs.base}, pm_lo_page)"]
    return lines


def pass_f_fault_address(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    lines = [
        comment_banner(f"{prefix}: masked address resolves to the model's access-fault address"),
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        f"LI(x{regs.base}, RVMODEL_ACCESS_FAULT_ADDRESS)",
    ]
    for upper in UPPER_PATTERNS:
        lines += [
            f"LI(x{regs.tmp}, {hex(upper << 48)})",
            f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
            *_sentinel(regs),
            td.add_testcase(_tid(f"{prefix}_flt", upper, "lw"), CP_FAULT, cg),
            *_fixed(f"lw x{regs.chk}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
            f"LI(x{regs.data}, {hex(VALUE_NEW)})",
            *_sentinel(regs),
            td.add_testcase(_tid(f"{prefix}_flt", upper, "sw"), CP_FAULT, cg),
            *_fixed(f"sw x{regs.data}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
    lines += ["#endif // RVMODEL_ACCESS_FAULT_ADDRESS", f"LA(x{regs.base}, pm_lo_page)"]
    return lines


def pass_b_sign_extension(cfg: object | None, prefix: str, mode: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    """ld/sd against an upper-half VA: only sign extension reproduces the base.

    For Sv39/Sv48/Sv57 modes where translation applies sign-extension instead
    of zero-extension to masked bits. Shared between Ssnpm and SmnpmS.
    """
    lines = [comment_banner(f"{prefix}: upper-half VA -- masking must sign extend, not zero extend")]
    lines += _load_base(mode, "hi", regs)
    for upper in UPPER_PATTERNS:
        lines += _tag_address(upper, regs)
        lines += _probe_load("ld", _tid(f"{prefix}_hi", upper, "ld"), td, regs, CP_MASKING, cg)
        lines += _probe_store("sd", "ld", _tid(f"{prefix}_hi", upper, "sd"), td, regs, CP_MASKING, cg)
    lines += _load_base(mode, "lo", regs)
    return lines


def pass_clear_on_xlen_change(
    cfg: object | None,
    prefix: str,
    td: TestData,
    regs: Regs,
    *,
    cp: str,
    cg: str,
    pmm_csr: str,
    pmm_shift: int,
    status_csr: str,
    status_shift: int,
    rv32_val: int = 0b01,
    rv64_val: int = 0b10,
    ifdef_guard: str | None = None,
) -> list[str]:
    """Setting status_csr's 2-bit field to 01 (RV32) must clear pmm_csr.PMM to 00.
    Generalizes Ssnpm's, SmnpmU's UXL-clear pass and SmnpmS's SXL-clear pass.

    ifdef_guard names the UDB define (UDB_UXLEN_32 / UDB_SXLEN_32) that says the mode
    can actually be switched to RV32; on a fixed-XLEN-64 config the write is a WARL
    no-op and the pass is skipped (the matching coverpoint is guarded the same way).
    """
    lines = [""]
    if ifdef_guard:
        lines.append(f"#ifdef {ifdef_guard}")
    lines += [
        comment_banner(f"{prefix}: {status_csr} field=01 must clear {pmm_csr}.PMM"),
        "RVTEST_GOTO_MMODE",
        "",
        f"csrr x{regs.chk}, {pmm_csr}",
        f"srli x{regs.chk}, x{regs.chk}, {pmm_shift}",
        f"andi x{regs.chk}, x{regs.chk}, 0x3",
        td.add_testcase(f"{prefix}_before", cp, cg),
        write_sigupd(regs.chk, td),
        "",
    ]
    mask = 0b11 << status_shift
    lines += [
        f"LI(x{regs.tmp}, {hex(mask)})",
        f"csrc {status_csr}, x{regs.tmp}",
        f"LI(x{regs.tmp}, {hex(rv32_val << status_shift)})",
        f"csrs {status_csr}, x{regs.tmp}",
        "",
    ]
    lines += [
        f"csrr x{regs.chk}, {pmm_csr}",
        f"srli x{regs.chk}, x{regs.chk}, {pmm_shift}",
        f"andi x{regs.chk}, x{regs.chk}, 0x3",
        td.add_testcase(f"{prefix}_after", cp, cg),
        write_sigupd(regs.chk, td),
        "",
    ]
    lines += [
        f"LI(x{regs.tmp}, {hex(mask)})",
        f"csrc {status_csr}, x{regs.tmp}",
        f"LI(x{regs.tmp}, {hex(rv64_val << status_shift)})",
        f"csrs {status_csr}, x{regs.tmp}",
    ]
    if ifdef_guard:
        lines.append(f"#endif // {ifdef_guard}")
    return lines


# ── MPRV Nested Loop Pass (Smmpm-specific) ────────────────────────────────


def _mprv_lw_sw_probe(
    mpp: int,
    cp: str,
    prefix: str,
    td: TestData,
    regs: Regs,
    cg: str,
) -> list[str]:
    """lw/sw through a pointer with MPRV=1/MPP=mpp, swept over
    _MPRV_UPPER_PATTERNS.
    MPRV is left set on return -- callers park each iteration's cursor at
    pm_lo_page and MPRV=0 is restored here once the sweep is done.
    """
    lines = []
    for upper in _MPRV_UPPER_PATTERNS:
        lines += [
            f"LI(x{regs.tmp}, {hex(upper << 48)})",
            f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
        ]
        tid_load = _tid(prefix, upper, "lw")
        lines += [
            *_seed(regs),
            *_sentinel(regs),
            *set_mprv(True, mpp, regs.tmp),
            td.add_testcase(tid_load, cp, cg),
            *_fixed(f"lw x{regs.chk}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
        tid_store = _tid(prefix, upper, "sw")
        lines += [
            *_seed(regs),
            f"LI(x{regs.data}, {hex(VALUE_NEW)})",
            *set_mprv(True, mpp, regs.tmp),
            td.add_testcase(tid_store, cp, cg),
            *_fixed(f"sw x{regs.data}, 0(x{regs.a})"),
            *set_mprv(True, mpp, regs.tmp),
            *_fixed(f"lw x{regs.chk}, 0(x{regs.base})"),
            write_sigupd(regs.chk, td),
        ]
    lines += set_mprv(False, 0, regs.tmp)
    return lines


def _mprv_satp_loop(
    mpp: int,
    mpp_name: str,
    cp: str,
    mxr_val: int,
    mseccfg_pmm: int,
    menvcfg_pmm: int,
    pmm_shift: int,
    td: TestData,
    regs: Regs,
    cg: str,
) -> list[str]:
    """Shared between MPP=U (S_SUPPORTED) and MPP=S,
    which loop identically and share the same coverpoint
    (cp_pm_mprv_mpp_u_s). The U-accessible data map is built once by the
    caller before entering the mxr/pmm loops.
    """
    lines = []
    for senvcfg_pmm, senvcfg_pmlen, _ in PMM_CONFIGS:
        lines += set_pmm_field("senvcfg", pmm_shift, senvcfg_pmm, senvcfg_pmlen, regs.tmp)

        for satp_mode in ["bare", "sv39"]:
            if satp_mode != "bare":
                lines += [
                    "SATP_SETUP_RV64(sv39)",
                    "sfence.vma",
                ]
            lines += [f"LA(x{regs.base}, pm_lo_page)"]
            prefix = (
                f"mprv_mxr{mxr_val}_mseccfg{mseccfg_pmm:02b}_"
                f"menvcfg{menvcfg_pmm:02b}_senvcfg{senvcfg_pmm:02b}_"
                f"{satp_mode}_{mpp_name}"
            )
            lines += _mprv_lw_sw_probe(mpp, cp, prefix, td, regs, cg)
            if satp_mode != "bare":
                lines += [
                    "RVTEST_GOTO_MMODE",
                    "csrwi satp, 0",
                    "sfence.vma",
                ]
    return lines


def pass_i_mprv_mxr_pmm_loop(
    td: TestData,
    regs: Regs,
    cg: str,
    sv39_data_map: list[str],
    pmm_shift: int = _PMM_FIELD_SHIFT,
) -> list[str]:
    """MPRV=1 test with nested loops over MXR, mseccfg.PMM, menvcfg.PMM, senvcfg.PMM, MPP, satp.MODE, upper patterns.

    Uses only Bare and Sv39 modes (not Sv48/Sv57).
    senvcfg.PMM is only programmed when S_SUPPORTED (CSR does not exist otherwise).
    MPP=M: no SATP at all (satp is an S-mode register); no S-mode required.
    MPP=U: no S-mode guard required; SATP used only when S_SUPPORTED. Under
    sv39, pm_lo_page's default PTE has no PTE_U, so the MPP=U probes remap
    the data range with build_data_only_u_map_asm before enabling SATP --
    without this, every mppu/sv39 access would page-fault regardless of
    tag/PMLEN and the masking behavior would never actually be exercised.
    MPP=S: guarded by S_SUPPORTED; loops satp.MODE in {Bare, Sv39}. No remap
    needed here -- S-mode can access pm_lo_page under the framework's
    default identity map without PTE_U, same as SmnpmS.

    mstatus.MPRV, .MXR and .SUM are all explicitly cleared at the end rather
    than snapshotted/restored
    """
    lines = [
        comment_banner(
            "Smmpm MPRV: pointer masking with MPRV=1 uses effective MPP's PMM settings",
            "MPRV=1 causes effective privilege = MPP, so mseccfg.PMM is ignored."
            "MPP=M: no SATP. MPP=U: no S guard. MPP=S and senvcfg: S_SUPPORTED only.",
        ),
        "RVTEST_GOTO_MMODE",
        "",
    ]

    # ---- Build the U-accessible data map ONCE (tables never change) ----
    lines += [
        "# Build the U-accessible data map once; the page tables never change",
        *sv39_data_map,
        "sfence.vma",
    ]

    # Enable SUM so we can access user-space pages from S-mode (only when S exists)
    lines.append("#ifdef S_SUPPORTED")
    lines += set_sum(True, regs.tmp)
    lines.append("#endif // S_SUPPORTED")

    # Loop over MXR settings (only meaningful when S-mode exists)
    for mxr_val in [0, 1]:
        lines.append("#ifdef S_SUPPORTED")
        lines += set_mxr(mxr_val != 0, regs.tmp, "mstatus")
        lines.append("#endif // S_SUPPORTED")

        # Loop over mseccfg.PMM (M-mode setting)
        for mseccfg_pmm, mseccfg_pmlen, _ in PMM_CONFIGS:
            lines += set_pmm_field("mseccfg", pmm_shift, mseccfg_pmm, mseccfg_pmlen, regs.tmp)

            # Loop over menvcfg.PMM
            for menvcfg_pmm, menvcfg_pmlen, _ in PMM_CONFIGS:
                lines += set_pmm_field("menvcfg", pmm_shift, menvcfg_pmm, menvcfg_pmlen, regs.tmp)

                # ============================================================
                # MPP=M: always runs, no SATP at all (satp is S-mode CSR)
                # ============================================================
                lines += [f"LA(x{regs.base}, pm_lo_page)"]
                prefix_m = f"mprv_mxr{mxr_val}_mseccfg{mseccfg_pmm:02b}_menvcfg{menvcfg_pmm:02b}_senvcfg00_nosatp_mppm"
                lines += _mprv_lw_sw_probe(_MPP_M, "cp_pm_mprv_mpp_m", prefix_m, td, regs, cg)

                # ============================================================
                # MPP=U: no S_SUPPORTED guard on the MPP itself.
                # senvcfg only exists / is programmed when S_SUPPORTED.
                # SATP only when S_SUPPORTED. Map was already built once above.
                # ============================================================
                lines.append("#ifdef S_SUPPORTED")
                lines += _mprv_satp_loop(
                    _MPP_U, "mppu", "cp_pm_mprv_mpp_u_s", mxr_val, mseccfg_pmm, menvcfg_pmm, pmm_shift, td, regs, cg
                )
                lines.append("#endif // S_SUPPORTED")

                # MPP=U when S is NOT supported: no senvcfg, no SATP
                lines.append("#ifndef S_SUPPORTED")
                lines += [f"LA(x{regs.base}, pm_lo_page)"]
                prefix_u_nos = (
                    f"mprv_mxr{mxr_val}_mseccfg{mseccfg_pmm:02b}_menvcfg{menvcfg_pmm:02b}_senvcfg00_nosatp_mppu"
                )
                lines += _mprv_lw_sw_probe(_MPP_U, "cp_pm_mprv_mpp_u_no_s", prefix_u_nos, td, regs, cg)
                lines.append("#endif // !S_SUPPORTED")

                # ============================================================
                # MPP=S: only when S_SUPPORTED; SATP in {Bare, Sv39}
                # ============================================================
                lines.append("#ifdef S_SUPPORTED")
                lines += _mprv_satp_loop(
                    _MPP_S, "mpps", "cp_pm_mprv_mpp_u_s", mxr_val, mseccfg_pmm, menvcfg_pmm, pmm_shift, td, regs, cg
                )
                lines.append("#endif // S_SUPPORTED")

    lines += set_pmm_field("mseccfg", pmm_shift, 0b00, 0, regs.tmp)
    lines += set_pmm_field("menvcfg", pmm_shift, 0b00, 0, regs.tmp)
    lines.append("#ifdef S_SUPPORTED")
    lines += set_pmm_field("senvcfg", pmm_shift, 0b00, 0, regs.tmp)
    lines += set_mxr(False, regs.tmp, "mstatus")
    lines += set_sum(False, regs.tmp)
    lines.append("#endif // S_SUPPORTED")
    lines += set_mprv(False, 0, regs.tmp)
    lines += [
        "# restore mstatus.MPP = M; set_mprv(False, ...) only clears MPRV",
        f"LI(x{regs.tmp}, {hex(0b11 << _MSTATUS_MPP_SHIFT)})",
        f"csrs mstatus, x{regs.tmp}",
    ]

    return lines
