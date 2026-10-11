##################################
# priv/extensions/ZicfissCommon.py
#
# Shared helpers for the Zicfiss (shadow stack) test generators.
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

from testgen.asm.helpers import comment_banner, write_sigupd
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
    if form.compressed:
        return [".option push", ".option arch, +zcmop", form.mnemonic, ".option pop"]
    return [form.mnemonic]


def zcmop_only(compressed: bool, lines: list[str]) -> list[str]:
    """Return ``lines``, guarded on Zcmop when they use a compressed form."""
    return ["#ifdef ZCMOP_SUPPORTED", *lines, "#endif"] if compressed else lines


def rv64_only(lines: list[str]) -> list[str]:
    """Return ``lines``, guarded to RV64."""
    return ["#if __riscv_xlen == 64", *lines, "#endif"]


def ssamoswap_only(width: SsamoswapWidth, lines: list[str]) -> list[str]:
    """Return ``lines`` for SSAMOSWAP.``width``, guarded to RV64 for SSAMOSWAP.D."""
    return lines if width == "w" else rv64_only(lines)


def vm_section(title: str, description: str, lines: list[str]) -> list[str]:
    """A section banner, and ``lines`` guarded on the configuration supporting Sv39/Sv32."""
    return [comment_banner(title, description), "#ifdef ZICFISS_VM_SUPPORTED", *lines, "#endif"]


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
        "#define ZICFISS_SATP_MODE   ((SATP64_MODE) & (SATP_MODE_SV39 << 60))",
        "#define ZICFISS_ROOT_SHIFT  30      // VA shift of the root-level VPN",
        "#define ZICFISS_LEAF_SPAN   21      // log2 of the bytes one leaf table maps",
        "#define ZICFISS_VPN_MASK    0x1FF",
        "#define ZICFISS_PTE_LOG2    3       // log2 of the PTE size",
        "#elif defined(SV32_SUPPORTED)",
        "#define ZICFISS_VM_SUPPORTED",
        "#define ZICFISS_VA_SS       0xC0300000",
        "#define ZICFISS_VA_RW       0xC0301000",
        "#define ZICFISS_VA_RO       0xC0302000",
        "#define ZICFISS_VA_UNMAPPED 0xC0400000    // not mapped: the walk fails at level 1",
        "#define ZICFISS_PTE_SETUP(PA, PERMS, VA, LEVEL) PTE_SETUP_SV32(PA, PERMS, VA, LEVEL)",
        "#define ZICFISS_SATP_MODE   SATP32_MODE",
        "#define ZICFISS_ROOT_SHIFT  22",
        "#define ZICFISS_LEAF_SPAN   22",
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
