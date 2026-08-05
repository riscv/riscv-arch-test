##################################
# priv/extensions/Sspmpss.py
#
# Sspmpss S-mode shadow-stack test generator.
# Copyright (C) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sspmpss S-mode shadow-stack test generator.

Sspmpss marks an SPMP entry as a shadow-stack region for S-mode and U-mode on
systems that use SPMP rather than page tables. An SPMP entry with XWR=010 and
SHARED=0 denotes the region. The encoding is otherwise reserved. The feature
requires menvcfg.SSE and applies only while satp.MODE is Bare.
"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

covergroup = "Sspmpss_cg"

# Not yet defined by encoding.h.
_CSR_MPMPDELEG = 0x316
_CSR_SPMPEN = 0x183

# Hardware entries below this stay PMP. Entries from here up become SPMP.
_SPMP_PMPNUM = 8

# SPMP logical entries the suite programs: the shadow-stack region, an ordinary
# region, and the catch-all.
_SPMP_ENTRIES_USED = 3

# *select value for SPMP logical entry 0.
_SPMP_SEL_ENTRY0 = 0x100

# spmpcfg encodings. Bit layout is R:0 W:1 X:2 A:4:3 SHARED:9.
_CFG_SHARED = 1 << 9
_CFG_SS_REGION = 0x1A  # A=NAPOT, XWR=010, SHARED=0: the shadow-stack region
_CFG_RW_REGION = 0x1B  # A=NAPOT, XWR=011: ordinary read/write
_CFG_RWX_CATCHALL = 0x1F  # A=NAPOT, XWR=111: S-mode catch-all
_CFG_RESERVED = _CFG_SHARED | _CFG_SS_REGION  # SHARED=1 with U=0 stays reserved

# Mask covering the configuration field as read back through the indirect window.
_CFG_MASK = 0x3FF

_PAGE = 4096
# NAPOT low-address bits encoding a 4 KiB region.
_NAPOT_4K = (_PAGE >> 3) - 1

# Deterministic sentinels, each distinctive in a signature dump.
_SENT_PUSH = 0xF1F1F1F1F1F1F1F1
_SENT_LR = 0xF5F5F5F5F5F5F5F5
_SENT_NONSS = 0xF2F2F2F2F2F2F2F2
_SENT_SW = 0x5757575757575757
_SENT_LD = 0x1D1D1D1D1D1D1D1D
_POISON_PUSH = 0xDEAD0001DEAD0001
_POISON_LR = 0xDEAD0002DEAD0002
_POISON_NONSS = 0xDEAD0003DEAD0003
_POISON_SW = 0xDEAD0004DEAD0004


def _select_spmp_entry(reg: int, logical: int, csr: str = "CSR_MISELECT") -> list[str]:
    """Point an indirect-window select register at one SPMP logical entry."""
    return [
        f"{INDENT}li x{reg}, {_SPMP_SEL_ENTRY0 + logical:#x}    # select SPMP logical entry {logical}",
        f"{INDENT}csrw {csr}, x{reg}",
    ]


def _enable_and_delegate(reg: int) -> list[str]:
    """Enable the shadow stack and split the hardware array between PMP and SPMP."""
    return [
        f"{INDENT}li x{reg}, MENVCFG_SSE",
        f"{INDENT}csrs CSR_MENVCFG, x{reg}    # Sspmpss has no effect while SSE is clear",
        f"{INDENT}li x{reg}, {_SPMP_PMPNUM}",
        f"{INDENT}csrw {_CSR_MPMPDELEG:#x}, x{reg}    # mpmpdeleg.pmpnum: entries {_SPMP_PMPNUM}+ are SPMP",
        "",
    ]


