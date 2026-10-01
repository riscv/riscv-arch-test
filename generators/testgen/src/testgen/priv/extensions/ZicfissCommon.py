##################################
# priv/extensions/ZicfissCommon.py
#
# Shared helpers for the Zicfiss (shadow stack) test generators.
# umer@riscv.org September 2026
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

Compressed encodings
--------------------
The tests are assembled without Zca or Zcmop, so every instruction keeps its 32-bit
encoding. The compressed shadow stack instructions exist only with Zcmop: ``ss_instr``
enables Zcmop around each one, and ``zcmop_only`` guards its testcase with
``#ifdef ZCMOP_SUPPORTED``.

XLEN
----
Every test body is emitted once. The XLEN-dependent values -- the virtual addresses,
the page-table geometry and satp.MODE -- are preprocessor symbols defined by
``page_table_data_section`` from the translation mode the configuration supports:
Sv39 on RV64 and Sv32 on RV32. A configuration with neither skips the tests that
need translation (``ZICFISS_VM_SUPPORTED`` undefined).

Page-table layout
-----------------
Three leaf pages share one leaf page table so a single PTE chain covers all of them:
  ZICFISS_VA_SS -- the shadow stack page,  pte.xwr = 010
  ZICFISS_VA_RW -- an ordinary read/write page, pte.xwr = 011
  ZICFISS_VA_RO -- a read-only page, pte.xwr = 001
ZICFISS_VA_UNMAPPED is deliberately left unmapped, and its walk fails above the leaf level.
"""

from typing import NamedTuple

from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

# PTE permission encodings. pte.xwr occupies bits [3:1]; V is bit 0.
PTE_SS = "PTE_D | PTE_A | PTE_W | PTE_V"  # xwr = 010, the SS page encoding
PTE_RW = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_V"  # xwr = 011
PTE_RO = "PTE_D | PTE_A | PTE_R | PTE_V"  # xwr = 001
# Every pte.xwr encoding. 000 at the last level is a pointer where a leaf is required, and
# 110 is reserved; both fail the walk.
XWR_PERMS = {
    "000": "PTE_V",
    "001": PTE_RO,
    "010": PTE_SS,
    "011": PTE_RW,
    "100": "PTE_D | PTE_A | PTE_X | PTE_V",
    "101": "PTE_D | PTE_A | PTE_X | PTE_R | PTE_V",
    "110": "PTE_D | PTE_A | PTE_X | PTE_W | PTE_V",
    "111": "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V",
}

# SSAMOSWAP follows the A-extension alignment rules, but the spec does not say whether the misaligned
# atomicity granule applies to it (https://github.com/riscv/riscv-isa-manual/issues/3425): Sail honors
# the granule and executes such an access, while Spike, QEMU and Whisper fault. The alignment sweep
# starts 8 bytes into a 16-byte granule so that every misaligned access crosses it and must fault.
# SSAMOSWAP.W with addr[2:0] of 1-3 cannot cross, so it is left out until that issue is resolved.
SSAMOSWAP_SWEEP_BASE = 0x408


def ssamoswap_sweep_offsets(width: str) -> list[int]:
    """addr[2:0] values swept for SSAMOSWAP.W ("w") or SSAMOSWAP.D ("d"); see SSAMOSWAP_SWEEP_BASE."""
    return [0, 4, 5, 6, 7] if width == "w" else list(range(8))


class SsForm(NamedTuple):
    """One encoding of a shadow stack push, pop or SSRDP."""

    mnemonic: str  # assembly, e.g. "sspush x1"
    link_reg: str | None  # "x1" or "x5", the register pushed or compared; None for SSRDP
    name: str  # used in testcase labels
    compressed: bool  # a Zcmop encoding (c.sspush / c.sspopchk)


PUSH_FORMS = [
    SsForm("sspush x1", "x1", "sspush_x1", compressed=False),
    SsForm("sspush x5", "x5", "sspush_x5", compressed=False),
    SsForm("c.sspush x1", "x1", "c_sspush_x1", compressed=True),
]
POP_FORMS = [
    SsForm("sspopchk x1", "x1", "sspopchk_x1", compressed=False),
    SsForm("sspopchk x5", "x5", "sspopchk_x5", compressed=False),
    SsForm("c.sspopchk x5", "x5", "c_sspopchk_x5", compressed=True),
]
# The MOP-encoded instructions, which revert to Zimop/Zcmop behaviour while Zicfiss is
# inactive. SSAMOSWAP is AMO-encoded and traps instead.
MOP_FORMS = [*PUSH_FORMS, *POP_FORMS, SsForm("ssrdp", None, "ssrdp", compressed=False)]


def ss_instr(form: SsForm) -> list[str]:
    """The instruction for ``form``, with Zcmop enabled around it if it is a compressed form."""
    if form.compressed:
        return [".option push", ".option arch, +zcmop", form.mnemonic, ".option pop"]
    return [form.mnemonic]


def zcmop_only(compressed: bool, lines: list[str]) -> list[str]:
    """Return ``lines``, guarded on Zcmop when they use a compressed form."""
    return ["#ifdef ZCMOP_SUPPORTED", *lines, "#endif"] if compressed else lines


def ss_forms_against(
    test_data: TestData, forms: list[SsForm], addr: str, value: str, tag: str, coverpoint: str, cg: str
) -> list[str]:
    """One testcase per push/pop form: ssp = ``addr`` and the form's link register = ``value``."""
    addr_reg = test_data.int_regs.get_register()
    lines: list[str] = []
    for form in forms:
        case = [
            f"LI(x{addr_reg}, {addr})",
            f"csrw ssp, x{addr_reg}",
            f"LI({form.link_reg}, {value})",
            test_data.add_testcase(f"{form.name}_{tag}", coverpoint, cg),
            *ss_instr(form),
        ]
        lines.extend(zcmop_only(form.compressed, case))
    test_data.int_regs.return_registers([addr_reg])
    return lines


