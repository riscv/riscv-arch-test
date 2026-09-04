##################################
# priv/extensions/ZicfissCommon.py
#
# Shared helpers for the Zicfiss (shadow stack) test generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared helpers for the Zicfiss shadow stack test generators.

Register constraints
--------------------
SSPUSH/SSPOPCHK are architecturally defined only for x1 and x5, but the ACT
framework already owns both: x1 is the call return address (reserved in
``priv_exclude_regs``) and x5 is ``link_reg``, used as a scratch pointer inside
``RVTEST_SIGUPD``. Every SS sequence therefore brackets itself with
``save_link_regs`` / ``restore_link_regs`` and only calls ``write_sigupd`` once
x1/x5 have been restored.

Encoding width
--------------
With Zcmop enabled the assembler compresses ``sspush x1`` to ``c.sspush x1`` and
``sspopchk x5`` to ``c.sspopchk x5``. The covergroups have distinct bins for the
32-bit and 16-bit encodings, so the 32-bit forms must be emitted inside
``.option norvc`` or those bins can never fill. ``ss_insn`` handles this.

Page-table layout
-----------------
Three leaf pages share one Sv39/Sv32 leaf table so a single PTE chain covers all
of them:
  _VA_SS   — the shadow stack page,  pte.xwr = 010
  _VA_RW   — an ordinary read/write page, pte.xwr = 011
  _VA_RO   — a read-only page, pte.xwr = 001
