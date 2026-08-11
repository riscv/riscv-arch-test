##################################
# priv/extensions/Ssnpm.py
#
# Ssnpm privileged extension test generator.
# Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssnpm S-mode pointer-masking test generator.

Ssnpm gives S-mode control (via ``senvcfg.PMM``) over pointer masking for the
next lower privilege mode, i.e. U-mode.  Every test here therefore runs its
probes in U-mode with ``senvcfg.PMM`` programmed from M-mode.

Normative behaviour being tested (RISC-V Pointer Masking v1.0.0)
---------------------------------------------------------------
* ``PMM`` = 00 -> PMLEN 0 (off), 10 -> PMLEN 7, 11 -> PMLEN 16.  01 is reserved.
* The transformation applies to the *effective address of explicit memory
  accesses only*: loads, stores, AMOs, FP and compressed load/stores, vector
  load/stores, CBO/prefetch and Zicfiss accesses.  It does **not** apply to
  instruction fetch, so a JALR through a tagged pointer must still fault.
* Under an active translation mode the masked bits are replaced by a copy of
  bit ``XLEN-PMLEN-1`` (**sign extension**, keeping canonical VAs canonical).
  In Bare mode -- and for any physical address -- they are replaced by zeroes
  (**zero extension**).
* When ``MXR`` is in effect at the effective privilege mode of the access,
  pointer masking does not apply at all, even with translation disabled.
* Pointer masking *is* applied to hardware writes of the faulting address, so
  ``xtval`` holds the **masked** address.

Test structure
--------------
One test file per satp mode (``Ssnpm_bare``, ``Ssnpm_sv39``, ``Ssnpm_sv48``,
``Ssnpm_sv57``); the Sv files are wholly ``#ifdef``-guarded so they compile
away on configs without that translation mode.  Each file runs six passes for
each of the three PMM settings:

===== ============================================================ ==============================
Pass  What it exercises                                            Covergroup cross fed
===== ============================================================ ==============================
A     all 100 masked-access instructions at 8 tag patterns         ``cp_pmlen_masking``
B     ld/sd against a high (bit-47/56 set) VA -- sign extension     ``cp_pmlen_masking``
C     misaligned sw/lw at 8 tag patterns                           ``cp_pmlen_misaligned_word``
D     sw/lw with ``mstatus.MXR=1`` (masking must be suppressed)     ``cp_pmm_mxr``
E     JALR through a tagged pointer, MXR=0 and MXR=1                ``cp_pmm_jalr``
F     sw/lw whose *masked* address is the model's fault address     ``cp_hardware_csr_writes_fault``
===== ============================================================ ==============================

