##################################
# priv/extensions/Zicfiss.py
#
# Zicfiss (shadow stack) test generators for the Sm, S and U groups.
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared helpers for the Zicfiss shadow stack test generators.

SSPUSH and SSPOPCHK name x1 or x5, which the tests load freely: x1 is kept out of the allocator
because framework calls clobber it, and x5 is the SIGUPD link register, written only on the
failure path.

The compressed forms need Zcmop, which the tests are not assembled with: ``ss_instr`` enables it
around each one, and ``zcmop_only`` guards the testcase.

``page_table_data_section`` defines the XLEN-dependent addresses and page-table geometry, and
the shadow stack (SS), read/write (RW) and read-only (RO) pages, which share one leaf table.
"""

from typing import Literal, NamedTuple

from testgen.asm.helpers import arch_block, comment_banner, gated, write_sigupd
from testgen.asm.tsbi import tsbi_call, tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SvMode, lower_table_data
from testgen.priv.registry import add_priv_test_generator

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
# Perms of every page of the test image's identity map, matching the superpage the boot code installs.
_IMAGE_PERMS = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V"

# Turn translation off from S- or M-mode.
SATP_OFF = ["csrw satp, x0", "sfence.vma"]

SsamoswapWidth = Literal["w", "d"]
SSAMOSWAP_WIDTHS: tuple[SsamoswapWidth, ...] = ("w", "d")


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
    return arch_block([form.mnemonic], "zcmop") if form.compressed else [form.mnemonic]


def zcmop_only(compressed: bool, lines: list[str]) -> list[str]:
    """Return ``lines``, guarded on Zcmop when they use a compressed form."""
    return ["#ifdef ZCMOP_SUPPORTED", *lines, "#endif"] if compressed else lines


def rv64_only(lines: list[str]) -> list[str]:
    """Return ``lines``, guarded to RV64."""
    return gated(lines, "__riscv_xlen == 64")


def ssamoswap_only(width: SsamoswapWidth, lines: list[str]) -> list[str]:
    """Return ``lines`` for SSAMOSWAP.``width``, guarded to RV64 for SSAMOSWAP.D."""
    return lines if width == "w" else rv64_only(lines)


def vm_section(title: str, description: str, lines: list[str]) -> list[str]:
    """A section banner, and ``lines`` guarded on the configuration supporting Sv39/Sv32."""
    return [comment_banner(title, description), *gated(lines, "defined(ZICFISS_VM_SUPPORTED)")]


def ss_forms_against(
    test_data: TestData, forms: list[SsForm], addr: str, value: str, tag: str, coverpoint: str, cg: str
) -> list[str]:
    """One testcase per push/pop form, with ssp = ``addr`` and the form's link register = ``value``.

    Each testcase records ssp afterwards, which shows whether the access completed.
    """
    ssp_reg = test_data.int_regs.get_register()
    lines: list[str] = []
    for form in forms:
        case = [
            f"LI(x{ssp_reg}, {addr})",
            f"csrw ssp, x{ssp_reg}",
            f"LI({form.link_reg}, {value})",
            test_data.add_testcase(f"{form.name}_{tag}", coverpoint, cg),
            *ss_instr(form),
            f"csrr x{ssp_reg}, ssp",
            write_sigupd(ssp_reg, test_data),
        ]
        lines.extend(zcmop_only(form.compressed, case))
    test_data.int_regs.return_registers([ssp_reg])
    return lines


# Zicfiss uses only some encodings of mop.rr.7 and mop.r.28. The rest stay Zimop/Zcmop.
# Each register field is swept over x0-x31 with the other fields held fixed, skipping the Zicfiss
# instructions: SSPUSH (rd = rs1 = x0, rs2 = x1/x5), SSPOPCHK (rd = x0, rs1 = x1/x5), SSRDP (rs1 = x0).
class _UnusedMop(NamedTuple):
    coverpoint: str  # suffix of the cp_ss_unused_mop_* coverpoint
    name: str
    instr: list[str]
    rd: int  # destination register; 0 if the instruction does not write one


def _unused_mop_list() -> list[_UnusedMop]:
    cases = [_UnusedMop("rr7_rs2", f"rs2_x{n}", [f"mop.rr.7 x0, x0, x{n}"], 0) for n in range(32) if n not in (1, 5)]
    cases += [_UnusedMop("rr7_rs1", f"rs1_x{n}", [f"mop.rr.7 x0, x{n}, x1"], 0) for n in range(1, 32)]
    cases += [_UnusedMop("rr7_rd", f"rd_x{n}", [f"mop.rr.7 x{n}, x0, x1"], n) for n in range(1, 32)]
    cases += [_UnusedMop("r28_rs1", f"rs1_x{n}", [f"mop.r.28 x0, x{n}"], 0) for n in range(32) if n not in (1, 5)]
    cases += [_UnusedMop("r28_rd", f"rd_x{n}", [f"mop.r.28 x{n}, x1"], n) for n in range(1, 32)]
    return cases


def unused_mop_cases(test_data: TestData, suffix: str, cg: str) -> list[str]:
    """Unused mop.rr.7, mop.r.28 and c.mop.n encodings, run while Zicfiss is active.

    Each must act as a Zimop/Zcmop: rd = 0 (when rd is not x0), ssp unchanged and nothing pushed.
    When rd is a framework register, it is saved and restored around the instruction.
    """
    pool = test_data.int_regs.get_registers(4)
    cases = _unused_mop_list()
    for n in (3, 7):
        c_mop = [".option push", ".option arch, +zcmop", f"c.mop.{n}", ".option pop"]
        cases.append(_UnusedMop("c", f"c_mop_{n}", c_mop, 0))

    lines: list[str] = []
    for case in cases:
        # Scratch registers must differ from rd.
        ssp_reg, save_reg, res_reg = [r for r in pool if r != case.rd][:3]
        body = [f"LI(x{ssp_reg}, ZICFISS_VA_SS + 0x800)", f"csrw ssp, x{ssp_reg}"]
        if case.rd:
            body += [f"mv x{save_reg}, x{case.rd}", f"LI(x{case.rd}, 0x0DDBA11)   # a Zimop writes 0 here"]
        body += [test_data.add_testcase(case.name, f"cp_ss_unused_mop_{case.coverpoint}{suffix}", cg), *case.instr]
        if case.rd:
            body += [f"mv x{res_reg}, x{case.rd}", f"mv x{case.rd}, x{save_reg}", write_sigupd(res_reg, test_data)]
        body += [
            f"csrr x{res_reg}, ssp   # unchanged",
            write_sigupd(res_reg, test_data),
            f"addi x{res_reg}, x{res_reg}, -REGWIDTH",
            f"LREG x{res_reg}, 0(x{res_reg})   # nothing was pushed",
            write_sigupd(res_reg, test_data),
        ]
        lines.extend(zcmop_only(case.coverpoint == "c", body))
    test_data.int_regs.return_registers(pool)
    return lines


def misaligned_store_cases(test_data: TestData, coverpoint: str, cg: str) -> list[str]:
    """Ordinary stores to an SS page at every low-address-bit value.

    Each store must raise a store/AMO access-fault, including when misaligned, and leave memory unchanged.
    """
    addr_reg, data_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = []
    for mnemonic in ("sb", "sh", "sw", "sd"):
        for offset in range(8):
            case = [
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x400 + {offset})",
                f"LI(x{data_reg}, 0x5A5A5A5A5A5A5A5A)",
                test_data.add_testcase(f"{mnemonic}_off{offset}", coverpoint, cg),
                f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x400)",
                f"LREG x{data_reg}, 0(x{addr_reg})   # unchanged",
                write_sigupd(data_reg, test_data),
                f"addi x{addr_reg}, x{addr_reg}, REGWIDTH",
                f"LREG x{data_reg}, 0(x{addr_reg})   # unchanged",
                write_sigupd(data_reg, test_data),
            ]
            lines.extend(rv64_only(case) if mnemonic == "sd" else case)
    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def ssamoswap_forms(test_data: TestData, addr: str, tag: str, coverpoint: str, cg: str) -> list[str]:
    """SSAMOSWAP.W, and SSAMOSWAP.D on RV64, against ``addr``, each recording rd afterwards."""
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
    lines = [f"LI(x{addr_reg}, {addr})", f"LI(x{rs2_reg}, 0x11223344)"]
    for width in SSAMOSWAP_WIDTHS:
        lines.extend(
            ssamoswap_only(
                width,
                [
                    f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                    test_data.add_testcase(f"ssamoswap_{width}_{tag}", coverpoint, cg),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ],
            )
        )
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg])
    return lines


def set_envcfg_sse(csr: str, value: int, test_data: TestData, *, mode: str) -> list[str]:
    """Set or clear the SSE field of menvcfg or senvcfg, through T-SBI when ``mode`` cannot access ``csr``.

    ``mode`` is the privilege mode this runs in.
    """
    reg = test_data.int_regs.get_register()
    op = "csrs" if value else "csrc"
    instr = f"{op} {csr}, x{reg}   # {'set' if value else 'clear'} {csr}.SSE"
    lines = [f"LI(x{reg}, {csr.upper()}_SSE)", tsbi_call_or_direct(instr, mode)]
    test_data.int_regs.return_registers([reg])
    return lines


def enable_translation(test_data: TestData, *, mode: Literal["M", "S", "U"]) -> list[str]:
    """Point satp at rvtest_Sroot_pg_tbl in Sv39 or Sv32 mode, through T-SBI from U-mode.

    ``mode`` is the privilege mode this runs in.
    """
    satp_reg, mode_reg = test_data.int_regs.get_registers(2)
    write = f"csrw satp, x{satp_reg}"
    lines = [
        f"LA(x{satp_reg}, rvtest_Sroot_pg_tbl)",
        f"srli x{satp_reg}, x{satp_reg}, 12",
        f"LI(x{mode_reg}, ZICFISS_SATP_MODE)",
        f"or x{satp_reg}, x{satp_reg}, x{mode_reg}",
        tsbi_call(write) if mode == "U" else write,
    ]
    test_data.int_regs.return_registers([satp_reg, mode_reg])
    return lines


def _sv_defines(mode: SvMode, va_ss: int, setup_macro: str, satp_mode: str) -> list[str]:
    """The ZICFISS_* addresses and page-table geometry for ``mode``. The addresses share one leaf table."""
    root_level = mode.levels - 1
    return [
        "#define ZICFISS_VM_SUPPORTED",
        f"#define ZICFISS_VA_SS       {va_ss:#x}",
        f"#define ZICFISS_VA_RW       {va_ss + 0x1000:#x}",
        f"#define ZICFISS_VA_RO       {va_ss + 0x2000:#x}",
        f"#define ZICFISS_VA_UNMAPPED {va_ss + 0x100000:#x}   // not mapped: the walk fails at level 1",
        f"#define ZICFISS_PTE_SETUP(PA, PERMS, VA, LEVEL) {setup_macro}(PA, PERMS, VA, LEVEL)",
        f"#define ZICFISS_SATP_MODE   {satp_mode}",
        f"#define ZICFISS_ROOT_SHIFT  {mode.page_offset_bits(root_level)}   // VA shift of the root-level VPN",
        f"#define ZICFISS_LEAF_SPAN   {mode.page_offset_bits(1)}   // log2 of the bytes one leaf table maps",
        f"#define ZICFISS_VPN_MASK    {(1 << mode.index_bits(0)) - 1:#x}",
        f"#define ZICFISS_PTE_LOG2    {mode.pte_bytes.bit_length() - 1}   // log2 of the PTE size",
    ]


def page_table_data_section() -> list[str]:
    """XLEN-dependent symbols, plus the page-table and backing-page labels.

    Prepended to every test chunk, because chunks are distributed across files when a
    suite is split. The #defines may repeat; the data block is guarded by .ifndef.
    """
    return [
        "",
        "#if defined(SV39_SUPPORTED)",
        *_sv_defines(SV39, 0x140300000, "PTE_SETUP_SV39", "((SATP64_MODE) & (SATP_MODE_SV39 << 60))"),
        "#elif defined(SV32_SUPPORTED)",
        *_sv_defines(SV32, 0xC0300000, "PTE_SETUP_SV32", "SATP32_MODE"),
        "#endif",
        ".ifndef rvtest_zicfiss_pages_declared",
        ".set rvtest_zicfiss_pages_declared, 1",
        ".pushsection .data",
        "#ifdef ZICFISS_VM_SUPPORTED",
        "#ifdef SV39_SUPPORTED",
        *lower_table_data(SV39),
        ".p2align 12",
        "rvtest_uimg_lvl1_pg_tbl:    .zero 4096   # Sv39 level-1 table for the test image",
        "#else",
        *lower_table_data(SV32),
        "#endif",
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


def _table_entry(test_data: TestData, table: str, shift: str, dest: int) -> list[str]:
    """Set x``dest`` to the entry of ``table`` that maps rvtest_code_begin, whose VPN is at VA bit ``shift``."""
    tmp = test_data.int_regs.get_register()
    lines = [
        f"LA(x{dest}, rvtest_code_begin)",
        f"srli x{dest}, x{dest}, {shift}",
        f"andi x{dest}, x{dest}, ZICFISS_VPN_MASK",
        f"slli x{dest}, x{dest}, ZICFISS_PTE_LOG2",
        f"LA(x{tmp}, {table})",
        f"add x{dest}, x{dest}, x{tmp}",
    ]
    test_data.int_regs.return_registers([tmp])
    return lines


def _identity_map(test_data: TestData) -> list[str]:
    """Map the root-level superpage holding the test image to itself, supervisor-only.

    The superpage is taken from the PC, because the image may be linked anywhere.
    """
    pte, entry = test_data.int_regs.get_registers(2)
    lines = [
        "# identity superpage for code+data",
        f"auipc x{pte}, 0",
        f"srli x{pte}, x{pte}, ZICFISS_ROOT_SHIFT",
        f"slli x{pte}, x{pte}, ZICFISS_ROOT_SHIFT",
        f"srli x{pte}, x{pte}, 12",
        f"slli x{pte}, x{pte}, 10",
        f"ori x{pte}, x{pte}, ({_IMAGE_PERMS})",
        *_table_entry(test_data, "rvtest_Sroot_pg_tbl", "ZICFISS_ROOT_SHIFT", entry),
        f"SREG x{pte}, 0(x{entry})",
        "sfence.vma",
    ]
    test_data.int_regs.return_registers([pte, entry])
    return lines


def _umode_image_map(test_data: TestData) -> list[str]:
    """Identity-map the test image with 4 KiB pages, user-accessible where U-mode needs it.

    The test body, below rvtest_code_end, and the data from the page above rvtest_data_begin are
    user pages. The trap handlers and save areas between them stay supervisor-only, because
    S-mode cannot fetch from a user page. Pages past the 2 MiB (Sv39) or 4 MiB (Sv32) that one
    leaf table maps are left unmapped. The leaf table is filled once per file; the root entry is
    rewritten every time because ``_identity_map`` may have replaced it.
    """
    page, pte, entry, tmp = test_data.int_regs.get_registers(4)
    lines = [
        f"LA(x{tmp}, rvtest_uimg_mapped)",
        f"LREG x{tmp}, 0(x{tmp})",
        f"bnez x{tmp}, 2f",
        f"LA(x{page}, rvtest_code_begin)",
        f"srli x{page}, x{page}, 12",
        f"slli x{page}, x{page}, 12",
        "1:",
        f"LA(x{tmp}, _end)",
        f"bgeu x{page}, x{tmp}, 2f",
        f"LA(x{tmp}, rvtest_code_begin)",
        f"xor x{tmp}, x{tmp}, x{page}",
        f"srli x{tmp}, x{tmp}, ZICFISS_LEAF_SPAN",
        f"bnez x{tmp}, 2f          # past what the leaf table maps",
        f"srli x{pte}, x{page}, 12",
        f"slli x{pte}, x{pte}, 10",
        f"ori x{pte}, x{pte}, ({_IMAGE_PERMS})",
        f"LA(x{tmp}, rvtest_code_end)",
        f"bltu x{page}, x{tmp}, 3f   # the test body: user",
        "# The S-mode save area ends at rvtest_data_begin, so its page stays supervisor-only.",
        f"LA(x{tmp}, rvtest_data_begin + 0xFFF)",
        f"srli x{tmp}, x{tmp}, 12",
        f"slli x{tmp}, x{tmp}, 12",
        f"bltu x{page}, x{tmp}, 4f   # trap handlers and save areas: supervisor only",
        "3:",
        f"ori x{pte}, x{pte}, PTE_U",
        "4:",
        f"srli x{entry}, x{page}, 12",
        f"andi x{entry}, x{entry}, ZICFISS_VPN_MASK",
        f"slli x{entry}, x{entry}, ZICFISS_PTE_LOG2",
        f"LA(x{tmp}, rvtest_uimg_lvl0_pg_tbl)",
        f"add x{entry}, x{entry}, x{tmp}",
        f"SREG x{pte}, 0(x{entry})",
        f"LI(x{tmp}, 0x1000)",
        f"add x{page}, x{page}, x{tmp}",
        "j 1b",
        "2:",
        "#ifdef SV39_SUPPORTED",
        f"LA(x{pte}, rvtest_uimg_lvl0_pg_tbl)",
        f"srli x{pte}, x{pte}, 12",
        f"slli x{pte}, x{pte}, 10",
        f"ori x{pte}, x{pte}, PTE_V",
        *_table_entry(test_data, "rvtest_uimg_lvl1_pg_tbl", "ZICFISS_LEAF_SPAN", entry),
        f"SREG x{pte}, 0(x{entry})",
        f"LA(x{pte}, rvtest_uimg_lvl1_pg_tbl)",
        "#else",
        f"LA(x{pte}, rvtest_uimg_lvl0_pg_tbl)",
        "#endif",
        f"srli x{pte}, x{pte}, 12",
        f"slli x{pte}, x{pte}, 10",
        f"ori x{pte}, x{pte}, PTE_V",
        *_table_entry(test_data, "rvtest_Sroot_pg_tbl", "ZICFISS_ROOT_SHIFT", entry),
        f"SREG x{pte}, 0(x{entry})",
        f"LA(x{tmp}, rvtest_uimg_mapped)",
        f"LI(x{pte}, 1)",
        f"SREG x{pte}, 0(x{tmp})",
        "sfence.vma",
    ]
    test_data.int_regs.return_registers([page, pte, entry, tmp])
    return lines


def map_zicfiss_pages(
    test_data: TestData, *, ss_perms: str = PTE_SS, user: bool = True, ss_page_user: bool | None = None
) -> list[str]:
    """Map the test image and the SS, RW and RO pages. Runs in S- or M-mode.

    ``ss_perms`` remaps the shadow stack page with a different encoding (e.g. PTE_RO).
    ``user`` adds PTE_U to every leaf and maps the image with user pages for U-mode testcases;
    otherwise the image is one supervisor superpage. ``ss_page_user`` overrides ``user`` for the
    shadow stack page; False leaves its U bit to ``ss_perms``. The PTE_SETUP macros clobber
    a0, a1, t0 and t1.
    """
    u = " | PTE_U" if user else ""
    ss_u = u if ss_page_user is None else (" | PTE_U" if ss_page_user else "")
    return [
        *(_umode_image_map(test_data) if user else _identity_map(test_data)),
        "#ifdef SV39_SUPPORTED",
        "ZICFISS_PTE_SETUP(rvtest_slvl1_pg_tbl, (PTE_V), ZICFISS_VA_SS, LEVEL2)",
        "#endif",
        "ZICFISS_PTE_SETUP(rvtest_slvl0_pg_tbl, (PTE_V), ZICFISS_VA_SS, LEVEL1)",
        f"ZICFISS_PTE_SETUP(rvtest_zicfiss_ss_page, ({ss_perms}{ss_u}), ZICFISS_VA_SS, LEVEL0)",
        f"ZICFISS_PTE_SETUP(rvtest_zicfiss_rw_page, ({PTE_RW}{u}), ZICFISS_VA_RW, LEVEL0)",
        f"ZICFISS_PTE_SETUP(rvtest_zicfiss_ro_page, ({PTE_RO}{u}), ZICFISS_VA_RO, LEVEL0)",
        "sfence.vma",
    ]


# ============================================================================
# Sm group
# ============================================================================
# ZicfissSm test generator.
#
# The ZicfissSm sheet of the testplan linked from docs/ctp/src/privmisc23.adoc: what needs
# M-mode to set up or observe. Use of Zicfiss in M-mode is not supported by the
# architecture, so what is testable here is the gating (menvcfg.SSE at the top of the
# enable chain, and the read-only-zero propagation into senvcfg/henvcfg), PMP, satp.MODE=Bare,
# the software-check exception taken in M-mode, and the one M-mode instruction behaviour the
# spec does define -- SSAMOSWAP always faults at M, unless mstatus.MPRV lowers the effective
# privilege mode.
#
# The suite boots to M-mode, so medeleg is zero and every trap is taken in M-mode.

_CG_SM = "Zicfiss_Sm_cg"

_CSR_OPS = (
    ("csrrw", "csrrw x{rd}, ssp, x{v}"),
    ("csrrs", "csrrs x{rd}, ssp, x{v}"),
    ("csrrc", "csrrc x{rd}, ssp, x{v}"),
    ("csrrwi", "csrrwi x{rd}, ssp, 1"),
    ("csrrsi", "csrrsi x{rd}, ssp, 1"),
    ("csrrci", "csrrci x{rd}, ssp, 1"),
)


# ---------------------------------------------------------------------------
# cp_ssamoswap_mmode_fault
# ---------------------------------------------------------------------------


def _mprv_on(mask_reg: int, mpp: str) -> list[str]:
    """Set mstatus.MPRV with MPP=``mpp`` ("MPP_SMODE" or "MPP_MMODE")."""
    return [
        f"LI(x{mask_reg}, MSTATUS_MPP)",
        f"csrc mstatus, x{mask_reg}",
        f"LI(x{mask_reg}, MSTATUS_MPRV | {mpp})",
        f"csrs mstatus, x{mask_reg}",
    ]


def _mprv_off(mask_reg: int) -> list[str]:
    """Clear mstatus.MPRV. A trap from M-mode leaves MPP=M, so mret keeps MPRV=1 and lowers MPP;
    this must come straight after the access, before any other load or store."""
    return [f"LI(x{mask_reg}, MSTATUS_MPRV)", f"csrc mstatus, x{mask_reg}"]


def _generate_ssamoswap_mmode_fault(test_data: TestData) -> list[str]:
    """SSAMOSWAP faults whenever the effective privilege mode is M -- sweep menvcfg.SSE, satp.MODE
    and MPRV with MPP=M.

    The target is the physical address of the shadow stack page, which the translating leg
    maps as a valid, writable SS page. The location is seeded first, and both it and rd are
    recorded after the fault to show that neither changed.

    Then MPRV=1 with MPP=S, where the effective privilege mode is S (menvcfg.SSE=1): with
    satp.MODE=Bare the swap raises a store/AMO access fault (norm:satp_mode_bare), and with
    translation it swaps the S-mode SS page.
    """
    coverpoint = "cp_ssamoswap_mmode_fault"
    lines: list[str] = [
        comment_banner(coverpoint, "SSAMOSWAP.W/.D always faults when the effective privilege mode is M")
    ]
    for sse in (0, 1):
        for satp_mode in ("bare", "translating"):
            lines.append(f"# --- menvcfg.SSE={sse}, satp.MODE {satp_mode} ---")
            if satp_mode == "translating":
                lines.extend(
                    gated(
                        [*map_zicfiss_pages(test_data, user=False), *enable_translation(test_data, mode="M")],
                        "defined(ZICFISS_VM_SUPPORTED)",
                    )
                )
            else:
                lines.extend(SATP_OFF)
            lines.extend(set_envcfg_sse("menvcfg", sse, test_data, mode="M"))
            addr_reg, rd_reg, rs2_reg, mask_reg = test_data.int_regs.get_registers(4)
            for mprv in (0, 1):
                for width in SSAMOSWAP_WIDTHS:
                    tag = f"ssamoswap_{width}_mmode_sse{sse}_{satp_mode}{'_mprv_mpp_m' if mprv else ''}"
                    case = [
                        f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                        f"LI(x{rs2_reg}, 0x5EED5EED)",
                        f"SREG x{rs2_reg}, 0(x{addr_reg})   # seed the location",
                        f"LI(x{rd_reg}, 0x0DDBA11)   # rd must keep this value",
                        f"LI(x{rs2_reg}, 0x11223344)",
                        *(_mprv_on(mask_reg, "MPP_MMODE") if mprv else []),
                        test_data.add_testcase(tag, coverpoint, _CG_SM),
                        f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                        *(_mprv_off(mask_reg) if mprv else []),
                        write_sigupd(rd_reg, test_data),
                        f"LREG x{rd_reg}, 0(x{addr_reg})   # memory must still hold the seed",
                        write_sigupd(rd_reg, test_data),
                    ]
                    body = ssamoswap_only(width, case)
                    lines.extend(gated(body, "defined(ZICFISS_VM_SUPPORTED)") if satp_mode == "translating" else body)
            test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, mask_reg])
    lines.extend(SATP_OFF)

    # MPRV=1 with MPP=S: the effective privilege mode is S.
    coverpoint = "cp_ssamoswap_mprv_s"
    lines.extend(
        [
            comment_banner(coverpoint, "SSAMOSWAP at M with MPRV=1, MPP=S follows the S-mode rules"),
            *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
        ]
    )
    for satp_mode in ("bare", "translating"):
        lines.append(f"# --- MPRV=1, MPP=S, satp.MODE {satp_mode} ---")
        if satp_mode == "translating":
            lines.extend(
                gated(
                    [*map_zicfiss_pages(test_data, user=False), *enable_translation(test_data, mode="M")],
                    "defined(ZICFISS_VM_SUPPORTED)",
                )
            )
        addr_reg, rd_reg, rs2_reg, mask_reg = test_data.int_regs.get_registers(4)
        # Bare: the physical address, which the swap must not change. Translating: the S-mode SS
        # page, which the swap must change.
        target = "rvtest_zicfiss_ss_page" if satp_mode == "bare" else "ZICFISS_VA_SS"
        for width in SSAMOSWAP_WIDTHS:
            case = [
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"LI(x{rs2_reg}, 0x5EED5EED)",
                f"SREG x{rs2_reg}, 0(x{addr_reg})   # seed the location",
                *([f"LI(x{addr_reg}, {target})"] if satp_mode == "translating" else []),
                f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                f"LI(x{rs2_reg}, 0x11223344)",
                *_mprv_on(mask_reg, "MPP_SMODE"),
                test_data.add_testcase(f"ssamoswap_{width}_mprv_mpp_s_{satp_mode}", coverpoint, _CG_SM),
                f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                *_mprv_off(mask_reg),
                write_sigupd(rd_reg, test_data),
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"LREG x{rd_reg}, 0(x{addr_reg})   # the seed if the swap faulted",
                write_sigupd(rd_reg, test_data),
            ]
            body = ssamoswap_only(width, case)
            lines.extend(gated(body, "defined(ZICFISS_VM_SUPPORTED)") if satp_mode == "translating" else body)
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, mask_reg])
    lines.extend(SATP_OFF)
    return lines


# ---------------------------------------------------------------------------
# cp_ssamoswap_mprv_non_idempotent
# ---------------------------------------------------------------------------


def _generate_mprv_non_idempotent(test_data: TestData) -> list[str]:
    """SSAMOSWAP in M-mode with mstatus.MPRV=1 and MPP=S accesses memory as S-mode.

    The effective privilege mode is then S, so the access is translated and the S-mode shadow
    stack rules apply: it completes on a PBMT=PMA shadow stack page and raises a store/AMO access
    fault on a PBMT=IO one, which is non-idempotent. PBMT=NC is left out for the reason given in
    cp_ss_non_idempotent. A trap taken in M-mode sets MPP to M and mret then lowers it, so MPRV
    and MPP are set before each swap, and MPRV is cleared before its result is recorded.
    """
    coverpoint = "cp_ssamoswap_mprv_non_idempotent"
    lines: list[str] = [
        comment_banner(coverpoint, "SSAMOSWAP at M with MPRV=1, MPP=S on PBMT=PMA and PBMT=IO shadow stack pages"),
        "#ifdef ZICFISS_VM_SUPPORTED",
        "#if defined(SVPBMT_SUPPORTED) && __riscv_xlen == 64",
        *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
    ]
    pbmte_reg = test_data.int_regs.get_register()
    lines.extend([f"LI(x{pbmte_reg}, MENVCFG_PBMTE)", f"csrs menvcfg, x{pbmte_reg}"])
    test_data.int_regs.return_registers([pbmte_reg])
    # pte.PBMT is bits [62:61]: 00 PMA, 10 IO.
    for tag, pbmt in (("pma", 0), ("io", 2)):
        lines.extend(
            [
                f"# --- pte.PBMT = {tag} ---",
                *map_zicfiss_pages(test_data, ss_perms=f"{PTE_SS} | ({pbmt} << 61)", user=False),
                *enable_translation(test_data, mode="M"),
            ]
        )
        addr_reg, rd_reg, rs2_reg, mask_reg = test_data.int_regs.get_registers(4)
        lines.extend([f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)", f"LI(x{rs2_reg}, 0x11223344)"])
        for width in SSAMOSWAP_WIDTHS:
            case = [
                f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                *_mprv_on(mask_reg, "MPP_SMODE"),
                "sfence.vma   # each swap walks, so the trace logs the PTE it used",
                test_data.add_testcase(f"ssamoswap_{width}_mprv_pbmt_{tag}", coverpoint, _CG_SM),
                f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                *_mprv_off(mask_reg),
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(ssamoswap_only(width, case))
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, mask_reg])
        lines.extend(SATP_OFF)
    pbmte_reg = test_data.int_regs.get_register()
    lines.extend(
        [
            f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
            f"csrc menvcfg, x{pbmte_reg}",
            "#endif  // SVPBMT_SUPPORTED && RV64",
            "#endif  // ZICFISS_VM_SUPPORTED",
        ]
    )
    test_data.int_regs.return_registers([pbmte_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_menvcfg_sse_gating / cp_menvcfg_sse_ss_page
# ---------------------------------------------------------------------------


def _generate_menvcfg_gating(test_data: TestData) -> list[str]:
    """menvcfg.SSE gates ssp CSR access, and the SS page encoding, for every mode below M.

    ssp is accessible from M-mode for both values of menvcfg.SSE, the positive control. From
    S-mode it is accessible only with menvcfg.SSE=1. Each access records rd, which an
    illegal-instruction exception leaves unchanged. With menvcfg.SSE=0 the xwr=010 encoding
    is reserved, so an ordinary load or store to such a page raises a page fault from S- and
    U-mode alike; with menvcfg.SSE=1 the page is an SS page, which loads may read and stores
    may not write, whatever senvcfg.SSE is.
    """
    lines: list[str] = [comment_banner("cp_menvcfg_sse_gating", "menvcfg.SSE gates ssp CSR access below M-mode")]
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    for sse in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", sse, test_data, mode="M"))
        for mode in ("M", "S"):
            lines.extend(["RVTEST_TSBI_GOTO_SMODE"] if mode == "S" else [])
            # An XLEN-aligned ssp value, different per mode so that each successful write shows
            lines.append(f"LI(x{val_reg}, {'0x2000' if mode == 'S' else '0x1000'})")
            for op, form in _CSR_OPS:
                lines.extend(
                    [
                        f"LI(x{rd_reg}, 0x0DDBA11)",
                        test_data.add_testcase(
                            f"ssp_{op}_{mode.lower()}mode_sse{sse}", "cp_menvcfg_sse_gating", _CG_SM
                        ),
                        form.format(rd=rd_reg, v=val_reg),
                        write_sigupd(rd_reg, test_data),
                    ]
                )
            lines.extend(["RVTEST_TSBI_GOTO_MMODE"] if mode == "S" else [])
    test_data.int_regs.return_registers([rd_reg, val_reg])

    # The SS page encoding, from S-mode (supervisor pages) and U-mode (user pages). Only
    # menvcfg.SSE makes xwr=010 reserved; senvcfg.SSE does not (norm:ssmp_menvcfg_sse), so with
    # menvcfg.SSE=1 and senvcfg.SSE=0 the page is still an SS page for U-mode ordinary accesses,
    # even though Zicfiss is inactive there.
    coverpoint = "cp_menvcfg_sse_ss_page"
    lines.extend(
        [
            comment_banner(coverpoint, "pte.xwr=010 is reserved below M-mode while menvcfg.SSE=0"),
            "#ifdef ZICFISS_VM_SUPPORTED",
        ]
    )
    for sse, senvcfg_sse in ((0, 0), (1, 1), (1, 0)):
        for mode in ("S", "U"):
            envcfg = [("senvcfg", 0), ("menvcfg", 0)] if not sse else [("menvcfg", 1), ("senvcfg", senvcfg_sse)]
            tag = f"sse{sse}" if sse == senvcfg_sse else "sse1_sen0"
            lines.extend(
                [
                    f"# --- menvcfg.SSE={sse}, senvcfg.SSE={senvcfg_sse}, {mode}-mode ---",
                    *map_zicfiss_pages(test_data, user=mode == "U"),
                    *enable_translation(test_data, mode="M"),
                    *[ln for csr, value in envcfg for ln in set_envcfg_sse(csr, value, test_data, mode="M")],
                    f"RVTEST_TSBI_GOTO_{mode}MODE",
                ]
            )
            addr_reg, rd_reg, val_reg = test_data.int_regs.get_registers(3)
            lines.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                    f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the load faults",
                    test_data.add_testcase(f"load_{mode.lower()}mode_{tag}", coverpoint, _CG_SM),
                    f"LREG x{rd_reg}, 0(x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                    f"LI(x{val_reg}, 0x55)",
                    test_data.add_testcase(f"store_{mode.lower()}mode_{tag}", coverpoint, _CG_SM),
                    f"SREG x{val_reg}, 0(x{addr_reg})",
                    "RVTEST_TSBI_GOTO_MMODE",
                    *SATP_OFF,
                ]
            )
            test_data.int_regs.return_registers([addr_reg, rd_reg, val_reg])
    lines.append("#endif  // ZICFISS_VM_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# cp_envcfg_sse_rdonly0_senvcfg / cp_envcfg_sse_rdonly0_henvcfg / cp_envcfg_sse_rdonly0_virt
# ---------------------------------------------------------------------------


def _generate_envcfg_rdonly0(test_data: TestData) -> list[str]:
    """menvcfg.SSE=0 makes senvcfg.SSE and henvcfg.SSE read-only zero (leg A), and henvcfg.SSE=0
    makes senvcfg.SSE read-only zero when V=1 (leg B).

    Only the SSE bit is set (csrs) or cleared (csrc), so no other field changes. The henvcfg
    and V=1 cases need the hypervisor extension and are assembled only with H_SUPPORTED.
    """
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [
        comment_banner("cp_envcfg_sse_rdonly0_*", "The SSE enable chain forces the lower SSE fields read-only zero"),
    ]

    # Leg A: menvcfg.SSE=0 and =1, then write both values into each child.
    for menvcfg_sse in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", menvcfg_sse, test_data, mode="M"))
        for csr in ("senvcfg", "henvcfg"):
            body: list[str] = []
            for written in (0, 1):
                op = "csrrs" if written else "csrrc"
                body.extend(
                    [
                        f"LI(x{val_reg}, {csr.upper()}_SSE)",
                        test_data.add_testcase(
                            f"{csr}_sse_{op}_men{menvcfg_sse}", f"cp_envcfg_sse_rdonly0_{csr}", _CG_SM
                        ),
                        f"{op} x{rd_reg}, {csr}, x{val_reg}",
                        f"csrr x{rd_reg}, {csr}   # SSE must read 0 when menvcfg.SSE=0",
                        write_sigupd(rd_reg, test_data),
                    ]
                )
            lines.extend(gated(body, "defined(H_SUPPORTED)") if csr == "henvcfg" else body)

    # Leg B: menvcfg.SSE=1 (still set from leg A); with henvcfg.SSE=0, and =1 as the positive
    # control, write both values into senvcfg.SSE from VS-mode and read it back. Its coverpoint
    # is in Zicfiss_H_cg.
    # VS-mode reaches senvcfg only when hstateen0.ENVCFG is set (Ssstateen), and HS-mode reaches
    # hstateen0.ENVCFG only when mstateen0.ENVCFG is set (Smstateen).
    lines.extend(
        [
            "#ifdef H_SUPPORTED",
            "#ifdef SMSTATEEN_SUPPORTED",
            "#if __riscv_xlen == 64",
            f"LI(x{val_reg}, MSTATEEN0_HENVCFG)",
            f"csrs mstateen0, x{val_reg}",
            "#else",
            f"LI(x{val_reg}, MSTATEEN0H_HENVCFG)",
            f"csrs mstateen0h, x{val_reg}",
            "#endif",
            "#endif",
            "#ifdef SSSTATEEN_SUPPORTED",
            "#if __riscv_xlen == 64",
            f"LI(x{val_reg}, HSTATEEN0_SENVCFG)",
            f"csrs hstateen0, x{val_reg}",
            "#else",
            f"LI(x{val_reg}, HSTATEEN0H_SENVCFG)",
            f"csrs hstateen0h, x{val_reg}",
            "#endif",
            "#endif",
        ]
    )
    for henvcfg_sse in (0, 1):
        lines.extend(
            [
                f"LI(x{val_reg}, HENVCFG_SSE)",
                f"{'csrs' if henvcfg_sse else 'csrc'} henvcfg, x{val_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
            ]
        )
        for written in (0, 1):
            op = "csrrs" if written else "csrrc"
            lines.extend(
                [
                    f"LI(x{val_reg}, SENVCFG_SSE)",
                    test_data.add_testcase(
                        f"senvcfg_sse_{op}_vs_hen{henvcfg_sse}", "cp_envcfg_sse_rdonly0_virt", "Zicfiss_H_cg"
                    ),
                    f"{op} x{rd_reg}, senvcfg, x{val_reg}",
                    f"csrr x{rd_reg}, senvcfg   # SSE must read 0 when henvcfg.SSE=0 and V=1",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.append("RVTEST_TSBI_GOTO_MMODE")
    lines.append("#endif  // H_SUPPORTED")

    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ss_pmp_permissions
# ---------------------------------------------------------------------------


def _generate_pmp_permissions(test_data: TestData) -> list[str]:
    """Shadow stack instructions require PMP read-write, including the read-only SSPOPCHK.

    Only M-mode can program PMP. Entry 0 covers the shadow stack page as one 4 KiB NAPOT
    region, so this needs NAPOT and a PMP granularity of at most 4 KiB; entry 1 grants
    everything else, and the lowest matching entry wins. The link register is set so that a
    pop would also mismatch, so the denied cases double as the fault-priority check.
    """
    coverpoint = "cp_ss_pmp_permissions"
    lines: list[str] = [
        comment_banner(coverpoint, "PMP read-write requirement and fault priority"),
        "#ifdef ZICFISS_VM_SUPPORTED",
        "#if defined(UDB_PMP_NAPOT_SUPPORTED) && UDB_PMP_GRANULARITY <= 12 && UDB_NUM_USABLE_PMP_ENTRIES >= 2",
    ]

    # pmp0cfg: A=NAPOT (0x18) plus the R/W bits under test. pmp1cfg = 0x1F allows the rest.
    # R=0 with W=1 is reserved, so it is not a configuration that can be tested.
    for tag, rw in (("none", 0x0), ("r", 0x1), ("rw", 0x3)):
        lines.extend(
            [
                f"# --- pmp0cfg R/W = {tag} ---",
                *enable_translation(test_data, mode="M"),
                *map_zicfiss_pages(test_data, user=False),
                *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
            ]
        )
        addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
        lines.extend(
            [
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"srli x{addr_reg}, x{addr_reg}, 2",
                f"LI(x{cfg_reg}, 0x1FF)",
                f"or x{addr_reg}, x{addr_reg}, x{cfg_reg}   # NAPOT, 4 KiB",
                f"csrw pmpaddr0, x{addr_reg}",
                f"LI(x{addr_reg}, -1)",
                f"csrw pmpaddr1, x{addr_reg}",
                f"LI(x{cfg_reg}, {hex(0x1F00 | 0x18 | rw)})   # pmp0 NAPOT {tag}; pmp1 NAPOT RWX",
                f"csrw pmpcfg0, x{cfg_reg}",
                "sfence.vma",
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
        test_data.int_regs.return_registers([addr_reg, cfg_reg])
        lines.extend(
            [
                *ss_forms_against(
                    test_data,
                    PUSH_FORMS + POP_FORMS,
                    "ZICFISS_VA_SS + 0x800",
                    "0x0BADF00D",
                    f"pmp_{tag}",
                    coverpoint,
                    _CG_SM,
                ),
                *ssamoswap_forms(test_data, "ZICFISS_VA_SS", f"pmp_{tag}", coverpoint, _CG_SM),
                "RVTEST_TSBI_GOTO_MMODE",
                *SATP_OFF,
            ]
        )
        addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
        lines.extend(
            [
                f"LI(x{addr_reg}, -1)",
                f"csrw pmpaddr0, x{addr_reg}",
                f"LI(x{cfg_reg}, 0x1F)",
                f"csrw pmpcfg0, x{cfg_reg}   # restore the boot-time allow-all region",
                "sfence.vma",
            ]
        )
        test_data.int_regs.return_registers([addr_reg, cfg_reg])
    lines.append("#endif  // PMP NAPOT, granularity <= 4 KiB, at least 2 usable entries")
    lines.append("#endif  // ZICFISS_VM_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# cp_ss_satp_bare
# ---------------------------------------------------------------------------


def _generate_satp_bare(test_data: TestData) -> list[str]:
    """Below M-mode, an SS instruction with satp.MODE=Bare raises a store/AMO access fault.

    ssp and the SSAMOSWAP address point at the shadow stack page's physical address. No page
    tables are involved, so this runs on configurations without Sv39/Sv32 too. Each testcase
    records ssp or rd, which the fault leaves unchanged.
    """
    coverpoint = "cp_ss_satp_bare"
    lines: list[str] = [
        comment_banner(coverpoint, "SS instructions in S- and U-mode with satp.MODE=Bare"),
        *SATP_OFF,
        *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
        *set_envcfg_sse("senvcfg", 1, test_data, mode="M"),
    ]
    addr_reg, data_reg, rd_reg = test_data.int_regs.get_registers(3)
    for mode in ("S", "U"):
        tag = f"{mode.lower()}mode_bare"
        lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
        for form in PUSH_FORMS + POP_FORMS:
            case = [
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page + 0x800)",
                f"csrw ssp, x{addr_reg}",
                f"LI({form.link_reg}, 0x0BADF00D)",
                test_data.add_testcase(f"{form.name}_{tag}", coverpoint, _CG_SM),
                *ss_instr(form),
                f"csrr x{rd_reg}, ssp",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(zcmop_only(form.compressed, case))
        lines.extend([f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)", f"LI(x{data_reg}, 0x11223344)"])
        for width in SSAMOSWAP_WIDTHS:
            lines.extend(
                ssamoswap_only(
                    width,
                    [
                        f"LI(x{rd_reg}, 0x0DDBA11)   # kept by the fault",
                        test_data.add_testcase(f"ssamoswap_{width}_{tag}", coverpoint, _CG_SM),
                        f"ssamoswap.{width} x{rd_reg}, x{data_reg}, (x{addr_reg})",
                        write_sigupd(rd_reg, test_data),
                    ],
                )
            )
        lines.append("RVTEST_TSBI_GOTO_MMODE")
    test_data.int_regs.return_registers([addr_reg, data_reg, rd_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ss_swcheck_mtval
# ---------------------------------------------------------------------------


def _generate_swcheck_mtval(test_data: TestData) -> list[str]:
    """An SSPOPCHK value mismatch in S-mode is taken in M-mode, reporting mtval = shadow stack fault.

    This suite boots to M-mode, where RVTEST_BOOT_TO_MMODE leaves medeleg at zero, so the
    software-check exception is not delegated.
    """
    coverpoint = "cp_ss_swcheck_mtval"
    lines = [
        comment_banner(coverpoint, "SSPOPCHK mismatch in S-mode reports the shadow stack fault code in mtval"),
        "#ifdef ZICFISS_VM_SUPPORTED",
        *enable_translation(test_data, mode="M"),
        *map_zicfiss_pages(test_data, user=False),
        *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
        "RVTEST_TSBI_GOTO_SMODE",
    ]
    addr_reg = test_data.int_regs.get_register()
    for pop in POP_FORMS:
        case = [
            f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
            f"csrw ssp, x{addr_reg}",
            f"LI({pop.link_reg}, 0xA5A5A5A5)",
            f"sspush {pop.link_reg}",
            f"LI({pop.link_reg}, 0x0BADF00D)   # no longer matches what the shadow stack holds",
            test_data.add_testcase(f"{pop.name}_mismatch", coverpoint, _CG_SM),
            *ss_instr(pop),
            f"csrr x{addr_reg}, ssp   # unchanged by the failed check",
            write_sigupd(addr_reg, test_data),
        ]
        lines.extend(zcmop_only(pop.compressed, case))
    lines.extend(["RVTEST_TSBI_GOTO_MMODE", *SATP_OFF, "#endif"])
    test_data.int_regs.return_registers([addr_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ss_instr_inactive_m / cp_ss_instr_inactive_s
# ---------------------------------------------------------------------------


def _generate_instr_inactive(test_data: TestData) -> list[str]:
    """MOP-encoded SS instructions stay inert whenever Zicfiss is inactive.

    Leg A is M-mode, where Zicfiss is never supported, across every SSE state. Leg B
    executes in S-mode with menvcfg.SSE=0; ssp is set from M-mode because it is not
    accessible to S-mode then. Both legs repeat every instruction with a hostile ssp.
    """
    lines: list[str] = [
        comment_banner("cp_ss_instr_inactive_m/s", "SS instructions inert while Zicfiss is inactive"),
        "#ifdef ZICFISS_VM_SUPPORTED",
    ]
    for mode, menvcfg, senvcfg in (("m", 0, 0), ("m", 1, 0), ("m", 1, 1), ("s", 0, 0)):
        leg = f"{mode}_men{menvcfg}_sen{senvcfg}"
        # Clear senvcfg.SSE before menvcfg.SSE, and set it after, so the pair never
        # passes through the unreachable menvcfg.SSE=0, senvcfg.SSE=1 state.
        envcfg = [("menvcfg", menvcfg), ("senvcfg", senvcfg)]
        if not senvcfg:
            envcfg.reverse()
        lines.extend(
            [
                f"# --- {mode.upper()}-mode, menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                *enable_translation(test_data, mode="M"),
                *map_zicfiss_pages(test_data, user=False),
                *[ln for csr, value in envcfg for ln in set_envcfg_sse(csr, value, test_data, mode="M")],
            ]
        )
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        for state, addr in (
            ("valid", "ZICFISS_VA_SS + 0x800"),
            ("unaligned", "ZICFISS_VA_SS + 0x804"),
            ("unmapped", "ZICFISS_VA_UNMAPPED"),
            ("mismatch", "ZICFISS_VA_SS + 0x800"),
        ):
            lines.extend([f"LI(x{addr_reg}, {addr})", f"csrw ssp, x{addr_reg}"])
            lines.extend(["RVTEST_TSBI_GOTO_SMODE"] if mode == "s" else [])
            for form in MOP_FORMS:
                label = test_data.add_testcase(f"{form.name}_{leg}_{state}", f"cp_ss_instr_inactive_{mode}", _CG_SM)
                if form.link_reg is None:  # SSRDP writes 0 while inactive
                    lines.extend([label, f"ssrdp x{rd_reg}", write_sigupd(rd_reg, test_data)])
                    continue
                value = "0xDEADBEEF" if state == "mismatch" else "0"
                lines.extend(zcmop_only(form.compressed, [f"LI({form.link_reg}, {value})", label, *ss_instr(form)]))
            lines.extend(["RVTEST_TSBI_GOTO_MMODE"] if mode == "s" else [])
            lines.extend([f"csrr x{rd_reg}, ssp   # unchanged", write_sigupd(rd_reg, test_data)])
        lines.extend(SATP_OFF)
        test_data.int_regs.return_registers([addr_reg, rd_reg])
    lines.append("#endif  // ZICFISS_VM_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Zicfiss",
    required_extensions=["Sm", "S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfisssm(test_data: TestData) -> list[TestChunk]:
    """Generate the Zicfiss Sm group."""
    test_chunks: list[TestChunk] = []
    for section in (
        _generate_ssamoswap_mmode_fault,
        _generate_mprv_non_idempotent,
        _generate_menvcfg_gating,
        _generate_envcfg_rdonly0,
        _generate_pmp_permissions,
        _generate_satp_bare,
        _generate_swcheck_mtval,
        _generate_instr_inactive,
    ):
        tc = test_data.begin_test_chunk("Sm")
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks


# ============================================================================
# S group
# ============================================================================
# ZicfissS test generator.
#
# Shadow stack behaviour seen from S/HS-mode, following the ZicfissS sheet of the testplan
# linked from docs/ctp/src/privmisc23.adoc:
#
#   1. S-specific gating -- menvcfg.SSE alone gates S/HS. senvcfg.SSE is swept to show that
#      it has no effect at S/HS.
#   2. The instruction behaviour of ZicfissU repeated in S-mode, including how pte.U,
#      sstatus.SUM and sstatus.MXR apply to shadow stack accesses from S-mode.
#
# The suite boots to S-mode and stays there. The page tables are supervisor pages, so the
# S-mode handler can take the traps as usual. menvcfg is the one M-mode CSR it writes, through
# T-SBI.

_CG_S = "Zicfiss_S_cg"


def _smode_prologue(test_data: TestData, *, menvcfg: int = 1, senvcfg: int = 1, ss_perms: str = PTE_SS) -> list[str]:
    """Translation, page mappings and the SSE bits, all from S-mode.

    Enabling translation before the mappings are written is safe because the boot code
    already identity-maps the superpage holding the code and data as supervisor RWX.
    """
    return [
        *enable_translation(test_data, mode="S"),
        *map_zicfiss_pages(test_data, ss_perms=ss_perms, user=False),
        *set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", senvcfg, test_data, mode="S"),
    ]


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_s / cp_ssamoswap_sse_gating_s -- senvcfg.SSE must NOT gate S/HS
# ---------------------------------------------------------------------------


def _generate_ssp_gating_s(test_data: TestData) -> list[str]:
    """menvcfg.SSE gates ssp access and SSAMOSWAP in S-mode; senvcfg.SSE must not.

    Each ssp access and SSAMOSWAP records rd, which an illegal-instruction exception leaves
    unchanged. SSAMOSWAP targets the SS page, so it succeeds whenever menvcfg.SSE=1.
    """
    coverpoint = "cp_ssp_csr_gating_s"
    lines: list[str] = []
    for menvcfg in (0, 1):
        for senvcfg in (0, 1):
            tag = f"m{menvcfg}s{senvcfg}"
            lines.extend(
                [
                    f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                    *_smode_prologue(test_data, menvcfg=menvcfg, senvcfg=senvcfg),
                ]
            )
            rd_reg, val_reg = test_data.int_regs.get_registers(2)
            # An XLEN-aligned value to write to ssp
            lines.append(f"LI(x{val_reg}, 0x3000)")
            for op, form in (
                ("csrrw", f"csrrw x{rd_reg}, ssp, x{val_reg}"),
                ("csrrs", f"csrrs x{rd_reg}, ssp, x{val_reg}"),
                ("csrrc", f"csrrc x{rd_reg}, ssp, x{val_reg}"),
                ("csrrwi", f"csrrwi x{rd_reg}, ssp, 1"),
                ("csrrsi", f"csrrsi x{rd_reg}, ssp, 1"),
                ("csrrci", f"csrrci x{rd_reg}, ssp, 1"),
            ):
                lines.extend(
                    [
                        f"LI(x{rd_reg}, 0x0DDBA11)",
                        test_data.add_testcase(f"ssp_{op}_{tag}", coverpoint, _CG_S),
                        form,
                        write_sigupd(rd_reg, test_data),
                    ]
                )
            addr_reg = test_data.int_regs.get_register()
            lines.extend([f"LI(x{addr_reg}, ZICFISS_VA_SS)", f"LI(x{val_reg}, 0x11223344)"])
            for width in SSAMOSWAP_WIDTHS:
                lines.extend(
                    ssamoswap_only(
                        width,
                        [
                            f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap is illegal",
                            test_data.add_testcase(f"ssamoswap_{width}_{tag}", "cp_ssamoswap_sse_gating_s", _CG_S),
                            f"ssamoswap.{width} x{rd_reg}, x{val_reg}, (x{addr_reg})",
                            write_sigupd(rd_reg, test_data),
                        ],
                    )
                )
            lines.extend(SATP_OFF)
            test_data.int_regs.return_registers([rd_reg, val_reg, addr_reg])
    return vm_section(coverpoint, "menvcfg.SSE gates ssp and SSAMOSWAP at S/HS; senvcfg.SSE must not", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_enc -- the xwr=010 encoding, gated by menvcfg.SSE
# ---------------------------------------------------------------------------


def _generate_page_enc_s(test_data: TestData) -> list[str]:
    """Loads record rd, which a page fault leaves unchanged."""
    lines: list[str] = []
    for menvcfg in (0, 1):
        lines.extend([f"# --- menvcfg.SSE={menvcfg} ---", *_smode_prologue(test_data, menvcfg=menvcfg)])
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines.extend(
            [
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                # ssp is illegal while menvcfg.SSE=0 (cp_ssp_csr_gating_s), and the inert sspush
                # does not use it then.
                *([f"csrw ssp, x{addr_reg}"] if menvcfg else []),
                "LI(x1, 0xC0FFEE11)",
                test_data.add_testcase(f"ss_page_enc_push_men{menvcfg}", "cp_ss_page_enc", _CG_S),
                "sspush x1",
            ]
        )
        if menvcfg:  # ssp is inaccessible while menvcfg.SSE=0
            lines.extend([f"csrr x{rd_reg}, ssp", write_sigupd(rd_reg, test_data)])
        # An ordinary load from an SS page is permitted; an ordinary store is not.
        for m in ("lb", "lh", "lw", "ld"):
            load = [
                f"LI(x{rd_reg}, 0x0DDBA11)",
                test_data.add_testcase(f"{m}_ss_page_men{menvcfg}", "cp_ss_page_enc_load", _CG_S),
                f"{m} x{rd_reg}, 0(x{addr_reg})",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(rv64_only(load) if m == "ld" else load)
        for m in ("sb", "sh", "sw", "sd"):
            store = [
                f"LI(x{rd_reg}, 0x55)",
                test_data.add_testcase(f"{m}_ss_page_men{menvcfg}", "cp_ss_page_enc_store", _CG_S),
                f"{m} x{rd_reg}, 0(x{addr_reg})",
            ]
            lines.extend(rv64_only(store) if m == "sd" else store)
        lines.extend(SATP_OFF)
        test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section("cp_ss_page_enc", "pte.xwr=010 is an SS page when menvcfg.SSE=1, reserved when 0", lines)


# ---------------------------------------------------------------------------
# S-mode re-run of the instruction behaviour
# ---------------------------------------------------------------------------


def _generate_instr_s(test_data: TestData) -> list[str]:
    ssp_top = "ZICFISS_VA_SS + 0x800"
    lines = _smode_prologue(test_data)
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)

    for form in PUSH_FORMS:
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({form.link_reg}, 0xA5A5A5A5)",
            test_data.add_testcase(f"{form.name}_s", "cp_sspush_s", _CG_S),
            *ss_instr(form),
            f"csrr x{rd_reg}, ssp",
            write_sigupd(rd_reg, test_data),
            # An SS page is readable by ordinary loads, so confirm the value
            # actually landed at the new top of stack.
            f"LREG x{rd_reg}, 0(x{rd_reg})",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(form.compressed, case))

    for push, pop in zip(PUSH_FORMS, POP_FORMS, strict=True):
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({push.link_reg}, 0x5A5A5A5A)",
            *ss_instr(push),
            f"mv {pop.link_reg}, {push.link_reg}",
            test_data.add_testcase(f"{pop.name}_match_s", "cp_sspopchk_match_s", _CG_S),
            *ss_instr(pop),
            f"csrr x{rd_reg}, ssp",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(push.compressed or pop.compressed, case))

    for pop in POP_FORMS:
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({pop.link_reg}, 0x11111111)",
            f"sspush {pop.link_reg}",
            f"LI({pop.link_reg}, 0x22222222)   # no longer matches the shadow copy",
            test_data.add_testcase(f"{pop.name}_mismatch_s", "cp_sspopchk_mismatch_s", _CG_S),
            *ss_instr(pop),
            f"csrr x{rd_reg}, ssp   # unchanged by the failed check",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(pop.compressed, case))

    lines.extend(
        [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            test_data.add_testcase("ssrdp_s", "cp_ssrdp_s", _CG_S),
            f"ssrdp x{rd_reg}",
            write_sigupd(rd_reg, test_data),
            f"LI(x{addr_reg}, ZICFISS_VA_SS)",
            f"LI(x{rs2_reg}, 0x11223344)",
        ]
    )
    for width in SSAMOSWAP_WIDTHS:
        lines.extend(
            ssamoswap_only(
                width,
                [
                    test_data.add_testcase(f"ssamoswap_{width}_s", "cp_ssamoswap_s", _CG_S),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ],
            )
        )

    lines.extend(SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg])
    return vm_section("ZicfissS instructions", "Shadow stack instruction behaviour re-run in S-mode", lines)


# ---------------------------------------------------------------------------
# cp_ss_address_alignment_*_s
# ---------------------------------------------------------------------------


def _generate_alignment_s(test_data: TestData) -> list[str]:
    """Sweep addr[2:0] for ssp and for SSAMOSWAP; every misaligned SSAMOSWAP faults."""
    lines = _smode_prologue(test_data)
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)

    for offset in range(8):
        addr = f"ZICFISS_VA_SS + {hex(0x400 + offset)}"
        tag = f"ssp_off{offset}_s"
        lines.extend(
            [
                *ss_forms_against(
                    test_data, PUSH_FORMS, addr, "0xDEADBEEF", tag, "cp_ss_address_alignment_ssp_s", _CG_S
                ),
                *ss_forms_against(
                    test_data, POP_FORMS, addr, "0xDEADBEEF", tag, "cp_ss_address_alignment_pop_s", _CG_S
                ),
            ]
        )

    for width in SSAMOSWAP_WIDTHS:
        block: list[str] = []
        for offset in range(8):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + {hex(0x400 + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                    test_data.add_testcase(f"ssamoswap_{width}_off{offset}_s", "cp_ss_address_alignment_swap_s", _CG_S),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.extend(ssamoswap_only(width, block))

    lines.extend(SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg])
    return vm_section("cp_ss_address_alignment_*_s", "ssp and SSAMOSWAP alignment sweep in S-mode", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page_s and cp_sspopchk_fault_priority_s
# ---------------------------------------------------------------------------


def _generate_target_page_s(test_data: TestData) -> list[str]:
    """Remap the shadow stack page with each pte.xwr encoding; then the memory-fault priority."""
    coverpoint = "cp_ss_instr_target_page_s"
    lines: list[str] = []
    mid = "ZICFISS_VA_SS + 0x800"  # sspush decrements before storing
    for xwr, perms in XWR_PERMS.items():
        lines.extend(
            [
                f"# --- pte.xwr = {xwr} ---",
                *_smode_prologue(test_data, ss_perms=perms),
                *ss_forms_against(
                    test_data, PUSH_FORMS + POP_FORMS, mid, "0xDEADBEEF", f"xwr{xwr}_s", coverpoint, _CG_S
                ),
                *ssamoswap_forms(test_data, mid, f"xwr{xwr}_s", coverpoint, _CG_S),
                *SATP_OFF,
            ]
        )

    # cp_sspopchk_fault_priority_s -- unmapped ssp plus a value mismatch.
    lines.extend(
        [
            *_smode_prologue(test_data),
            *ss_forms_against(
                test_data,
                POP_FORMS,
                "ZICFISS_VA_UNMAPPED",
                "0x0BADF00D",
                "fault_priority_s",
                "cp_sspopchk_fault_priority_s",
                _CG_S,
            ),
            *SATP_OFF,
        ]
    )
    return vm_section(coverpoint, "SS instructions against every pte.xwr encoding, and memory-fault priority", lines)


# ---------------------------------------------------------------------------
# cp_ss_non_idempotent_s
# ---------------------------------------------------------------------------


def _generate_non_idempotent_s(test_data: TestData) -> list[str]:
    """Svpbmt NC memory is idempotent and IO memory is not, so SS instructions fault only on IO.

    menvcfg.PBMTE is swept: with PBMTE=0 a nonzero PBMT is reserved and the walk page-faults.
    With PBMTE=1, SSAMOSWAP is left out on NC pages, because an implementation may also override
    the AMO PMA there (norm:Svpbmt_impl_may_override_pmas), so its outcome is implementation-defined
    and no UDB parameter says which behavior a DUT has. Those coverage bins stay as a known gap.
    """
    coverpoint = "cp_ss_non_idempotent_s"
    mid = "ZICFISS_VA_SS + 0x800"
    lines = ["#if defined(SVPBMT_SUPPORTED) && __riscv_xlen == 64"]
    for pbmte in (1, 0):
        pbmte_reg = test_data.int_regs.get_register()
        lines.extend(
            [
                f"# --- menvcfg.PBMTE = {pbmte} ---",
                f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
                tsbi_call(f"{'csrs' if pbmte else 'csrc'} menvcfg, x{pbmte_reg}"),
            ]
        )
        test_data.int_regs.return_registers([pbmte_reg])
        # pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO.
        for tag, pbmt in (("pma", 0), ("nc", 1), ("io", 2)):
            name = f"pbmte{pbmte}_pbmt_{tag}_s"
            lines.extend(
                [
                    f"# --- pte.PBMT = {tag} ---",
                    *_smode_prologue(test_data, ss_perms=f"{PTE_SS} | ({pbmt} << 61)"),
                    *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0x1D1D1D1D", name, coverpoint, _CG_S),
                    *(ssamoswap_forms(test_data, mid, name, coverpoint, _CG_S) if (pbmte, tag) != (1, "nc") else []),
                    *SATP_OFF,
                ]
            )
    lines.append("#endif  // SVPBMT_SUPPORTED && RV64")
    return vm_section(coverpoint, "Svpbmt memory types on the shadow stack page, by menvcfg.PBMTE", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_perm_priority
# ---------------------------------------------------------------------------


def _generate_perm_priority_s(test_data: TestData) -> list[str]:
    """U/SUM/MXR resolve during translation, before any Zicfiss rule."""
    coverpoint = "cp_ss_page_perm_priority"
    ssp_top = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for u_bit in (0, 1):
        lines.extend(
            [
                f"# --- pte.U = {u_bit} ---",
                *_smode_prologue(test_data, ss_perms=PTE_SS + (" | PTE_U" if u_bit else "")),
            ]
        )
        for sum_bit in (0, 1):
            for mxr_bit in (0, 1):
                tag = f"u{u_bit}_sum{sum_bit}_mxr{mxr_bit}"
                set_bits = " | ".join(
                    ["0"] + (["SSTATUS_SUM"] if sum_bit else []) + (["SSTATUS_MXR"] if mxr_bit else [])
                )
                mask_reg = test_data.int_regs.get_register()
                lines.extend(
                    [
                        f"LI(x{mask_reg}, SSTATUS_SUM | SSTATUS_MXR)",
                        f"csrc sstatus, x{mask_reg}",
                        f"LI(x{mask_reg}, {set_bits})",
                        f"csrs sstatus, x{mask_reg}",
                    ]
                )
                test_data.int_regs.return_registers([mask_reg])
                lines.extend(
                    [
                        *ss_forms_against(
                            test_data, PUSH_FORMS + POP_FORMS, ssp_top, "0x5A5A5A5A", tag, coverpoint, _CG_S
                        ),
                        *ssamoswap_forms(test_data, ssp_top, tag, coverpoint, _CG_S),
                    ]
                )
                # An ordinary load is permitted by the shadow stack rules, for both MXR
                # values; an ordinary store is not. Loads record rd, which a fault leaves unchanged.
                addr_reg, data_reg = test_data.int_regs.get_registers(2)
                lines.append(f"LI(x{addr_reg}, {ssp_top})")
                for m in ("lb", "lh", "lw", "ld"):
                    load = [
                        f"LI(x{data_reg}, 0x0DDBA11)",
                        test_data.add_testcase(f"{m}_{tag}", "cp_ss_page_perm_priority_load", _CG_S),
                        f"{m} x{data_reg}, 0(x{addr_reg})",
                        write_sigupd(data_reg, test_data),
                    ]
                    lines.extend(rv64_only(load) if m == "ld" else load)
                for m in ("sb", "sh", "sw", "sd"):
                    store = [
                        f"LI(x{data_reg}, 0x55)",
                        test_data.add_testcase(f"{m}_{tag}", "cp_ss_page_perm_priority_store", _CG_S),
                        f"{m} x{data_reg}, 0(x{addr_reg})",
                    ]
                    lines.extend(rv64_only(store) if m == "sd" else store)
                test_data.int_regs.return_registers([addr_reg, data_reg])
        lines.extend(SATP_OFF)
    return vm_section(coverpoint, "pte.U, sstatus.SUM and sstatus.MXR against the SS page", lines)


# ---------------------------------------------------------------------------
# cp_senvcfg_sse_rdonly0_s
# ---------------------------------------------------------------------------


def _generate_senvcfg_rdonly0_s(test_data: TestData) -> list[str]:
    """senvcfg.SSE reads back 0 from S-mode whenever menvcfg.SSE is 0.

    csrrs sets and csrrc clears only the SSE bit, so no other senvcfg field changes.
    """
    coverpoint = "cp_senvcfg_sse_rdonly0_s"
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [comment_banner(coverpoint, "senvcfg.SSE read-only zero while menvcfg.SSE=0")]
    for menvcfg in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"))
        for written in (0, 1):
            op = "csrrs" if written else "csrrc"
            lines.extend(
                [
                    f"LI(x{val_reg}, SENVCFG_SSE)",
                    test_data.add_testcase(f"senvcfg_{op}_men{menvcfg}_wrote{written}", coverpoint, _CG_S),
                    f"{op} x{rd_reg}, senvcfg, x{val_reg}",
                    f"csrr x{rd_reg}, senvcfg   # SSE must read 0 when menvcfg.SSE=0",
                    write_sigupd(rd_reg, test_data),
                ]
            )
    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


def _generate_unused_mop_s(test_data: TestData) -> list[str]:
    lines = _smode_prologue(test_data)
    lines.extend(unused_mop_cases(test_data, "_s", _CG_S))
    return lines


def _generate_misaligned_store_s(test_data: TestData) -> list[str]:
    coverpoint = "cp_ss_page_access_store_misaligned_s"
    lines = _smode_prologue(test_data)
    lines.extend(misaligned_store_cases(test_data, coverpoint, _CG_S))
    return lines


@add_priv_test_generator(
    "Zicfiss",
    required_extensions=["S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicfisss(test_data: TestData) -> list[TestChunk]:
    """Generate the Zicfiss S group."""
    test_chunks: list[TestChunk] = []
    for section in (
        _generate_ssp_gating_s,
        _generate_page_enc_s,
        _generate_instr_s,
        _generate_unused_mop_s,
        _generate_misaligned_store_s,
        _generate_alignment_s,
        _generate_target_page_s,
        _generate_non_idempotent_s,
        _generate_perm_priority_s,
        _generate_senvcfg_rdonly0_s,
    ):
        tc = test_data.begin_test_chunk("S")
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks


# ============================================================================
# U group
# ============================================================================
# ZicfissU test generator.
#
# Shadow stack behaviour seen from U-mode: the ssp CSR; SSPUSH, SSPOPCHK, SSRDP and
# SSAMOSWAP; how shadow stack instructions treat pages of every type; how ordinary, atomic,
# cache-block and (with Zve32x) vector accesses treat a shadow stack page; and the U-mode
# half of the SSE enable chain.
#
# The suite boots to U-mode. Each section steps up to S-mode through T-SBI to build the
# page tables and set the SSE bits, drops back to U-mode, turns translation on (see
# ``_umode_prologue``), runs its testcases, and turns translation off again. The testplan
# is the ZicfissU sheet linked from docs/ctp/src/privmisc23.adoc.

_CG_U = "Zicfiss_U_cg"

# Turn translation off from U-mode.
_SATP_OFF = [tsbi_call("csrw satp, x0")]


def _umode_prologue(
    test_data: TestData,
    *,
    menvcfg: int = 1,
    senvcfg: int = 1,
    ss_perms: str = PTE_SS,
    ss_page_user: bool | None = None,
    extra_mappings: tuple[str, ...] = (),
) -> list[str]:
    """Build the page tables and SSE state in S-mode, then enable translation from U-mode.

    The test body is mapped as user pages, which S-mode cannot fetch, so satp is written
    through T-SBI from U-mode. sstatus.SUM lets the S-mode trap handler record trap signatures
    in the user-mapped signature region. Arguments other than ``test_data`` are those of
    ``map_zicfiss_pages`` and the SSE values; ``extra_mappings`` adds page-table lines.
    """
    sum_reg = test_data.int_regs.get_register()
    lines = [
        "RVTEST_TSBI_GOTO_SMODE",
        *map_zicfiss_pages(test_data, ss_perms=ss_perms, user=True, ss_page_user=ss_page_user),
        *extra_mappings,
        f"LI(x{sum_reg}, SSTATUS_SUM)",
        f"csrs sstatus, x{sum_reg}",
        *set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", senvcfg, test_data, mode="S"),
        "RVTEST_TSBI_GOTO_UMODE",
        *enable_translation(test_data, mode="U"),
    ]
    test_data.int_regs.return_registers([sum_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ssp_access / cp_ssp_low_bits_ro_zero
# ---------------------------------------------------------------------------


def _generate_ssp_access(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssp_access"
    lines = _umode_prologue(test_data)
    val_reg, rd_reg = test_data.int_regs.get_registers(2)

    # Write all-ones and all-zeros through each register form.
    for op in ("csrrw", "csrrs", "csrrc"):
        for name, pattern in (("ones", "-1"), ("zeros", "0")):
            lines.extend(
                [
                    f"LI(x{val_reg}, {pattern})",
                    test_data.add_testcase(f"ssp_{op}_{name}", coverpoint, _CG_U),
                    f"{op} x{rd_reg}, ssp, x{val_reg}",
                    f"csrr x{rd_reg}, ssp   # read back",
                    write_sigupd(rd_reg, test_data),
                ]
            )

    # Immediate-form CSR ops so the csrrwi/csrrsi/csrrci bins fill.
    for op in ("csrrwi", "csrrsi", "csrrci"):
        lines.extend(
            [
                test_data.add_testcase(f"ssp_{op}", coverpoint, _CG_U),
                f"{op} x{rd_reg}, ssp, 3   # bits [1:0] are read-only zero",
                f"csrr x{rd_reg}, ssp",
                write_sigupd(rd_reg, test_data),
            ]
        )

    # cp_ssp_low_bits_ro_zero: every CSR form x every value written into ssp[2:0].
    for low in range(8):
        for op, form in (
            ("csrrw", f"csrrw x{rd_reg}, ssp, x{val_reg}"),
            ("csrrs", f"csrrs x{rd_reg}, ssp, x{val_reg}"),
            ("csrrc", f"csrrc x{rd_reg}, ssp, x{val_reg}"),
            ("csrrwi", f"csrrwi x{rd_reg}, ssp, {low}"),
            ("csrrsi", f"csrrsi x{rd_reg}, ssp, {low}"),
            ("csrrci", f"csrrci x{rd_reg}, ssp, {low}"),
        ):
            lines.extend(
                [
                    f"LI(x{val_reg}, ZICFISS_VA_SS | {low})",
                    test_data.add_testcase(f"ssp_low_bits_{op}_{low}", "cp_ssp_low_bits_ro_zero", _CG_U),
                    form,
                    f"csrr x{rd_reg}, ssp   # ssp low bits must read as zero",
                    write_sigupd(rd_reg, test_data),
                ]
            )

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([val_reg, rd_reg])
    return vm_section(coverpoint, "ssp CSR access, width, and read-only-zero low bits", lines)


# ---------------------------------------------------------------------------
# cp_sspush / cp_sspopchk_match / cp_sspopchk_mismatch
# ---------------------------------------------------------------------------


def _generate_push_pop(test_data: TestData) -> list[str]:
    # Start ssp near the top of the SS page so pushes have room to grow down.
    ssp_top = "ZICFISS_VA_SS + 0x800"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)

    # cp_sspush -- each encoding pushes all-zeros, all-ones and a pattern; read back ssp
    # and the pushed value.
    for form in PUSH_FORMS:
        for value_name, value in (("zeros", "0"), ("ones", "-1"), ("pattern", "0x5A5A5A5A")):
            case = [
                f"LI(x{addr_reg}, {ssp_top})",
                f"csrw ssp, x{addr_reg}",
                f"LI({form.link_reg}, {value})",
                test_data.add_testcase(f"{form.name}_{value_name}", "cp_sspush", _CG_U),
                *ss_instr(form),
                f"csrr x{rd_reg}, ssp   # must be ssp_top - XLEN/8",
                write_sigupd(rd_reg, test_data),
                f"LREG x{rd_reg}, 0(x{rd_reg})   # the pushed value",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(zcmop_only(form.compressed, case))

    # cp_sspopchk_match -- push then pop the same value back.
    for push, pop in zip(PUSH_FORMS, POP_FORMS, strict=True):
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({push.link_reg}, 0x5A5A5A5A)",
            *ss_instr(push),
            f"mv {pop.link_reg}, {push.link_reg}   # matching value in the pop's link register",
            test_data.add_testcase(f"{pop.name}_match", "cp_sspopchk_match", _CG_U),
            *ss_instr(pop),
            f"csrr x{rd_reg}, ssp   # must be back at ssp_top",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(push.compressed or pop.compressed, case))

    # cp_sspopchk_mismatch -- corrupt the link register so the compare fails, including
    # values that differ from the shadow copy in exactly one bit, at each end.
    for pop in POP_FORMS:
        for edge, pushed, popped in (
            ("", "0x11111111", "0x22222222"),
            ("_bit0", "0", "1"),
            ("_bit_msb", "0", "(1 << (__riscv_xlen - 1))"),
        ):
            case = [
                f"LI(x{addr_reg}, {ssp_top})",
                f"csrw ssp, x{addr_reg}",
                f"LI({pop.link_reg}, {pushed})",
                f"sspush {pop.link_reg}",
                f"LI({pop.link_reg}, {popped})   # no longer matches the shadow copy",
                test_data.add_testcase(f"{pop.name}_mismatch{edge}", "cp_sspopchk_mismatch", _CG_U),
                *ss_instr(pop),
                f"csrr x{rd_reg}, ssp   # unchanged by the failed check",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(zcmop_only(pop.compressed, case))

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section("cp_sspush/cp_sspopchk", "Shadow stack push and pop, matching and mismatching", lines)


# ---------------------------------------------------------------------------
# cp_sspopchk_fault_priority
# ---------------------------------------------------------------------------


def _generate_fault_priority(test_data: TestData) -> list[str]:
    """A memory fault on the pop outranks the software-check exception.

    ssp is pointed at a deliberately unmapped VA *and* the link register is given a
    value that would not match, so both faults are live at once. Only the memory
    fault may be reported.
    """
    coverpoint = "cp_sspopchk_fault_priority"
    lines = [
        *_umode_prologue(test_data),
        *ss_forms_against(
            test_data, POP_FORMS, "ZICFISS_VA_UNMAPPED", "0x0BADF00D", "fault_priority", coverpoint, _CG_U
        ),
        *_SATP_OFF,
    ]
    return vm_section(coverpoint, "Memory fault on the pop outranks the software-check exception", lines)


# ---------------------------------------------------------------------------
# Call/return round trip
# ---------------------------------------------------------------------------


def _generate_call_return(test_data: TestData) -> list[str]:
    """Nested prologue pushes and epilogue pops of x1, then a subverted return address."""
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines.extend([f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)", f"csrw ssp, x{addr_reg}"])

    # Three nested prologues: each spills the link register to the shadow stack.
    for depth in range(3):
        lines.extend(
            [
                f"LI(x1, {hex(0xC0DE0000 + depth)})   # simulated return address at depth {depth}",
                test_data.add_testcase(f"call_prologue_depth{depth}", "cp_sspush", _CG_U),
                "sspush x1",
            ]
        )
    # Three matching epilogues, unwinding in reverse order.
    for depth in reversed(range(3)):
        lines.extend(
            [
                f"LI(x1, {hex(0xC0DE0000 + depth)})   # link register reloaded from the regular stack",
                test_data.add_testcase(f"return_epilogue_depth{depth}", "cp_sspopchk_match", _CG_U),
                "sspopchk x1",
            ]
        )
    lines.extend([f"csrr x{rd_reg}, ssp   # must be back at the starting ssp", write_sigupd(rd_reg, test_data)])

    # Subverted return address: the epilogue compare must catch it.
    lines.extend(
        [
            "LI(x1, 0xC0DE1234)",
            "sspush x1",
            "LI(x1, 0xBAD00BAD)   # attacker-supplied return address",
            test_data.add_testcase("return_subverted", "cp_sspopchk_mismatch", _CG_U),
            "sspopchk x1",
            f"csrr x{rd_reg}, ssp   # unchanged by the failed check",
            write_sigupd(rd_reg, test_data),
        ]
    )

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section("call/return", "Non-leaf prologue/epilogue round trip across nested depth", lines)


# ---------------------------------------------------------------------------
# cp_ssrdp
# ---------------------------------------------------------------------------


def _generate_ssrdp(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssrdp"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines.extend(
        [
            f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
            f"csrw ssp, x{addr_reg}",
            test_data.add_testcase("ssrdp_reads_ssp", coverpoint, _CG_U),
            f"ssrdp x{rd_reg}",
            write_sigupd(rd_reg, test_data),
            "LI(x1, 0xFEEDFACE)",
            "sspush x1",
            test_data.add_testcase("ssrdp_after_push", coverpoint, _CG_U),
            f"ssrdp x{rd_reg}   # must equal ssp after the push",
            write_sigupd(rd_reg, test_data),
            *_SATP_OFF,
        ]
    )
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section(coverpoint, "SSRDP moves ssp into rd", lines)


# ---------------------------------------------------------------------------
# cp_ssamoswap
# ---------------------------------------------------------------------------


def _generate_ssamoswap(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssamoswap"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg, rs2_reg, seed_reg = test_data.int_regs.get_registers(4)

    # The loaded value's bit 31 (the sign bit RV64 SSAMOSWAP.W extends) and, on RV64, whether
    # rs2[63:32] is non-zero, which SSAMOSWAP.W must ignore.
    for width in SSAMOSWAP_WIDTHS:
        block: list[str] = []
        for msb in (0, 1):
            for upper in (0, 1):
                name = f"ssamoswap_{width}_msb{msb}_upper{upper}"
                case = [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{seed_reg}, {'0x80000000' if msb else '0x7FFFFFFF'})",
                    # Ordinary stores to an SS page raise an access fault, so a swap seeds the location.
                    f"ssamoswap.{width} x{rd_reg}, x{seed_reg}, (x{addr_reg})",
                    f"LI(x{rs2_reg}, {'0xAAAAAAAA12345678' if upper else '0x12345678'})",
                    test_data.add_testcase(name, coverpoint, _CG_U),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
                block.extend(rv64_only(case) if upper else case)
        lines.extend(ssamoswap_only(width, block))

    for width in SSAMOSWAP_WIDTHS:
        block = []
        # cp_ssamoswap_aqrl: all four ordering-bit encodings.
        for aq, rl, suffix in ((0, 0, ""), (0, 1, ".rl"), (1, 0, ".aq"), (1, 1, ".aqrl")):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{rs2_reg}, {hex(0x5A5A5A50 + 2 * aq + rl)})",
                    test_data.add_testcase(f"ssamoswap_{width}_aq{aq}_rl{rl}", "cp_ssamoswap_aqrl", _CG_U),
                    f"ssamoswap.{width}{suffix} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        # cp_ssamoswap_reg_edges: all distinct, rd=x0, rs2=x0, rd==rs1. rd records the value the
        # previous swap stored; a load of the location records what this one stored.
        for name, form, rd in (
            ("distinct", f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})", rd_reg),
            ("rd_x0", f"ssamoswap.{width} x0, x{rs2_reg}, (x{addr_reg})", None),
            ("rs2_x0", f"ssamoswap.{width} x{rd_reg}, x0, (x{addr_reg})", rd_reg),
            ("rd_eq_rs1", f"ssamoswap.{width} x{addr_reg}, x{rs2_reg}, (x{addr_reg})", addr_reg),
        ):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{rs2_reg}, 0x3C3C3C3C)",
                    test_data.add_testcase(f"ssamoswap_{width}_{name}", "cp_ssamoswap_reg_edges", _CG_U),
                    form,
                    *([write_sigupd(rd, test_data)] if rd is not None else []),
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"l{width} x{rd_reg}, 0(x{addr_reg})   # the stored value",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.extend(ssamoswap_only(width, block))

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, seed_reg])
    return vm_section(coverpoint, "SSAMOSWAP.W/.D swap, sign-extension, ordering bits and register edges", lines)


# ---------------------------------------------------------------------------
# cp_ss_address_alignment
# ---------------------------------------------------------------------------


def _generate_alignment(test_data: TestData) -> list[str]:
    """Sweep addr[2:0] for ssp and for SSAMOSWAP; every misaligned SSAMOSWAP faults."""
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)

    for offset in range(8):
        addr = f"ZICFISS_VA_SS + {hex(0x400 + offset)}"
        lines.extend(
            [
                *ss_forms_against(
                    test_data, PUSH_FORMS, addr, "0xDEADBEEF", f"ssp_off{offset}", "cp_ss_address_alignment_ssp", _CG_U
                ),
                *ss_forms_against(
                    test_data, POP_FORMS, addr, "0xDEADBEEF", f"ssp_off{offset}", "cp_ss_address_alignment_pop", _CG_U
                ),
            ]
        )

    for width in SSAMOSWAP_WIDTHS:
        block: list[str] = []
        for offset in range(8):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + {hex(0x400 + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                    test_data.add_testcase(f"ssamoswap_{width}_off{offset}", "cp_ss_address_alignment_swap", _CG_U),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.extend(ssamoswap_only(width, block))

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg])
    return vm_section("cp_ss_address_alignment", "ssp and SSAMOSWAP address alignment sweep over addr[2:0]", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page -- SS instructions against every kind of page
# ---------------------------------------------------------------------------


def _generate_target_page(test_data: TestData) -> list[str]:
    """Remap the shadow stack page with each of the eight pte.xwr encodings."""
    coverpoint = "cp_ss_instr_target_page"
    # Aim at the middle of the page: sspush decrements ssp before storing, so a pointer at
    # the page base would push into the preceding page instead.
    mid = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for xwr, perms in XWR_PERMS.items():
        lines.extend(
            [
                f"# --- pte.xwr = {xwr} ---",
                *_umode_prologue(test_data, ss_perms=perms),
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0xDEADBEEF", f"xwr{xwr}", coverpoint, _CG_U),
                *ssamoswap_forms(test_data, mid, f"xwr{xwr}", coverpoint, _CG_U),
                *_SATP_OFF,
            ]
        )
    return vm_section(coverpoint, "SS instructions against every pte.xwr encoding", lines)


def _generate_target_page_mxr_u(test_data: TestData) -> list[str]:
    """Sweep sstatus.MXR and the SS page's U bit against the SS instructions."""
    coverpoint = "cp_ss_instr_target_page_u_mxr"
    mid = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for u_bit in (0, 1):
        # ss_page_user=False leaves the SS page's U bit to ss_perms.
        lines.extend(
            [
                f"# --- pte.U = {u_bit} ---",
                *_umode_prologue(test_data, ss_perms=PTE_SS + (" | PTE_U" if u_bit else ""), ss_page_user=False),
            ]
        )
        for mxr in (0, 1):
            tag = f"u{u_bit}_mxr{mxr}"
            mask_reg = test_data.int_regs.get_register()
            lines.extend(
                [
                    f"LI(x{mask_reg}, SSTATUS_MXR)",
                    tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{mask_reg}"),
                    *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0x4D4D4D4D", tag, coverpoint, _CG_U),
                    *ssamoswap_forms(test_data, mid, tag, coverpoint, _CG_U),
                ]
            )
            test_data.int_regs.return_registers([mask_reg])
        lines.extend(_SATP_OFF)
    return vm_section(coverpoint, "MXR and pte.U axes on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_crossing
# ---------------------------------------------------------------------------


def _generate_page_crossing(test_data: TestData) -> list[str]:
    """A push at a page base writes into the preceding page; a pop reads its own page."""
    coverpoint = "cp_ss_page_crossing"
    lines = _umode_prologue(test_data)
    # a_base: ssp at the SS page base, so ssp-XLEN/8 lands on the unmapped page below.
    # b_below_valid: ssp on the ordinary RW page, so ssp-XLEN/8 lands back on the SS page.
    # The boundary cases stay inside the SS page: a push from one slot above the base
    # writes the first slot, and a pop from the last slot reads it.
    for case, va in (
        ("a_base", "ZICFISS_VA_SS"),
        ("b_below_valid", "ZICFISS_VA_RW"),
        ("near_base", "ZICFISS_VA_SS + REGWIDTH"),
        ("near_top", "ZICFISS_VA_SS + 0x1000 - REGWIDTH"),
    ):
        lines.extend(ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, va, "0xC0DECAFE", case, coverpoint, _CG_U))
    lines.extend(_SATP_OFF)
    return vm_section(coverpoint, "Shadow stack accesses that straddle a page boundary", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_ad_bits
# ---------------------------------------------------------------------------


def _generate_page_ad_bits(test_data: TestData) -> list[str]:
    """D is required by the writing SS instructions but not by SSPOPCHK; A by all."""
    coverpoint = "cp_ss_page_ad_bits"
    mid = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for a_bit, d_bit in ((0, 0), (1, 0), (0, 1), (1, 1)):
        perms = " | ".join(["PTE_W", "PTE_V"] + (["PTE_A"] if a_bit else []) + (["PTE_D"] if d_bit else []))
        tag = f"a{a_bit}_d{d_bit}"
        lines.extend(
            [
                f"# --- pte.A={a_bit}, pte.D={d_bit} ---",
                *_umode_prologue(test_data, ss_perms=perms),
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0xADADADAD", tag, coverpoint, _CG_U),
                *ssamoswap_forms(test_data, mid, tag, coverpoint, _CG_U),
                *_SATP_OFF,
            ]
        )
    return vm_section(coverpoint, "PTE A/D bits on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_non_idempotent
# ---------------------------------------------------------------------------


def _generate_non_idempotent(test_data: TestData) -> list[str]:
    """Svpbmt NC memory is idempotent and IO memory is not, so SS instructions fault only on IO.

    menvcfg.PBMTE is set for this section, without which a nonzero PBMT is reserved. SSAMOSWAP
    is left out on NC pages, because an implementation may also override the AMO PMA there
    (norm:Svpbmt_impl_may_override_pmas), so its outcome is implementation-defined and no UDB
    parameter says which behavior a DUT has. Those coverage bins stay as a known gap.
    """
    coverpoint = "cp_ss_non_idempotent"
    mid = "ZICFISS_VA_SS + 0x800"
    pbmte_reg = test_data.int_regs.get_register()
    lines = [
        "#if defined(SVPBMT_SUPPORTED) && __riscv_xlen == 64",
        f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
        tsbi_call(f"csrs menvcfg, x{pbmte_reg}"),
    ]
    test_data.int_regs.return_registers([pbmte_reg])
    # pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO.
    for tag, pbmt in (("pma", 0), ("nc", 1), ("io", 2)):
        lines.extend(
            [
                f"# --- pte.PBMT = {tag} ---",
                *_umode_prologue(test_data, ss_perms=f"{PTE_SS} | ({pbmt} << 61)"),
                *ss_forms_against(
                    test_data, PUSH_FORMS + POP_FORMS, mid, "0x1D1D1D1D", f"pbmt_{tag}", coverpoint, _CG_U
                ),
                *(ssamoswap_forms(test_data, mid, f"pbmt_{tag}", coverpoint, _CG_U) if tag != "nc" else []),
                *_SATP_OFF,
            ]
        )
    pbmte_reg = test_data.int_regs.get_register()
    lines.extend(
        [
            f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
            tsbi_call(f"csrc menvcfg, x{pbmte_reg}"),
            "#endif  // SVPBMT_SUPPORTED && RV64",
        ]
    )
    test_data.int_regs.return_registers([pbmte_reg])
    return vm_section(coverpoint, "Svpbmt NC and IO memory types on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_access -- non-SS accessors against an SS page
# ---------------------------------------------------------------------------


def _generate_page_access(test_data: TestData) -> list[str]:
    """Ordinary, atomic and cache-block accesses to an SS page, and a fetch from it.

    Loads and LR succeed; stores, AMOs, SC and CBOs raise a store/AMO access fault. Each
    testcase records rd, or for the stores and CBOs, the location read back afterwards. A jump
    to the SS page raises an instruction access fault, recorded by the trap handler.
    """
    lines = _umode_prologue(test_data)
    addr_reg, data_reg, mxr_reg = test_data.int_regs.get_registers(3)

    def access(mnemonic: str, form: str, coverpoint: str, tag: str = "", read_back: bool = False) -> list[str]:
        return [
            test_data.add_testcase(f"{mnemonic.replace('.', '_')}_on_ss_page{tag}", coverpoint, _CG_U),
            form,
            *([f"LREG x{data_reg}, 0(x{addr_reg})   # unchanged"] if read_back else []),
            write_sigupd(data_reg, test_data),
        ]

    lines.append(f"LI(x{addr_reg}, ZICFISS_VA_SS)")
    for mnemonic in ("sb", "sh", "sw", "sd"):
        store = [
            f"LI(x{data_reg}, 0xDEADBEEF)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, 0(x{addr_reg})", "cp_ss_page_access_store", read_back=True),
        ]
        lines.extend(rv64_only(store) if mnemonic == "sd" else store)

    for mxr in (0, 1):
        lines.extend([f"LI(x{mxr_reg}, SSTATUS_MXR)", tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{mxr_reg}")])
        for mnemonic in ("lb", "lh", "lw", "lbu", "lhu", "ld", "lwu"):
            load = access(mnemonic, f"{mnemonic} x{data_reg}, 0(x{addr_reg})", "cp_ss_page_access_load", f"_mxr{mxr}")
            lines.extend(rv64_only(load) if mnemonic in ("ld", "lwu") else load)

    # Zicfiss requires Zaamo, so the ordinary AMOs are always present.
    for mnemonic in ("amoswap.w", "amoadd.w", "amoor.w", "amoswap.d", "amoadd.d"):
        amo = [
            f"LI(x{data_reg}, 0x1)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amo"),
        ]
        lines.extend(rv64_only(amo) if mnemonic.endswith(".d") else amo)

    # The CBOs are gated by the CBIE, CBCFE and CBZE fields of menvcfg and senvcfg; enable them so
    # that a CBO traps on the SS page rather than on its own gating. The boot code enables them
    # too, so they are left set afterwards.
    def cbo_enables(op: str) -> list[str]:
        return [
            f"LI(x{data_reg}, MENVCFG_CBIE | MENVCFG_CBCFE | MENVCFG_CBZE)",
            tsbi_call(f"{op} menvcfg, x{data_reg}"),
            f"LI(x{data_reg}, SENVCFG_CBIE | SENVCFG_CBCFE | SENVCFG_CBZE)",
            tsbi_call(f"{op} senvcfg, x{data_reg}"),
        ]

    lines.extend(
        [
            *cbo_enables("csrs"),
            "#ifdef ZICBOM_SUPPORTED",
            ".option push",
            ".option arch, +zicbom",
            *access("cbo.clean", f"cbo.clean (x{addr_reg})", "cp_ss_page_access_cbo", read_back=True),
            *access("cbo.flush", f"cbo.flush (x{addr_reg})", "cp_ss_page_access_cbo", read_back=True),
            *access("cbo.inval", f"cbo.inval (x{addr_reg})", "cp_ss_page_access_cbo", read_back=True),
            ".option pop",
            "#endif",
            "#ifdef ZICBOZ_SUPPORTED",
            ".option push",
            ".option arch, +zicboz",
            *access("cbo.zero", f"cbo.zero (x{addr_reg})", "cp_ss_page_access_cboz", read_back=True),
            ".option pop",
            "#endif",
        ]
    )

    lines.extend(
        [
            "#ifdef ZALRSC_SUPPORTED",
            ".option push",
            ".option arch, +a",
            *access("lr.w", f"lr.w x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
            *access("sc.w", f"sc.w x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
            *rv64_only(
                [
                    *access("lr.d", f"lr.d x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
                    *access("sc.d", f"sc.d x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
                ]
            ),
            ".option pop",
            "#endif",
            "#ifdef ZACAS_SUPPORTED",
            ".option push",
            ".option arch, +zacas",
            f"LI(x{data_reg}, 0x1)",
            *access("amocas.w", f"amocas.w x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amocas"),
            *rv64_only(
                [
                    f"LI(x{data_reg}, 0x1)",
                    *access(
                        "amocas.d", f"amocas.d x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amocas"
                    ),
                ]
            ),
            ".option pop",
            "#endif",
            # Instruction fetches are implicit accesses, which an SS page does not permit: the fetch
            # raises an instruction access fault, and the handler returns to ra.
            f"LI(x{addr_reg}, ZICFISS_VA_SS)",
            test_data.add_testcase("jalr_fetch_ss_page", "cp_ss_page_fetch", _CG_U),
            f"jalr ra, 0(x{addr_reg})",
            *_SATP_OFF,
        ]
    )
    test_data.int_regs.return_registers([addr_reg, data_reg, mxr_reg])
    return vm_section("cp_ss_page_access", "Non-SS accessors against an SS page, and a fetch from it", lines)


# ---------------------------------------------------------------------------
# cp_ss_vector_* -- vector accesses to an SS page (Zve32x)
# ---------------------------------------------------------------------------


# A fixed vl keeps every vector access within 16 bytes of its base whatever VLEN is, where VLMAX
# could run past the shadow stack page. The strided and indexed accesses from the page below need
# three elements to reach the SS page.
_VECTOR_VL = 4


def _generate_vector(test_data: TestData) -> list[str]:
    """A shadow stack page is readable by vector loads and not writable by vector stores.

    The page below the shadow stack page is also mapped, as a second view of the read/write
    page, so a strided or indexed access can begin there and run up into the SS page.
    """
    below = f"ZICFISS_PTE_SETUP(rvtest_zicfiss_rw_page, ({PTE_RW} | PTE_U), (ZICFISS_VA_SS - 0x1000), LEVEL0)"
    lines = [
        "#ifdef ZVE32X_SUPPORTED",
        *_umode_prologue(test_data, extra_mappings=(below, "sfence.vma")),
        ".option push",
        ".option arch, +zve32x",
    ]
    addr_reg, tmp_reg, stride_reg = test_data.int_regs.get_registers(3)

    # Unit-stride loads succeed, whether or not MXR is set; the SS page has R=0.
    for mxr in (0, 1):
        lines.extend([f"LI(x{tmp_reg}, SSTATUS_MXR)", tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{tmp_reg}")])
        for sew in (8, 16, 32):
            lines.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                    test_data.add_testcase(f"vle{sew}_ss_page_mxr{mxr}", "cp_ss_vector_load", _CG_U),
                    f"vle{sew}.v v1, (x{addr_reg})",
                    f"vmv.x.s x{tmp_reg}, v1   # the first element read from the SS page",
                    write_sigupd(tmp_reg, test_data),
                ]
            )

    # Unit-stride stores fault, leaving the SS page unchanged. The stored data is all ones, which
    # the SS page does not hold, so the readback shows any write.
    for sew in (8, 16, 32):
        lines.extend(
            [
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                "vmv.v.i v1, -1",
                test_data.add_testcase(f"vse{sew}_ss_page", "cp_ss_vector_store", _CG_U),
                f"vse{sew}.v v1, (x{addr_reg})",
                f"lw x{tmp_reg}, 0(x{addr_reg})   # unchanged",
                write_sigupd(tmp_reg, test_data),
            ]
        )

    def record_load() -> list[str]:
        """Record elements 0 and 2; element 2 is on the SS page whichever page the access began on."""
        return [
            f"vmv.x.s x{tmp_reg}, v1",
            write_sigupd(tmp_reg, test_data),
            "vslidedown.vi v3, v1, 2",
            f"vmv.x.s x{tmp_reg}, v3",
            write_sigupd(tmp_reg, test_data),
        ]

    def record_store() -> list[str]:
        """Record the word at the base and the SS page word element 2 targets, which must be unchanged.

        From the page below, elements 0 and 1 land on the read/write page before element 2 faults,
        so the first readback shows the all-ones data there.
        """
        return [
            f"lw x{tmp_reg}, 0(x{addr_reg})",
            write_sigupd(tmp_reg, test_data),
            f"lw x{tmp_reg}, 8(x{addr_reg})",
            write_sigupd(tmp_reg, test_data),
        ]

    # Strided and indexed accesses with rs1 on the SS page, and on the page below it with
    # the elements running up into it: 4-byte steps from 8 bytes below reach it by the third.
    for origin, base in (("on_ss", "ZICFISS_VA_SS + 0x800"), ("adjacent", "ZICFISS_VA_SS - 8")):
        for sew in (8, 32):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {base})",
                    f"LI(x{stride_reg}, 4)",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                    test_data.add_testcase(f"vlse{sew}_{origin}", "cp_ss_vector_strided", _CG_U),
                    f"vlse{sew}.v v1, (x{addr_reg}), x{stride_reg}",
                    *record_load(),
                ]
            )
        for mnemonic in ("vluxei8.v", "vsuxei8.v"):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {base})",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e8, m1, tu, mu",
                    "vid.v v2",
                    "vsll.vi v2, v2, 2   # byte offsets 0, 4, 8, ...",
                    *([] if mnemonic.startswith("vl") else ["vmv.v.i v1, -1   # data neither page holds"]),
                    test_data.add_testcase(f"{mnemonic.replace('.', '_')}_{origin}", "cp_ss_vector_indexed", _CG_U),
                    f"{mnemonic} v1, (x{addr_reg}), v2",
                    *(record_load() if mnemonic.startswith("vl") else record_store()),
                ]
            )

    lines.extend([".option pop", *_SATP_OFF, "#endif  // ZVE32X_SUPPORTED"])
    test_data.int_regs.return_registers([addr_reg, tmp_reg, stride_reg])
    return vm_section("cp_ss_vector_*", "Vector accesses to a shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_u / cp_ssamoswap_sse_gating
# ---------------------------------------------------------------------------


def _generate_sse_gating(test_data: TestData) -> list[str]:
    """Sweep the reachable (menvcfg.SSE, senvcfg.SSE) states from U-mode.

    menvcfg.SSE=0 makes senvcfg.SSE read-only zero, so (0, 1) is the same state as (0, 0).
    Each ssp access records rd, which an illegal-instruction exception leaves unchanged.
    """
    lines: list[str] = []
    for menvcfg, senvcfg in ((1, 1), (1, 0), (0, 0)):
        tag = f"m{menvcfg}s{senvcfg}"
        lines.extend(
            [
                f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                *_umode_prologue(test_data, menvcfg=menvcfg, senvcfg=senvcfg),
            ]
        )
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines.append(f"LI(x{addr_reg}, ZICFISS_VA_SS)")
        # ssp CSR access: allowed only when both bits are set, else illegal-instruction.
        for op, form in (
            ("csrrw", f"csrrw x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrs", f"csrrs x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrc", f"csrrc x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrwi", f"csrrwi x{rd_reg}, ssp, 1"),
            ("csrrsi", f"csrrsi x{rd_reg}, ssp, 1"),
            ("csrrci", f"csrrci x{rd_reg}, ssp, 1"),
        ):
            lines.extend(
                [
                    f"LI(x{rd_reg}, 0x0DDBA11)",
                    test_data.add_testcase(f"ssp_{op}_{tag}", "cp_ssp_csr_gating_u", _CG_U),
                    form,
                    write_sigupd(rd_reg, test_data),
                ]
            )
        test_data.int_regs.return_registers([addr_reg, rd_reg])

        if not (menvcfg and senvcfg):
            # SSAMOSWAP is AMO-encoded, so unlike the MOP-encoded instructions it traps
            # rather than becoming inert. The inert case is cp_ss_instr_inactive_u.
            lines.extend(ssamoswap_forms(test_data, "ZICFISS_VA_SS", f"gated_{tag}", "cp_ssamoswap_sse_gating", _CG_U))
        lines.extend(_SATP_OFF)
    return vm_section("cp_ssp_csr_gating_u", "SSE enable chain seen from U-mode", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_inactive_u / cp_ssrdp (inactive half)
# ---------------------------------------------------------------------------


def _generate_instr_inactive_u(test_data: TestData) -> list[str]:
    """MOP-encoded SS instructions stay inert in U-mode while Zicfiss is inactive for it.

    ssp is only writable while Zicfiss is active, so each ssp value is set first and the
    enable chain is cleared through T-SBI afterwards. The unmapped and mismatching ssp
    values would fault or raise a software check if the instruction were not inert.
    """
    coverpoint = "cp_ss_instr_inactive_u"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)

    for gate, cleared in (("men1_sen0", ("senvcfg",)), ("men0_sen0", ("senvcfg", "menvcfg"))):
        for state, addr in (
            ("valid", "ZICFISS_VA_SS + 0x800"),
            ("unaligned", "ZICFISS_VA_SS + 0x804"),
            ("unmapped", "ZICFISS_VA_UNMAPPED"),
            ("mismatch", "ZICFISS_VA_SS + 0x800"),
        ):
            lines.extend([f"LI(x{addr_reg}, {addr})", f"csrw ssp, x{addr_reg}"])
            for csr in cleared:
                lines.extend(set_envcfg_sse(csr, 0, test_data, mode="U"))
            for form in MOP_FORMS:
                name = f"{form.name}_{gate}_{state}"
                if form.link_reg is None:  # SSRDP writes 0 while inactive
                    lines.extend(
                        [
                            test_data.add_testcase(name, "cp_ssrdp", _CG_U),
                            f"ssrdp x{rd_reg}",
                            write_sigupd(rd_reg, test_data),
                        ]
                    )
                    continue
                value = "0xDEADBEEF" if state == "mismatch" else "0"
                case = [
                    f"LI({form.link_reg}, {value})",
                    test_data.add_testcase(name, coverpoint, _CG_U),
                    *ss_instr(form),
                ]
                lines.extend(zcmop_only(form.compressed, case))
            lines.extend(
                [
                    *set_envcfg_sse("menvcfg", 1, test_data, mode="U"),
                    *set_envcfg_sse("senvcfg", 1, test_data, mode="U"),
                    f"csrr x{rd_reg}, ssp   # unchanged",
                    write_sigupd(rd_reg, test_data),
                ]
            )

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section(coverpoint, "SS instructions inert in U-mode while Zicfiss is inactive", lines)


def _generate_unused_mop_u(test_data: TestData) -> list[str]:
    lines = _umode_prologue(test_data)
    lines.extend(unused_mop_cases(test_data, "", _CG_U))
    lines.extend(_SATP_OFF)
    return vm_section("cp_ss_unused_mop", "Unused MOP encodings stay Zimop/Zcmop while Zicfiss is active", lines)


def _generate_misaligned_store_u(test_data: TestData) -> list[str]:
    coverpoint = "cp_ss_page_access_store_misaligned"
    lines = _umode_prologue(test_data)
    lines.extend(misaligned_store_cases(test_data, coverpoint, _CG_U))
    lines.extend(_SATP_OFF)
    return vm_section(coverpoint, "Misaligned ordinary stores to an SS page raise an access fault", lines)


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Zicfiss",
    required_extensions=["S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
)
def make_zicfissu(test_data: TestData) -> list[TestChunk]:
    """Generate the Zicfiss U group.

    The sections go into three files, each under 100k instructions: the instructions and the
    SSE enable chain, the page types and non-SS accessors, and the page A/D bits.
    """
    test_chunks: list[TestChunk] = []
    for section, split_name in (
        (_generate_ssp_access, "U"),
        (_generate_push_pop, None),
        (_generate_fault_priority, None),
        (_generate_call_return, None),
        (_generate_ssrdp, None),
        (_generate_ssamoswap, None),
        (_generate_alignment, None),
        (_generate_sse_gating, None),
        (_generate_instr_inactive_u, None),
        (_generate_unused_mop_u, None),
        (_generate_misaligned_store_u, None),
        (_generate_target_page, "U_pages"),
        (_generate_target_page_mxr_u, None),
        (_generate_page_crossing, None),
        (_generate_non_idempotent, None),
        (_generate_page_access, None),
        (_generate_vector, None),
        (_generate_page_ad_bits, "U_page_ad_bits"),
    ):
        tc = test_data.begin_test_chunk(split_name)
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
