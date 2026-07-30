##################################
# priv/extensions/Ssnpm.py
#
# Ssnpm privileged extension test generator.
# Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssnpm S-mode pointer-masking test generator."""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_UPPER_PATTERNS: list[int] = [
    0x0000,  # baseline, masking is a no-op
    0x0001,  # bit 48 set
    0x0100,  # bit 56 set
    0x0200,  # bit 57 set
    0x8000,  # bit 63 set
    0xFFFF,  # all 16 bits set
    0xFE00,  # bits 63:57 set -- exactly the PMLEN=7 window
    0xFF00,  # bits 63:56 set
]

# (pmm value, pmlen, label)
_PMM_CONFIGS: list[tuple[int, int, str]] = [
    (0b00, 0, "pmm00_disabled"),
    (0b10, 7, "pmm10_pmlen7"),
    (0b11, 16, "pmm11_pmlen16"),
]

_SENVCFG_PMM_SHIFT: int = 32

_SATP_MODES: list[str] = ["bare"]  # , "sv57" , "sv48", "sv57"]

_SATP_GUARD: dict[str, str | None] = {
    "bare": None,
    "sv39": "#ifdef SV39_SUPPORTED",
    "sv48": "#ifdef SV48_SUPPORTED",
    "sv57": "#ifdef SV57_SUPPORTED",
}

_CANONICAL_ONES_VA: dict[str, int] = {
    "sv39": 0xFFFFFFC000000000,
    "sv48": 0xFFFF800000000000,
    "sv57": 0xFF00000000000000,
}

VALUE_OLD: int = 0xABCD_1234_ABCD_1234  # pre-loaded in scratch
VALUE_DIFF: int = 0xCAFE_BABE_CAFE_BABE  # pre-loaded in other_page
VALUE_NEW: int = 0xA5A5_A5A5_A5A5_A5A5  # written by store tests

PTE_V, PTE_R, PTE_W, PTE_X, PTE_U, PTE_A, PTE_D = 0x01, 0x02, 0x04, 0x08, 0x10, 0x40, 0x80
_NONLEAF_PERMS = "PTE_V"  # non-leaf PTEs must have ONLY V set
_LEAF_PERMS = "PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V"  # RW, U-accessible, no X needed


_READS: list[str] = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]
_WRITES: list[tuple[str, str]] = [("sb", "lbu"), ("sh", "lhu"), ("sw", "lw"), ("sd", "ld")]

# perform AMO at A (Treated as WRITEs), read back from scratch.
_RV64A_AMOS: list[tuple[str, str]] = [
    ("amoswap.w", "lw"),
    ("amoswap.d", "ld"),
    ("amoadd.w", "lw"),
    ("amoadd.d", "ld"),
    ("amoxor.w", "lw"),
    ("amoxor.d", "ld"),
    ("amoand.w", "lw"),
    ("amoand.d", "ld"),
    ("amoor.w", "lw"),
    ("amoor.d", "ld"),
    ("amomin.w", "lw"),
    ("amomin.d", "ld"),
    ("amomax.w", "lw"),
    ("amomax.d", "ld"),
    ("amominu.w", "lw"),
    ("amominu.d", "ld"),
    ("amomaxu.w", "lw"),
    ("amomaxu.d", "ld"),
]

_ZABHA_AMOS: list[tuple[str, str]] = [
    ("amoswap.b", "lbu"),
    ("amoswap.h", "lhu"),
    ("amoadd.b", "lbu"),
    ("amoadd.h", "lhu"),
    ("amoxor.b", "lbu"),
    ("amoxor.h", "lhu"),
    ("amoand.b", "lbu"),
    ("amoand.h", "lhu"),
    ("amoor.b", "lbu"),
    ("amoor.h", "lhu"),
    ("amomin.b", "lbu"),
    ("amomin.h", "lhu"),
    ("amomax.b", "lbu"),
    ("amomax.h", "lhu"),
    ("amominu.b", "lbu"),
    ("amominu.h", "lhu"),
    ("amomaxu.b", "lbu"),
    ("amomaxu.h", "lhu"),
]

# Zacas: amocas.w/d for RV64. rd and rs2 must each be an even-numbered
# NOTE : amocas.q is flagged as illegal instruction in the current RV64 generator, so it is NOT included here.
_ZACAS_AMOS: list[str] = ["amocas.w", "amocas.d"]

_FP_READS: list[tuple[str, str]] = [
    ("flw", "#ifdef F_SUPPORTED"),
    ("fld", "#ifdef D_SUPPORTED"),
    # ("flq", "#ifdef Q_SUPPORTED"),   Q not supported in the current RV64 generator, so it is NOT included here.
]

