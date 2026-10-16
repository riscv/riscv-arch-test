##################################
# priv/extensions/Smcfiss.py
#
# Smcfiss M-mode shadow-stack test generator.
# Copyright (C) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smcfiss M-mode shadow-stack test generator.

Smcfiss marks a PMP entry as an M-mode shadow-stack region: the entry carries
the Smpmpind enable bit E=1 together with the otherwise-reserved XWR=010
encoding, and mseccfg.MSSE enables the feature. Within such a region M-mode
shadow-stack instructions and explicit loads are permitted, ordinary stores
fault, and shadow-stack stores to any other matched region fault.

The three groups are split into separate files because their reset-state
assumptions conflict: m_ss_negative needs mseccfg.MSSE clear, m_ss_basic
sets it, and m_ss_interlock needs no locked entry and then creates one
irreversibly.
"""

from __future__ import annotations

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

covergroup = "Smcfiss_cg"

# miselect value selecting a PMP entry in the Smcsrind indirect window.
_MISELECT_PMPIND_BASE = 0x300

_MIREG2_E = 1 << 63

# mseccfg.MSSE. Not yet defined by encoding.h.
_MSECCFG_MSSE = 1 << 11

# Shadow-stack region encoding: TOR with XWR=010.
_CFG_SS_TOR = "(PMP_TOR | PMP_W)"

# Ordinary read/write NAPOT region, used as the deliberately non-shadow-stack
# target of the exclusivity case.
_CFG_ORDINARY_NAPOT = "(PMP_NAPOT | PMP_R | PMP_W)"

_PAGE = 4096

# Byte offset probed inside the shadow-stack region. Any in-region offset works.
_PROBE_OFFSET = 0x100

# Offset of ssp into the ordinary region for the exclusivity case. The push
# targets ssp-8, which must still fall inside the region.
_NONSS_SSP_OFFSET = 0x400


def _select_entry(reg: int, entry: int) -> list[str]:
    """Point miselect at one PMP entry."""
    return [
        f"{INDENT}li x{reg}, {_MISELECT_PMPIND_BASE | entry:#x}    # miselect = PMP indirect base | entry {entry}",
        f"{INDENT}csrw CSR_MISELECT, x{reg}",
    ]


def _region_data_section(labels: list[tuple[str, str]]) -> list[str]:
    """Emit page-aligned regions, each as a start label, a page, and an end label."""
    lines = [
        "",
        "# Regions under test. Injected into .data via .pushsection. Page-aligned so",
        "# the TOR bounds and NAPOT encodings are exact.",
        ".pushsection .data",
    ]
    for label, description in labels:
        lines.extend(
            [
                ".p2align 12",
                f"{label}_start:    # {description}",
                f"{INDENT}.fill {_PAGE}, 1, 0",
                f"{label}_end:",
            ]
        )
    lines.extend([".popsection", ""])
    return lines


def _reset_entry_zero(addr_reg: int, tmp_reg: int, region: str) -> list[str]:
    """Retire the boot-time all-RWX entry 0 and reuse it as a TOR lower bound.

    Written through the indirect window so that only entry 0 is touched: a
    direct pmpcfg0 write would rewrite every packed entry in the same register.
    """
    lines = [
        f"{INDENT}LA(x{addr_reg}, {region}_start)",
        f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2    # TOR lower bound",
    ]
    lines.extend(_select_entry(tmp_reg, 0))
    lines.extend(
        [
            f"{INDENT}csrw CSR_MIREG, x{addr_reg}",
            f"{INDENT}csrw CSR_MIREG2, x0    # cfg = OFF, E = 0",
            "",
        ]
    )
    return lines


def _generate_m_ss_basic(test_data: TestData) -> TestChunk:
    """Positive path: configure a shadow-stack region, enable it, and exercise it."""
    tc = test_data.begin_test_chunk("m_ss_basic")
    coverpoint = "cp_m_ss_region"

    addr_reg, cfg_reg, tmp_reg, check_reg = test_data.int_regs.get_registers(4)
    push_reg = 1  # Zicfiss constrains sspush/sspopchk to x1 or x5.

    tc.code.extend(_region_data_section([("ss", "shadow-stack region"), ("nonss", "ordinary region")]))

    tc.code.append(
        comment_banner(
            coverpoint,
            "Configure the entry as a shadow-stack region: TOR, XWR=010, enable bit set.",
        )
    )
    tc.code.extend(_reset_entry_zero(addr_reg, tmp_reg, "ss"))
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, ss_end)",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2    # TOR upper bound",
            f"{INDENT}li x{cfg_reg}, {_CFG_SS_TOR}",
            f"{INDENT}li x{tmp_reg}, {_MIREG2_E:#x}    # enable bit at MXLEN-1",
            f"{INDENT}or x{cfg_reg}, x{cfg_reg}, x{tmp_reg}",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg, 1))
    tc.code.extend(
        [
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

    tc.code.append(comment_banner(coverpoint, "mseccfg.MSSE enables the M-mode shadow stack."))
    tc.code.extend(
        [
            f"{INDENT}csrr x{check_reg}, CSR_MSECCFG",
            f"{INDENT}li x{tmp_reg}, {_MSECCFG_MSSE:#x}    # mseccfg.MSSE",
            f"{INDENT}or x{check_reg}, x{check_reg}, x{tmp_reg}",
            f"{INDENT}csrw CSR_MSECCFG, x{check_reg}",
        ]
    )
    tc.code.append(test_data.add_testcase("msse_set", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MSECCFG", None), test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "A shadow-stack push followed by a matching pop leaves ssp unchanged.\n"
            "Neither is permitted to fault inside an enabled shadow-stack region.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, ss_end)",
            f"{INDENT}csrw CSR_SSP, x{addr_reg}    # ssp = top of the region",
        ]
    )
    tc.code.append(test_data.add_testcase("ssp_initialised", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_SSP", None), test_data))

    tc.code.extend(
        [
            f"{INDENT}LI(x{push_reg}, 0x0DEADBEEFCAFEBABE)    # x{push_reg}: sspush/sspopchk take x1 or x5",
            f"{INDENT}sspush x{push_reg}",
            f"{INDENT}sspopchk x{push_reg}",
        ]
    )
    tc.code.append(test_data.add_testcase("ssp_after_push_pop", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_SSP", None), test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "Inside a shadow-stack region an ordinary store raises a store/AMO\n"
            "access fault while an explicit load is permitted.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, ss_start)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, {_PROBE_OFFSET:#x}",
            f"{INDENT}LI(x{cfg_reg}, 0x55AA55AA55AA55AA)    # value the faulting store attempts",
            f"{INDENT}sw x{cfg_reg}, 0(x{addr_reg})    # store/AMO access fault",
            f"{INDENT}nop",
            "",
            f"{INDENT}ld x{check_reg}, 0(x{addr_reg})    # permitted, reads the zero-filled region",
            f"{INDENT}nop",
            "",
        ]
    )
    tc.code.append(test_data.add_testcase("ordinary_store_faults", coverpoint, covergroup))
    tc.code.append(write_sigupd(cfg_reg, test_data))
    tc.code.append(test_data.add_testcase("ordinary_load_permitted", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "A shadow-stack store to a matched non-shadow-stack region raises a store/AMO\n"
            "access fault. The region carries ordinary read/write permission so only the\n"
            "shadow-stack restriction can deny the push, and it must match: unmatched\n"
            "M-mode accesses are allowed by default.",
        )
    )
    napot_low_bits = (_PAGE >> 3) - 1
    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, nonss_start)",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2",
            f"{INDENT}li x{tmp_reg}, {napot_low_bits:#x}    # NAPOT low bits encoding a {_PAGE}-byte region",
            f"{INDENT}or x{addr_reg}, x{addr_reg}, x{tmp_reg}",
            f"{INDENT}li x{cfg_reg}, {_CFG_ORDINARY_NAPOT}    # ordinary region: enable bit clear",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg, 2))
    tc.code.extend(
        [
            f"{INDENT}csrw CSR_MIREG, x{addr_reg}",
            f"{INDENT}csrw CSR_MIREG2, x{cfg_reg}",
            "",
            f"{INDENT}LA(x{addr_reg}, nonss_start)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, {_NONSS_SSP_OFFSET:#x}",
            f"{INDENT}csrw CSR_SSP, x{addr_reg}    # push targets ssp-8, inside the region",
            f"{INDENT}LI(x{push_reg}, 0x0123456789ABCDEF)",
            f"{INDENT}sspush x{push_reg}    # store/AMO access fault",
            f"{INDENT}nop",
            "",
        ]
    )
    tc.code.append(test_data.add_testcase("ss_store_to_matched_non_ss_region", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_SSP", None), test_data))

    test_data.int_regs.return_registers([addr_reg, cfg_reg, tmp_reg, check_reg])
    return test_data.end_test_chunk()


def _generate_m_ss_negative(test_data: TestData) -> TestChunk:
    """The shadow-stack encoding stays reserved while mseccfg.MSSE is clear."""
    tc = test_data.begin_test_chunk("m_ss_negative")
    coverpoint = "cp_reserved_when_msse_clear"

    addr_reg, cfg_reg, tmp_reg, check_reg = test_data.int_regs.get_registers(4)

    tc.code.extend(_region_data_section([("ss", "region under test")]))
    tc.code.append(
        comment_banner(
            coverpoint,
            "With mseccfg.MSSE clear, an entry with the enable bit set and XWR=010\n"
            "is neither a shadow-stack region nor a legal ordinary encoding, so it\n"
            "denies every access. A plain load raises a load access fault.",
        )
    )
    tc.code.extend(_reset_entry_zero(addr_reg, tmp_reg, "ss"))

    # Pin the precondition: if boot ever set MSSE the case would silently invert.
    tc.code.append(test_data.add_testcase("msse_clear", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MSECCFG", None), test_data))

    tc.code.extend(
        [
            f"{INDENT}LA(x{addr_reg}, ss_end)",
            f"{INDENT}srli x{addr_reg}, x{addr_reg}, 2    # TOR upper bound",
            f"{INDENT}li x{cfg_reg}, {_CFG_SS_TOR}",
            f"{INDENT}li x{tmp_reg}, {_MIREG2_E:#x}    # enable bit at MXLEN-1",
            f"{INDENT}or x{cfg_reg}, x{cfg_reg}, x{tmp_reg}",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg, 1))
    tc.code.extend(
        [
            f"{INDENT}csrw CSR_MIREG, x{addr_reg}",
            f"{INDENT}csrw CSR_MIREG2, x{cfg_reg}",
            "",
            f"{INDENT}LI(x{check_reg}, 0x0BADF00DBADF00D)    # poison: visible if the load wrongly succeeds",
            f"{INDENT}LA(x{addr_reg}, ss_start)",
            f"{INDENT}addi x{addr_reg}, x{addr_reg}, {_PROBE_OFFSET:#x}",
            f"{INDENT}ld x{check_reg}, 0(x{addr_reg})    # load access fault",
            f"{INDENT}nop",
            "",
        ]
    )
    tc.code.append(test_data.add_testcase("load_denied", coverpoint, covergroup))
    tc.code.append(write_sigupd(check_reg, test_data))

    test_data.int_regs.return_registers([addr_reg, cfg_reg, tmp_reg, check_reg])
    return test_data.end_test_chunk()


def _generate_m_ss_interlock(test_data: TestData) -> TestChunk:
    """The Smepmp interlock makes mseccfg.MSSE read-only once a PMP entry is locked."""
    tc = test_data.begin_test_chunk("m_ss_interlock")
    coverpoint = "cp_smepmp_interlock"

    cfg_reg, tmp_reg, check_reg = test_data.int_regs.get_registers(3)

    tc.code.append(
        comment_banner(
            coverpoint,
            "With no PMP entry locked and RLB clear, mseccfg.MSSE is writable.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}csrr x{check_reg}, CSR_MSECCFG",
            f"{INDENT}li x{tmp_reg}, {_MSECCFG_MSSE:#x}    # mseccfg.MSSE",
            f"{INDENT}or x{check_reg}, x{check_reg}, x{tmp_reg}",
            f"{INDENT}csrw CSR_MSECCFG, x{check_reg}",
        ]
    )
    tc.code.append(test_data.add_testcase("msse_writable_before_lock", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MSECCFG", None), test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "Lock an A=OFF entry to arm the interlock without matching memory.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}li x{cfg_reg}, PMP_L    # L only: A=OFF, XWR=000",
        ]
    )
    tc.code.extend(_select_entry(tmp_reg, 7))
    tc.code.extend(
        [
            f"{INDENT}csrw CSR_MIREG, x0    # address unused while A=OFF",
            f"{INDENT}csrw CSR_MIREG2, x{cfg_reg}",
            "",
        ]
    )
    tc.code.append(test_data.add_testcase("entry_locked", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MIREG2", None), test_data))

    tc.code.append(
        comment_banner(
            coverpoint,
            "With an entry locked and RLB clear, mseccfg.MSSE is read-only, so an\n"
            "attempt to clear it leaves the field set.",
        )
    )
    tc.code.extend(
        [
            f"{INDENT}csrr x{check_reg}, CSR_MSECCFG",
            f"{INDENT}li x{tmp_reg}, {_MSECCFG_MSSE:#x}",
            f"{INDENT}not x{tmp_reg}, x{tmp_reg}",
            f"{INDENT}and x{check_reg}, x{check_reg}, x{tmp_reg}    # clear MSSE in the written value",
            f"{INDENT}csrw CSR_MSECCFG, x{check_reg}",
        ]
    )
    tc.code.append(test_data.add_testcase("msse_read_only_after_lock", coverpoint, covergroup))
    tc.code.append(gen_csr_read_sigupd(check_reg, ("CSR_MSECCFG", None), test_data))

    test_data.int_regs.return_registers([cfg_reg, tmp_reg, check_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "Smcfiss",
    # The MSSE lock interlock is defined only with Smepmp.
    required_extensions=["Sm", "Smepmp", "Smcfiss"],
    march_extensions=["Zicfiss"],
    params=[
        "MXLEN: 64",
        # Entries 0-2 are programmed and entry 7 is locked to arm the interlock.
        # Entry 1 is TOR, entry 2 is NAPOT. Usable, not implemented: an entry
        # whose registers read as zero cannot guard a region.
        "NUM_USABLE_PMP_ENTRIES: '>=8'",
        "PMP_TOR_SUPPORTED: true",
        "PMP_NAPOT_SUPPORTED: true",
        # Fixed 4 KiB regions, so the granule must be no coarser (log2 of the
        # smallest supported region).
        "PMP_GRANULARITY: '<=12'",
    ],
    extra_defines=[
        "#define BOOT_TO_MMODE",
        # Two traps in m_ss_basic.
        "#define TRAP_SIGUPD_COUNT 14",
    ],
)
def make_smcfiss(test_data: TestData) -> list[TestChunk]:
    return [
        _generate_m_ss_basic(test_data),
        _generate_m_ss_negative(test_data),
        _generate_m_ss_interlock(test_data),
    ]