A probe that is expected to fault is not a defect: for a given (PMM, satp) only
some tag patterns survive masking, and both the surviving value and the trap
record (cause/epc/tval) are part of the signature, so the reference model pins
down the whole matrix.  Each probe seeds its destination with a sentinel first
so a trapped probe records a distinguishable value rather than stale state.
"""

from __future__ import annotations

from dataclasses import dataclass

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Ssnpm_cg"
CP_MASKING = "cp_pmlen_masking"
CP_MISALIGN = "cp_pmlen_misaligned_word"
CP_MXR = "cp_pmm_mxr"
CP_JALR = "cp_pmm_jalr"
CP_FAULT = "cp_hardware_csr_writes_fault"

# ---------------------------------------------------------------------------
# Constants describing the matrix
# ---------------------------------------------------------------------------

# Tag patterns written into bits 63:48 of the probe address. These are exactly
# the bins of the shared `a_upper_bits` coverpoint; the comments record which
# PMLEN actually strips them.
_UPPER_PATTERNS: list[int] = [
    0x0000,  # no tag: masking is a no-op, the control case
    0x0001,  # bit 48   -- stripped by PMLEN=16 only
    0x0100,  # bit 56   -- stripped by PMLEN=16 only
    0x0200,  # bit 57   -- stripped by PMLEN=16 and PMLEN=7
    0x8000,  # bit 63   -- stripped by PMLEN=16 and PMLEN=7
    0xFFFF,  # bits 63:48 -- fully stripped by PMLEN=16, partially by PMLEN=7
    0xFE00,  # bits 63:57 -- exactly the PMLEN=7 window
    0xFF00,  # bits 63:56 -- fully stripped by PMLEN=16, partially by PMLEN=7
]

# (senvcfg.PMM value, resulting PMLEN, label used in testcase names)
_PMM_CONFIGS: list[tuple[int, int, str]] = [
    (0b00, 0, "pmm00"),
    (0b10, 7, "pmm10"),
    (0b11, 16, "pmm11"),
]

_SATP_MODES: list[str] = ["bare", "sv39", "sv48", "sv57"]

_SATP_GUARD: dict[str, str | None] = {
    "bare": None,
    "sv39": "SV39_SUPPORTED",
    "sv48": "SV48_SUPPORTED",
    "sv57": "SV57_SUPPORTED",
}

# Highest-numbered page table each mode walks through. Sv39 needs slvl1/slvl0,
# Sv48 adds slvl2, Sv57 adds slvl3. The root table is emitted by the framework.
_LEVELS_BELOW_ROOT: dict[str, int] = {"sv39": 2, "sv48": 3, "sv57": 4}

# Root-table index the boot-time identity map occupies for each mode, i.e. the
# VPN slice of `rvtest_data_begin` that rvtest_setup.h wrote a leaf superpage
# into. Used to OR PTE_U into that entry so U-mode can run from it.
_IDENTITY_VPN_SHIFT: dict[str, int] = {"sv39": 30, "sv48": 39, "sv57": 48}

# A canonical "upper half" VA per mode, used by pass B to prove masking sign
# extends under translation instead of zero extending. Each has both bit 47 and
# bit 56 set, so PMLEN=16 (sign extend from bit 47) and PMLEN=7 (sign extend
# from bit 56) both reproduce it from a tagged pointer.
_HIGH_VA: dict[str, int] = {
    "sv39": 0xFFFF_FFC0_0000_0000,  # bits 63:38 all ones -> canonical Sv39
    "sv48": 0xFFFF_8000_0000_0000,  # bits 63:47 all ones -> canonical Sv48
    "sv57": 0xFFFF_8000_0000_0000,  # bits 63:56 all ones -> canonical Sv57
}

VALUE_OLD: int = 0xABCD_1234_ABCD_1234  # seeded into the scratch pages
VALUE_NEW: int = 0xA5A5_A5A5_A5A5_A5A5  # written by every store-style probe
SENTINEL: int = 0x1BAD_0BAD_1BAD_0BAD  # left in the destination if a probe traps

_NONLEAF_PERMS = "PTE_V"  # non-leaf PTEs must have ONLY V set
_LEAF_PERMS = "PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V"  # RW data page, U-accessible

# CSR field positions
_SENVCFG_PMM_SHIFT = 32
_SENVCFG_CBIE_SHIFT = 4
_SENVCFG_CBCFE_SHIFT = 6
_SENVCFG_CBZE_SHIFT = 7
_ENVCFG_SSE_BIT = 1 << 3  # Zicfiss shadow stack enable (menvcfg/senvcfg)
_MSTATUS_SUM = 1 << 18
_MSTATUS_MXR = 1 << 19
_MSTATUS_FS_DIRTY = 3 << 13
_MSTATUS_VS_DIRTY = 3 << 9

# ---------------------------------------------------------------------------
# Instruction inventory -- one entry per `pm_insn` coverpoint bin
# ---------------------------------------------------------------------------

_READS: list[str] = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]

# (store mnemonic, load mnemonic used for the read-back check)
_WRITES: list[tuple[str, str]] = [("sb", "lbu"), ("sh", "lhu"), ("sw", "lw"), ("sd", "ld")]

_AMO_OPS = ["swap", "add", "xor", "and", "or", "min", "max", "minu", "maxu"]

# Zaamo: word/doubleword atomics, treated as writes for masking purposes.
_RV64A_AMOS: list[tuple[str, str]] = [
    (f"amo{op}.{w}", "lw" if w == "w" else "ld") for op in _AMO_OPS for w in ("w", "d")
]

# Zabha: the same set at byte/halfword width.
_ZABHA_AMOS: list[tuple[str, str]] = [
    (f"amo{op}.{w}", "lbu" if w == "b" else "lhu") for op in _AMO_OPS for w in ("b", "h")
]

# Zacas compare-and-swap. amocas.q needs an even/odd register pair and is not
# part of the coverage model, so only the single-register widths appear here.
_ZACAS_AMOS: list[str] = ["amocas.w", "amocas.d"]

# (mnemonic, guard macro, move-to-FP instruction used to seed the sentinel)
_FP_READS: list[tuple[str, str, str]] = [
    ("flw", "F_SUPPORTED", "fmv.w.x"),
    ("fld", "D_SUPPORTED", "fmv.d.x"),
]
# (store mnemonic, load mnemonic, guard macro, move-to-FP instruction)
_FP_WRITES: list[tuple[str, str, str, str]] = [
    ("fsw", "lw", "F_SUPPORTED", "fmv.w.x"),
    ("fsd", "ld", "D_SUPPORTED", "fmv.d.x"),
]

_ZCA_READS_CL: list[str] = ["c.lw", "c.ld"]
_ZCA_WRITES_CS: list[tuple[str, str]] = [("c.sw", "lw"), ("c.sd", "ld")]
_ZCA_READS_SP: list[str] = ["c.lwsp", "c.ldsp"]
_ZCA_WRITES_SP: list[tuple[str, str]] = [("c.swsp", "lw"), ("c.sdsp", "ld")]

_ZICBOM_OPS: list[str] = ["cbo.clean", "cbo.flush", "cbo.inval"]
_ZICBOP_OPS: list[str] = ["prefetch.r", "prefetch.w", "prefetch.i"]

# Zicfiss shadow-stack atomics, as (mnemonic, read-back load, funct3). Enabled through
# menvcfg.SSE + senvcfg.SSE. Emitted as a raw `.insn` because Zicfiss is still experimental
# in LLVM, so naming it in the march string makes clang reject the whole file.
_ZICFISS_AMOS: list[tuple[str, str, int]] = [("ssamoswap.w", "lw", 0x2), ("ssamoswap.d", "ld", 0x3)]

# Vector loads: (mnemonic, SEW used to set vtype, asm template).
# `{a}` is the tagged base register, `{t}` a scratch integer register.
_VEC_READS: list[tuple[str, int, str]] = [
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

# Vector stores: (mnemonic, SEW, asm template, read-back load).
_VEC_WRITES: list[tuple[str, int, str, str]] = [
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


# ---------------------------------------------------------------------------
# Small assembly helpers
# ---------------------------------------------------------------------------


@dataclass
class Regs:
    """The six pool registers a probe block needs, allocated once per file.

    ``a``/``data``/``chk``/``tmp`` are constrained to x8-x15 so the same
    registers can serve as ``rd'``/``rs1'``/``rs2'`` in the compressed CL/CS
    probes, which cannot encode anything outside that range.
    """

    base: int  # untagged, always-valid base address of the probe page
    a: int  # tagged probe address (base | tag << 48)
    data: int  # value fed to store-style probes
    chk: int  # value handed to RVTEST_SIGUPD
    tmp: int  # scratch
    tmp2: int  # scratch
    fp: int  # FP probe destination
    fp_c: int  # FP destination for Zcd probes (must be f8-f15)


def _li(reg: int, val: int) -> str:
    """LI() accepts arbitrarily wide hex literals, unlike bare `li`."""
    return f"LI(x{reg}, {hex(val)})"


def _fixed(instr: str) -> list[str]:
    """Emit one instruction with a pinned 32-bit encoding.


    Extension availability comes from the suite's ``march_extensions`` rather
    than a local ``.option arch``: no other suite in the repo uses that
    directive, and its extension-name vocabulary varies between binutils and
    LLVM releases, so relying on it makes the tests toolchain-sensitive.
    """
    return [".option push", ".option norvc", instr, ".option pop"]


def _compressed(instr: str) -> list[str]:
    """Emit one instruction that must keep its 16-bit encoding."""
    return [".option push", ".option rvc", instr, ".option pop"]


def _guard_open(macro: str | None) -> list[str]:
    return [f"#ifdef {macro}"] if macro else []


def _guard_close(macro: str | None) -> list[str]:
    return [f"#endif // {macro}"] if macro else []


# ---------------------------------------------------------------------------
# Data section and page tables
# ---------------------------------------------------------------------------


def _data_section(mode: str) -> list[str]:
    """Probe pages plus the page tables this satp mode walks.

    ``rvtest_Sroot_pg_tbl`` is declared by the framework; every level below it is
    private to this test so the image mapping and the upper-half mapping cannot
    collide in a shared table.
    """
    lines = [
        ".pushsection .data",
        ".p2align 12",
        f"pm_lo_page:     .dword {hex(VALUE_OLD)}   # probe target inside the identity-mapped image",
        "                .zero 4088",
    ]
    if mode != "bare":
        lines += [
            ".p2align 12",
            f"pm_hi_page:     .dword {hex(VALUE_OLD)}   # probe target reached through the upper-half VA",
            "                .zero 4088",
        ]
        # Two independent chains hanging off the framework's root table: one for the
        # test image, one for the upper-half probe page. They occupy different root
        # slots, and each owns every level below the root so their VPN indices at the
        # interior levels cannot collide.
        for level in range(_LEVELS_BELOW_ROOT[mode] - 1, -1, -1):
            lines += [".p2align 12", f"pm_pt_l{level}:      .zero 4096"]
        for level in range(_LEVELS_BELOW_ROOT[mode] - 1, -1, -1):
            lines += [".p2align 12", f"pm_pt_hi_l{level}:   .zero 4096"]
    lines.append(".popsection")
    return lines


def _nonleaf(parent: str, child: str, shift: int, va_reg: str) -> list[str]:
    """parent[VPN(va, shift)] = child, valid but not a leaf."""
    return [
        f"srli t1, {va_reg}, {shift}",
        "andi t1, t1, 0x1FF",
        "slli t1, t1, 3",
        f"LA(t2, {parent})",
        "add  t2, t2, t1",
        f"LA(t3, {child})",
        "srli t3, t3, 12",
        "slli t3, t3, 10",
        f"ori  t3, t3, ({_NONLEAF_PERMS})",
        "sd   t3, 0(t2)",
    ]


def _walk(mode: str, tables: list[str], va_reg: str) -> list[str]:
    """Install the non-leaf entries from the framework root down to ``tables[0]``."""
    # Root indexes the highest VPN slice; each level below shifts down by 9.
    shifts = [12 + 9 * k for k in range(_LEVELS_BELOW_ROOT[mode], 0, -1)]
    chain = ["rvtest_Sroot_pg_tbl", *tables]
    lines: list[str] = []
    for parent, child, shift in zip(chain, chain[1:], shifts):
        lines += _nonleaf(parent, child, shift, va_reg)
    return lines


def _build_page_tables(mode: str) -> list[str]:
    """Map the test image at 4 KiB granularity, with PTE_U only where U-mode needs it.

    The boot code installs one identity superpage without PTE_U, which U-mode cannot
    execute from. Adding PTE_U to that superpage is not an option either: the supervisor
    may never *fetch* from a U=1 page, so the S-mode trap handler, which lives in the same
    superpage, would take an instruction page fault on every trap and loop forever.
    Splitting the superpage into 4 KiB leaves lets PTE_U cover exactly the test's own code
    and data, leaving the handlers and the model shim S-mode-fetchable.
    """
    top = _LEVELS_BELOW_ROOT[mode]
    img = [f"pm_pt_l{lvl}" for lvl in range(top - 1, -1, -1)]
    hi = [f"pm_pt_hi_l{lvl}" for lvl in range(top - 1, -1, -1)]
    hi_va = _HIGH_VA[mode]

    lines = [f"# {mode.upper()}: 4 KiB mapping of the test image; PTE_U only on test code and data"]
    lines += ["LA(t0, rvtest_code_begin)"]
    lines += _walk(mode, img, "t0")

    lines += [
        "# Fill the leaf table for the 2 MiB region holding the image.",
        "LA(t0, rvtest_code_begin)",
        "srli t0, t0, 21",
        "slli t0, t0, 21                  # t0 = 2 MiB-aligned base of the image",
        f"LA(t1, {img[-1]})",
        "LA(t2, pm_utext_begin)",
        "LA(t3, pm_utext_end)",
        "sub  t3, t3, t2                  # t3 = size of the U-executable text",
        "LA(t4, rvtest_data_begin)",
        "LA(t5, end_signature)            # the signature sits just past rvtest_data_end",
        "sub  t5, t5, t4                  # t5 = size of the U-accessible data",
        "li   t6, 512",
        "1:",
        "li   a0, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V)",
        "sub  a1, t0, t2",
        "bltu a1, t3, 2f                  # inside the code segment -> U-accessible",
        "sub  a1, t0, t4",
        "bgeu a1, t5, 3f                  # outside the data segment -> keep U clear",
        "2:",
        "ori  a0, a0, PTE_U",
        "3:",
        "srli a1, t0, 12",
        "slli a1, a1, 10",
        "or   a1, a1, a0",
        "sd   a1, 0(t1)",
        "addi t1, t1, 8",
        "lui  a1, 1                       # 4096",
        "add  t0, t0, a1",
        "addi t6, t6, -1",
        "bnez t6, 1b",
    ]

    lines += [
        f"# Upper-half probe page at {hex(hi_va)}: proves masking sign extends under translation.",
        f"LI(t0, {hex(hi_va)})",
    ]
    lines += _walk(mode, hi, "t0")
    lines += [
        f"LI(t0, {hex(hi_va)})",
        "srli t1, t0, 12",
        "andi t1, t1, 0x1FF",
        "slli t1, t1, 3",
        f"LA(t2, {hi[-1]})",
        "add  t2, t2, t1",
        "LA(t3, pm_hi_page)",
        "srli t3, t3, 12",
        "slli t3, t3, 10",
        f"ori  t3, t3, ({_LEAF_PERMS})",
        "sd   t3, 0(t2)",
    ]
    return lines


# ---------------------------------------------------------------------------
# M-mode configuration helpers
# ---------------------------------------------------------------------------


def _set_pmm(pmm_val: int, pmlen: int, tmp: int) -> list[str]:
    """Program senvcfg.PMM without disturbing the CBO/SSE fields beside it."""
    mask = 0b11 << _SENVCFG_PMM_SHIFT
    field = pmm_val << _SENVCFG_PMM_SHIFT
    return [
        f"# senvcfg.PMM = {pmm_val:#04b} -> PMLEN={pmlen}",
        _li(tmp, mask),
        f"csrc senvcfg, x{tmp}",
        _li(tmp, field),
        f"csrs senvcfg, x{tmp}",
    ]


def _set_mxr(enable: bool, tmp: int) -> list[str]:
    """MXR gates pointer masking off entirely when set.

    Written through *sstatus*, not mstatus, even though this runs in M-mode and
    both views share the bit. The coverage front-end reconstructs CSR state from
    the RVVI write-back stream keyed by CSR address, and `mxr_bit` samples
    sstatus -- an mstatus write updates only the mstatus entry, leaving the
    sstatus shadow reading 0 and the MXR=1 bin permanently unreachable.
    """
    op = "csrs" if enable else "csrc"
    return [
        f"# sstatus.MXR = {int(enable)}",
        _li(tmp, _MSTATUS_MXR),
        f"{op} sstatus, x{tmp}",
    ]


def _mmode_prelude(mode: str, regs: Regs) -> list[str]:
    """Everything that has to be true before the first U-mode probe."""
    cbo_fields = (
        (0b11 << _SENVCFG_CBIE_SHIFT) | (1 << _SENVCFG_CBCFE_SHIFT) | (1 << _SENVCFG_CBZE_SHIFT) | _ENVCFG_SSE_BIT
    )
    lines = [
        "RVTEST_GOTO_MMODE",
        "",
        "# Let U-mode run cbo.*/prefetch.* (CBIE=11, CBCFE=1, CBZE=1) and the Zicfiss",
        "# shadow-stack atomics (SSE=1). menvcfg gates senvcfg, so both are written.",
        _li(regs.tmp, _ENVCFG_SSE_BIT),
        f"csrs menvcfg, x{regs.tmp}",
        _li(regs.tmp, cbo_fields),
        f"csrc senvcfg, x{regs.tmp}",
        _li(regs.tmp, cbo_fields),
        f"csrs senvcfg, x{regs.tmp}",
        "",
        "# FP and vector state must be on for the FP/vector probes to be legal. SUM lets the",
        "# S-mode trap handler reach its save area and trap signature, which live on the same",
        "# U-accessible data pages the U-mode probes use.",
        _li(regs.tmp, _MSTATUS_FS_DIRTY | _MSTATUS_VS_DIRTY | _MSTATUS_SUM),
        f"csrs mstatus, x{regs.tmp}",
    ]
    if mode != "bare":
        lines += ["", *_build_page_tables(mode)]
        lines += [
            "sfence.vma",
            f"SATP_SETUP_RV64({mode})",
            "sfence.vma",
        ]
    # Stash medeleg only after the page-table setup, which clobbers a0/a1 and t0-t6;
    # t1 is x6, which is in the allocatable pool.
    lines += []
    return lines


def _teardown(regs: Regs) -> list[str]:
    """Return the machine to the state the framework epilogs expect."""
    return [
        "RVTEST_GOTO_MMODE",
        *_set_pmm(0b00, 0, regs.tmp),
        *_set_mxr(False, regs.tmp),
        "csrwi satp, 0",
        "sfence.vma",
    ]


# ---------------------------------------------------------------------------
# Probe primitives
# ---------------------------------------------------------------------------


def _load_base(mode: str, region: str, regs: Regs) -> list[str]:
    """Point REG_BASE at the untagged address the probes should resolve to."""
    if region == "hi":
        return [
            f"# upper-half VA base: masking must sign extend to reproduce {hex(_HIGH_VA[mode])}",
            _li(regs.base, _HIGH_VA[mode]),
        ]
    return [f"LA(x{regs.base}, pm_lo_page)"]


def _tag_address(upper: int, regs: Regs, byte_offset: int = 0) -> list[str]:
    """REG_A = REG_BASE | (upper << 48), optionally nudged off alignment."""
    lines = [
        f"# tagged pointer: bits 63:48 = 0x{upper:04X}",
        _li(regs.tmp, upper << 48),
        f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
    ]
    if byte_offset:
        lines.append(f"addi x{regs.a}, x{regs.a}, {byte_offset}   # force a misaligned effective address")
    return lines


def _seed(regs: Regs) -> list[str]:
    """Re-seed the probe page through the untagged base."""
    return [_li(regs.data, VALUE_OLD), f"sd x{regs.data}, 0(x{regs.base})"]


def _sentinel(regs: Regs) -> list[str]:
    """Poison the destination so a trapped probe is distinguishable."""
    return [_li(regs.chk, SENTINEL)]


def _tid(prefix: str, upper: int, mnemonic: str) -> str:
    return f"{prefix}_up{upper:04X}_{mnemonic.replace('.', '_')}"


# --- integer -----------------------------------------------------------------


def _probe_load(mn: str, tid: str, td: TestData, regs: Regs, cp: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        td.add_testcase(tid, cp, COVERGROUP),
        *_fixed(f"{mn} x{regs.chk}, 0(x{regs.a})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_store(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cp: str) -> list[str]:
    """Store through the tagged pointer, then read back through the untagged one.

    A masked store lands on the probe page and the read-back sees VALUE_NEW; a
    store that faulted (or landed elsewhere) leaves VALUE_OLD behind.
    """
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, cp, COVERGROUP),
        *_fixed(f"{mn} x{regs.data}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_amo(mn: str, readback: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_fixed(f"{mn} x0, x{regs.data}, (x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_zacas(mn: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    """amocas.w/.d on RV64 need no register pair -- only amocas.q does."""
    return [
        *_seed(regs),
        f"{_li(regs.chk, VALUE_OLD)}   # comparand matches the seeded value",
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_fixed(f"{mn} x{regs.chk}, x{regs.data}, (x{regs.a})"),
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_zicfiss(mn: str, readback: str, funct3: int, tid: str, td: TestData, regs: Regs) -> list[str]:
    """Zicfiss shadow-stack AMO through a tagged pointer.

    The probe page is an ordinary data page, not a shadow-stack page, so this is
    expected to fault; the point is that it faults on the *masked* address.

    Encoded with `.insn` (AMO opcode 0x2f, funct7 0x24 = funct5 01001 with
    aq=rl=0) instead of the mnemonic -- see `_ZICFISS_AMOS` for why.
    """
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        *_sentinel(regs),
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_fixed(
            f".insn r 0x2f, {funct3:#x}, 0x24, x{regs.chk}, x{regs.a}, x{regs.data}"
            f"   # {mn} x{regs.chk}, x{regs.data}, (x{regs.a})"
        ),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


# --- floating point ----------------------------------------------------------


def _probe_fp_load(mn: str, mv: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"{mv} f{regs.fp}, x{regs.chk}   # poison the FP destination",
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_fixed(f"{mn} f{regs.fp}, 0(x{regs.a})"),
        write_sigupd(regs.fp, td, "float"),
    ]


def _probe_fp_store(mn: str, readback: str, mv: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        f"{mv} f{regs.fp}, x{regs.data}",
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_fixed(f"{mn} f{regs.fp}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


# --- compressed --------------------------------------------------------------


def _probe_c_load_cl(mn: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    """CL-format compressed load: rd' and rs1' must both be x8-x15."""
    return [
        *_seed(regs),
        *_sentinel(regs),
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_compressed(f"{mn} x{regs.chk}, 0(x{regs.a})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_store_cs(mn: str, readback: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    """CS-format compressed store: rs1' and rs2' must both be x8-x15."""
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_compressed(f"{mn} x{regs.data}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_load_sp(mn: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    """SP-relative compressed load. sp doubles as the signature pointer, so it is
    borrowed for exactly one instruction and restored before the next SIGUPD.
    The trap handler swaps sp with its own scratch on entry, so a faulting probe
    still returns with the borrowed value intact."""
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_compressed(f"{mn} x{regs.chk}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        write_sigupd(regs.chk, td),
    ]


def _probe_c_store_sp(mn: str, readback: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_compressed(f"{mn} x{regs.data}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_cd_load_sp(tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"fmv.d.x f{regs.fp_c}, x{regs.chk}",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_compressed(f"c.fldsp f{regs.fp_c}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        write_sigupd(regs.fp_c, td, "float"),
    ]


def _probe_cd_store_sp(tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        f"fmv.d.x f{regs.fp_c}, x{regs.data}",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_compressed(f"c.fsdsp f{regs.fp_c}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


# --- cache management --------------------------------------------------------


def _probe_cbo(mn: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    """cbo.*/prefetch.* take their address in rs1 with no data operand.

    cbo.zero is the only one with an architectural memory effect, so the
    read-back distinguishes "landed on the probe page" (zero) from "faulted or
    landed elsewhere" (VALUE_OLD). The others are checked purely by whether they
    trap and on what address.
    """
    return [
        *_seed(regs),
        td.add_testcase(tid, CP_MASKING, COVERGROUP),
        *_fixed(f"{mn} 0(x{regs.a})"),
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


# --- vector ------------------------------------------------------------------


def _vset(sew: int, regs: Regs) -> list[str]:
    """Establish a small, legal vtype/vl and a zeroed index vector.

    vl is deliberately tiny so segment and whole-register forms stay inside the
    4 KiB probe page, and vstart is cleared because a faulting vector probe can
    leave it non-zero and make the next probe resume mid-operation.
    """
    return [
        "csrw vstart, x0",
        f"vsetivli x{regs.tmp}, 2, e{sew}, m1, ta, ma",
        "vmv.v.i v4, 0   # zero index vector: indexed probes address the base itself",
    ]


def _probe_vec_load(mn: str, sew: int, template: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        *_fixed_block(
            [
                *_vset(sew, regs),
                f"vmv.v.x v2, x{regs.chk}   # poison the destination vector",
                td.add_testcase(tid, CP_MASKING, COVERGROUP),
                template.format(a=regs.a),
                f"vmv.x.s x{regs.chk}, v2",
                "csrw vstart, x0",
            ],
        ),
        write_sigupd(regs.chk, td),
    ]


def _probe_vec_store(mn: str, sew: int, template: str, readback: str, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        *_fixed_block(
            [
                *_vset(sew, regs),
                f"vmv.v.x v2, x{regs.data}",
                td.add_testcase(tid, CP_MASKING, COVERGROUP),
                template.format(a=regs.a),
                "csrw vstart, x0",
            ],
        ),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _fixed_block(body: list[str]) -> list[str]:
    """`.option` wrapper around a multi-instruction block (labels included)."""
    return [".option push", ".option norvc", *body, ".option pop"]


# ---------------------------------------------------------------------------
# Passes
# ---------------------------------------------------------------------------


def _pass_a_all_instructions(prefix: str, td: TestData, regs: Regs) -> list[str]:
    """Every `pm_insn` bin at every tag pattern -- the bulk of cp_pmlen_masking."""
    lines: list[str] = []
    for upper in _UPPER_PATTERNS:
        lines.append(comment_banner(f"{prefix}: tag 0x{upper:04X} -- full instruction sweep"))
        lines += _tag_address(upper, regs)

        for mn in _READS:
            lines += _probe_load(mn, _tid(prefix, upper, mn), td, regs, CP_MASKING)
        for mn, rb in _WRITES:
            lines += _probe_store(mn, rb, _tid(prefix, upper, mn), td, regs, CP_MASKING)

        lines += _guard_open("ZAAMO_SUPPORTED")
        for mn, rb in _RV64A_AMOS:
            lines += _probe_amo(mn, rb, _tid(prefix, upper, mn), td, regs)
        lines += _guard_open("ZABHA_SUPPORTED")
        for mn, rb in _ZABHA_AMOS:
            lines += _probe_amo(mn, rb, _tid(prefix, upper, mn), td, regs)
        lines += _guard_close("ZABHA_SUPPORTED")
        lines += _guard_open("ZACAS_SUPPORTED")
        for mn in _ZACAS_AMOS:
            lines += _probe_zacas(mn, _tid(prefix, upper, mn), td, regs)
        lines += _guard_close("ZACAS_SUPPORTED")
        lines += _guard_close("ZAAMO_SUPPORTED")

        for mn, guard, mv in _FP_READS:
            lines += _guard_open(guard)
            lines += _probe_fp_load(mn, mv, _tid(prefix, upper, mn), td, regs)
            lines += _guard_close(guard)
        for mn, rb, guard, mv in _FP_WRITES:
            lines += _guard_open(guard)
            lines += _probe_fp_store(mn, rb, mv, _tid(prefix, upper, mn), td, regs)
            lines += _guard_close(guard)

        lines += _guard_open("ZCA_SUPPORTED")
        for mn in _ZCA_READS_CL:
            lines += _probe_c_load_cl(mn, _tid(prefix, upper, mn), td, regs)
        for mn, rb in _ZCA_WRITES_CS:
            lines += _probe_c_store_cs(mn, rb, _tid(prefix, upper, mn), td, regs)
        for mn in _ZCA_READS_SP:
            lines += _probe_c_load_sp(mn, _tid(prefix, upper, mn), td, regs)
        for mn, rb in _ZCA_WRITES_SP:
            lines += _probe_c_store_sp(mn, rb, _tid(prefix, upper, mn), td, regs)
        lines += _guard_open("ZCD_SUPPORTED")
        lines += _probe_cd_load_sp(_tid(prefix, upper, "c.fldsp"), td, regs)
        lines += _probe_cd_store_sp(_tid(prefix, upper, "c.fsdsp"), td, regs)
        lines += _guard_close("ZCD_SUPPORTED")
        lines += _guard_close("ZCA_SUPPORTED")

        lines += _guard_open("ZICBOZ_SUPPORTED")
        lines += _probe_cbo("cbo.zero", _tid(prefix, upper, "cbo.zero"), td, regs)
        lines += _guard_close("ZICBOZ_SUPPORTED")
        lines += _guard_open("ZICBOM_SUPPORTED")
        for mn in _ZICBOM_OPS:
            lines += _probe_cbo(mn, _tid(prefix, upper, mn), td, regs)
        lines += _guard_close("ZICBOM_SUPPORTED")
        lines += _guard_open("ZICBOP_SUPPORTED")
        for mn in _ZICBOP_OPS:
            lines += _probe_cbo(mn, _tid(prefix, upper, mn), td, regs)
        lines += _guard_close("ZICBOP_SUPPORTED")

        lines += _guard_open("ZICFISS_SUPPORTED")
        for mn, rb, f3 in _ZICFISS_AMOS:
            lines += _probe_zicfiss(mn, rb, f3, _tid(prefix, upper, mn), td, regs)
        lines += _guard_close("ZICFISS_SUPPORTED")

        lines += _guard_open("ZVL32B_SUPPORTED")
        for mn, sew, template in _VEC_READS:
            lines += _probe_vec_load(mn, sew, template, _tid(prefix, upper, mn), td, regs)
        for mn, sew, template, rb in _VEC_WRITES:
            lines += _probe_vec_store(mn, sew, template, rb, _tid(prefix, upper, mn), td, regs)
        lines += _guard_close("ZVL32B_SUPPORTED")
    return lines


def _pass_b_sign_extension(prefix: str, mode: str, td: TestData, regs: Regs) -> list[str]:
    """ld/sd against an upper-half VA: only sign extension reproduces the base."""
    lines = [comment_banner(f"{prefix}: upper-half VA -- masking must sign extend, not zero extend")]
    lines += _load_base(mode, "hi", regs)
    for upper in _UPPER_PATTERNS:
        lines += _tag_address(upper, regs)
        lines += _probe_load("ld", _tid(f"{prefix}_hi", upper, "ld"), td, regs, CP_MASKING)
        lines += _probe_store("sd", "ld", _tid(f"{prefix}_hi", upper, "sd"), td, regs, CP_MASKING)
    lines += _load_base(mode, "lo", regs)
    return lines


def _pass_c_misaligned(prefix: str, td: TestData, regs: Regs) -> list[str]:
    """Misaligned sw/lw at every tag pattern -- feeds cp_pmlen_misaligned_word."""
    lines = [comment_banner(f"{prefix}: misaligned word accesses through a tagged pointer")]
    for upper in _UPPER_PATTERNS:
        lines += _tag_address(upper, regs, byte_offset=1)
        lines += _probe_load("lw", _tid(f"{prefix}_mis", upper, "lw"), td, regs, CP_MISALIGN)
        lines += _probe_store("sw", "lw", _tid(f"{prefix}_mis", upper, "sw"), td, regs, CP_MISALIGN)
    return lines


def _pass_d_mxr(prefix: str, td: TestData, regs: Regs) -> list[str]:
    """sw/lw with MXR set. MXR suppresses masking, so tagged pointers must fault.

    MXR lives in mstatus, so it is set from M-mode around the U-mode probes; the
    MXR=0 half of the cross is already supplied by pass A.
    """
    lines = [comment_banner(f"{prefix}: mstatus.MXR=1 suppresses pointer masking")]
    lines += ["RVTEST_GOTO_MMODE", *_set_mxr(True, regs.tmp), "RVTEST_TSBI_GOTO_UMODE"]
    lines += _load_base("bare", "lo", regs)
    for upper in _UPPER_PATTERNS:
        lines += _tag_address(upper, regs)
        lines += _probe_load("lw", _tid(f"{prefix}_mxr", upper, "lw"), td, regs, CP_MXR)
        lines += _probe_store("sw", "lw", _tid(f"{prefix}_mxr", upper, "sw"), td, regs, CP_MXR)
    return lines


def _pass_e_jalr(prefix: str, td: TestData, regs: Regs, mxr: int) -> list[str]:
    """JALR through a tagged pointer.

    Pointer masking never applies to instruction fetch, so every non-zero tag
    must produce a fetch fault rather than jumping to the masked address. The
    landing pad bumps the check register, so the signature separates "the pad
    ran" (1) from "the fetch faulted" (0); the trap record carries the cause and
    the unmasked target. On a fetch fault the handler resumes at ra, which the
    JALR itself has already set to the instruction after the probe.
    """
    lines = [comment_banner(f"{prefix}: JALR through a tagged pointer, MXR={mxr} (fetch is never masked)")]
    lines.append(f"LA(x{regs.base}, pm_jalr_pad)")
    for upper in _UPPER_PATTERNS:
        lines += _tag_address(upper, regs)
        lines += [
            f"li x{regs.chk}, 0   # the pad sets this to 1 if the fetch succeeded",
            td.add_testcase(_tid(f"{prefix}_mxr{mxr}", upper, "jalr"), CP_JALR, COVERGROUP),
            *_fixed(f"jalr ra, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
    lines += _load_base("bare", "lo", regs)
    return lines


def _pass_f_fault_address(prefix: str, td: TestData, regs: Regs) -> list[str]:
    """sw/lw whose masked address is the model's guaranteed-faulting address.

    The probe address is (tag << 48) | RVMODEL_ACCESS_FAULT_ADDRESS, so the low
    48 bits are identical for every tag -- which is what lets the `illegal_addr`
    coverpoint cross with all eight `a_upper_bits` bins. The access always
    faults; what is under test is that xtval holds the *masked* address.
    """
    lines = [comment_banner(f"{prefix}: masked address resolves to the model's access-fault address")]
    lines.append("#ifdef RVMODEL_ACCESS_FAULT_ADDRESS")
    lines.append(f"LI(x{regs.base}, RVMODEL_ACCESS_FAULT_ADDRESS)")
    for upper in _UPPER_PATTERNS:
        lines += _tag_address(upper, regs)
        lines += [
            *_sentinel(regs),
            td.add_testcase(_tid(f"{prefix}_flt", upper, "lw"), CP_FAULT, COVERGROUP),
            *_fixed(f"lw x{regs.chk}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
            _li(regs.data, VALUE_NEW),
            *_sentinel(regs),
            td.add_testcase(_tid(f"{prefix}_flt", upper, "sw"), CP_FAULT, COVERGROUP),
            *_fixed(f"sw x{regs.data}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
    lines.append("#endif // RVMODEL_ACCESS_FAULT_ADDRESS")
    lines += _load_base("bare", "lo", regs)
    return lines


# ---------------------------------------------------------------------------
# One file per satp mode
# ---------------------------------------------------------------------------


def _emit_mode_file(mode: str, td: TestData, regs: Regs) -> list[str]:
    guard = _SATP_GUARD[mode]
    lines: list[str] = []
    if guard:
        lines.append(f"#ifdef {guard}")

    lines += _data_section(mode)
    lines += [
        "# Bracket the U-mode-executable text on 4 KiB boundaries. The U bit is per page,",
        "# and rvtest_code_end lands mid-page with the trap handlers, so deriving the range",
        "# from it would mark the handler page U=1 and make it unfetchable from S-mode.",
        ".p2align 12",
        "pm_utext_begin:",
    ]
    lines += [
        comment_banner(
            f"Ssnpm pointer masking -- satp={mode.upper()}",
            "senvcfg.PMM is programmed from M-mode; every probe runs in U-mode.",
        ),
        "",
        "# Landing pad for the JALR probes. Reached only when the tagged target",
        "# happens to be a legal, mapped, executable address -- which is exactly what",
        "# pointer masking must NOT arrange for a tagged pointer.",
        "j pm_jalr_pad_end",
        "pm_jalr_pad:",
        f"addi x{regs.chk}, x{regs.chk}, 1",
        "jr ra",
        "pm_jalr_pad_end:",
    ]
    lines += _mmode_prelude(mode, regs)

    for pmm_val, pmlen, pmm_label in _PMM_CONFIGS:
        prefix = f"{pmm_label}_{mode}"
        lines.append(comment_banner(f"PMM={pmm_val:#04b} (PMLEN={pmlen}), satp={mode.upper()}"))
        lines += ["RVTEST_GOTO_MMODE", *_set_pmm(pmm_val, pmlen, regs.tmp), *_set_mxr(False, regs.tmp)]
        lines.append("RVTEST_TSBI_GOTO_UMODE")
        lines += _load_base(mode, "lo", regs)

        lines += _pass_a_all_instructions(prefix, td, regs)
        if mode != "bare":
            lines += _pass_b_sign_extension(prefix, mode, td, regs)
        lines += _pass_c_misaligned(prefix, td, regs)
        lines += _pass_e_jalr(prefix, td, regs, mxr=0)
        lines += _pass_f_fault_address(prefix, td, regs)
        lines += _pass_d_mxr(prefix, td, regs)
        lines += _pass_e_jalr(prefix, td, regs, mxr=1)

        lines += ["RVTEST_GOTO_MMODE", *_set_mxr(False, regs.tmp)]

    lines += _teardown(regs)
    lines += [".p2align 12", "pm_utext_end:"]
    if guard:
        lines.append(f"#endif // {guard}")
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["Ssnpm"],
    # Under an active satp most tag patterns cannot survive masking, so nearly every
    # probe traps and the trap signature outgrows the default budget.
    extra_defines=["#define TRAP_SIGUPD_COUNT 40000"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_ssnpm(test_data: TestData) -> list[TestChunk]:
    """Generate the Ssnpm pointer-masking tests for every supported satp mode."""
    test_chunks: list[TestChunk] = []

    # x8-x15 for the four registers that have to be encodable in compressed
    # CL/CS operands; the remaining two come from the general pool.
    a, data, chk, tmp = test_data.int_regs.get_registers(4, reg_range=list(range(8, 16)))
    tmp2, base = test_data.int_regs.get_registers(2)
    fp = test_data.float_regs.get_register()
    fp_c = test_data.float_regs.get_register(reg_range=list(range(8, 16)))
    regs = Regs(base=base, a=a, data=data, chk=chk, tmp=tmp, tmp2=tmp2, fp=fp, fp_c=fp_c)

    for mode in _SATP_MODES:
        tc = test_data.begin_test_chunk(split_name=mode)
        tc.code = _emit_mode_file(mode, test_data, regs)
        test_chunks.append(test_data.end_test_chunk())

    test_data.int_regs.return_registers([base, a, data, chk, tmp, tmp2])
    test_data.float_regs.return_registers([fp, fp_c])
    return test_chunks