_FP_OPS: list[tuple[str, str, str]] = [
    ("fsw", "flw", "#ifdef F_SUPPORTED"),
    ("fsd", "fld", "#ifdef D_SUPPORTED"),
    # ("fsq", "flq", "#ifdef Q_SUPPORTED"),
]

_FP_MVX: dict[str, tuple[str, str]] = {
    "fsw": ("fmv.w.x", "fmv.x.w"),
    "fsd": ("fmv.d.x", "fmv.x.d"),
}

# Zca: CL/CS-format loads/stores. rd'/rs1'/rs2' are restricted to x8-x15
# reg_range=list(range(8, 16))).
_ZCA_READS_CL: list[str] = ["c.lw", "c.ld"]
_ZCA_WRITES_CS: list[tuple[str, str]] = [("c.sw", "lw"), ("c.sd", "ld")]

_ZCA_READS_SP: list[str] = ["c.lwsp", "c.ldsp"]
_ZCA_WRITES_SP: list[tuple[str, str]] = [("c.swsp", "lw"), ("c.sdsp", "ld")]

_ZCD_READ_SP: str = "c.fldsp"
_ZCD_WRITE_SP: str = "c.fsdsp"

_ZICBOZ_OP: str = "cbo.zero"
_ZICBOM_OPS: list[str] = ["cbo.clean", "cbo.flush"]
_ZICBOM_INVAL_OP: str = "cbo.inval"
_ZICBOP_OPS: list[str] = ["prefetch.r", "prefetch.w", "prefetch.i"]


#   SENVCFG_CBIE  = 0x30 -> bits [5:4] (00=illegal, 01=inval acts as flush,
#                            10=reserved, 11=normal invalidate)
#   SENVCFG_CBCFE = 0x40 -> bit  [6]   (0=clean/flush illegal in U-mode, 1=flush/clean permitted)
#   SENVCFG_CBZE  = 0x80 -> bit  [7]   (0=cbo.zero illegal in U-mode, 1=cbo.zero permitted)
_SENVCFG_CBIE_SHIFT: int = 4
_SENVCFG_CBCFE_SHIFT: int = 6
_SENVCFG_CBZE_SHIFT: int = 7

covergroup = "Ssnpm_cg"
coverpoint = "cp_pmlen_masking"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _arch_guard(instr: str, exts: list[str]) -> list[str]:
    """Bracket a single instruction with `.option arch, +ext...` (no-op if exts empty)."""
    if not exts:
        return [instr]
    adds = ", ".join(f"+{e.strip().lower()}" for e in exts)
    return [".option push", f".option arch, {adds}", instr, ".option pop"]


def _amo_ext(amo_mn: str) -> str:
    return "zabha" if amo_mn.endswith((".b", ".h")) else "zaamo"


def _li(reg: int, val: int) -> str:
    """LI() accepts arbitrarily large hex literals directly"""
    return f"LI(x{reg}, {hex(val)})"


def _generate_data_section() -> list[str]:
    """
    Declare the two pages and the non-root Sv page tables.
    rvtest_Sroot_pg_tbl is declared automatically by RVTEST_DATA_END whenever
    S_SUPPORTED is defined, so it is NOT declared here.

    rvtest_slvl0_pg_tbl / rvtest_slvl1_pg_tbl / rvtest_slvl2_pg_tbl /
    rvtest_slvl3_pg_tbl are NOT auto-declared by the framework , so we set it here.
      Sv39 walks root -> slvl1 -> slvl0 -> leaf   (uses slvl0, slvl1)
      Sv48 walks root -> slvl2 -> slvl1 -> slvl0 -> leaf (uses slvl0..slvl2)
      Sv57 walks root -> slvl3 -> slvl2 -> slvl1 -> slvl0 -> leaf (all four)
    """
    return [
        "",
        ".pushsection .data",
        ".p2align 12",
        f"pm_scratch:     .dword {hex(VALUE_OLD)}",
        "                .zero 4088",
        ".p2align 12",
        f"pm_other_page:  .dword {hex(VALUE_DIFF)}",
        "                .zero 4088",
        "#if defined(SV39_SUPPORTED) || defined(SV48_SUPPORTED) || defined(SV57_SUPPORTED)",
        ".p2align 12",
        "rvtest_slvl0_pg_tbl: .zero 4096   # LEVEL0 leaf table, used by all 3 modes",
        ".p2align 12",
        "rvtest_slvl1_pg_tbl: .zero 4096   # LEVEL1 table, used by all 3 modes",
        "#if defined(SV48_SUPPORTED) || defined(SV57_SUPPORTED)",
        ".p2align 12",
        "rvtest_slvl2_pg_tbl: .zero 4096   # LEVEL2 table, used by Sv48 and Sv57 only",
        "#ifdef SV57_SUPPORTED",
        ".p2align 12",
        "rvtest_slvl3_pg_tbl: .zero 4096   # LEVEL3 table, used by Sv57 only",
        "#endif  // SV57_SUPPORTED",
        "#endif  // SV48_SUPPORTED || SV57_SUPPORTED",
        "#endif  // SV39_SUPPORTED || SV48_SUPPORTED || SV57_SUPPORTED",
        ".popsection",
        "",
    ]