def rv64_only(width: str, lines: list[str]) -> list[str]:
    """Return ``lines``, guarded to RV64 when ``width`` is "d" (SSAMOSWAP.D is RV64-only)."""
    return lines if width == "w" else ["#if __riscv_xlen == 64", *lines, "#endif"]


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


def set_envcfg_sse(csr: str, value: int, test_data: TestData, *, mode: str) -> list[str]:
    """Set or clear the SSE field of menvcfg or senvcfg.

    ``mode`` is the privilege mode this runs in. menvcfg below M-mode, and senvcfg in
    U-mode, are written through T-SBI.
    """
    reg = test_data.int_regs.get_register()
    op = "csrs" if value else "csrc"
    instr = f"{op} {csr}, x{reg}   # {'set' if value else 'clear'} {csr}.SSE"
    direct = mode == "M" or (mode == "S" and csr == "senvcfg")
    lines = [f"LI(x{reg}, {csr.upper()}_SSE)", instr if direct else tsbi_call(instr)]
    test_data.int_regs.return_registers([reg])
    return lines


def page_table_data_section() -> list[str]:
    """XLEN-dependent symbols, plus the page-table and backing-page labels.

    Prepended to every test chunk, because chunks are distributed across files when a
    suite is split. The #defines may repeat; the data block is guarded by .ifndef.
    """
    return [
        "",
        "#if defined(SV39_SUPPORTED)",
        "#define ZICFISS_VM_SUPPORTED",
        "#define ZICFISS_VA_SS       0x140300000",
        "#define ZICFISS_VA_RW       0x140301000",
        "#define ZICFISS_VA_RO       0x140302000",
        "#define ZICFISS_VA_UNMAPPED 0x140400000   // not mapped: the walk fails at level 1",
        "#define ZICFISS_PTE_SETUP(PA, PERMS, VA, LEVEL) PTE_SETUP_SV39(PA, PERMS, VA, LEVEL)",
        "#define ZICFISS_SATP_SETUP  SATP_SETUP_RV64(sv39)",
        "#define ZICFISS_SATP_MODE   ((SATP64_MODE) & (SATP_MODE_SV39 << 60))",
        "#define ZICFISS_ROOT_SHIFT  30      // VA shift of the root-level VPN",
        "#define ZICFISS_VPN_MASK    0x1FF",
        "#define ZICFISS_PTE_LOG2    3       // log2 of the PTE size",
        "#elif defined(SV32_SUPPORTED)",
        "#define ZICFISS_VM_SUPPORTED",
        "#define ZICFISS_VA_SS       0xC0300000",
        "#define ZICFISS_VA_RW       0xC0301000",
        "#define ZICFISS_VA_RO       0xC0302000",
        "#define ZICFISS_VA_UNMAPPED 0xC0400000    // not mapped: the walk fails at level 1",
        "#define ZICFISS_PTE_SETUP(PA, PERMS, VA, LEVEL) PTE_SETUP_SV32(PA, PERMS, VA, LEVEL)",
        "#define ZICFISS_SATP_SETUP  SATP_SETUP_SV32",
        "#define ZICFISS_SATP_MODE   SATP32_MODE",
        "#define ZICFISS_ROOT_SHIFT  22",
        "#define ZICFISS_VPN_MASK    0x3FF",
        "#define ZICFISS_PTE_LOG2    2",
        "#endif",
        ".ifndef rvtest_zicfiss_pages_declared",
        ".set rvtest_zicfiss_pages_declared, 1",
        ".pushsection .data",
        "#ifdef ZICFISS_VM_SUPPORTED",
        "#ifdef SV39_SUPPORTED",
        ".p2align 12",
        "rvtest_slvl1_pg_tbl: .zero 4096",
        ".p2align 12",
        "rvtest_uimg_lvl1_pg_tbl:    .zero 4096   # Sv39 level-1 table for the test image",
        "#endif",
        ".p2align 12",
        "rvtest_slvl0_pg_tbl: .zero 4096",
        ".p2align 12",
        "rvtest_uimg_lvl0_pg_tbl:    .zero 4096   # 4 KiB leaves for the test image itself",
        ".p2align 3",
        "rvtest_uimg_mapped:         .zero 8      # set once the image map has been built",
        "#endif  // ZICFISS_VM_SUPPORTED",
        ".p2align 12",
        "rvtest_zicfiss_ss_page:     .zero 4096   # mapped as an SS page (xwr=010)",
        ".p2align 12",
        "rvtest_zicfiss_rw_page:     .zero 4096   # mapped read/write (xwr=011)",
        ".p2align 12",
        "rvtest_zicfiss_ro_page:     .zero 4096   # mapped read-only (xwr=001)",
        ".popsection",
        ".endif",
        "",
    ]