"""

from __future__ import annotations

from collections.abc import Callable

from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

# ---------------------------------------------------------------------------
# Virtual addresses (page-aligned, sharing one leaf page table)
# ---------------------------------------------------------------------------

VA_SS_RV64 = 0x140300000
VA_RW_RV64 = 0x140301000
VA_RO_RV64 = 0x140302000
# Deliberately NOT mapped by map_zicfiss_pages: used to make a shadow stack pop's
# load fault so the memory fault can be shown to outrank the software-check
# exception. The walk fails at level 1, so no leaf PTE is read.
VA_UNMAPPED_RV64 = 0x140400000

VA_SS_RV32 = 0xC0300000
VA_RW_RV32 = 0xC0301000
VA_RO_RV32 = 0xC0302000
VA_UNMAPPED_RV32 = 0xC0400000

# PTE permission encodings. pte.xwr occupies bits [3:1]; V is bit 0.
PTE_SS = "PTE_D | PTE_A | PTE_W | PTE_V"  # xwr = 010, the SS page encoding
PTE_RW = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_V"  # xwr = 011
PTE_RO = "PTE_D | PTE_A | PTE_R | PTE_V"  # xwr = 001

# menvcfg/senvcfg/henvcfg SSE field is bit 3.
SSE_BIT = 3

# Guard for testcases that perform a translated access through a leaf PTE with the
# shadow stack encoding (pte.xwr=010).
#
# sail-riscv 0.13.1 aborts with "Assertion failed: sys/vmem_pte.sail:148.24-148.25"
# when its page-table walker resolves such a PTE, so those testcases cannot currently
# have a reference signature generated. Everything else in the Zicfiss suites — the
# ssp CSR, the enable-chain gating, the Zimop-revert behaviour, and SS instructions
# aimed at non-SS pages — is unaffected and runs today.
#
# The guard is deliberately NOT defined anywhere in-tree. Define it (or delete the
# guard entirely) once the reference model handles the SS page encoding. See
# sail-zicfiss-bug/BUG_REPORT.md for a standalone reproducer.
SS_PAGE_GUARD = "ZICFISS_SS_PAGE_REF_MODEL_OK"


def guard_ss_page(lines: list[str], *, reason: str) -> list[str]:
    """Wrap a block that performs a translated access through an SS page (pte.xwr=010)."""
    return [
        f"#ifdef {SS_PAGE_GUARD}  // blocked on sail-riscv vmem_pte.sail:148 — {reason}",
        *lines,
        f"#endif  // {SS_PAGE_GUARD}",
    ]


GOTO_UMODE = "RVTEST_TSBI_GOTO_UMODE  # enter U-mode"
GOTO_SMODE = "RVTEST_TSBI_GOTO_SMODE  # enter S-mode"
GOTO_MMODE = "RVTEST_TSBI_GOTO_MMODE  # return to M-mode"

# ---------------------------------------------------------------------------
# Privileged CSR access
# ---------------------------------------------------------------------------

# Lowest privilege mode that may execute a CSR access directly. Anything below it goes
# through the T-SBI handler instead, so every CSR listed here must also appear in
# tsbi_instr_table (tests/env/rvtest_trap_handler.h). medeleg is deliberately absent
# from both: it is M-mode-only and a lower mode cannot reach it at all.
_CSR_MIN_MODE = {
    "menvcfg": "M",
    "satp": "S",
    "senvcfg": "S",
    "sstatus": "S",
}

_MODE_RANK = {"U": 0, "S": 1, "M": 2}


def priv_csr(instr: str, mode: str) -> str:
    """Emit a privileged CSR access, directly or through T-SBI.

    ``mode`` is the privilege mode the instruction executes in. When that mode owns the
    CSR the instruction is emitted verbatim; otherwise it is marshalled through
    ``tsbi_call``, which hands the encoding to the M-mode handler. Only the CSRs in
    ``_CSR_MIN_MODE`` are recognized — anything else raises here rather than emitting an
    access the mode cannot perform, or a T-SBI call the handler cannot service.
    """
    mnemonic, first, second = (token.strip(" ,") for token in instr.split("#", 1)[0].split(None, 2))
    csr = second.split(",")[0].strip() if mnemonic.lower() == "csrr" else first
    return instr if _MODE_RANK[mode] >= _MODE_RANK[_CSR_MIN_MODE[csr]] else tsbi_call(instr)


# ---------------------------------------------------------------------------
# Instruction emission
# ---------------------------------------------------------------------------


def ss_insn(mnemonic: str, *, compressed: bool = False) -> list[str]:
    """Emit one SS instruction, pinning its encoding width.

    The assembler will happily compress ``sspush x1`` / ``sspopchk x5``, which would
    leave the 32-bit covergroup bins unreachable. Wrap the uncompressed forms in
    ``.option norvc`` and spell the compressed forms explicitly.
    """
    if compressed:
        return [f"{mnemonic}"]
    return [".option push", ".option norvc", mnemonic, ".option pop"]


def save_link_regs(test_data: TestData) -> tuple[int, int, list[str]]:
    """Save x1 and x5 into freshly allocated registers.

    Returns (save_x1, save_x5, lines). The caller must pass both back to
    ``restore_link_regs`` and return them to the allocator.
    """
    save_x1, save_x5 = test_data.int_regs.get_registers(2)
    return (
        save_x1,
        save_x5,
        [
            f"mv x{save_x1}, x1   # preserve framework return address",
            f"mv x{save_x5}, x5   # preserve RVTEST_SIGUPD link register",
        ],
    )


def restore_link_regs(save_x1: int, save_x5: int) -> list[str]:
    """Restore x1 and x5 after an SS sequence."""
    return [
        f"mv x1, x{save_x1}   # restore framework return address",
        f"mv x5, x{save_x5}   # restore RVTEST_SIGUPD link register",
    ]


# ---------------------------------------------------------------------------
# SSE enable-chain control
# ---------------------------------------------------------------------------


def set_envcfg_sse(csr: str, value: int, test_data: TestData, *, mode: str) -> list[str]:
    """Set or clear the SSE field of menvcfg/senvcfg.

    ``mode`` is the privilege mode this runs in; an access the mode cannot perform is
    routed through T-SBI.
    """
    reg = test_data.int_regs.get_register()
    op = "csrs" if value else "csrc"
    lines = [
        f"LI(x{reg}, {hex(1 << SSE_BIT)})   # {csr}.SSE",
        priv_csr(f"{op} {csr}, x{reg}   # {'set' if value else 'clear'} {csr}.SSE", mode),
    ]
    test_data.int_regs.return_registers([reg])
    return lines


# ---------------------------------------------------------------------------
# Page-table setup
# ---------------------------------------------------------------------------


def page_table_data_section() -> list[str]:
    """Declare the page-table and backing-page labels used by the Zicfiss tests.

    Emitted once per generated file. Test chunks are distributed across files when a
    suite is split, so the block guards itself with .ifndef and is prepended to every
    chunk rather than living in a chunk of its own.
    """
    return [
        "",
        ".ifndef rvtest_zicfiss_pages_declared",
        ".set rvtest_zicfiss_pages_declared, 1",
        ".pushsection .data",
        "#ifdef SV39_SUPPORTED",
        ".p2align 12",
        "rvtest_slvl1_pg_tbl: .zero 4096",
        ".p2align 12",
        "rvtest_uimg_lvl1_pg_tbl:    .zero 4096   # Sv39 level-1 table for the test image",
        "#endif  // SV39_SUPPORTED",
        "#if defined(SV39_SUPPORTED) || defined(SV32_SUPPORTED)",
        ".p2align 12",
        "rvtest_slvl0_pg_tbl: .zero 4096",
        ".p2align 12",
        "rvtest_uimg_lvl0_pg_tbl:    .zero 4096   # 4 KiB leaves for the test image itself",
        ".p2align 3",
        "rvtest_uimg_mapped:         .zero 8      # set once the image map has been built",
        ".p2align 12",
        "rvtest_zicfiss_ss_page:     .zero 4096   # mapped as an SS page (xwr=010)",
        ".p2align 12",
        "rvtest_zicfiss_rw_page:     .zero 4096   # mapped read/write (xwr=011)",
        ".p2align 12",
        "rvtest_zicfiss_ro_page:     .zero 4096   # mapped read-only (xwr=001)",
        "#endif  // SV39_SUPPORTED || SV32_SUPPORTED",
        ".popsection",
        ".endif",
        "",
    ]


def _identity_map(xlen: int, *, user: bool = True) -> list[str]:
    """Identity superpage covering code+data, PC-relative so it survives any link address.

    Hand-rolled rather than SUPERPAGE_PTE_SETUP_* because that macro needs a constant
    VA, and we must map whatever PA the linker chose for rvtest_code_begin back to itself.

    ``user`` adds PTE_U. It is required whenever the testcases execute in U-mode: without
    it the first U-mode instruction fetch takes an instruction page fault, and the S-mode
    handler's fetch-fault recovery resumes at x1, which loops forever on the poison value.
    """
    if xlen == 64:
        shift, mask_bits, idx_mask, ent_shift, store = 30, 30, "0x1FF", 3, "sd"
    else:
        shift, mask_bits, idx_mask, ent_shift, store = 22, 22, "0x3FF", 2, "sw"
    perms = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V" + (" | PTE_U" if user else "")
    return [
        f"# Sv{'39' if xlen == 64 else '32'}: identity superpage for code+data",
        "auipc t0, 0",
        f"li t1, ~((1 << {mask_bits}) - 1)",
        "and t0, t0, t1",
        "srli t0, t0, 12",
        "slli t0, t0, 10",
        f"li t1, ({perms})",
        "or t0, t0, t1",
        "LA(t2, rvtest_Sroot_pg_tbl)",
        "LA(t1, rvtest_code_begin)",
        f"srli t1, t1, {shift}",
        f"andi t1, t1, {idx_mask}",
        f"slli t1, t1, {ent_shift}",
        "add t2, t2, t1",
        f"{store} t0, 0(t2)",
        "sfence.vma",
    ]


# Perms carried by every page of the identity map: D|A|R|W|X|V, matching the superpage the
# boot code installs. PTE_U (0x10) is added per page by _umode_image_map.
_IMAGE_PERMS = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V"


def code_end_page_align() -> list[str]:
    """Pad to a page boundary so ``rvtest_code_end`` lands page-aligned.

    Appended to every test chunk, so whichever chunk ends up last in a file leaves the
    framework's trap handlers -- which the linker places immediately after
    ``rvtest_code_end``, inside .text.rvtest -- starting on a fresh page.
    ``_umode_image_map`` relies on that to keep the handlers off user pages.
    """
    return ["", "# Page-align rvtest_code_end so the trap handlers start on their own page.", ".p2align 12", ""]


def _umode_image_map(xlen: int) -> list[str]:
    """Identity-map the test image at 4 KiB granularity, splitting user from supervisor.

    U-mode has to fetch the test body and write the signature area, while the trap handler
    that boot-time delegation sends S-mode traps to has to fetch its own code -- and S-mode
    cannot execute from a user page (SUM covers loads and stores, never instruction fetch).
    The framework's own layout already separates the two: the handlers follow
    ``rvtest_code_end`` inside .text.rvtest, and the signature area follows
    ``rvtest_data_begin``. So

      [image start, rvtest_code_end)   PTE_U -- the test body, fetched from U-mode
      [rvtest_code_end, data page)     supervisor only -- trap handlers and save areas
      [data page, _end)                PTE_U -- test data and the signature region

    where ``data page`` is ``rvtest_data_begin`` rounded down. The handler still writes trap
    signatures into the user-mapped signature region, which is why the caller also sets
    ``sstatus.SUM``.

    Emitted with translation disabled; the root entry is written last either way. One leaf
    table covers 2 MiB (Sv39) or 4 MiB (Sv32), which is far more than a priv test image needs
    -- anything past it is simply left unmapped rather than silently mismapped.
    """
    if xlen == 64:
        store, ent_shift, idx_mask, lvl_shift = "sd", 3, "0x1FF", 30
    else:
        store, ent_shift, idx_mask, lvl_shift = "sw", 2, "0x3FF", 22

    lines = [
        f"# Sv{'39' if xlen == 64 else '32'}: 4 KiB identity map, user pages only where U-mode needs them",
        "# Built once per test file: the tables persist across sections, and satp being",
        "# cleared between sections does not disturb them.",
        "LA(t0, rvtest_uimg_mapped)",
        "LREG t1, 0(t0)",
        "bnez t1, 9f",
        "LA(t0, rvtest_code_begin)",
        "srli t0, t0, 12",
        "slli t0, t0, 12",
        "# t2 = &leaf[index of the first page]",
        "LA(t2, rvtest_uimg_lvl0_pg_tbl)",
        "srli t1, t0, 12",
        f"andi t1, t1, {idx_mask}",
        f"slli t1, t1, {ent_shift}",
        "add t2, t2, t1",
        "LA(t1, _end)",
        "LA(t3, rvtest_code_end)   # first page that must not be user-executable",
        "LA(t4, rvtest_data_begin)",
        "srli t4, t4, 12",
        "slli t4, t4, 12          # first page of the user-writable data region",
        "li t6, 4096",
        "1:",
        "bgeu t0, t1, 2f",
        "srli t5, t0, 12",
        "slli t5, t5, 10",
        f"ori t5, t5, ({_IMAGE_PERMS})",
        "bltu t0, t3, 3f          # in the test body -> user",
        "bltu t0, t4, 4f          # handlers and save areas -> supervisor only",
        "3:",
        "ori t5, t5, PTE_U",
        "4:",
        f"{store} t5, 0(t2)",
        f"addi t2, t2, {1 << ent_shift}",
        "add t0, t0, t6",
        "j 1b",
        "2:",
    ]

    if xlen == 64:
        lines.extend(
            [
                "# Link the leaf table into the level-1 table",
                "LA(t5, rvtest_uimg_lvl0_pg_tbl)",
                "srli t5, t5, 12",
                "slli t5, t5, 10",
                "ori t5, t5, PTE_V",
                "LA(t2, rvtest_uimg_lvl1_pg_tbl)",
                "LA(t1, rvtest_code_begin)",
                "srli t1, t1, 21",
                "andi t1, t1, 0x1FF",
                "slli t1, t1, 3",
                "add t2, t2, t1",
                "sd t5, 0(t2)",
                "# Link the level-1 table into the root",
                "LA(t5, rvtest_uimg_lvl1_pg_tbl)",
            ]
        )
    else:
        lines.append("LA(t5, rvtest_uimg_lvl0_pg_tbl)")

    lines.extend(
        [
            "srli t5, t5, 12",
            "slli t5, t5, 10",
            "ori t5, t5, PTE_V",
            "LA(t2, rvtest_Sroot_pg_tbl)",
            "LA(t1, rvtest_code_begin)",
            f"srli t1, t1, {lvl_shift}",
            f"andi t1, t1, {idx_mask}",
            f"slli t1, t1, {ent_shift}",
            "add t2, t2, t1",
            f"{store} t5, 0(t2)",
            "LA(t0, rvtest_uimg_mapped)",
            "li t1, 1",
            "SREG t1, 0(t0)",
            "9:",
        ]
    )
    return lines


def set_sum() -> list[str]:
    """Set sstatus.SUM so the delegated S-mode trap handler can reach user pages.

    The handler records trap signatures in the signature region, which _umode_image_map maps
    user-accessible for RVTEST_SIGUPD. sstatus is an S-mode CSR, so this needs no help from
    M-mode. None of the U/V covergroups sample SUM, so pinning it costs no coverage.

    Uses t0 rather than an allocated register, like the page-table setup around it, so the
    register numbering of the testcases themselves is unaffected.
    """
    return [
        f"LI(t0, {hex(1 << 18)})   # sstatus.SUM",
        "csrs sstatus, t0   # let the S-mode handler reach the user-mapped signature area",
    ]


def identity_map_only(xlen: int, *, user: bool = False) -> list[str]:
    """Identity-map code+data without creating any shadow stack page.

    Used by the M-mode suite, which needs satp to be non-Bare for one coverage bin but
    never performs a translated access (M-mode does not translate), and therefore must
    not create an SS-page mapping at all.
    """
    return _identity_map(xlen, user=user)


def map_zicfiss_pages(xlen: int, *, ss_perms: str = PTE_SS, user: bool = True) -> list[str]:
    """Wire up the PTE chain mapping the SS / RW / RO pages.

    ``ss_perms`` lets a caller remap the shadow stack page with a different
    encoding (e.g. PTE_RO) to exercise the wrong-page-type coverpoints.
    ``user`` adds PTE_U to every leaf, required when the testcases run in U-mode, and
    selects the split 4 KiB image map over the plain supervisor superpage.
    """
    u = " | PTE_U" if user else ""
    if xlen == 64:
        setup, va_ss, va_rw, va_ro = "PTE_SETUP_SV39", VA_SS_RV64, VA_RW_RV64, VA_RO_RV64
        chain = [
            f"{setup}(rvtest_slvl1_pg_tbl, (PTE_V), {hex(va_ss)}, LEVEL2)",
            f"{setup}(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va_ss)}, LEVEL1)",
        ]
    else:
        setup, va_ss, va_rw, va_ro = "PTE_SETUP_SV32", VA_SS_RV32, VA_RW_RV32, VA_RO_RV32
        chain = [f"{setup}(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va_ss)}, LEVEL1)"]

    return [
        *(_umode_image_map(xlen) if user else _identity_map(xlen, user=False)),
        *chain,
        f"{setup}(rvtest_zicfiss_ss_page, ({ss_perms}{u}), {hex(va_ss)}, LEVEL0)",
        f"{setup}(rvtest_zicfiss_rw_page, ({PTE_RW}{u}), {hex(va_rw)}, LEVEL0)",
        f"{setup}(rvtest_zicfiss_ro_page, ({PTE_RO}{u}), {hex(va_ro)}, LEVEL0)",
        "sfence.vma",
    ]


def satp_setup(xlen: int) -> list[str]:
    """Enable translation for the given XLEN."""
    return ["SATP_SETUP_RV64(sv39)"] if xlen == 64 else ["SATP_SETUP_SV32"]


def satp_on_from_umode(xlen: int) -> list[str]:
    """Turn translation on from U-mode, through T-SBI.

    satp cannot be written by the S-mode setup code itself: that code lives in the test
    body, which _umode_image_map marks user-executable so U-mode can fetch it, and S-mode
    cannot fetch from a user page. Writing satp in S-mode therefore faults on the very next
    instruction. Handing the write to the T-SBI handler -- which runs in M-mode, untranslated
    -- and returning into U-mode means the first translated fetch is a U-mode one, on a user
    page, which is exactly what the map provides.

    The value is computed in U-mode with plain arithmetic; only the CSR write needs help.
    Uses t0/t1 rather than allocated registers so the testcases keep their own numbering.
    """
    mode_bits = "(SATP64_MODE) & (SATP_MODE_SV39 << 60)" if xlen == 64 else "SATP32_MODE"
    return [
        "# Enable translation from U-mode via T-SBI; see satp_on_from_umode",
        "LA(t0, rvtest_Sroot_pg_tbl)",
        "srli t0, t0, 12",
        f"LI(t1, {mode_bits})",
        "or t0, t0, t1",
        tsbi_call("csrw satp, t0"),
    ]


def satp_off_from_umode() -> list[str]:
    """Turn translation back off from U-mode, through T-SBI."""
    return [
        "# Disable translation from U-mode via T-SBI",
        tsbi_call("csrw satp, x0"),
    ]


def teardown_vm(mode: str) -> list[str]:
    """Disable translation and leave the hart back in the suite's boot mode.

    ``mode`` is the boot mode of the suite, and every section is expected to both start
    and end there. A U-mode suite never leaves U-mode here: it drops translation through a
    T-SBI satp write, and the next section's prologue does the sfence.vma while translation
    is already off.
    """
    if mode == "S":
        return ["csrwi satp, 0", "sfence.vma", ""]
    if mode == "M":
        return [GOTO_MMODE, "csrwi satp, 0", "sfence.vma", ""]
    return [*satp_off_from_umode(), ""]


def both_xlens(build: Callable[[int], list[str]]) -> list[str]:
    """Emit ``build(64)`` and ``build(32)`` inside the XLEN and Sv-mode guards.

    Both branches are always emitted; the preprocessor selects one at build time.
    """
    return [
        "#if __riscv_xlen == 64",
        "#ifdef SV39_SUPPORTED",
        *build(64),
        "#endif  // SV39_SUPPORTED",
        "#else",
        "#ifdef SV32_SUPPORTED",
        *build(32),
        "#endif  // SV32_SUPPORTED",
        "#endif  // __riscv_xlen",
    ]


def va_for(xlen: int) -> tuple[int, int, int]:
    """Return (ss_va, rw_va, ro_va) for the given XLEN."""
    if xlen == 64:
        return VA_SS_RV64, VA_RW_RV64, VA_RO_RV64
    return VA_SS_RV32, VA_RW_RV32, VA_RO_RV32


def va_unmapped(xlen: int) -> int:
    """Return the deliberately unmapped VA for the given XLEN."""
    return VA_UNMAPPED_RV64 if xlen == 64 else VA_UNMAPPED_RV32


def set_ssp(va: int, test_data: TestData, *, offset: int = 0) -> tuple[int, list[str]]:
    """Point ssp at ``va + offset``. Returns the register holding the address."""
    reg = test_data.int_regs.get_register()
    lines = [f"LI(x{reg}, {hex(va + offset)})", f"csrw ssp, x{reg}"]
    return reg, lines