def _pte_chain(mode: str, va: int | str, leaf_label: str, leaf_perms: str) -> list[str]:
    va_str = hex(va) if isinstance(va, int) else va

    setup: dict[str, list[str]] = {
        "sv39": [
            f"PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL2)  # root -> slvl1",
            f"PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL1)  # slvl1 -> slvl0",
            f"PTE_SETUP_SV39({leaf_label}, ({leaf_perms}), {va_str}, LEVEL0)  # slvl0 -> {leaf_label}",
        ],
        "sv48": [
            f"PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL3)  # root -> slvl2",
            f"PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL2)  # slvl2 -> slvl1",
            f"PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL1)  # slvl1 -> slvl0",
            f"PTE_SETUP_SV48({leaf_label}, ({leaf_perms}), {va_str}, LEVEL0)  # slvl0 -> {leaf_label}",
        ],
        "sv57": [
            f"PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL4)  # root -> slvl3",
            f"PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL3)  # slvl3 -> slvl2",
            f"PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL2)  # slvl2 -> slvl1",
            f"PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, ({_NONLEAF_PERMS}), {va_str}, LEVEL1)  # slvl1 -> slvl0",
            f"PTE_SETUP_SV57({leaf_label}, ({leaf_perms}), {va_str}, LEVEL0)  # slvl0 -> {leaf_label}",
        ],
    }
    return setup[mode]


def _grant_umode_access_to_boot_identity_map(mode: str) -> list[str]:
    """
    pm_scratch already lies inside the gigapage/terapage/petapage that
    rvtest_setup.h's rvtest_identity_map boot routine pre-installed as a
    LEAF entry directly in rvtest_Sroot_pg_tbl (perms 0xCF = D|A|X|W|R|V,
    no PTE_U).

    DO NOT walk a fresh PTE_SETUP_SVxx chain down from root for pm_scratch.
    Instead, OR PTE_U into the existing leaf so it stays a leaf but is
    also U-mode accessible. VPN shift must match what the boot code used
    for this mode: 30 (sv39, root=level2), 39 (sv48, root=level3),
    48 (sv57, root=level4).
    """
    shift = {"sv39": 30, "sv48": 39, "sv57": 48}[mode]
    return [
        f"# {mode.upper()}: grant U-mode access to the framework's boot-time",
        "LA(a1, rvtest_data_begin)   # any address inside the boot-mapped region",
        f"srli a1, a1, {shift}",
        "andi a1, a1, 0x1FF",
        "slli a1, a1, 3",
        "LA(a0, rvtest_Sroot_pg_tbl)",
        "add  a0, a0, a1            # a0 = &rvtest_Sroot_pg_tbl[VPN index]",
        "ld   t0, 0(a0)             # existing boot leaf PTE (RWX, no U)",
        "li   t1, PTE_U",
        "or   t0, t0, t1",
        "sd   t0, 0(a0)             # same leaf, now also U-mode accessible",
    ]


def _emit_vm_setup(mode: str) -> list[str]:
    """
    For a VM mode, wire up BOTH mappings and turn on translation:
      - identity mapping: VA == PA of pm_scratch
      - canonical "all leading 1s" mapping: VA(upper=all 1s, sign-extended) -> pm_other_page
    """
    if mode == "bare":
        return []
    lines: list[str] = [
        f"    # VM setup for {mode.upper()}: two mappings + enable translation",
        "    # (1) identity map: VA == PA of pm_scratch",
    ]
    lines += [f"    {line}" for line in _grant_umode_access_to_boot_identity_map(mode)]
    lines.append(f"    # (2) canonical ones map: VA=0x{_CANONICAL_ONES_VA[mode]:016x} -> pm_other_page")
    lines += [f"    {line}" for line in _pte_chain(mode, _CANONICAL_ONES_VA[mode], "pm_other_page", _LEAF_PERMS)]
    lines += [
        "    sfence.vma",
        f"    SATP_SETUP_RV64({mode})",
        "    sfence.vma",
    ]
    return lines


def _emit_vm_teardown(mode: str) -> list[str]:
    """Disable translation (back to Bare) before moving to the next block."""
    if mode == "bare":
        return []
    return [
        "    # Disable translation before the next satp_mode/pmm block",
        "    csrwi satp, 0",
        "    sfence.vma",
    ]