def _generate_spmp_ss_region(test_data: TestData) -> TestChunk:
    """Configuration path: the shadow-stack encoding is accepted and readable."""
    tc = test_data.begin_test_chunk("spmp_ss_region")
    coverpoint = "cp_spmp_ss_region_config"

    tmp_reg, check_reg = test_data.int_regs.get_registers(2)

    tc.code.append(
        comment_banner(
            coverpoint,
            "Write the shadow-stack configuration through the indirect window and read it\n"
            "back. Without Sspmpss the encoding is reserved and the write is dropped, so a\n"
            "faithful readback is what distinguishes a supporting implementation.",
        )
    )
    tc.code.extend(_enable_and_delegate(tmp_reg))
    tc.code.extend(_select_spmp_entry(tmp_reg, 0))
    tc.code.extend(
        [
            f"{INDENT}li x{tmp_reg}, {_CFG_SS_REGION:#x}    # A=NAPOT, XWR=010, SHARED=0",
            f"{INDENT}csrw CSR_MIREG2, x{tmp_reg}",
            f"{INDENT}csrr x{check_reg}, CSR_MIREG2",
            f"{INDENT}andi x{check_reg}, x{check_reg}, {_CFG_MASK:#x}",
        ]
    )
    tc.code.append(test_data.add_testcase("ss_cfg_accepted", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "The S-mode alias of the indirect window addresses the same SPMP entry.",
        )
    )
    tc.code.extend(_select_spmp_entry(tmp_reg, 0, csr="CSR_SISELECT"))
    tc.code.extend(
        [
            f"{INDENT}csrr x{check_reg}, CSR_SIREG2",
            f"{INDENT}andi x{check_reg}, x{check_reg}, {_CFG_MASK:#x}",
        ]
    )
    tc.code.append(test_data.add_testcase("ss_cfg_via_s_alias", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.append(comment_banner(coverpoint, "The entry's address register round-trips through the window."))
    tc.code.extend(_select_spmp_entry(tmp_reg, 0))
    tc.code.extend(
        [
            f"{INDENT}li x{tmp_reg}, 0x2000FFFF    # NAPOT pattern chosen to survive grain masking",
            f"{INDENT}csrw CSR_MIREG, x{tmp_reg}",
            f"{INDENT}csrr x{check_reg}, CSR_MIREG",
        ]
    )
    tc.code.append(test_data.add_testcase("ss_addr_round_trip", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "The carve-out is specific to XWR=010 with SHARED=0. An encoding that\n"
            "is reserved for another reason must still be dropped, and dropping it\n"
            "must not disturb the entry configured above.",
        )
    )
    tc.code.extend(_select_spmp_entry(tmp_reg, 1))
    tc.code.extend(
        [
            f"{INDENT}li x{tmp_reg}, {_CFG_RESERVED:#x}    # SHARED=1 with U=0",
            f"{INDENT}csrw CSR_MIREG2, x{tmp_reg}",
            f"{INDENT}csrr x{check_reg}, CSR_MIREG2",
            f"{INDENT}andi x{check_reg}, x{check_reg}, {_CFG_MASK:#x}",
        ]
    )
    tc.code.append(test_data.add_testcase("reserved_cfg_dropped", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.extend(_select_spmp_entry(tmp_reg, 0))
    tc.code.extend(
        [
            f"{INDENT}csrr x{check_reg}, CSR_MIREG2",
            f"{INDENT}andi x{check_reg}, x{check_reg}, {_CFG_MASK:#x}",
        ]
    )
    tc.code.append(test_data.add_testcase("ss_cfg_still_set", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    test_data.int_regs.return_registers([tmp_reg, check_reg])
    return test_data.end_test_chunk()


def _generate_spmp_ss_access(test_data: TestData) -> TestChunk:
    """Access policy at effective privilege S. Five sub-cases, two expected to fault."""
    tc = test_data.begin_test_chunk("spmp_ss_access")
    coverpoint = "cp_spmp_ss_access"

    # Allocated registers survive RVTEST_GOTO_MMODE; a0 is excluded.
    addr_reg, val_reg, tmp_reg, check_reg, lr_reg = test_data.int_regs.get_registers(5)
    push_reg = 1  # Zicfiss constrains sspush/sspopchk to x1 or x5.

    tc.code.extend(
        [
            "",
            "# Two page-aligned regions. Injected into .data via .pushsection. The",
            "# slots sit at the start of each page so their offsets are fixed.",
            ".pushsection .data",
            ".p2align 12",
            "ss_page_start:",
            f"ss_lr_slot:{INDENT}.dword 0    # +0x00 source for the load-reserved case",
            f"ss_ld_slot:{INDENT}.dword 0    # +0x08 source for the ordinary load case",
            f"ss_sw_slot:{INDENT}.dword 0    # +0x10 target of the faulting ordinary store",
            f"ss_push_slot:{INDENT}.dword 0    # +0x18 target of the shadow-stack push",
            f"{INDENT}.fill {_PAGE - 32}, 1, 0",
            "ss_page_end:",
            ".p2align 12",
            "nonss_page_start:",
            f"nonss_slot:{INDENT}.dword 0    # +0x00 target of the faulting shadow-stack push",
            f"{INDENT}.fill {_PAGE - 8}, 1, 0",
            "nonss_page_end:",
            ".popsection",
            "",
        ]
    )

    tc.code.append(
        comment_banner(
            coverpoint,
            "Set up from M-mode, where accesses bypass SPMP. satp.MODE must be\n"
            "Bare: Sspmpss does not apply under a page-based translation mode.",
        )
    )
    tc.code.append(f"{INDENT}csrw satp, zero")
    tc.code.extend(_enable_and_delegate(tmp_reg))

    for label, value, note in (
        ("ss_push_slot", _POISON_PUSH, "read back if the push faulted"),
        ("ss_lr_slot", _SENT_LR, "source for the load-reserved case"),
        ("ss_ld_slot", _SENT_LD, "source for the ordinary load case"),
        ("ss_sw_slot", _SENT_SW, "must survive the faulting store"),
        ("nonss_slot", _SENT_NONSS, "must survive the faulting push"),
    ):
        tc.code.extend(
            [
                f"{INDENT}LA(x{addr_reg}, {label})",
                f"{INDENT}LI(x{val_reg}, {value:#x})    # {note}",
                f"{INDENT}sd x{val_reg}, 0(x{addr_reg})",
            ]
        )
    tc.code.append("")

    for logical, region, cfg, note in (
        (0, "ss_page_start", _CFG_SS_REGION, "shadow-stack region"),
        (1, "nonss_page_start", _CFG_RW_REGION, "ordinary read/write region"),
    ):
        tc.code.extend(_select_spmp_entry(tmp_reg, logical))
        tc.code.extend(
            [
                f"{INDENT}LA(x{addr_reg}, {region})",
                f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2",
                f"{INDENT}ori x{addr_reg}, x{addr_reg}, {_NAPOT_4K:#x}",
                f"{INDENT}csrw CSR_MIREG, x{addr_reg}",
                f"{INDENT}li x{tmp_reg}, {cfg:#x}    # {note}",
                f"{INDENT}csrw CSR_MIREG2, x{tmp_reg}",
                "",
            ]
        )

    tc.code.append(
        comment_banner(
            coverpoint,
            "A catch-all entry of lowest priority grants S-mode access to code,\n"
            "data, handlers and the signature area. It is required because once\n"
            "any SPMP entry is active an unmatched S or U access is denied.",
        )
    )
    tc.code.extend(_select_spmp_entry(tmp_reg, 2))
    tc.code.extend(
        [
            f"{INDENT}li x{addr_reg}, -1    # NAPOT all-ones: the whole address space",
            f"{INDENT}csrw CSR_MIREG, x{addr_reg}",
            f"{INDENT}li x{tmp_reg}, {_CFG_RWX_CATCHALL:#x}",
            f"{INDENT}csrw CSR_MIREG2, x{tmp_reg}",
            "",
        ]
    )

    # spmpen is indexed by hardware entry, not by SPMP logical entry.
    activate = ((1 << _SPMP_ENTRIES_USED) - 1) << _SPMP_PMPNUM
    tc.code.append(
        comment_banner(
            coverpoint,
            "Set spmpen for all three entries and fence before entering S-mode.\n"
            "Without spmpen the accesses below are unrestricted.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}li x{tmp_reg}, {activate:#x}    # switch bits for the three entries",
            f"{INDENT}csrw {_CSR_SPMPEN:#x}, x{tmp_reg}",
            f"{INDENT}sfence.vma x0, x0",
            "",
            f"{INDENT}LA(x{addr_reg}, ss_push_slot)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, 8    # a push stores at ssp-8",
            f"{INDENT}csrw CSR_SSP, x{addr_reg}",
            f"{INDENT}LI(x{lr_reg}, {_POISON_LR:#x})    # survives if the load-reserved faults",
            "",
        ]
    )

    tc.code.append(
        comment_banner(
            coverpoint,
            "At effective privilege S. A load-reserved is a distinct access type\n"
            "from an ordinary load, so both are checked.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}RVTEST_GOTO_LOWER_MODE Smode",
            "",
            f"{INDENT}LI(x{push_reg}, {_SENT_PUSH:#x})",
            f"{INDENT}sspush x{push_reg}    # permitted",
            f"{INDENT}nop",
            "",
            f"{INDENT}LA(x{addr_reg}, ss_lr_slot)",
            f"{INDENT}lr.d x{lr_reg}, (x{addr_reg})    # permitted",
            f"{INDENT}nop",
            "",
            f"{INDENT}LA(x{addr_reg}, nonss_slot)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, 8",
            f"{INDENT}csrw CSR_SSP, x{addr_reg}    # repoint ssp into the ordinary region",
            f"{INDENT}LI(x{push_reg}, {_POISON_NONSS:#x})",
            f"{INDENT}sspush x{push_reg}    # store/AMO access fault",
            f"{INDENT}nop",
            "",
            f"{INDENT}LA(x{addr_reg}, ss_sw_slot)",
            f"{INDENT}LI(x{val_reg}, {_POISON_SW:#x})",
            f"{INDENT}sw x{val_reg}, 0(x{addr_reg})    # store/AMO access fault",
            f"{INDENT}nop",
            "",
            f"{INDENT}LA(x{addr_reg}, ss_ld_slot)",
            f"{INDENT}ld x{val_reg}, 0(x{addr_reg})    # permitted",
            f"{INDENT}nop",
            "",
            f"{INDENT}RVTEST_GOTO_MMODE",
            "",
        ]
    )

    tc.code.append(
        comment_banner(
            coverpoint,
            "Every observable is read back from M-mode, which bypasses SPMP, so\n"
            "recording cannot itself perturb the outcome.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, ss_push_slot)",
            f"{INDENT}ld x{check_reg}, 0(x{addr_reg})",
        ]
    )
    tc.code.append(test_data.add_testcase("push_to_ss_region", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    # The load-reserved result was carried back in a register, so it needs no read.
    tc.code.append(test_data.add_testcase("load_reserved_from_ss_region", coverpoint, covergroup))
    tc.code.append(write_sigupd(lr_reg, test_data))

    for label, bin_name in (
        ("nonss_slot", "push_to_non_ss_region_faults"),
        ("ss_sw_slot", "ordinary_store_to_ss_region_faults"),
    ):
        tc.code.extend(
            [
                f"{INDENT}LA(x{addr_reg}, {label})",
                f"{INDENT}ld x{check_reg}, 0(x{addr_reg})",
            ]
        )
        tc.code.append(test_data.add_testcase(bin_name, coverpoint, covergroup))
        tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.append(test_data.add_testcase("ordinary_load_from_ss_region", coverpoint, covergroup))
    tc.code.append(write_sigupd(val_reg, test_data))

    test_data.int_regs.return_registers([addr_reg, val_reg, tmp_reg, check_reg, lr_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "Sspmpss",
    # Zalrsc, not A: lr.d is the only atomic used.
    # Smpmpind stands in for the SPMP base, which UDB cannot represent.
    required_extensions=["Sm", "S", "Zalrsc", "Smcsrind", "Smpmpind", "Sspmpss"],
    march_extensions=["Zalrsc", "Zicfiss"],
    params=[
        "MXLEN: 64",
        # Proxy: SPMP entries are carved from the shared PMP array, so entries
        # 8 to 10 must be usable. No NAPOT or granularity claim, since those PMP
        # parameters describe a different structure.
        f"NUM_USABLE_PMP_ENTRIES: '>={_SPMP_PMPNUM + _SPMP_ENTRIES_USED}'",
    ],
    extra_defines=[
        "#define BOOT_TO_MMODE",
        # Two traps in spmp_ss_access.
        "#define TRAP_SIGUPD_COUNT 20",
    ],
)
def make_sspmpss(test_data: TestData) -> list[TestChunk]:
    return [
        _generate_spmp_ss_region(test_data),
        _generate_spmp_ss_access(test_data),
    ]