# Perms carried by every page of the identity map: D|A|R|W|X|V, matching the superpage the
# boot code installs.
_IMAGE_PERMS = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V"


def identity_map() -> list[str]:
    """Identity superpage covering code+data, supervisor-only, PC-relative.

    Hand-rolled rather than SUPERPAGE_PTE_SETUP_* because that macro needs a constant VA,
    and this must map whatever PA the linker chose for rvtest_code_begin back to itself.
    """
    return [
        "# identity superpage for code+data",
        "auipc t0, 0",
        "LI(t1, ~((1 << ZICFISS_ROOT_SHIFT) - 1))",
        "and t0, t0, t1",
        "srli t0, t0, 12",
        "slli t0, t0, 10",
        f"LI(t1, ({_IMAGE_PERMS}))",
        "or t0, t0, t1",
        "LA(t2, rvtest_Sroot_pg_tbl)",
        "LA(t1, rvtest_code_begin)",
        "srli t1, t1, ZICFISS_ROOT_SHIFT",
        "andi t1, t1, ZICFISS_VPN_MASK",
        "slli t1, t1, ZICFISS_PTE_LOG2",
        "add t2, t2, t1",
        "SREG t0, 0(t2)",
        "sfence.vma",
    ]


def _umode_image_map() -> list[str]:
    """Identity-map the test image at 4 KiB granularity, splitting user from supervisor.

    U-mode has to fetch the test body and write the signature area, while the trap handler
    that boot-time delegation sends S-mode traps to has to fetch its own code -- and S-mode
    cannot execute from a user page (SUM covers loads and stores, never instruction fetch).
    The framework's own layout already separates the two: the handlers follow
    ``rvtest_code_end``, which RVTEST_CODE_END page-aligns, and the signature area follows
    ``rvtest_data_begin``. So

      [image start, rvtest_code_end)   PTE_U -- the test body, fetched from U-mode
      [rvtest_code_end, data page)     supervisor only -- trap handlers and save areas
      [data page, _end)                PTE_U -- test data and the signature region

    where ``data page`` is ``rvtest_data_begin`` rounded UP, so the page holding the
    S-mode save area stays supervisor-only. The handler still writes trap
    signatures into the user-mapped signature region, which is why the caller also sets
    ``sstatus.SUM``.

    Emitted with translation disabled; the root entry is written last either way. One leaf
    table covers 2 MiB (Sv39) or 4 MiB (Sv32), which is far more than a priv test image needs
    -- anything past it is simply left unmapped rather than silently mismapped.
    """
    return [
        "# 4 KiB identity map of the test image, user pages only where U-mode needs them.",
        "# The leaf table is filled once per test file; the root entry is rewritten every",
        "# time, because identity_map() may have replaced it with a supervisor superpage.",
        "LA(t0, rvtest_uimg_mapped)",
        "LREG t1, 0(t0)",
        "bnez t1, 2f",
        "LA(t0, rvtest_code_begin)",
        "srli t0, t0, 12",
        "slli t0, t0, 12",
        "# t2 = &leaf[index of the first page]",
        "LA(t2, rvtest_uimg_lvl0_pg_tbl)",
        "srli t1, t0, 12",
        "andi t1, t1, ZICFISS_VPN_MASK",
        "slli t1, t1, ZICFISS_PTE_LOG2",
        "add t2, t2, t1",
        "LA(t1, _end)",
        "LA(t3, rvtest_code_end)   # first page that must not be user-executable",
        "LI(t6, 4096)",
        "# Round rvtest_data_begin UP: the S-mode save area sits just below it and the",
        "# T-SBI S-mode handler executes its CSR instruction out of that save area, so its",
        "# page must stay supervisor-only or S-mode cannot fetch the scratch code.",
        "LA(t4, rvtest_data_begin)",
        "add t4, t4, t6",
        "addi t4, t4, -1",
        "srli t4, t4, 12",
        "slli t4, t4, 12          # first page of the user-writable data region",
        "1:",
        "bgeu t0, t1, 2f",
        "LA(t5, rvtest_uimg_lvl0_pg_tbl + 4096)",
        "bgeu t2, t5, 2f          # leaf table full: leave the rest unmapped",
        "srli t5, t0, 12",
        "slli t5, t5, 10",
        f"ori t5, t5, ({_IMAGE_PERMS})",
        "bltu t0, t3, 3f          # in the test body -> user",
        "bltu t0, t4, 4f          # handlers and save areas -> supervisor only",
        "3:",
        "ori t5, t5, PTE_U",
        "4:",
        "SREG t5, 0(t2)",
        "addi t2, t2, (1 << ZICFISS_PTE_LOG2)",
        "add t0, t0, t6",
        "j 1b",
        "2:",
        "#ifdef SV39_SUPPORTED",
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
        "#else",
        "LA(t5, rvtest_uimg_lvl0_pg_tbl)",
        "#endif",
        "srli t5, t5, 12",
        "slli t5, t5, 10",
        "ori t5, t5, PTE_V",
        "LA(t2, rvtest_Sroot_pg_tbl)",
        "LA(t1, rvtest_code_begin)",
        "srli t1, t1, ZICFISS_ROOT_SHIFT",
        "andi t1, t1, ZICFISS_VPN_MASK",
        "slli t1, t1, ZICFISS_PTE_LOG2",
        "add t2, t2, t1",
        "SREG t5, 0(t2)",
        "LA(t0, rvtest_uimg_mapped)",
        "LI(t1, 1)",
        "SREG t1, 0(t0)",
        "sfence.vma",
    ]


