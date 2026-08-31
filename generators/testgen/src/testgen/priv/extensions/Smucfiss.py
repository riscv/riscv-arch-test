##################################
# priv/extensions/Smucfiss.py
#
# Smucfiss U-mode shadow-stack test generator.
# Copyright (C) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smucfiss U-mode shadow-stack test generator.

Smucfiss provides a U-mode shadow stack on systems that implement M-mode and U-mode
but no S-mode, where page tables are not available to mark shadow-stack pages. A
PMP entry with the Smpmpind enable bit and XWR=110 denotes the region, and
menvcfg.SSE enables it for U-mode. Note the encoding differs from Smcfiss,
which marks its M-mode region with XWR=010.
"""

from __future__ import annotations

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

covergroup = "Smucfiss_cg"
coverpoint = "cp_u_ss_region"

# miselect value selecting a PMP entry in the Smcsrind indirect window.
_MISELECT_PMPIND_BASE = 0x300

_MIREG2_E = 1 << 63

_PAGE = 4096
_PROBE_OFFSET = 0x100
_POISON_M_LOAD = 0xBAD0BAD0BAD0BAD0

# Configuration bytes for the three entries programmed from M-mode. Entry 1 is
# the shadow-stack region. Entries 0 and 2 bracket it so U-mode can still reach
# its own code, stack and the signature area.
_CFG_BELOW = "(PMP_TOR | PMP_X | PMP_W | PMP_R)"
_CFG_SS = "(PMP_TOR | PMP_X | PMP_W)"
_CFG_ABOVE = "(PMP_NAPOT | PMP_X | PMP_W | PMP_R)"


def _select_entry(reg: int, entry: int) -> list[str]:
    """Point miselect at one PMP entry."""
    return [
        f"{INDENT}li x{reg}, {_MISELECT_PMPIND_BASE | entry:#x}    # miselect = PMP indirect base | entry {entry}",
        f"{INDENT}csrw CSR_MISELECT, x{reg}",
    ]


def _generate_u_ss_basic(test_data: TestData) -> TestChunk:
    """Configure a U-mode shadow-stack region, then exercise it from U-mode."""
    tc = test_data.begin_test_chunk("u_ss_basic")

    addr_reg, cfg_reg, tmp_reg, check_reg, val_reg = test_data.int_regs.get_registers(5)
    # Zicfiss constrains sspush/sspopchk to x1 or x5.
    push_reg = 1

    tc.code.extend(
        [
            "",
            "# Shadow-stack region. Injected into .data via .pushsection, page-aligned",
            "# so the TOR bounds are exact.",
            ".pushsection .data",
            ".p2align 12",
            "uss_start:",
            f"{INDENT}.fill {_PAGE}, 1, 0",
            "uss_end:",
            ".popsection",
            "",
        ]
    )

    tc.code.append(
        comment_banner(
            coverpoint,
            "Program three PMP entries from M-mode: an ordinary region below the\n"
            "shadow stack, the shadow-stack region itself, and a catch-all above\n"
            "it. The brackets are what let U-mode reach its own code and data, so\n"
            "that only the shadow-stack rules can deny an access.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, uss_start)",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2",
            f"{INDENT}csrw pmpaddr0, x{addr_reg}    # TOR bound: below the region",
            f"{INDENT}LA(x{addr_reg}, uss_end)",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2",
            f"{INDENT}csrw pmpaddr1, x{addr_reg}    # TOR bound: top of the region",
            f"{INDENT}li x{addr_reg}, -1",
            f"{INDENT}csrw pmpaddr2, x{addr_reg}    # NAPOT catch-all: everything above",
            "",
            f"{INDENT}li x{cfg_reg}, ({_CFG_ABOVE} << 16) | ({_CFG_SS} << 8) | {_CFG_BELOW}",
            f"{INDENT}csrw pmpcfg0, x{cfg_reg}    # entries 0, 1 and 2 in one packed write",
            "",
        ]
    )

    # The direct write does not encode the enable bit, so entry 1 is rewritten
    # through the indirect window to set it.
    tc.code.extend(
        [
            f"{INDENT}li x{cfg_reg}, {_CFG_SS}",
            f"{INDENT}li x{tmp_reg}, {_MIREG2_E:#x}    # enable bit at MXLEN-1",
            f"{INDENT}or x{cfg_reg}, x{cfg_reg}, x{tmp_reg}",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg, 1))
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, uss_end)",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2",
            f"{INDENT}csrw CSR_MIREG, x{addr_reg}",
            f"{INDENT}csrw CSR_MIREG2, x{cfg_reg}",
            "",
            f"{INDENT}csrr x{check_reg}, pmpcfg0",
            f"{INDENT}srli x{check_reg}, x{check_reg}, 8    # entry 1 occupies bits[15:8]",
            f"{INDENT}andi x{check_reg}, x{check_reg}, 0xFF",
        ]
    )
    tc.code.append(test_data.add_testcase("direct_cfg_byte", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.extend(_select_entry(tmp_reg, 1))
    tc.code.append(test_data.add_testcase("indirect_cfg_and_enable", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MIREG2", None), test_data))

    tc.code.append(comment_banner(coverpoint, "menvcfg.SSE enables the shadow stack for U-mode."))
    tc.code.extend(
        [
            f"{INDENT}csrr x{check_reg}, CSR_MENVCFG",
            f"{INDENT}ori x{check_reg}, x{check_reg}, MENVCFG_SSE",
            f"{INDENT}csrw CSR_MENVCFG, x{check_reg}",
        ]
    )
    tc.code.append(test_data.add_testcase("sse_enabled", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MENVCFG", None), test_data))

    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, uss_end)",
            f"{INDENT}csrw CSR_SSP, x{addr_reg}    # ssp = top of the region",
            "",
        ]
    )

    tc.code.append(
        comment_banner(
            coverpoint,
            "In U-mode a shadow-stack push and pop round-trip inside the region,\n"
            "an explicit load from it is permitted, and an ordinary store to it\n"
            "raises a store/AMO access fault.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}RVTEST_GOTO_LOWER_MODE Umode",
            "",
            f"{INDENT}LI(x{push_reg}, 0x0CAFEF00DDEADBEEF)    # x{push_reg}: sspush/sspopchk take x1 or x5",
            f"{INDENT}sspush x{push_reg}",
            f"{INDENT}nop",
            f"{INDENT}sspopchk x{push_reg}",
            f"{INDENT}nop",
            "",
            f"{INDENT}LA(x{addr_reg}, uss_start)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, {_PROBE_OFFSET:#x}",
            f"{INDENT}ld x{check_reg}, 0(x{addr_reg})    # permitted",
            f"{INDENT}nop",
            "",
            f"{INDENT}LI(x{val_reg}, 0xA55AA55AA55AA55A)    # value the faulting store attempts",
            f"{INDENT}sw x{val_reg}, 0(x{addr_reg})    # store/AMO access fault",
            f"{INDENT}nop",
            "",
            f"{INDENT}RVTEST_GOTO_MMODE",
            "",
        ]
    )

    tc.code.append(test_data.add_testcase("push_pop_round_trip", coverpoint, covergroup))
    tc.code.append(write_sigupd(push_reg, test_data))
    tc.code.append(test_data.add_testcase("load_permitted", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))
    tc.code.append(test_data.add_testcase("ordinary_store_faults", coverpoint, covergroup))
    tc.code.append(write_sigupd(val_reg, test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "M-mode cannot use its normal unlocked-PMP bypass to reach an active\n"
            "U-mode shadow-stack region. An explicit load raises a load access fault,\n"
            "leaving the destination register unchanged.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, uss_start)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, {_PROBE_OFFSET:#x}",
            f"{INDENT}LI(x{check_reg}, {_POISON_M_LOAD:#x})",
            f"{INDENT}ld x{check_reg}, 0(x{addr_reg})    # load access fault",
            f"{INDENT}nop",
        ]
    )
    tc.code.append(test_data.add_testcase("m_mode_load_faults", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    test_data.int_regs.return_registers([addr_reg, cfg_reg, tmp_reg, check_reg, val_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "Smucfiss",
    required_extensions=["Sm", "U", "Smucfiss"],
    march_extensions=["Zicfiss"],
    params=[
        "MXLEN: 64",
        # Entries 0 and 1 are TOR, entry 2 is NAPOT. Usable, not implemented: an
        # entry whose registers read as zero cannot guard a region.
        "NUM_USABLE_PMP_ENTRIES: '>=3'",
        "PMP_TOR_SUPPORTED: true",
        "PMP_NAPOT_SUPPORTED: true",
        # Fixed 4 KiB TOR range, so the granule must be no coarser (log2 of the
        # smallest supported region).
        "PMP_GRANULARITY: '<=12'",
    ],
    extra_defines=[
        "#define BOOT_TO_MMODE",
        "#define TRAP_SIGUPD_COUNT 12",
    ],
)
def make_smucfiss(test_data: TestData) -> list[TestChunk]:
    return [_generate_u_ss_basic(test_data)]