def _set_pmm(pmm_val: int, pmlen: int, tmp_reg: int) -> list[str]:
    """
    Set senvcfg.PMM = pmm_val (00=disabled, 10=PMLEN=7, 11=PMLEN=16)
    """
    mask = 0b11 << _SENVCFG_PMM_SHIFT
    field = pmm_val << _SENVCFG_PMM_SHIFT
    return [
        f"    # Set senvcfg.PMM = {pmm_val:#04b} (PMLEN={pmlen})",
        f"    {_li(tmp_reg, mask)}",
        f"    csrc senvcfg, x{tmp_reg}       # clear PMM bits [33:32]",
        f"    {_li(tmp_reg, field)}",
        f"    csrs senvcfg, x{tmp_reg}        # set PMM field",
    ]


def _enable_cbo_envcfg(tmp_reg: int) -> list[str]:
    """
    Permit cbo.zero / cbo.clean / cbo.flush / cbo.inval to execute in
    U-mode.
    """
    field = (
        (0b11 << _SENVCFG_CBIE_SHIFT)  # CBIE=11: cbo.inval executes normally
        | (0b1 << _SENVCFG_CBCFE_SHIFT)  # CBCFE=1: cbo.clean/flush permitted
        | (0b1 << _SENVCFG_CBZE_SHIFT)  # CBZE=1: cbo.zero permitted
    )
    mask = (0b11 << _SENVCFG_CBIE_SHIFT) | (0b1 << _SENVCFG_CBCFE_SHIFT) | (0b1 << _SENVCFG_CBZE_SHIFT)
    return [
        "    # Permit cbo.zero/cbo.clean/cbo.flush/cbo.inval in U-mode",
        f"    {_li(tmp_reg, mask)}",
        f"    csrc senvcfg, x{tmp_reg}        # clear CBIE/CBCFE/CBZE fields",
        f"    {_li(tmp_reg, field)}",
        f"    csrs senvcfg, x{tmp_reg}        # CBIE=11, CBCFE=1, CBZE=1",
    ]


def _build_tagged_address(upper: int, REG_BASE: int, REG_A: int, REG_TMP: int) -> list[str]:
    """REG_A = REG_BASE | (upper << 48)."""
    return [
        f"    # Build tagged address A: upper[63:48] = 0x{upper:04X}",
        f"    {_li(REG_TMP, upper << 48)}",
        f"    or    x{REG_A}, x{REG_BASE}, x{REG_TMP}",
    ]


def _reseed_scratch(REG_BASE: int, REG_DATA: int) -> list[str]:
    """Re-seed scratch with VALUE_OLD before every test sub-block"""
    return [
        "    # Reseed scratch with VALUE_OLD",
        f"    {_li(REG_DATA, VALUE_OLD)}",
        f"    sd    x{REG_DATA}, 0(x{REG_BASE})",
    ]