def map_zicfiss_pages(*, ss_perms: str = PTE_SS, user: bool = True, ss_page_user: bool | None = None) -> list[str]:
    """Wire up the PTE chain mapping the SS / RW / RO pages.

    ``ss_perms`` lets a caller remap the shadow stack page with a different
    encoding (e.g. PTE_RO) to exercise the wrong-page-type coverpoints.
    ``user`` adds PTE_U to every leaf, required when the testcases run in U-mode, and
    selects the split 4 KiB image map over the plain supervisor superpage.
    ``ss_page_user`` overrides ``user`` for the shadow stack page alone; False leaves its
    U bit to ``ss_perms``.
    """
    u = " | PTE_U" if user else ""
    ss_u = u if ss_page_user is None else (" | PTE_U" if ss_page_user else "")
    return [
        *(_umode_image_map() if user else identity_map()),
        "#ifdef SV39_SUPPORTED",
        "ZICFISS_PTE_SETUP(rvtest_slvl1_pg_tbl, (PTE_V), ZICFISS_VA_SS, LEVEL2)",
        "#endif",
        "ZICFISS_PTE_SETUP(rvtest_slvl0_pg_tbl, (PTE_V), ZICFISS_VA_SS, LEVEL1)",
        f"ZICFISS_PTE_SETUP(rvtest_zicfiss_ss_page, ({ss_perms}{ss_u}), ZICFISS_VA_SS, LEVEL0)",
        f"ZICFISS_PTE_SETUP(rvtest_zicfiss_rw_page, ({PTE_RW}{u}), ZICFISS_VA_RW, LEVEL0)",
        f"ZICFISS_PTE_SETUP(rvtest_zicfiss_ro_page, ({PTE_RO}{u}), ZICFISS_VA_RO, LEVEL0)",
        "sfence.vma",
    ]