def _emit_read_test(
    load_mn: str, test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> list[str]:
    """
    READ test.
      masking worked  -> load hits pm_scratch    -> returns VALUE_OLD
    """
    lines = [f"    # ---- READ {load_mn} [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{load_mn} x{REG_DATA}, 0(x{REG_A})", []),
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_write_test(
    store_mn: str, load_mn: str, test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> list[str]:
    """
    WRITE test.
      1. Reseed scratch = VALUE_OLD
      2. Store VALUE_NEW to A (tagged address)
      3. Read back from scratch using REG_BASE
      masking worked -> step 2 landed on scratch -> readback = VALUE_NEW
      masking failed -> step 2 landed elsewhere   -> readback = VALUE_OLD
    """
    lines = [f"    # ---- WRITE {store_mn}/{load_mn} [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {_li(REG_DATA, VALUE_NEW)}",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{store_mn} x{REG_DATA}, 0(x{REG_A})", []),
        *_arch_guard(f"{load_mn} x{REG_DATA}, 0(x{REG_BASE})", []),
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_amo_test(
    amo_mn: str, load_mn: str, test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> list[str]:
    """
    AMO test (treated as WRITE per testplan):
      1. Reseed scratch = VALUE_OLD
      2. AMO with VALUE_NEW at tagged address A (rd=x0, old value discarded)
      3. Read back from scratch via REG_BASE
      masking worked -> AMO landed on scratch    -> readback = VALUE_NEW
      masking failed -> AMO landed on other_page -> readback = VALUE_OLD
    """
    lines = [f"    # ---- AMO {amo_mn}/{load_mn} [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {_li(REG_DATA, VALUE_NEW)}",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{amo_mn} x0, x{REG_DATA}, (x{REG_A})", [_amo_ext(amo_mn)]),
        *_arch_guard(f"{load_mn} x{REG_DATA}, 0(x{REG_BASE})", []),
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_zacas_test(
    amo_mn: str, test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_RD: int, REG_RS2: int
) -> list[str]:
    """
    amocas.w/amocas.d (RV64): operand width (32b/64b) fits within a single
    XLEN=64 register, so rd/rs2 do NOT need to be an even/odd register pair.
    That pairing rule only applies to amocas.q (128b), which is not emitted
    here (see _ZACAS_AMOS). Reuse REG_RD/REG_RS2, already reserved for this
    block, instead of allocating a fresh pair -- the priv register pool is
    too small (6 regs total after priv.py's exclusions) to spare a pair.
    """
    lines = [f"    # ---- AMO {amo_mn} (Zacas) [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_RD)
    lines += [
        f"    {_li(REG_RD, VALUE_OLD)}     # comparand: must match scratch's current value",
        f"    {_li(REG_RS2, VALUE_NEW)}    # value written on successful compare",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{amo_mn} x{REG_RD}, x{REG_RS2}, (x{REG_A})", ["zacas"]),
        f"    ld    x{REG_RD}, 0(x{REG_BASE})",
        write_sigupd(REG_RD, test_data),
    ]
    return lines


def _emit_cbo_zero_test(test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int) -> list[str]:
    """
    Zicboz WRITE test.
      masking worked -> cbo.zero's block lands on scratch    -> readback = 0
    """
    lines = [f"    # ---- WRITE cbo.zero [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"cbo.zero 0(x{REG_A})", ["zicboz"]),
        f"    ld    x{REG_DATA}, 0(x{REG_BASE})",
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_cbom_test(
    cbo_mn: str, test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> list[str]:
    """
    Zicbom WRITE test (cbo.clean / cbo.flush).
    """
    lines = [f"    # ---- WRITE {cbo_mn} [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{cbo_mn} 0(x{REG_A})", ["zicbom"]),
        f"    ld    x{REG_DATA}, 0(x{REG_BASE})",
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_cbo_inval_test(test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int) -> list[str]:
    """
    cbo.inval test. Gated on senvcfg.CBIE=11 (set by _enable_cbo_envcfg
    before U-mode entry).
    """
    lines = [f"    # ---- WRITE cbo.inval [{test_id}] (requires senvcfg.CBIE=11) ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"cbo.inval 0(x{REG_A})", ["zicbom"]),
        f"    ld    x{REG_DATA}, 0(x{REG_BASE})",
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_prefetch_test(
    pf_mn: str, test_id: str, test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> list[str]:
    """
    Zicbop test (prefetch.r / prefetch.w / prefetch.i).
    """
    lines = [f"    # ---- {pf_mn} [{test_id}] ----"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{pf_mn} 0(x{REG_A})", ["zicbop"]),
        f"    ld    x{REG_DATA}, 0(x{REG_BASE})",
        write_sigupd(REG_DATA, test_data),
    ]
    return lines


def _emit_fp_read_test(
    load_mn: str,
    test_id: str,
    lines: list[str],
    test_data: TestData,
    REG_A: int,
    REG_BASE: int,
    REG_DATA: int,
    REG_FP: int,
) -> None:
    """
    FP READ test.
      masking worked  -> load hits scratch     -> f{REG_FP} = VALUE_OLD
    """
    lines += [f"    # ── READ {load_mn} [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {test_data.add_testcase(test_id, 'cp_pmlen_masking', 'Ssnpm_cg')}",
        f"    {load_mn}   f{REG_FP}, 0(x{REG_A})",
        write_sigupd(REG_FP, test_data, "float"),
    ]


def _emit_fp_test(
    store_mn: str,
    load_mn: str,
    test_id: str,
    lines: list[str],
    test_data: TestData,
    REG_A: int,
    REG_BASE: int,
    REG_DATA: int,
    REG_FP: int,
) -> None:
    """
    FP WRITE test (fsw/fsd only -- fsq is not yet supported, see _FP_OPS).
    """
    lines += [f"    # ── WRITE {store_mn}/{load_mn} [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)

    mv_to_fp, _ = _FP_MVX[store_mn]
    lines += [
        _li(REG_DATA, VALUE_NEW),
        f"    {mv_to_fp}   f{REG_FP}, x{REG_DATA}",
        f"    {test_data.add_testcase(test_id, 'cp_pmlen_masking', 'Ssnpm_cg')}",
        f"    {store_mn}  f{REG_FP}, 0(x{REG_A})",
        f"    {load_mn}   f{REG_FP}, 0(x{REG_BASE})",
        write_sigupd(REG_FP, test_data, "float"),
    ]


def _emit_c_read_cl_test(
    load_mn: str,
    test_id: str,
    lines: list[str],
    test_data: TestData,
    REG_A: int,
    REG_BASE: int,
    REG_TMP: int,
    REG_DATA: int,
) -> None:
    """Zca READ test (c.lw/c.ld, CL format). rd'/rs1' both need x8-x15.
    Reuses REG_TMP/REG_DATA (pinned to x8-x15 in make_ssnpm) instead of
    allocating fresh registers -- the priv pool has none to spare."""
    lines += [f"    # ── READ {load_mn} [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    mv    x{REG_TMP}, x{REG_A}    # tagged address -> x8-x15 reg (CL-format base restriction)",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{load_mn} x{REG_DATA}, 0(x{REG_TMP})", ["zca"]),
        write_sigupd(REG_DATA, test_data),
    ]


def _emit_c_write_cs_test(
    store_mn: str,
    load_mn: str,
    test_id: str,
    lines: list[str],
    test_data: TestData,
    REG_A: int,
    REG_BASE: int,
    REG_TMP: int,
    REG_DATA: int,
) -> None:
    """Zca WRITE test (c.sw/c.sd, CS format). rs1'/rs2' both need x8-x15."""
    lines += [f"    # ── WRITE {store_mn}/{load_mn} [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    mv    x{REG_TMP}, x{REG_A}    # tagged address -> x8-x15 reg (CS-format base restriction)",
        f"    {_li(REG_DATA, VALUE_NEW)}",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{store_mn} x{REG_DATA}, 0(x{REG_TMP})", ["zca"]),
        f"    {load_mn}    x{REG_DATA}, 0(x{REG_BASE})",
        write_sigupd(REG_DATA, test_data),
    ]


def _emit_c_read_sp_test(
    load_mn: str,
    test_id: str,
    lines: list[str],
    test_data: TestData,
    REG_A: int,
    REG_BASE: int,
    REG_TMP: int,
    REG_DATA: int,
) -> None:
    lines += [f"    # ── READ {load_mn} [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    mv    x{REG_TMP}, sp       # save sp",
        f"    mv    sp, x{REG_A}          # sp := tagged address A (temporary)",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{load_mn} x{REG_DATA}, 0(sp)", ["zca"]),
        f"    mv    sp, x{REG_TMP}       # restore sp immediately",
        write_sigupd(REG_DATA, test_data),
    ]


def _emit_c_write_sp_test(
    store_mn: str,
    load_mn: str,
    test_id: str,
    lines: list[str],
    test_data: TestData,
    REG_A: int,
    REG_BASE: int,
    REG_TMP: int,
    REG_DATA: int,
) -> None:
    lines += [f"    # ── WRITE {store_mn}/{load_mn} [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    {_li(REG_DATA, VALUE_NEW)}",
        f"    mv    x{REG_TMP}, sp       # save sp",
        f"    mv    sp, x{REG_A}          # sp := tagged address A (temporary)",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"{store_mn} x{REG_DATA}, 0(sp)", ["zca"]),
        f"    mv    sp, x{REG_TMP}       # restore sp immediately",
        f"    {load_mn}    x{REG_DATA}, 0(x{REG_BASE})",
        write_sigupd(REG_DATA, test_data),
    ]


def _emit_cd_read_sp_test(
    test_id: str, lines: list[str], test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> None:
    """Zcd READ test (c.fldsp). Same sp-swap technique; freg restricted to f8-f15."""
    c_savesp = test_data.int_regs.get_register(reg_range=list(range(8, 16)))
    c_fp = test_data.float_regs.get_register(reg_range=list(range(8, 16)))
    lines += [f"    # ── READ c.fldsp [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        f"    mv    x{c_savesp}, sp",
        f"    mv    sp, x{REG_A}",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"c.fldsp f{c_fp}, 0(sp)", ["zcd"]),
        f"    mv    sp, x{c_savesp}",
        write_sigupd(c_fp, test_data, "float"),
    ]
    test_data.int_regs.return_register(c_savesp)
    test_data.float_regs.return_register(c_fp)


def _emit_cd_write_sp_test(
    test_id: str, lines: list[str], test_data: TestData, REG_A: int, REG_BASE: int, REG_DATA: int
) -> None:
    """Zcd WRITE test (c.fsdsp). Same sp-swap technique."""
    c_savesp = test_data.int_regs.get_register(reg_range=list(range(8, 16)))
    c_fp = test_data.float_regs.get_register(reg_range=list(range(8, 16)))
    lines += [f"    # ── WRITE c.fsdsp [{test_id}] ──"]
    lines += _reseed_scratch(REG_BASE, REG_DATA)
    lines += [
        _li(REG_DATA, VALUE_NEW),
        f"    fmv.d.x   f{c_fp}, x{REG_DATA}",
        f"    mv    x{c_savesp}, sp",
        f"    mv    sp, x{REG_A}",
        f"    {test_data.add_testcase(test_id, coverpoint, covergroup)}",
        *_arch_guard(f"c.fsdsp f{c_fp}, 0(sp)", ["zcd"]),
        f"    mv    sp, x{c_savesp}",
        f"    fld   f{c_fp}, 0(x{REG_BASE})",
        write_sigupd(c_fp, test_data, "float"),
    ]
    test_data.int_regs.return_register(c_savesp)
    test_data.float_regs.return_register(c_fp)


# ---------------------------------------------------------------------------
# Main block emitter: one (PMM, satp_mode) combination
# ---------------------------------------------------------------------------
def _emit_pmm_satp_block(
    pmm_val: int,
    pmlen: int,
    pmm_label: str,
    mode: str,
    test_data: TestData,
    REG_BASE: int,
    REG_A: int,
    REG_TMP: int,
    REG_DATA: int,
    REG_SENV: int,
    REG_FP: int,
) -> list[str]:
    """
    Full test sequence for one (PMM, satp_mode) combination.
    """
    guard = _SATP_GUARD[mode]
    lines: list[str] = []
    if guard:
        lines += [guard, ""]

    lines += [
        comment_banner(f"{coverpoint}  PMM={pmm_val:#04b} ({pmm_label})  satp={mode.upper()}"),
        "RVTEST_GOTO_MMODE      # ensure M-mode before any mode switch ",
    ]
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines += _set_pmm(pmm_val, pmlen, REG_SENV)
    lines.append("RVTEST_GOTO_MMODE")
    lines += _enable_cbo_envcfg(REG_SENV)
    lines += _emit_vm_setup(mode)
    lines.append("RVTEST_GOTO_LOWER_MODE Umode")

    for upper in _UPPER_PATTERNS:
        lines.append(comment_banner(f"  upper[63:48]=0x{upper:04X}  pmlen={pmlen}  mode={mode}"))
        lines += _build_tagged_address(upper, REG_BASE, REG_A, REG_TMP)
        tid = f"{pmm_label}_{mode}_up{upper:04X}"

        for load_mn in _READS:
            lines += _emit_read_test(load_mn, f"{tid}_{load_mn}", test_data, REG_A, REG_BASE, REG_DATA)

        for store_mn, load_mn in _WRITES:
            lines += _emit_write_test(store_mn, load_mn, f"{tid}_{store_mn}", test_data, REG_A, REG_BASE, REG_DATA)

        # ---- Atomics: Zaamo (optional) / Zabha / Zacas ----
        lines.append("#ifdef ZAAMO_SUPPORTED")
        for amo_mn, load_mn in _RV64A_AMOS:
            tid_amo = f"{tid}_{amo_mn.replace('.', '_')}"
            lines += _emit_amo_test(amo_mn, load_mn, tid_amo, test_data, REG_A, REG_BASE, REG_DATA)

        lines.append("#ifdef ZABHA_SUPPORTED")
        for amo_mn, load_mn in _ZABHA_AMOS:
            tid_amo = f"{tid}_{amo_mn.replace('.', '_')}"
            lines += _emit_amo_test(amo_mn, load_mn, tid_amo, test_data, REG_A, REG_BASE, REG_DATA)
        lines.append("#endif  // ZABHA_SUPPORTED")

        lines.append("#ifdef ZACAS_SUPPORTED")
        for amo_mn in _ZACAS_AMOS:
            tid_amo = f"{tid}_{amo_mn.replace('.', '_')}"
            lines += _emit_zacas_test(amo_mn, tid_amo, test_data, REG_A, REG_BASE, REG_TMP, REG_SENV)
        lines.append("#endif  // ZACAS_SUPPORTED")
        lines.append("#endif  // ZAAMO_SUPPORTED")

        # # FP reads (flw/fld) -- flq stays commented out in _FP_READS, Q not supported yet
        for load_mn, g in _FP_READS:
            lines.append(g)
            _emit_fp_read_test(load_mn, f"{tid}_{load_mn}", lines, test_data, REG_A, REG_BASE, REG_DATA, REG_FP)
            lines.append("#endif")

        # FP writes (fsw/fsd) -- fsq stays commented out in _FP_OPS, Q not supported yet
        for store_mn, load_mn, g in _FP_OPS:
            lines.append(g)
            _emit_fp_test(store_mn, load_mn, f"{tid}_{store_mn}", lines, test_data, REG_A, REG_BASE, REG_DATA, REG_FP)
            lines.append("#endif")

        # ---- Compressed: Zca , Zcd nested inside it ----
        lines.append("#ifdef ZCA_SUPPORTED")
        for load_mn in _ZCA_READS_CL:
            _emit_c_read_cl_test(
                load_mn, f"{tid}_{load_mn.replace('.', '_')}", lines, test_data, REG_A, REG_BASE, REG_TMP, REG_DATA
            )
        for store_mn, load_mn in _ZCA_WRITES_CS:
            _emit_c_write_cs_test(
                store_mn,
                load_mn,
                f"{tid}_{store_mn.replace('.', '_')}",
                lines,
                test_data,
                REG_A,
                REG_BASE,
                REG_TMP,
                REG_DATA,
            )
        for load_mn in _ZCA_READS_SP:
            _emit_c_read_sp_test(
                load_mn, f"{tid}_{load_mn.replace('.', '_')}", lines, test_data, REG_A, REG_BASE, REG_TMP, REG_DATA
            )
        for store_mn, load_mn in _ZCA_WRITES_SP:
            _emit_c_write_sp_test(
                store_mn,
                load_mn,
                f"{tid}_{store_mn.replace('.', '_')}",
                lines,
                test_data,
                REG_A,
                REG_BASE,
                REG_TMP,
                REG_DATA,
            )

        lines.append("#ifdef ZCD_SUPPORTED")
        _emit_cd_read_sp_test(f"{tid}_c_fldsp", lines, test_data, REG_A, REG_BASE, REG_DATA)
        _emit_cd_write_sp_test(f"{tid}_c_fsdsp", lines, test_data, REG_A, REG_BASE, REG_DATA)
        lines.append("#endif  // ZCD_SUPPORTED")
        lines.append("#endif  // ZCA_SUPPORTED")

        # ---- Cache management: Zicboz / Zicbom (incl. cbo.inval) / Zicbop ----
        lines.append("#ifdef ZICBOZ_SUPPORTED")
        lines += _emit_cbo_zero_test(f"{tid}_cbo_zero", test_data, REG_A, REG_BASE, REG_DATA)
        lines.append("#endif  // ZICBOZ_SUPPORTED")

        lines.append("#ifdef ZICBOM_SUPPORTED")
        for cbo_mn in _ZICBOM_OPS:
            lines += _emit_cbom_test(cbo_mn, f"{tid}_{cbo_mn.replace('.', '_')}", test_data, REG_A, REG_BASE, REG_DATA)
        lines += _emit_cbo_inval_test(f"{tid}_cbo_inval", test_data, REG_A, REG_BASE, REG_DATA)
        lines.append("#endif  // ZICBOM_SUPPORTED")

        # prefetch.*
        for pf_mn in _ZICBOP_OPS:
            lines += _emit_prefetch_test(
                pf_mn, f"{tid}_{pf_mn.replace('.', '_')}", test_data, REG_A, REG_BASE, REG_DATA
            )

    lines += [
        "RVTEST_GOTO_MMODE      # ensure M-mode before any mode switch (framework precondition)",
    ]
    lines += _emit_vm_teardown(mode)
    lines.append("RVTEST_GOTO_LOWER_MODE Smode  # back to S-mode baseline for next block")

    if guard:
        lines += [f"#endif  // {mode.upper()}_SUPPORTED", ""]
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["Ssnpm", "Zicsr", "S"],
    march_extensions=["f", "d"],
)
def make_ssnpm(test_data: TestData) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    lines: list[str] = _generate_data_section()
    lines.append(comment_banner("cp_pmlen_masking — Ssnpm (load/store step)"))

    REG_TMP, REG_DATA = test_data.int_regs.get_registers(2, reg_range=list(range(8, 16)))
    REG_BASE, REG_A, REG_SENV = test_data.int_regs.get_registers(3, exclude_regs=[])

    REG_FP = test_data.float_regs.get_register()

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "# Load  page physical base address ...",
            f"LA(x{REG_BASE}, pm_scratch)",
            f"{_li(REG_DATA, VALUE_DIFF)}",
            "LA(t0, pm_other_page)",
            f"sd    x{REG_DATA}, 0(t0)      # pre-seed pm_other_page = VALUE_DIFF",
        ]
    )

    for pmm_val, pmlen, pmm_label in _PMM_CONFIGS:
        for mode in _SATP_MODES:
            lines.extend(
                _emit_pmm_satp_block(
                    pmm_val, pmlen, pmm_label, mode, test_data, REG_BASE, REG_A, REG_TMP, REG_DATA, REG_SENV, REG_FP
                )
            )

    lines.append(comment_banner("Restore defaults: PMM=00, satp=Bare"))
    lines.append("RVTEST_GOTO_MMODE")
    lines.extend(_set_pmm(0b00, 0, REG_SENV))
    lines.extend(["csrwi satp, 0", "sfence.vma"])

    test_data.int_regs.return_registers([REG_BASE, REG_A, REG_TMP, REG_DATA, REG_SENV])
    test_data.float_regs.return_registers([REG_FP])

    tc.code = lines
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
