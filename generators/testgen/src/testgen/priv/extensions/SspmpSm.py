##################################
# SspmpSm.py
#
# SPMP (S-level Physical Memory Protection) privileged extension test generator.
# Covers Sspmp, Sspmpen (optional), and Smpmpdeleg (M-mode delegation).
# bichengyang@sjtu.edu.cn Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SPMP privileged extension test generator."""

import sys
from collections.abc import Callable
from pathlib import Path
from random import seed

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, reproducible_hash, write_sigupd
from testgen.asm.sections import generate_test_data_section, generate_test_string_section
from testgen.constants import INDENT, indent_asm
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.io.templates import insert_footer_template, insert_header_template
from testgen.priv.registry import add_priv_test_generator

# SPMP CSR addresses used via indirect access
# siselect values for SPMP entries: 0x100 + entry_index
SISELECT_SPMP_BASE = 0x100
# sireg (0x151) accesses spmpaddr[i], sireg2 (0x152) accesses spmpcfg[i]

# Number of SPMP entries to test (we test a representative subset)
NUM_TEST_ENTRIES = 4  # Test entries 0, 1, 2, 3
BASELINE_ENTRY = 7  # Lowest-priority resident entry used to keep the test environment executable

# spmpcfg bit positions
SPMPCFG_R = 0  # bit 0: Read
SPMPCFG_W = 1  # bit 1: Write
SPMPCFG_X = 2  # bit 2: Execute
SPMPCFG_A_LO = 3  # bits [4:3]: Address matching mode
SPMPCFG_A_HI = 4
SPMPCFG_L = 7  # bit 7: Lock
SPMPCFG_U = 8  # bit 8: U-mode
SPMPCFG_SHARED = 9  # bit 9: Shared-Region

# The spec describes permission encodings as RWX, while spmpcfg[2:0] is
# physically laid out as {X, W, R}. Keep named values here to avoid reversing
# read and execute permissions when constructing the CSR value.
RWX_NONE = 0
RWX_R = 1 << SPMPCFG_R
RWX_W = 1 << SPMPCFG_W
RWX_X = 1 << SPMPCFG_X
RWX_RW = RWX_R | RWX_W
RWX_RX = RWX_R | RWX_X
RWX_RWX = RWX_R | RWX_W | RWX_X

# Address matching modes
A_OFF = 0b00
A_TOR = 0b01
A_NA4 = 0b10
A_NAPOT = 0b11

# Shared RWX=111 grants S-mode RWX and U-mode execute-only access. This is
# sufficient for resident test/trap code; explicit lower-numbered rules govern
# every U-mode data access exercised by the suite.
BASELINE_CFG = RWX_RWX | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U) | (1 << SPMPCFG_SHARED)


def _spmp_select(entry: int, reg: int) -> list[str]:
    """Generate assembly to select an SPMP entry via siselect."""
    return [
        f"LI(x{reg}, 0x{SISELECT_SPMP_BASE + entry:x})  # siselect = SPMP entry {entry}",
        f"CSRW(siselect, x{reg})",
    ]


def _spmp_write_cfg(reg: int, cfg_val: int) -> list[str]:
    """Generate assembly to write spmpcfg via sireg2."""
    return [
        f"LI(x{reg}, 0x{cfg_val:x})  # spmpcfg value",
        f"CSRW(0x152, x{reg})  # write sireg2 (spmpcfg)",
        "nop",
    ]


def _spmp_write_addr(reg: int, addr_val: int) -> list[str]:
    """Generate assembly to write spmpaddr via sireg."""
    return [
        f"LI(x{reg}, 0x{addr_val:x})  # spmpaddr value",
        f"CSRW(0x151, x{reg})  # write sireg (spmpaddr)",
        "nop",
    ]


def _spmp_read_cfg_sigupd(check_reg: int, test_data: TestData) -> str:
    """Generate assembly to read spmpcfg via sireg2 and write to signature."""
    assert test_data.test_chunk is not None
    test_data.test_chunk.sigupd_count += 1
    return (
        f"{INDENT}# Read spmpcfg (sireg2) into x{check_reg} and check.\n"
        f"RVTEST_SIGUPD_CSR_READ(0x152, x{check_reg}, "
        f"{test_data.current_testcase_label}, {test_data.current_testcase_label}_str)"
    )


def _spmp_read_addr_sigupd(check_reg: int, test_data: TestData) -> str:
    """Generate assembly to read spmpaddr via sireg and write to signature."""
    assert test_data.test_chunk is not None
    test_data.test_chunk.sigupd_count += 1
    return (
        f"{INDENT}# Read spmpaddr (sireg) into x{check_reg} and check.\n"
        f"RVTEST_SIGUPD_CSR_READ(0x151, x{check_reg}, "
        f"{test_data.current_testcase_label}, {test_data.current_testcase_label}_str)"
    )


def _sfence_vma() -> str:
    """Generate SFENCE.VMA to synchronize SPMP changes."""
    return "sfence.vma x0, x0  # synchronize SPMP CSR writes with subsequent memory accesses"


def _spmp_preamble(test_data: TestData) -> list[str]:
    """Delegate the shared entries and install a resident catch-all rule.

    These tests exercise the Smpmpdeleg resource-sharing profile explicitly.
    After pmpnum is set to zero, reset PMP state would otherwise leave S-mode
    with no matching SPMP entry, so the very next instruction fetch could
    fault. Entry 7 is kept below the entries under test and grants S-mode RWX
    plus U-mode execute access to resident code. Lower-numbered test entries
    still take priority over it and explicitly govern U-mode data accesses.
    """
    sel_reg, val_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    lines = [
        comment_banner(
            "SPMP boot preamble",
            "Exercise the Smpmpdeleg resource-sharing profile by delegating all writable\n"
            "PMP entries, then install a lowest-priority resident rule for the test code.",
        ),
        "RVTEST_GOTO_MMODE",
        "CSRW(CSR_MPMPDELEG, zero)  # pmpnum = 0 -> delegate all writable entries",
        "nop",
        f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + BASELINE_ENTRY:x})",
        f"CSRW(miselect, x{sel_reg})  # select resident SPMP entry {BASELINE_ENTRY}",
        f"LI(x{val_reg}, -1)  # maximal NAPOT region",
        f"CSRW(mireg, x{val_reg})",
        f"LI(x{val_reg}, 0x{BASELINE_CFG:x})  # shared S:RWX / U:X resident rule",
        f"CSRW(mireg2, x{val_reg})",
        "nop",
    ]
    lines.extend(
        [
            "#ifdef SSPMPEN_SUPPORTED",
            f"LI(x{val_reg}, -1)",
            f"CSRW(CSR_SPMPEN, x{val_reg})  # activate all delegated entries",
            "nop",
            "#endif",
        ]
    )
    lines.extend(
        [
            _sfence_vma(),
            "RVTEST_GOTO_LOWER_MODE Smode",
            _sfence_vma(),
        ]
    )
    test_data.int_regs.return_registers([sel_reg, val_reg])
    return lines


def _generate_spmp_csr_indirect_access_tests(test_data: TestData) -> list[str]:
    """Test indirect CSR access to SPMP entries via siselect/sireg/sireg2.

    Covers: cp_spmp_indirect_access, cp_spmpaddr_write, cp_spmpcfg_write
    """
    covergroup = "SspmpSm_csr_cg"
    sel_reg, val_reg, check_reg, save_cfg_reg, save_addr_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_spmp_indirect_access / cp_spmpaddr_write / cp_spmpcfg_write",
            "Test reading and writing SPMP CSRs via siselect + sireg/sireg2.\n"
            "For each test entry, write spmpaddr and spmpcfg, then read back.",
        ),
    ]

    for entry in range(NUM_TEST_ENTRIES):
        lines.append(f"\n# === SPMP entry {entry} ===")
        # Select SPMP entry
        lines.extend(_spmp_select(entry, sel_reg))

        # Save original values
        lines.extend(
            [
                f"CSRR(x{save_addr_reg}, 0x151)  # save spmpaddr[{entry}]",
                "nop",
                f"CSRR(x{save_cfg_reg}, 0x152)  # save spmpcfg[{entry}]",
                "nop",
            ]
        )

        # ---------- cp_spmp_indirect_access ----------
        if entry == 0:
            lines.extend(
                [
                    test_data.add_testcase("sireg_indirect_access", "cp_spmp_indirect_access", covergroup),
                ]
            )

        # ---------- Test spmpaddr write/read ----------
        coverpoint = "cp_spmpaddr_write"

        # Write a non-zero address
        addr_val = 0x80000000 + entry * 0x1000
        lines.extend(_spmp_write_addr(val_reg, addr_val >> 2))  # spmpaddr stores addr[55:2]
        lines.extend(
            [
                test_data.add_testcase(f"entry{entry}_addr_write", coverpoint, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
            ]
        )

        # Write zero address
        lines.extend(_spmp_write_addr(val_reg, 0))
        lines.extend(
            [
                test_data.add_testcase(f"entry{entry}_addr_zero", coverpoint, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
            ]
        )

        # Write all-ones to probe address width
        lines.extend(
            [
                f"li x{val_reg}, -1  # all ones",
                f"CSRW(0x151, x{val_reg})",
                "nop",
                test_data.add_testcase(f"entry{entry}_addr_allones", coverpoint, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
            ]
        )

        # ---------- Test spmpcfg write/read ----------
        coverpoint = "cp_spmpcfg_write"

        # Test each A field encoding
        for a_mode, a_name in [(A_OFF, "off"), (A_TOR, "tor"), (A_NA4, "na4"), (A_NAPOT, "napot")]:
            # cfg: R=1, W=0, X=1, A=mode, U=1
            cfg_val = (1 << SPMPCFG_R) | (1 << SPMPCFG_X) | (a_mode << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
            lines.extend(_spmp_write_cfg(val_reg, cfg_val))
            lines.extend(
                [
                    test_data.add_testcase(f"entry{entry}_cfg_a_{a_name}", coverpoint, covergroup),
                    _spmp_read_cfg_sigupd(check_reg, test_data),
                ]
            )

        # Test writing all zeros to cfg
        lines.extend(_spmp_write_cfg(val_reg, 0))
        lines.extend(
            [
                test_data.add_testcase(f"entry{entry}_cfg_zero", coverpoint, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

        # Restore original values
        lines.extend(
            [
                f"CSRW(0x151, x{save_addr_reg})  # restore spmpaddr[{entry}]",
                "nop",
                f"CSRW(0x152, x{save_cfg_reg})  # restore spmpcfg[{entry}]",
                "nop",
            ]
        )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_cfg_reg, save_addr_reg])
    return lines


def _generate_spmp_lock_tests(test_data: TestData) -> list[str]:
    """Test SPMP lock bit behavior.

    Covers: cp_spmp_lock, cp_spmp_lock_write_ignored, cp_spmp_lock_tor_prevaddr
    """
    covergroup = "SspmpSm_csr_cg"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_spmp_lock / cp_spmp_lock_write_ignored / cp_spmp_lock_tor_prevaddr",
            "Test that locked SPMP entries cannot be modified from S-mode.\n"
            "Also test that locked TOR entries lock the preceding spmpaddr.\n"
            "NOTE: Lock can only be cleared from M-mode via miselect.",
        ),
    ]

    # Use entries 1 and 2 for lock tests (entry 2 is TOR using entry 1's addr)
    test_entry = 2
    prev_entry = test_entry - 1

    # --- Setup: configure entry 2 with TOR mode, unlocked ---
    lines.extend(_spmp_select(prev_entry, sel_reg))
    lines.extend(_spmp_write_addr(val_reg, 0x20000000 >> 2))  # base addr
    lines.extend(_spmp_select(test_entry, sel_reg))
    lines.extend(_spmp_write_addr(val_reg, 0x20001000 >> 2))  # top addr

    # Write cfg with TOR, R, U=1, unlocked
    cfg_unlocked = (1 << SPMPCFG_R) | (A_TOR << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_write_cfg(val_reg, cfg_unlocked))

    # ---------- Test writing when unlocked ----------
    coverpoint = "cp_spmp_lock"
    lines.extend(
        [
            "",
            "# Verify entry is currently unlocked",
            test_data.add_testcase(f"entry{test_entry}_unlocked", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # ---------- Lock the entry ----------
    cfg_locked = cfg_unlocked | (1 << SPMPCFG_L)
    lines.extend(_spmp_write_cfg(val_reg, cfg_locked))
    lines.extend(
        [
            test_data.add_testcase(f"entry{test_entry}_locked", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # ---------- Attempt to write spmpcfg of locked entry (should be ignored) ----------
    coverpoint = "cp_spmp_lock_write_ignored"

    # Try CSRRW to locked cfg
    new_cfg = (1 << SPMPCFG_R) | (1 << SPMPCFG_W) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_write_cfg(val_reg, new_cfg))
    lines.extend(
        [
            test_data.add_testcase(f"entry{test_entry}_locked_csrrw_cfg", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Try CSRRS to locked cfg
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{(1 << SPMPCFG_W):x})  # try to set W bit",
            f"CSRS(0x152, x{val_reg})  # csrrs sireg2",
            "nop",
            test_data.add_testcase(f"entry{test_entry}_locked_csrrs_cfg", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Try CSRRC to locked cfg
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{(1 << SPMPCFG_R):x})  # try to clear R bit",
            f"CSRC(0x152, x{val_reg})  # csrrc sireg2",
            "nop",
            test_data.add_testcase(f"entry{test_entry}_locked_csrrc_cfg", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Try to write spmpaddr of locked entry
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{0xDEAD:x})  # attempt to change locked spmpaddr",
            f"CSRW(0x151, x{val_reg})  # write sireg (spmpaddr)",
            "nop",
            test_data.add_testcase(f"entry{test_entry}_locked_addr_write", coverpoint, covergroup),
            _spmp_read_addr_sigupd(check_reg, test_data),
        ]
    )

    # ---------- Test locked TOR also locks prev spmpaddr ----------
    coverpoint = "cp_spmp_lock_tor_prevaddr"
    lines.extend(_spmp_select(prev_entry, sel_reg))
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{0xBEEF:x})  # attempt to change prev entry's spmpaddr",
            f"CSRW(0x151, x{val_reg})  # write sireg (spmpaddr[{prev_entry}])",
            "nop",
            test_data.add_testcase(f"entry{prev_entry}_locked_tor_prevaddr", coverpoint, covergroup),
            _spmp_read_addr_sigupd(check_reg, test_data),
        ]
    )

    # ---------- Unlock via M-mode (miselect) ----------
    coverpoint = "cp_spmp_lock_clear_mmode"
    lines.extend(
        [
            "",
            "# Clear lock bit from M-mode via miselect",
            "RVTEST_GOTO_MMODE",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + test_entry:x})",
            f"CSRW(miselect, x{sel_reg})  # miselect = SPMP entry {test_entry}",
            "nop",
        ]
    )
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_unlocked:x})  # cfg without L bit",
            f"CSRW(mireg2, x{val_reg})  # write mireg2 to clear lock",
            "nop",
            test_data.add_testcase(f"entry{test_entry}_mmode_unlock", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("mireg2", None), test_data),
        ]
    )

    # Clean up: clear the entries
    lines.extend(
        [
            "CSRW(mireg2, zero)  # clear mireg2",
            "nop",
            "CSRW(mireg, zero)  # clear mireg",
            "nop",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + prev_entry:x})",
            f"CSRW(miselect, x{sel_reg})",
            "nop",
            "CSRW(mireg, zero)",
            "nop",
            "CSRW(mireg2, zero)",
            "nop",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_spmp_oob_access_tests(test_data: TestData) -> list[str]:
    """Test out-of-bounds siselect index behavior.

    Covers: cp_spmp_oob_read_zero, cp_spmp_oob_write_ignored
    """
    covergroup = "SspmpSm_csr_cg"
    read_cp = "cp_spmp_oob_read_zero"
    write_cp = "cp_spmp_oob_write_ignored"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_spmp_oob_read_zero / cp_spmp_oob_write_ignored",
            "Access out-of-bounds SPMP index via siselect.\nReads should return zero, writes should be ignored.",
        ),
    ]

    # Test the first implementation-specific OOB index as well as values beyond
    # the architectural 64-entry selector space.
    oob_indices = [
        ("0x100 + UDB_NUM_PMP_ENTRIES", "first_unimplemented"),
        ("0x150", "reserved_150"),
        ("0x1ff", "reserved_1ff"),
    ]
    for oob_expr, oob_name in oob_indices:
        lines.extend(
            [
                f"\n# Out-of-bounds index {oob_expr}",
                f"LI(x{sel_reg}, {oob_expr})",
                f"CSRW(siselect, x{sel_reg})",
                "nop",
            ]
        )

        # Read spmpaddr - should be 0
        lines.extend(
            [
                test_data.add_testcase(f"oob_{oob_name}_read_addr", read_cp, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
            ]
        )

        # Read spmpcfg - should be 0
        lines.extend(
            [
                test_data.add_testcase(f"oob_{oob_name}_read_cfg", read_cp, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

        # Write spmpaddr, then read back - should still be 0
        lines.extend(
            [
                f"li x{val_reg}, -1",
                f"CSRW(0x151, x{val_reg})  # write sireg (should be ignored)",
                "nop",
                test_data.add_testcase(f"oob_{oob_name}_write_addr", write_cp, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
            ]
        )

    # Canonical bin-name labels so the SVH bins are reported by exact name.
    lines.extend(
        [
            test_data.add_testcase("oob_read_returns_zero", read_cp, covergroup),
            test_data.add_testcase("oob_write_no_state_change", write_cp, covergroup),
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_addr_match_tests(test_data: TestData) -> list[str]:
    """Test address matching modes: OFF, TOR, NA4, NAPOT.

    Covers: cp_addr_match_off, cp_addr_match_tor, cp_addr_match_na4, cp_addr_match_napot
    """
    covergroup = "SspmpSm_addr_cg"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_addr_match_{off,tor,na4,napot}",
            "Test each address matching mode by configuring SPMP entries\nand verifying the matching behavior.",
        ),
    ]

    # ---------- A=OFF: entry disabled, no match ----------
    coverpoint = "cp_addr_match_off"
    entry = 0
    lines.extend(
        [
            "\n# A=OFF: entry disabled",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    cfg_off = A_OFF << SPMPCFG_A_LO  # A=OFF
    lines.extend(_spmp_write_cfg(val_reg, cfg_off))
    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase(f"entry{entry}_off", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # ---------- A=TOR ----------
    coverpoint = "cp_addr_match_tor"
    # Entry 0 addr = base, Entry 1 cfg with A=TOR means range [0, entry1.addr)
    lines.extend(
        [
            "\n# A=TOR: top of range matching",
        ]
    )
    # Set entry 0 addr (base of range)
    lines.extend(_spmp_select(0, sel_reg))
    base_addr = 0x80000000
    lines.extend(_spmp_write_addr(val_reg, base_addr >> 2))
    lines.extend(_spmp_write_cfg(val_reg, 0))  # entry 0 cfg does not matter for TOR match

    # Set entry 1 with TOR mode
    lines.extend(_spmp_select(1, sel_reg))
    top_addr = 0x80010000
    lines.extend(_spmp_write_addr(val_reg, top_addr >> 2))
    cfg_tor = (1 << SPMPCFG_R) | (1 << SPMPCFG_W) | (A_TOR << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_write_cfg(val_reg, cfg_tor))
    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase("entry1_tor_cfg", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Verify entry 0 spmpaddr (the base)
    lines.extend(_spmp_select(0, sel_reg))
    lines.extend(
        [
            test_data.add_testcase("entry0_tor_base_addr", coverpoint, covergroup),
            _spmp_read_addr_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    lines.extend(_spmp_select(1, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_select(0, sel_reg))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.extend(_spmp_write_cfg(val_reg, 0))

    # ---------- A=NA4 ----------
    coverpoint = "cp_addr_match_na4"
    entry = 0
    lines.extend(
        [
            "\n# A=NA4: naturally aligned 4-byte region",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    na4_addr = 0x80000000
    lines.extend(_spmp_write_addr(val_reg, na4_addr >> 2))
    cfg_na4 = (1 << SPMPCFG_R) | (A_NA4 << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_write_cfg(val_reg, cfg_na4))
    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase(f"entry{entry}_na4", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))

    # ---------- A=NAPOT ----------
    coverpoint = "cp_addr_match_napot"
    entry = 0
    lines.extend(
        [
            "\n# A=NAPOT: naturally aligned power-of-two region (8 bytes minimum)",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    # For NAPOT with 8-byte region: addr = base >> 2, lsb = 0 (encodes 8 bytes)
    napot_addr = 0x80000000
    # For an 8-byte NAPOT region, spmpaddr = (base >> 2) | 0 (the pattern encodes size)
    lines.extend(_spmp_write_addr(val_reg, napot_addr >> 2))
    cfg_napot = (1 << SPMPCFG_R) | (1 << SPMPCFG_W) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_write_cfg(val_reg, cfg_napot))
    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase(f"entry{entry}_napot", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Also test a larger NAPOT region (4KB = 0x1000 bytes)
    # For 4KB NAPOT: spmpaddr LSBs = 0b0_1111_1111 (9 bits set for 2^12 region)
    napot_4k_addr = (napot_addr >> 2) | 0x1FF
    lines.extend(_spmp_write_addr(val_reg, napot_4k_addr))
    lines.extend(
        [
            test_data.add_testcase(f"entry{entry}_napot_4k", coverpoint, covergroup),
            _spmp_read_addr_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_permission_smode_tests(test_data: TestData) -> list[str]:
    """Test S-mode-only rules (SHARED=0, U=0).

    Covers: cp_smode_rule
    S-mode: permissions R/W/X enforced
    U-mode: denied
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_smode_rule"
    sel_reg, val_reg, check_reg, addr_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Configure SPMP S-mode-only rules (SHARED=0, U=0) with various RWX.\n"
            "Exercise each permission from S-mode, then verify that U-mode is denied\n"
            "regardless of the RWX bits.",
        ),
    ]

    entry = 0
    lines.extend(
        [
            "# Delegate U-mode ecall so RVTEST_GOTO_SMODE can return from each U-mode probe",
            "RVTEST_GOTO_MMODE",
            f"LI(x{val_reg}, 0x100)",
            f"CSRS(CSR_MEDELEG, x{val_reg})",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"LA(x{addr_reg}, scratch)",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(
        [
            f"srli x{check_reg}, x{addr_reg}, 2  # 8-byte NAPOT region",
            f"CSRW(0x151, x{check_reg})",
            "nop",
        ]
    )

    # Test all valid RWX combinations for S-mode rules
    valid_rwx = [
        (RWX_NONE, "none"),
        (RWX_X, "x"),
        (RWX_R, "r"),
        (RWX_RX, "rx"),
        (RWX_RW, "rw"),
        (RWX_RWX, "rwx"),
    ]

    for rwx_val, rwx_name in valid_rwx:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO)  # SHARED=0, U=0
        lines.extend(
            [
                f"\n# === S-mode-only rule with RWX={rwx_name} ===",
                "# Install a safe jalr target while the specific rule is OFF",
                f"LI(x{val_reg}, 0x00008067)  # ret",
                f"sw x{val_reg}, 0(x{addr_reg})",
                "fence.i",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))
        lines.extend(
            [
                _sfence_vma(),
                f"# S load: {'allowed' if rwx_val & RWX_R else 'load page fault'}",
                test_data.add_testcase(f"smode_rwx_{rwx_name}_load", coverpoint, covergroup),
                f"lw x{check_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )
        if rwx_val & RWX_R:
            lines.append(write_sigupd(check_reg, test_data))
        lines.extend(
            [
                f"# S store: {'allowed' if rwx_val & RWX_W else 'store page fault'}",
                test_data.add_testcase(f"smode_rwx_{rwx_name}_store", coverpoint, covergroup),
                f"LI(x{val_reg}, 0x00008067)",
                f"sw x{val_reg}, 0(x{addr_reg})",
                "nop",
                f"# S fetch: {'allowed' if rwx_val & RWX_X else 'instruction page fault'}",
                test_data.add_testcase(f"smode_rwx_{rwx_name}_fetch", coverpoint, covergroup),
                "LI(x4, 0xACCE)  # SKIP_MEPC sentinel",
                f"jalr x1, 0(x{addr_reg})",
                "nop",
                "RVTEST_GOTO_MMODE",
                "RVTEST_GOTO_LOWER_MODE Umode",
                "# U-mode is denied by every S-mode-only rule",
                test_data.add_testcase(f"umode_denied_{rwx_name}_load", coverpoint, covergroup),
                f"lw x{check_reg}, 0(x{addr_reg})",
                "nop",
                test_data.add_testcase(f"umode_denied_{rwx_name}_store", coverpoint, covergroup),
                f"sw x{val_reg}, 0(x{addr_reg})",
                "nop",
                test_data.add_testcase(f"umode_denied_{rwx_name}_fetch", coverpoint, covergroup),
                "LI(x4, 0xACCE)",
                f"jalr x1, 0(x{addr_reg})",
                "nop",
                "RVTEST_GOTO_SMODE",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, 0))
        lines.append(_sfence_vma())

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg])
    return lines


def _generate_permission_umode_tests(test_data: TestData) -> list[str]:
    """Test U-mode rules (SHARED=0, U=1) with *real* U-mode accesses.

    Covers: cp_umode_rule
      For each RWX encoding we program SPMP entry 0 as a U-mode region
      covering `scratch`, drop to U-mode, and verify the access checks:
        - lw   succeeds iff R=1, else load page fault (cause 13)
        - sw   succeeds iff W=1, else store page fault (cause 15)
        - jalr succeeds iff X=1, else fetch page fault (cause 12),
                recovered via SKIP_MEPC + x4 = 0xACCE sentinel.
      After each iteration, RVTEST_GOTO_SMODE ecalls back to S-mode; medeleg
      bit 8 is set up-front so U-mode ecall is delegated to S-mode, which
      provides the rtn2smode fast path.
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_umode_rule"
    # x4 is framework-reserved as the RVTEST_SIGUPD temp and is also the
    # SKIP_MEPC sentinel we LI just before jalr.
    sel_reg, val_reg, check_reg, addr_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Configure SPMP U-mode rules (SHARED=0, U=1) with various RWX and\n"
            "exercise R / W / X permissions from inside U-mode.  Faulting\n"
            "instructions rely on the framework's trap handler to advance xepc;\n"
            "the fetch case uses SKIP_MEPC (x4 = 0xACCE) to force xepc = ra.",
        ),
    ]

    entry = 0

    # Pre-install `ret` (0x00008067) at scratch[0] from S-mode, before SPMP is
    # programmed.  This keeps the jalr target clean for cases where X=1.
    lines.extend(
        [
            "\n# Pre-install `ret` (0x00008067) at scratch[0]",
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{val_reg}, 0x00008067)  # ret",
            f"sw x{val_reg}, 0(x{addr_reg})",
            "fence.i  # sync icache with the data write",
        ]
    )

    # Delegate U-mode ecall (cause 8) to S-mode so RVTEST_GOTO_SMODE can use
    # the strap handler's rtn2smode fast path to return here.
    lines.extend(
        [
            "\n# Delegate U-mode ecall (medeleg bit 8) to S-mode for RVTEST_GOTO_SMODE",
            "RVTEST_GOTO_MMODE",
            f"LI(x{val_reg}, 0x100)  # bit 8: U-mode ecall",
            f"CSRS(CSR_MEDELEG, x{val_reg})",
            "nop",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    valid_rwx = [
        (RWX_NONE, "none"),
        (RWX_X, "x"),
        (RWX_R, "r"),
        (RWX_RX, "rx"),
        (RWX_RW, "rw"),
        (RWX_RWX, "rwx"),
    ]

    for rwx_val, rwx_name in valid_rwx:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
        lines.extend(
            [
                f"\n# === U-mode rule with RWX={rwx_name} ===",
                "RVTEST_GOTO_MMODE",
                f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + entry:x})",
                f"CSRW(miselect, x{sel_reg})",
                "nop",
                f"LA(x{addr_reg}, scratch)",
                f"srli x{addr_reg}, x{addr_reg}, 2  # spmpaddr format",
                "# No low bits set: 8-byte NAPOT region, excluding trap save areas",
                f"CSRW(mireg, x{addr_reg})  # spmpaddr via mireg",
                "nop",
                f"LI(x{val_reg}, 0x{cfg_val:x})  # U=1, RWX={rwx_name}",
                f"CSRW(mireg2, x{val_reg})  # spmpcfg via mireg2",
                "nop",
                "sfence.vma x0, x0",
                "RVTEST_GOTO_LOWER_MODE Umode",
                "",
                "# === In U-mode ===",
                f"# load: succeeds iff R=1 ({'yes' if rwx_val & RWX_R else 'no'}) in RWX={rwx_name}",
                test_data.add_testcase(f"umode_rwx_{rwx_name}_load", coverpoint, covergroup),
                f"LA(x{addr_reg}, scratch)",
                f"lw x{check_reg}, 0(x{addr_reg})",
                "nop  # trap handler skips here on R=0",
                "",
                f"# store: succeeds iff W=1 ({'yes' if rwx_val & RWX_W else 'no'}) in RWX={rwx_name}",
                test_data.add_testcase(f"umode_rwx_{rwx_name}_store", coverpoint, covergroup),
                f"LI(x{val_reg}, 0x00008067)  # ret (preserves the jalr target)",
                f"sw x{val_reg}, 0(x{addr_reg})",
                "nop  # trap handler skips here on W=0",
                "",
                f"# fetch: succeeds iff X=1 ({'yes' if rwx_val & RWX_X else 'no'}) in RWX={rwx_name}",
                test_data.add_testcase(f"umode_rwx_{rwx_name}_fetch", coverpoint, covergroup),
                "LI(x4, 0xACCE)  # SKIP_MEPC sentinel",
                f"jalr x1, 0(x{addr_reg})  # on fetch fault (X=0) handler forces xepc = ra",
                "nop",
                "",
                "# Return to S-mode (strap handler's rtn2smode path; medeleg[8]=1)",
                "RVTEST_GOTO_SMODE",
            ]
        )

    # Clean up: clear spmpcfg and restore medeleg (bit 8 cleared at CODE_END
    # by the framework's resto_edeleg, but clear explicitly to be polite).
    lines.extend(
        [
            "\n# Clean up: clear spmpcfg via S-mode indirect access",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg])
    return lines


def _generate_sum_effect_tests(test_data: TestData) -> list[str]:
    """Test SUM bit effect on S-mode access to U-mode regions.

    Covers: cp_sum_effect, cp_sum_denied, cp_enforce_no_x
      SUM=0: S-mode denied any access to a U-mode region -> load/store fault.
      SUM=1: S-mode data access allowed; instruction fetch still denied
             (EnforceNoX), even when X=1 on the U-mode rule.
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_sum_effect"
    # x4 is reserved by the framework (RVTEST_SIGUPD temp) AND used by this
    # test as the SKIP_MEPC sentinel for the EnforceNoX jalr.  We LI 0xACCE
    # into x4 immediately before the jalr; no sigupd happens in between, so
    # the sentinel survives until the trap handler inspects it.
    sel_reg, val_reg, check_reg, save_reg, addr_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test sstatus.SUM effect on S-mode access to a U-mode SPMP region.\n"
            "SUM=0: S-mode is denied any access (load/store both fault).\n"
            "SUM=1: S-mode data access is allowed; instruction fetch is still\n"
            "       denied by EnforceNoX even when X=1 in the rule.",
        ),
    ]

    entry = 0

    # Pre-install `ret` (0x00008067) at scratch[0] so that if EnforceNoX ever
    # fails to fire and the fetch succeeds, the jalr lands on a clean return
    # rather than executing garbage.  This write must happen BEFORE we program
    # SPMP because afterwards the region is U-mode-only with no S-mode
    # permissions.
    lines.extend(
        [
            "\n# Pre-install `ret` (0x00008067) at scratch[0]",
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{val_reg}, 0x00008067)  # ret",
            f"sw x{val_reg}, 0(x{addr_reg})",
            "fence.i  # sync icache with the data write",
        ]
    )

    # Configure SPMP entry 0 over the first 8 bytes of scratch. Keeping the
    # trap save areas outside this region lets the S-mode handler record the
    # expected permission faults safely.
    # X=1 is required so that cp_enforce_no_x.sum1_fetch_denied can fire
    # (the bin requires umode_rule_rwx ∈ {rx, rwx, x_only}).
    cfg_val = RWX_RWX | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"srli x{addr_reg}, x{addr_reg}, 2  # convert to spmpaddr format",
            "# No low bits set: 8-byte NAPOT region",
            f"CSRW(0x151, x{addr_reg})  # write spmpaddr via sireg",
            "nop",
        ]
    )
    lines.extend(_spmp_write_cfg(val_reg, cfg_val))
    lines.append(_sfence_vma())

    # ---- SUM=0: S-mode is denied any access to the U-mode region ----
    lines.extend(
        [
            "\n# sstatus.SUM = 0  ->  S-mode denied any access to U-mode region",
            f"CSRR(x{save_reg}, sstatus)  # save sstatus",
            f"LI(x{val_reg}, 0x40000)  # sstatus.SUM bit (bit 18)",
            f"CSRC(sstatus, x{val_reg})  # clear SUM bit",
            "",
            "# Expected: load page fault (cause 13); strap handler advances sepc by 4.",
            test_data.add_testcase("sum_0_smode_load_denied", "cp_sum_denied", covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})  # faults",
            "nop  # trap handler skips to here",
            "",
            "# Expected: store page fault (cause 15); strap handler advances sepc by 4.",
            test_data.add_testcase("sum_0_smode_store_denied", "cp_sum_denied", covergroup),
            f"sw x{val_reg}, 0(x{addr_reg})  # faults",
            "nop  # trap handler skips to here",
        ]
    )

    # ---- SUM=1: data access allowed; fetch still denied (EnforceNoX) ----
    lines.extend(
        [
            "\n# sstatus.SUM = 1  ->  S-mode data access allowed; fetch denied (EnforceNoX)",
            f"LI(x{val_reg}, 0x40000)",
            f"CSRS(sstatus, x{val_reg})  # set SUM bit",
            "",
            "# Expected: load succeeds, reads the `ret` instruction value.",
            test_data.add_testcase("sum_1_data_allowed_load", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            "",
            "# Expected: store succeeds.  Re-install `ret` so the jalr target is clean.",
            test_data.add_testcase("sum_1_data_allowed_store", coverpoint, covergroup),
            f"LI(x{val_reg}, 0x00008067)  # ret",
            f"sw x{val_reg}, 0(x{addr_reg})",
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            "fence.i  # sync icache with the data write",
            "",
            "# Expected: instruction fetch denied by EnforceNoX even though X=1 in cfg.",
            "# SKIP_MEPC + x4=0xACCE tells the trap handler to force xepc=ra on fetch fault.",
            test_data.add_testcase("sum_1_fetch_denied", "cp_enforce_no_x", covergroup),
            "LI(x4, 0xACCE)  # SKIP_MEPC sentinel",
            f"LA(x{addr_reg}, scratch)",
            f"jalr x1, 0(x{addr_reg})  # fetch page fault (cause 12); handler returns here",
            "nop",
            "",
            f"CSRW(sstatus, x{save_reg})  # restore sstatus",
        ]
    )

    # ---- Clean up: clear spmpcfg ----
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg, addr_reg])
    return lines


def _generate_mxr_effect_tests(test_data: TestData) -> list[str]:
    """Test MXR bit effect (Make eXecutable Readable).

    Covers: cp_mxr_effect
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_mxr_effect"
    sel_reg, val_reg, check_reg, save_reg, addr_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test sstatus.MXR effect on SPMP permission checking.\nMXR=1 makes execute-only regions also readable.",
        ),
    ]

    # Put known data in an 8-byte region before making it execute-only. The
    # narrow region leaves the trap-handler save area covered by the resident
    # catch-all rule when the MXR=0 load faults.
    entry = 0
    cfg_val = RWX_X | (A_NAPOT << SPMPCFG_A_LO)
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{val_reg}, 0x5A5A5A5A)",
            f"sw x{val_reg}, 0(x{addr_reg})",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(
        [
            f"srli x{check_reg}, x{addr_reg}, 2  # 8-byte NAPOT encoding",
            f"CSRW(0x151, x{check_reg})",
            "nop",
        ]
    )
    lines.extend(_spmp_write_cfg(val_reg, cfg_val))
    lines.append(_sfence_vma())
    lines.append(f"CSRR(x{save_reg}, sstatus)  # save sstatus")

    for mxr_val in (0, 1):
        lines.extend(
            [
                f"\n# sstatus.MXR = {mxr_val}",
            ]
        )
        if mxr_val == 1:
            lines.append(f"LI(x{val_reg}, 0x{1 << 19:x})  # sstatus.MXR bit (bit 19)")
            lines.append(f"CSRS(sstatus, x{val_reg})  # set MXR bit")
        else:
            lines.append(f"LI(x{val_reg}, 0x{1 << 19:x})  # sstatus.MXR bit (bit 19)")
            lines.append(f"CSRC(sstatus, x{val_reg})  # clear MXR bit")

        lines.extend(
            [
                test_data.add_testcase(f"mxr_{mxr_val}_x_only_region", coverpoint, covergroup),
                f"lw x{check_reg}, 0(x{addr_reg})  # faults for MXR=0, succeeds for MXR=1",
                "nop  # trap handler resumes here after the MXR=0 load fault",
            ]
        )
        if mxr_val == 1:
            lines.append(write_sigupd(check_reg, test_data))

    # Clean up
    lines.append(f"CSRW(sstatus, x{save_reg})  # restore sstatus")
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg, addr_reg])
    return lines


def _generate_shared_rule_tests(test_data: TestData) -> list[str]:
    """Test Shared-Region rules (SHARED=1, U=1).

    Covers: cp_shared_rule
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_shared_rule"
    sel_reg, val_reg, check_reg, addr_reg, save_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Configure SPMP Shared-Region rules (SHARED=1, U=1) with various RWX.\n"
            "Both S and U modes: Enforced per encoding table.\n"
            "Special: RWX=110 -> S:Enforce, U:Read-only\n"
            "         RWX=111 -> S:Enforce, U:Exec-only",
        ),
    ]

    entry = 0
    lines.extend(
        [
            "# Delegate U-mode ecall so each U-mode probe can return to S-mode",
            "RVTEST_GOTO_MMODE",
            f"LI(x{val_reg}, 0x100)",
            f"CSRS(CSR_MEDELEG, x{val_reg})",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"LA(x{addr_reg}, scratch)",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(
        [
            f"srli x{check_reg}, x{addr_reg}, 2  # 8-byte NAPOT region",
            f"CSRW(0x151, x{check_reg})",
            "nop",
        ]
    )

    shared_rwx = [
        (RWX_NONE, "none"),
        (RWX_X, "x"),
        (RWX_R, "r"),
        (RWX_RX, "rx"),
        (RWX_RW, "rw"),
        (RWX_RWX, "rwx"),
    ]

    for rwx_val, rwx_name in shared_rwx:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U) | (1 << SPMPCFG_SHARED)
        u_read = bool(rwx_val & RWX_R) and rwx_val != RWX_RWX
        u_exec = bool(rwx_val & RWX_X)
        lines.extend(
            [
                f"\n# === Shared rule with RWX={rwx_name} ===",
                "# Install a safe jalr target while the specific rule is OFF",
                f"LI(x{val_reg}, 0x00008067)",
                f"sw x{val_reg}, 0(x{addr_reg})",
                "fence.i",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))
        lines.extend(
            [
                _sfence_vma(),
                f"# S load: {'allowed' if rwx_val & RWX_R else 'load page fault'}",
                test_data.add_testcase(f"shared_s_{rwx_name}_load", coverpoint, covergroup),
                f"lw x{check_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )
        if rwx_val & RWX_R:
            lines.append(write_sigupd(check_reg, test_data))
        lines.extend(
            [
                f"# S store: {'allowed' if rwx_val & RWX_W else 'store page fault'}",
                test_data.add_testcase(f"shared_s_{rwx_name}_store", coverpoint, covergroup),
                f"LI(x{val_reg}, 0x00008067)",
                f"sw x{val_reg}, 0(x{addr_reg})",
                "nop",
                f"# S fetch: {'allowed' if rwx_val & RWX_X else 'instruction page fault'}",
                test_data.add_testcase(f"shared_s_{rwx_name}_fetch", coverpoint, covergroup),
                "LI(x4, 0xACCE)",
                f"jalr x1, 0(x{addr_reg})",
                "nop",
                "RVTEST_GOTO_MMODE",
                "RVTEST_GOTO_LOWER_MODE Umode",
                f"# U load: {'allowed' if u_read else 'load page fault'}",
                test_data.add_testcase(f"shared_u_{rwx_name}_load", coverpoint, covergroup),
                f"lw x{check_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )
        if u_read:
            lines.append(write_sigupd(check_reg, test_data))
        lines.extend(
            [
                "# Shared encodings never grant U-mode write permission",
                test_data.add_testcase(f"shared_u_{rwx_name}_store", coverpoint, covergroup),
                f"sw x{val_reg}, 0(x{addr_reg})",
                "nop",
                f"# U fetch: {'allowed' if u_exec else 'instruction page fault'}",
                test_data.add_testcase(f"shared_u_{rwx_name}_fetch", coverpoint, covergroup),
                "LI(x4, 0xACCE)",
                f"jalr x1, 0(x{addr_reg})",
                "nop",
                "RVTEST_GOTO_SMODE",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, 0))
        lines.append(_sfence_vma())

    # Shared-region permissions do not depend on sstatus.SUM. Exercise the
    # same permitted S-mode load with SUM clear and set so the normative rule
    # is covered behaviorally rather than inferred from the cfg encoding.
    shared_read_cfg = RWX_R | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U) | (1 << SPMPCFG_SHARED)
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, shared_read_cfg))
    lines.extend(
        [
            "\n# Shared-region S-mode access ignores sstatus.SUM",
            f"CSRR(x{save_reg}, sstatus)",
            f"LI(x{val_reg}, 0x{1 << 18:x})  # sstatus.SUM",
            f"CSRC(sstatus, x{val_reg})",
            test_data.add_testcase("sum0_shared_load_allowed", "cp_shared_sum_ignored", covergroup),
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            f"CSRS(sstatus, x{val_reg})",
            test_data.add_testcase("sum1_shared_load_allowed", "cp_shared_sum_ignored", covergroup),
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            f"CSRW(sstatus, x{save_reg})",
        ]
    )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg, save_reg])
    return lines


def _generate_reserved_encoding_tests(test_data: TestData) -> list[str]:
    """Test reserved RWX encodings (010 and 011).

    Covers: cp_reserved_encoding
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_reserved_encoding"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Write reserved RWX encodings (010, 011) to spmpcfg.\n"
            "Implementation may accept or reject these (WARL field).",
        ),
    ]

    entry = 0
    # Reserved conceptual RWX=010/011 map to physical {X,W,R}=010/110.
    for rwx_val, rwx_name in [(RWX_W, "010"), (RWX_W | RWX_X, "011")]:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
        lines.extend(
            [
                f"\n# Reserved RWX={rwx_name}",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))
        lines.extend(
            [
                test_data.add_testcase(f"reserved_rwx_{rwx_name}", coverpoint, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

    # Also test SHARED=1, U=0 (reserved)
    cfg_val = RWX_R | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_SHARED)
    lines.extend(
        [
            "\n# Reserved: SHARED=1, U=0",
        ]
    )
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, cfg_val))
    lines.extend(
        [
            test_data.add_testcase("reserved_shared1_u0", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_no_match_deny_tests(test_data: TestData) -> list[str]:
    """Test that no-match causes access denial.

    Covers: cp_no_match_deny
    When S or U mode accesses memory and no SPMP entry matches but at least one
    entry is implemented, the access is denied.
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_no_match_deny"
    sel_reg, val_reg, check_reg, addr_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Verify that when no SPMP entry matches, S/U-mode access is denied.\n"
            "Leave the scratch bytes unmatched while retaining explicit resident rules\n"
            "for test code and trap-handler data, then load from scratch.",
        ),
        "RVTEST_GOTO_MMODE",
    ]

    # Entry 0 permits S-mode below scratch, which contains the test and S-mode
    # trap-handler code. Entry 1 is OFF but supplies the lower TOR bound for
    # entry 2. Entry 2 permits memory above the 264-byte scratch region, which
    # includes trap save areas and signatures. The scratch bytes themselves
    # match no entry once the catch-all entry is disabled.
    resident_cfg = RWX_RWX | (A_TOR << SPMPCFG_A_LO)
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"srli x{addr_reg}, x{addr_reg}, 2",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE:x})",
            f"CSRW(miselect, x{sel_reg})",
            f"CSRW(mireg, x{addr_reg})  # entry 0 TOR top = scratch",
            f"LI(x{val_reg}, 0x{resident_cfg:x})",
            f"CSRW(mireg2, x{val_reg})",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + 1:x})",
            f"CSRW(miselect, x{sel_reg})",
            f"addi x{addr_reg}, x{addr_reg}, {264 // 4}",
            f"CSRW(mireg, x{addr_reg})  # entry 1 boundary = scratch + 264",
            "CSRW(mireg2, zero)  # entry 1 OFF: leave scratch unmatched",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + 2:x})",
            f"CSRW(miselect, x{sel_reg})",
            f"LI(x{val_reg}, -1)",
            f"CSRW(mireg, x{val_reg})  # entry 2 TOR top = maximum address",
            f"LI(x{val_reg}, 0x{resident_cfg:x})",
            f"CSRW(mireg2, x{val_reg})",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + BASELINE_ENTRY:x})",
            f"CSRW(miselect, x{sel_reg})",
            "CSRW(mireg2, zero)  # temporarily disable the catch-all entry",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
            "sfence.vma x0, x0",
            test_data.add_testcase("no_match_load_fault", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})  # no matching entry: load page fault",
            "nop  # trap handler resumes here",
            "RVTEST_GOTO_MMODE",
        ]
    )

    # Restore the catch-all before clearing the temporary TOR entries.
    lines.extend(
        [
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + BASELINE_ENTRY:x})",
            f"CSRW(miselect, x{sel_reg})",
            f"LI(x{val_reg}, -1)",
            f"CSRW(mireg, x{val_reg})",
            f"LI(x{val_reg}, 0x{BASELINE_CFG:x})",
            f"CSRW(mireg2, x{val_reg})",
        ]
    )
    for entry in range(3):
        lines.extend(
            [
                f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + entry:x})",
                f"CSRW(miselect, x{sel_reg})",
                "CSRW(mireg2, zero)",
                "CSRW(mireg, zero)",
            ]
        )
    lines.extend(["sfence.vma x0, x0", "RVTEST_GOTO_LOWER_MODE Smode"])

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg])
    return lines


def _generate_priority_match_tests(test_data: TestData) -> list[str]:
    """Test priority matching: lowest-numbered entry wins.

    Covers: cp_priority_match
    """
    covergroup = "SspmpSm_addr_cg"
    coverpoint = "cp_priority_match"
    sel_reg, val_reg, check_reg, addr_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test that lowest-numbered matching SPMP entry determines access.\n"
            "Configure overlapping entries with different permissions.",
        ),
    ]

    # Install known data before the higher-priority entry removes read access.
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{val_reg}, 0x13579BDF)",
            f"sw x{val_reg}, 0(x{addr_reg})",
            f"srli x{addr_reg}, x{addr_reg}, 2  # 8-byte NAPOT region",
        ]
    )

    # Entry 0: matching S-mode rule with no permissions.
    lines.extend(_spmp_select(0, sel_reg))
    lines.extend(
        [
            f"CSRW(0x151, x{addr_reg})",
            "nop",
        ]
    )
    cfg_no_perm = A_NAPOT << SPMPCFG_A_LO
    lines.extend(_spmp_write_cfg(val_reg, cfg_no_perm))

    # Entry 1: same address range, with read/write permissions.
    lines.extend(_spmp_select(1, sel_reg))
    lines.extend(
        [
            f"CSRW(0x151, x{addr_reg})",
            "nop",
        ]
    )
    cfg_rw = RWX_RW | (A_NAPOT << SPMPCFG_A_LO)
    lines.extend(_spmp_write_cfg(val_reg, cfg_rw))

    # Keep siselect on entry 0 so the coverpoint's selected-entry proxy agrees
    # with the rule expected to win.
    lines.extend(_spmp_select(0, sel_reg))
    lines.extend(
        [
            _sfence_vma(),
            "# Entry 0 matches first, so the load must fault despite entry 1 allowing it",
            test_data.add_testcase("priority_entry0_wins_deny", coverpoint, covergroup),
            test_data.add_testcase("match_ignores_entry0_permissions", "cp_match_irrespective_perm_bits", covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})",
            "nop  # trap handler resumes here",
        ]
    )

    # Disable entry 0. Entry 1 now becomes the first match and the same load
    # must succeed.
    lines.extend(_spmp_select(0, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_select(1, sel_reg))
    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase("priority_entry1_allows_after_entry0_off", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    for e in range(2):
        lines.extend(_spmp_select(e, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, 0))
        lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg])
    return lines


def _generate_mmode_bypass_tests(test_data: TestData) -> list[str]:
    """Test that M-mode bypasses SPMP.

    Covers: cp_mmode_bypass
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_mmode_bypass"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Verify M-mode memory access is allowed regardless of SPMP.\n"
            "Configure SPMP to deny all access, then do M-mode access.",
        ),
    ]

    # Go to M-mode for this test
    lines.append("RVTEST_GOTO_MMODE")

    # Configure entry 0 with deny-all for S/U via miselect
    lines.extend(
        [
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE:x})",
            f"CSRW(miselect, x{sel_reg})  # miselect = SPMP entry 0",
            "nop",
        ]
    )
    # NAPOT covering a wide range, no permissions
    napot_wide = (0x80000000 >> 2) | 0xFFF
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{napot_wide:x})",
            f"CSRW(mireg, x{val_reg})  # write spmpaddr via mireg",
            "nop",
        ]
    )
    cfg_deny = A_NAPOT << SPMPCFG_A_LO  # RWX=000, U=0: denies S/U
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_deny:x})",
            f"CSRW(mireg2, x{val_reg})  # write spmpcfg via mireg2",
            "nop",
            "sfence.vma x0, x0",
        ]
    )

    # M-mode access should still succeed
    lines.extend(
        [
            test_data.add_testcase("mmode_bypass_load", coverpoint, covergroup),
            f"LA(x{val_reg}, scratch)",
            f"lw x{check_reg}, 0(x{val_reg})  # M-mode load should succeed despite SPMP",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    lines.extend(
        [
            "CSRW(mireg2, zero)  # clear spmpcfg",
            "nop",
            "CSRW(mireg, zero)  # clear spmpaddr",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_mmode_indirect_access_tests(test_data: TestData) -> list[str]:
    """Test M-mode access to SPMP via miselect/mireg/mireg2.

    Covers: cp_mmode_indirect_access
    """
    covergroup = "SspmpSm_csr_cg"
    coverpoint = "cp_mmode_indirect_access"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test M-mode indirect access to SPMP CSRs via miselect/mireg/mireg2.\n"
            "M-mode uses miselect (0x350), mireg (0x351), mireg2 (0x352).",
        ),
    ]

    lines.append("RVTEST_GOTO_MMODE")

    for entry in range(NUM_TEST_ENTRIES):
        lines.extend(
            [
                f"\n# M-mode access to SPMP entry {entry}",
                f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + entry:x})",
                f"CSRW(miselect, x{sel_reg})  # miselect = SPMP entry {entry}",
                "nop",
            ]
        )

        # Write and readback spmpaddr via mireg
        addr_val = 0x90000000 + entry * 0x2000
        lines.extend(
            [
                f"LI(x{val_reg}, 0x{addr_val >> 2:x})",
                f"CSRW(mireg, x{val_reg})  # write spmpaddr via mireg",
                "nop",
                test_data.add_testcase(f"mmode_entry{entry}_addr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, ("mireg", None), test_data),
            ]
        )

        # Write and readback spmpcfg via mireg2
        cfg_val = RWX_RX | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
        lines.extend(
            [
                f"LI(x{val_reg}, 0x{cfg_val:x})",
                f"CSRW(mireg2, x{val_reg})  # write spmpcfg via mireg2",
                "nop",
                test_data.add_testcase(f"mmode_entry{entry}_cfg", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, ("mireg2", None), test_data),
            ]
        )

        # Clean up
        lines.extend(
            [
                "CSRW(mireg2, zero)",
                "nop",
                "CSRW(mireg, zero)",
                "nop",
            ]
        )

    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_mpmpdeleg_tests(test_data: TestData) -> list[str]:
    """Test mpmpdeleg.pmpnum field (Smpmpdeleg extension).

    Covers: cp_mpmpdeleg_pmpnum_field, cp_mpmpdeleg_pmpnum_zero,
            cp_mpmpdeleg_no_delegation, cp_mpmpdeleg_locked
    """
    covergroup = "SspmpSm_csr_cg"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_mpmpdeleg_pmpnum_field / cp_mpmpdeleg_locked",
            "Test mpmpdeleg CSR (Smpmpdeleg extension).\n"
            "mpmpdeleg.pmpnum[6:0] determines the delegation boundary.\n"
            "Entries >= pmpnum are delegated as SPMP entries.",
        ),
    ]

    # These tests run from M-mode
    lines.append("RVTEST_GOTO_MMODE")

    # ---------- Test pmpnum field ----------
    # The SVH defines cp_mpmpdeleg_pmpnum_field with bins
    #   zero_all_delegated / partial[4] / max_none_delegated
    # and companion cross coverpoints cp_mpmpdeleg_pmpnum_zero and
    # cp_mpmpdeleg_no_delegation.  Each test-case label below maps to a
    # coverpoint that actually exists in the SVH.
    coverpoint_field = "cp_mpmpdeleg_pmpnum_field"

    mpmpdeleg_csr = "CSR_MPMPDELEG"

    # Test writing pmpnum = 0 (all entries delegated)
    lines.extend(
        [
            "\n# pmpnum = 0 (delegate all PMP entries as SPMP)",
            f"CSRW({mpmpdeleg_csr}, zero)",
            "nop",
            test_data.add_testcase("zero_all_delegated", coverpoint_field, covergroup),
            gen_csr_read_sigupd(check_reg, (mpmpdeleg_csr, None), test_data),
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + BASELINE_ENTRY:x})",
            f"CSRW(siselect, x{sel_reg})",
            test_data.add_testcase("zero_and_delegating", "cp_mpmpdeleg_pmpnum_zero", covergroup),
            gen_csr_read_sigupd(check_reg, ("0x151", None), test_data),
            "RVTEST_GOTO_MMODE",
        ]
    )

    # Distribute partial values over the implementation's writable range so
    # the four dynamic partial bins are exercised for both small and 64-entry
    # implementations admitted by the test constraint.
    partial_pmpnums = [
        ("min", "1"),
        ("quarter", "UDB_NUM_PMP_ENTRIES / 4"),
        ("half", "UDB_NUM_PMP_ENTRIES / 2"),
        ("three_quarters", "3 * UDB_NUM_PMP_ENTRIES / 4"),
        ("last", "UDB_NUM_PMP_ENTRIES - 1"),
    ]
    for pmpnum_name, pmpnum_expr in partial_pmpnums:
        lines.extend(
            [
                f"\n# partial pmpnum: {pmpnum_expr}",
                f"LI(x{val_reg}, {pmpnum_expr})",
                f"CSRW({mpmpdeleg_csr}, x{val_reg})",
                "nop",
                test_data.add_testcase(f"partial_pmpnum_{pmpnum_name}", coverpoint_field, covergroup),
                gen_csr_read_sigupd(check_reg, (mpmpdeleg_csr, None), test_data),
            ]
        )

    # Request the architectural maximum. On implementations with fewer than
    # 64 writable entries, the WARL field clamps to the writable count.
    lines.extend(
        [
            "\n# Request pmpnum = 64 (clamps to writable count; no SPMP delegation)",
            f"LI(x{val_reg}, 64)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("max_none_delegated", coverpoint_field, covergroup),
            gen_csr_read_sigupd(check_reg, (mpmpdeleg_csr, None), test_data),
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE:x})",
            f"CSRW(siselect, x{sel_reg})",
            test_data.add_testcase("max_no_deleg_reads_zero", "cp_mpmpdeleg_no_delegation", covergroup),
            gen_csr_read_sigupd(check_reg, ("0x151", None), test_data),
            "RVTEST_GOTO_MMODE",
        ]
    )

    # Test writing pmpnum > 64 (should clamp to max)
    lines.extend(
        [
            "\n# pmpnum = 100 (should clamp to number of writable entries)",
            f"LI(x{val_reg}, 100)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("clamp_pmpnum_100", coverpoint_field, covergroup),
            gen_csr_read_sigupd(check_reg, (mpmpdeleg_csr, None), test_data),
        ]
    )

    # ---------- Test locked PMP constraint ----------
    coverpoint = "cp_mpmpdeleg_locked"

    # Lock PMP entry 7, then try to set pmpnum < 8
    lines.extend(
        [
            comment_banner(
                coverpoint,
                "Lock PMP entry 7, then try to set pmpnum < 8.\nShould be rejected (pmpnum retains prior value).",
            ),
            "",
            "# Lock PMP[7]",
            f"LI(x{sel_reg}, -1)",
            f"CSRW(pmpaddr7, x{sel_reg})  # deterministic maximal NAPOT region",
            f"LI(x{val_reg}, 0x{0x80 | (A_NAPOT << 3) | RWX_RWX:x})  # L=1, A=NAPOT, RWX",
        ]
    )

    # pmpcfg1 on RV64 holds cfg for entries 8-15, pmpcfg0 for 0-7
    # PMP[7] cfg is byte 7 of pmpcfg0 (RV64)
    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f"CSRR(x{check_reg}, pmpcfg0)",
            "nop",
            f"li x{sel_reg}, 0xFF",
            f"slli x{sel_reg}, x{sel_reg}, 56  # mask for byte 7 (entry 7)",
            f"not x{sel_reg}, x{sel_reg}",
            f"and x{check_reg}, x{check_reg}, x{sel_reg}  # clear byte 7",
            f"slli x{val_reg}, x{val_reg}, 56  # shift cfg to byte 7",
            f"or x{check_reg}, x{check_reg}, x{val_reg}",
            f"CSRW(pmpcfg0, x{check_reg})",
            "nop",
            "#else",
            f"CSRR(x{check_reg}, pmpcfg1)",
            "nop",
            f"li x{sel_reg}, 0xFF",
            f"slli x{sel_reg}, x{sel_reg}, 24  # mask for byte 3 (entry 7)",
            f"not x{sel_reg}, x{sel_reg}",
            f"and x{check_reg}, x{check_reg}, x{sel_reg}  # clear byte 3",
            f"slli x{val_reg}, x{val_reg}, 24  # shift cfg to byte 3",
            f"or x{check_reg}, x{check_reg}, x{val_reg}",
            f"CSRW(pmpcfg1, x{check_reg})",
            "nop",
            "#endif",
        ]
    )

    # Move to the lowest boundary permitted by locked PMP[7]. Starting below
    # the maximum makes the following request for 64 observably succeed rather
    # than merely retaining an already-maximal WARL value.
    lines.extend(
        [
            f"\nLI(x{val_reg}, 8)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
        ]
    )

    # Request the architectural maximum. Implementations with fewer than 64
    # writable entries clamp it to their writable count; either result means
    # no SPMP entries are delegated and remains legal with PMP[7] locked.
    lines.extend(
        [
            f"\nLI(x{val_reg}, 64)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("locked_pmpnum_max_ok", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, (mpmpdeleg_csr, None), test_data),
        ]
    )

    # Try pmpnum = 4 (should be rejected because PMP[7] is locked)
    lines.extend(
        [
            f"\nLI(x{val_reg}, 4)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("locked_pmpnum_4_rejected", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, (mpmpdeleg_csr, None), test_data),
        ]
    )

    # PMP[7].L cannot be cleared without reset, so pmpnum cannot be restored
    # below 8. This generator must remain the final SPMP sub-test; it leaves
    # delegation disabled and returns to S-mode with Sspmp effectively off.
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_sfence_ordering_tests(test_data: TestData) -> list[str]:
    """Test SFENCE.VMA ordering of SPMP CSR writes (Spec §2.7).

    Covers: cp_sfence_ordering

    Per the spec: "Indirect accesses to SPMP CSRs are not ordered with respect
    to each other or with subsequent memory accesses. To enforce ordering ...
    software must execute an SFENCE.VMA instruction with rs1=x0 and rs2=x0,
    which synchronizes subsequent memory accesses with all preceding SPMP CSR
    writes."

    The test exercises this sequence: select an SPMP entry, write spmpaddr +
    spmpcfg via sireg / sireg2, issue SFENCE.VMA x0,x0, then perform a
    readback.  The coverpoint samples SFENCE.VMA whose previous instruction
    targeted an SPMP siselect value.
    """
    covergroup = "SspmpSm_csr_cg"
    coverpoint = "cp_sfence_ordering"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "SFENCE.VMA x0,x0 orders preceding SPMP CSR writes against subsequent\n"
            "S/U-mode memory accesses (Spec §2.7).  Exercise the ordering sequence\n"
            "for several SPMP entries / configurations.",
        ),
    ]

    for entry in range(NUM_TEST_ENTRIES):
        lines.append(f"\n# === Ordering sequence for SPMP entry {entry} ===")
        lines.extend(_spmp_select(entry, sel_reg))

        # Write spmpaddr via sireg
        addr_val = (0x80000000 + entry * 0x1000) >> 2
        lines.extend(_spmp_write_addr(val_reg, addr_val))

        # Write spmpcfg via sireg2 (NAPOT + RW + U)
        cfg_val = (1 << SPMPCFG_R) | (1 << SPMPCFG_W) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))

        # Repeat the cfg write without an intervening nop so the trace can
        # directly associate the preceding indirect write with SFENCE.VMA.
        lines.append(f"CSRW(0x152, x{val_reg})")

        # Label and issue SFENCE.VMA x0,x0. This is the instruction
        # cp_sfence_ordering samples after the SPMP CSR write above.
        lines.append(test_data.add_testcase(f"entry{entry}_sfence_after_cfg", coverpoint, covergroup))
        lines.append(_sfence_vma())
        lines.append(_spmp_read_cfg_sigupd(check_reg, test_data))

    # Clean up: zero the last touched entry
    lines.extend(_spmp_select(NUM_TEST_ENTRIES - 1, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_satp_bare_spmp_tests(test_data: TestData) -> list[str]:
    """Test that SPMP is active when satp.mode == Bare.

    Covers: cp_satp_bare_spmp
    """
    covergroup = "SspmpSm_paging_cg"
    coverpoint = "cp_satp_bare_spmp"
    check_reg = test_data.int_regs.get_registers(1, exclude_regs=[0])[0]

    lines = [
        comment_banner(
            coverpoint,
            "Verify SPMP and paging are mutually exclusive.\n"
            "When satp.mode == Bare, SPMP provides isolation.\n"
            "Read satp to confirm Bare mode.",
        ),
    ]

    # Read satp to verify mode
    lines.extend(
        [
            "# Read satp to confirm Bare mode (required for SPMP)",
            test_data.add_testcase("satp_bare_mode", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("satp", None), test_data),
        ]
    )

    # Also test from M-mode
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            test_data.add_testcase("satp_bare_mmode_check", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("satp", None), test_data),
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([check_reg])
    return lines


def _generate_spmp_fault_tests(test_data: TestData) -> list[str]:
    """Test SPMP fault exception codes.

    Covers: cp_spmp_fault_instr, cp_spmp_fault_load, cp_spmp_fault_store
    SPMP violations use page fault exception codes (12, 13, 15).
    """
    covergroup = "SspmpSm_perm_cg"
    sel_reg, val_reg, check_reg, addr_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_spmp_fault_{instr,load,store}",
            "Test that SPMP violations generate the correct page fault exception codes.\n"
            "Exception code 12 = instruction page fault\n"
            "Exception code 13 = load page fault\n"
            "Exception code 15 = store/AMO page fault",
        ),
    ]

    # ---------- Setup: configure SPMP to protect a region ----------
    # S-mode setup: create an S-mode-only rule that allows S-mode access (U denied)
    entry = 0
    lines.extend(_spmp_select(entry, sel_reg))

    # Use only the first 8 bytes of scratch so trap-handler save areas remain
    # accessible through the resident catch-all rule.
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"srli x{addr_reg}, x{addr_reg}, 2  # convert to spmpaddr format",
            "# No low bits set: 8-byte NAPOT region",
            f"CSRW(0x151, x{addr_reg})  # write spmpaddr via sireg",
            "nop",
        ]
    )

    # S-mode only (U=0, SHARED=0), RWX=111 -> S-mode gets full access, U-mode denied
    cfg_val = RWX_RWX | (A_NAPOT << SPMPCFG_A_LO)  # U=0, SHARED=0
    lines.extend(_spmp_write_cfg(val_reg, cfg_val))
    lines.append(_sfence_vma())

    # ---------- Test load page fault from S-mode (should succeed) ----------
    coverpoint = "cp_spmp_fault_load"
    lines.extend(
        [
            "",
            "# S-mode load to S-mode-only region should succeed",
            test_data.add_testcase("smode_load_ok", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )

    # ---------- Test store page fault ----------
    coverpoint = "cp_spmp_fault_store"
    lines.extend(
        [
            "",
            "# S-mode store to S-mode-only region should succeed",
            test_data.add_testcase("smode_store_ok", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{val_reg}, 0xCAFEBABE)",
            f"sw x{val_reg}, 0(x{addr_reg})",
            "nop",
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
        ]
    )

    # ---------- Now reconfigure to deny S-mode to test fault generation ----------
    # Install a safe target in case a broken implementation incorrectly allows
    # the later fetch, then go to M-mode to reconfigure.
    lines.extend(
        [
            "",
            f"LI(x{val_reg}, 0x00008067)  # ret",
            f"LA(x{addr_reg}, scratch)",
            f"sw x{val_reg}, 0(x{addr_reg})",
            "fence.i",
            "RVTEST_GOTO_MMODE",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + entry:x})",
            f"CSRW(miselect, x{sel_reg})",
            "nop",
        ]
    )

    # U-mode only (U=1), RWX=000 -> both U and S get no permissions
    cfg_deny = (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # U=1, RWX=000
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_deny:x})",
            f"CSRW(mireg2, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
            _sfence_vma(),
        ]
    )

    # S-mode instruction fetch from a region without execute permission should fault.
    lines.extend(
        [
            "",
            "# S-mode fetch from U-mode region with no perms -> instruction page fault (12)",
            test_data.add_testcase("smode_instr_fault", "cp_spmp_fault_instr", covergroup),
            "LI(x4, 0xACCE)  # SKIP_MEPC sentinel; fetch-fault handler resumes at ra",
            f"LA(x{addr_reg}, scratch)",
            f"jalr x1, 0(x{addr_reg})  # should cause instruction page fault",
            "nop",
        ]
    )

    # S-mode load to region with no permissions should fault
    coverpoint = "cp_spmp_fault_load"
    lines.extend(
        [
            "",
            "# S-mode load with SUM=0 to U-mode region with no perms -> page fault (13)",
            test_data.add_testcase("smode_load_fault", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"lw x{check_reg}, 0(x{addr_reg})  # should cause load page fault",
            "nop  # trap handler skips this",
        ]
    )

    # S-mode store to region with no permissions should fault
    coverpoint = "cp_spmp_fault_store"
    lines.extend(
        [
            "",
            "# S-mode store to U-mode region with no perms -> page fault (15)",
            test_data.add_testcase("smode_store_fault", coverpoint, covergroup),
            f"LA(x{addr_reg}, scratch)",
            f"sw x{val_reg}, 0(x{addr_reg})  # should cause store page fault",
            "nop  # trap handler skips this",
        ]
    )

    # ---------- Clean up ----------
    lines.extend(
        [
            "",
            "RVTEST_GOTO_MMODE",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + entry:x})",
            f"CSRW(miselect, x{sel_reg})",
            "nop",
            "CSRW(mireg2, zero)",
            "nop",
            "CSRW(mireg, zero)",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg])
    return lines


def _generate_spmp_entry_tor_entry0_tests(test_data: TestData) -> list[str]:
    """Test TOR mode with entry 0 (base = 0).

    Covers: cp_addr_match_tor_entry0
    When spmpcfg[0].A == TOR, the lower bound is 0.
    """
    covergroup = "SspmpSm_addr_cg"
    coverpoint = "cp_addr_match_tor_entry0"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "TOR entry 0 (base = 0)",
            "When entry 0 uses TOR mode, the lower bound is implicitly 0.\nThe range is [0, spmpaddr[0]).",
        ),
    ]

    # Configure entry 0 with TOR
    lines.extend(_spmp_select(0, sel_reg))
    top_addr = 0x80010000
    lines.extend(_spmp_write_addr(val_reg, top_addr >> 2))
    cfg_tor_e0 = (1 << SPMPCFG_R) | (1 << SPMPCFG_W) | (A_TOR << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(_spmp_write_cfg(val_reg, cfg_tor_e0))
    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase("tor_on_entry0", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_spmpen_tests(test_data: TestData) -> list[str]:
    """Test spmpen CSR (Sspmpen extension) for per-entry enable control.

    Covers:
    - cp_spmpen_readwrite: Basic read/write of spmpen
    - cp_spmpen_activation: Entry active iff spmpen[i] & spmpcfg[i].A != 0
    - cp_spmpen_locked_readonly: spmpen[i] is read-only when spmpcfg[i].L == 1
    """
    covergroup = "SspmpSm_spmpen_cg"
    sel_reg, val_reg, check_reg, save_reg, save_high_reg, addr_reg = test_data.int_regs.get_registers(
        6, exclude_regs=[0]
    )

    lines = [
        comment_banner(
            "Sspmpen: spmpen CSR tests",
            "Test the spmpen register (Sspmpen extension).\n"
            "spmpen[i] controls whether SPMP entry i is active.\n"
            "An entry is active only when spmpen[i] & spmpcfg[i].A != 0.\n"
            "When spmpcfg[i].L == 1, spmpen[i] becomes read-only.",
        ),
        # Basic WARL probing includes spmpen=0. Run it in M-mode so disabling
        # the resident entry cannot fault the test's own instruction fetches.
        "RVTEST_GOTO_MMODE",
    ]

    # ---------- Basic read/write ----------
    coverpoint = "cp_spmpen_readwrite"

    # Save current spmpen (S-mode CSR, accessible from S-mode)
    lines.extend(
        [
            f"CSRR(x{save_reg}, CSR_SPMPEN)  # save spmpen",
            "nop",
            "#if __riscv_xlen == 32",
            f"CSRR(x{save_high_reg}, CSR_SPMPENH)  # save upper 32 bits",
            "nop",
            "#endif",
        ]
    )

    # Write all-ones and read back (WARL)
    lines.extend(
        [
            "\n# Write all-ones to spmpen, read back (WARL register)",
            f"LI(x{val_reg}, -1)  # all ones",
            f"CSRW(CSR_SPMPEN, x{val_reg})",
            "nop",
            test_data.add_testcase("spmpen_write_allones", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
        ]
    )

    # Write zero and read back
    lines.extend(
        [
            "\n# Write zero to spmpen (disable all entries)",
            "CSRW(CSR_SPMPEN, zero)",
            "nop",
            test_data.add_testcase("spmpen_write_zero", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
        ]
    )

    # Write specific bit patterns
    for bit in [0, 1, 2, 3]:
        mask = 1 << bit
        lines.extend(
            [
                f"\n# Enable only entry {bit}",
                f"LI(x{val_reg}, {mask})",
                f"CSRW(CSR_SPMPEN, x{val_reg})",
                "nop",
                test_data.add_testcase(f"spmpen_bit{bit}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
            ]
        )

    lines.extend(
        [
            "#if __riscv_xlen == 32",
            "\n# Probe the RV32 alias for spmpen[63:32]",
            f"LI(x{val_reg}, -1)",
            f"CSRW(CSR_SPMPENH, x{val_reg})",
            "nop",
            test_data.add_testcase("spmpenh_write_allones", "cp_spmpenh_readwrite", covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPENH", None), test_data),
            "CSRW(CSR_SPMPENH, zero)",
            "nop",
            test_data.add_testcase("spmpenh_write_zero", "cp_spmpenh_readwrite", covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPENH", None), test_data),
            f"CSRW(CSR_SPMPENH, x{save_high_reg})  # restore upper 32 bits",
            "#endif",
            f"CSRW(CSR_SPMPEN, x{save_reg})  # restore resident entry before returning to S-mode",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    # ---------- Activation logic: entry active iff spmpen[i] & A != 0 ----------
    coverpoint = "cp_spmpen_activation"
    entry = 0

    # Configure entry 0 as a deny rule over scratch. Toggling spmpen[0]
    # therefore produces an observable allow/fault distinction against the
    # lower-priority resident rule.
    cfg_napot_deny = A_NAPOT << SPMPCFG_A_LO

    lines.extend(
        [
            comment_banner(
                coverpoint,
                "Verify entry activation depends on spmpen[i] & spmpcfg[i].A.\n"
                "Configure entry 0 as a deny rule over scratch, then toggle spmpen[0]\n"
                "and perform real S-mode loads to observe allow/fault behavior.",
            ),
            "",
        ]
    )

    # Configure entry 0 via S-mode indirect CSR access (siselect/sireg/sireg2)
    lines.extend(_spmp_select(entry, sel_reg))

    # Put known data in scratch before enabling the deny rule, then configure
    # an 8-byte NAPOT region so trap-handler save areas remain resident.
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{val_reg}, 0x2468ACE0)",
            f"sw x{val_reg}, 0(x{addr_reg})",
            f"srli x{check_reg}, x{addr_reg}, 2",
            f"CSRW(0x151, x{check_reg})",
            "nop",
        ]
    )

    # Set cfg
    lines.extend(_spmp_write_cfg(val_reg, cfg_napot_deny))

    resident_mask = 1 << BASELINE_ENTRY

    # Disable entry 0 while keeping the resident entry active.
    lines.extend(
        [
            "\n# Disable entry 0 via spmpen[0] = 0",
            f"LI(x{val_reg}, 0x{resident_mask:x})",
            f"CSRW(CSR_SPMPEN, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            test_data.add_testcase("spmpen_entry0_disabled", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
            test_data.add_testcase("disabled_napot_load_allowed", coverpoint, covergroup),
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
        ]
    )

    # Enable entry 0 while keeping the resident entry active.
    lines.extend(
        [
            "\n# Enable entry 0 via spmpen[0] = 1",
            f"LI(x{val_reg}, 0x{resident_mask | 1:x})",
            f"CSRW(CSR_SPMPEN, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            test_data.add_testcase("spmpen_entry0_enabled", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
            test_data.add_testcase("enabled_napot_load_denied", coverpoint, covergroup),
            f"lw x{check_reg}, 0(x{addr_reg})",
            "nop  # trap handler resumes here",
        ]
    )

    # Verify: when A=OFF, spmpen[0]=1 should still not activate entry
    lines.extend(
        [
            "\n# Set A=OFF (disable), spmpen[0]=1 -> entry still inactive",
            "CSRW(0x152, zero)  # spmpcfg.A=OFF via sireg2",
            "nop",
            f"LI(x{val_reg}, 0x{resident_mask | 1:x})",
            f"CSRW(CSR_SPMPEN, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            test_data.add_testcase("spmpen_aoff_no_activate", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("0x152", None), test_data),
            test_data.add_testcase("enabled_off_load_allowed", coverpoint, covergroup),
            f"lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
        ]
    )

    # Clean up activation test entry 0 (S-mode)
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    # ---------- spmpen[i] read-only when locked (requires M-mode) ----------
    coverpoint = "cp_spmpen_locked_readonly"
    lock_entry = 1

    # Go to M-mode: setting/clearing L bit requires M-mode via miselect/mireg2
    lines.append("RVTEST_GOTO_MMODE")

    lines.extend(
        [
            comment_banner(
                coverpoint,
                "When spmpcfg[i].L == 1, spmpen[i] becomes read-only.\n"
                "Test: lock entry 1, then try to toggle spmpen[1].",
            ),
            "",
            # Select entry 1 via M-mode indirect access
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + lock_entry:x})",
            f"CSRW(miselect, x{sel_reg})  # miselect = SPMP entry {lock_entry}",
            "nop",
        ]
    )

    # First, set spmpen[1] = 1 BEFORE locking, so we can verify read-only behavior
    lines.extend(
        [
            "\n# Pre-set spmpen[1] = 1 before locking",
            f"LI(x{val_reg}, 0x{1 << lock_entry:x})",
            f"CSRS(CSR_SPMPEN, x{val_reg})",
            "nop",
        ]
    )

    # Configure entry 1 with L=1 (locked), A=NAPOT, R
    cfg_locked = (1 << SPMPCFG_L) | (1 << SPMPCFG_R) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_locked:x})  # L=1, R, NAPOT, U",
            f"CSRW(mireg2, x{val_reg})",
            "nop",
        ]
    )

    # Try to clear spmpen[1] (should be rejected since L=1, value stays 1)
    lines.extend(
        [
            "\n# Try to clear spmpen[1] (locked, should be rejected -> stays 1)",
            f"LI(x{val_reg}, 0x{1 << lock_entry:x})",
            f"CSRC(CSR_SPMPEN, x{val_reg})",
            "nop",
            test_data.add_testcase("locked_csrrc_attempt", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
        ]
    )

    # Try to set another bit via CSRS (should also be ignored for locked entry)
    lines.extend(
        [
            "\n# Verify spmpen[1] is still 1 (read-only when locked)",
            test_data.add_testcase("locked_bit_still_set", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, ("CSR_SPMPEN", None), test_data),
        ]
    )

    # ---------- Clean up: M-mode may clear an SPMP lock via miselect ----------
    lines.extend(
        [
            "\n# Clean up: clear locked entry config",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + lock_entry:x})",
            f"CSRW(miselect, x{sel_reg})",
            "nop",
            "CSRW(mireg2, zero)  # M-mode indirect access clears L and deactivates the entry",
            "nop",
            "CSRW(mireg, zero)",
            "nop",
            f"CSRW(CSR_SPMPEN, x{save_reg})  # restore spmpen",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg, save_high_reg, addr_reg])
    return lines


# ---------------------------------------------------------------------------
# Framework integration: register Sspmp so ``testgen testplans --extensions Sspmp`` works.
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Sspmp",
    # The combined test exercises Sspmpen (spmpen CSR) via _generate_spmpen_tests,
    # and this suite explicitly exercises the Smpmpdeleg resource-sharing profile.
    required_extensions=["Sm", "S", "Zicsr", "Smcsrind", "Sscsrind", "Sspmp", "Sspmpen", "Smpmpdeleg"],
    march_extensions=["Zicsr", "Zifencei"],
    params=["NUM_PMP_ENTRIES: '>=8'"],
    extra_defines=["#define SKIP_MEPC"],  # needed for EnforceNoX / U-mode exec-fault tests
)
def make_sspmp(test_data: TestData) -> list[TestChunk]:
    """Generate all SPMP sub-tests (combined into one file by the framework)."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []
    lines.extend(_spmp_preamble(test_data))
    # CSR Access Tests
    lines.extend(_generate_spmp_csr_indirect_access_tests(test_data))
    lines.extend(_generate_spmp_lock_tests(test_data))
    lines.extend(_generate_spmp_oob_access_tests(test_data))
    # Address Matching Tests
    lines.extend(_generate_addr_match_tests(test_data))
    lines.extend(_generate_spmp_entry_tor_entry0_tests(test_data))
    lines.extend(_generate_priority_match_tests(test_data))
    # Permission Tests
    lines.extend(_generate_permission_smode_tests(test_data))
    lines.extend(_generate_permission_umode_tests(test_data))
    lines.extend(_generate_sum_effect_tests(test_data))
    lines.extend(_generate_mxr_effect_tests(test_data))
    lines.extend(_generate_shared_rule_tests(test_data))
    lines.extend(_generate_reserved_encoding_tests(test_data))
    lines.extend(_generate_no_match_deny_tests(test_data))
    # Fault Tests
    lines.extend(_generate_spmp_fault_tests(test_data))
    # M-mode Tests
    lines.extend(_generate_mmode_bypass_tests(test_data))
    lines.extend(_generate_mmode_indirect_access_tests(test_data))
    # Sspmpen Tests
    lines.extend(_generate_spmpen_tests(test_data))
    # Ordering Tests
    lines.extend(_generate_sfence_ordering_tests(test_data))
    # Paging Tests
    lines.extend(_generate_satp_bare_spmp_tests(test_data))
    # This test permanently locks PMP[7] and must remain last.
    lines.extend(_generate_mpmpdeleg_tests(test_data))
    tc.code.extend(lines)
    return [test_data.end_test_chunk()]


# ---------------------------------------------------------------------------
# Standalone Sspmp test generation (separate files, no "-00" suffix)
# Run: uv run python generators/testgen/src/testgen/priv/extensions/SspmpSm.py tests
# ---------------------------------------------------------------------------

_SIGUPD_MARGIN = 10

# (filename_stem, generator_function, extra_required_extensions) for each sub-test.
# Every test explicitly uses Smpmpdeleg to allocate the shared PMP/SPMP resource.
# Sspmpen remains optional and is declared only by tests that access spmpen.
_SSPMP_SUB_TESTS: list[tuple[str, Callable[[TestData], list[str]], list[str]]] = [
    ("SspmpSmCsrAccess", _generate_spmp_csr_indirect_access_tests, []),
    ("SspmpSmLock", _generate_spmp_lock_tests, []),
    ("SspmpSmOobAccess", _generate_spmp_oob_access_tests, []),
    ("SspmpSmAddrMatch", _generate_addr_match_tests, []),
    ("SspmpSmTorEntry0", _generate_spmp_entry_tor_entry0_tests, []),
    ("SspmpSmPriority", _generate_priority_match_tests, []),
    ("SspmpSmPermSmode", _generate_permission_smode_tests, []),
    ("SspmpSmPermUmode", _generate_permission_umode_tests, []),
    ("SspmpSmSum", _generate_sum_effect_tests, []),
    ("SspmpSmMxr", _generate_mxr_effect_tests, []),
    ("SspmpSmShared", _generate_shared_rule_tests, []),
    ("SspmpSmReserved", _generate_reserved_encoding_tests, []),
    ("SspmpSmNoMatch", _generate_no_match_deny_tests, []),
    ("SspmpSmFault", _generate_spmp_fault_tests, []),
    ("SspmpSmMmodeBypass", _generate_mmode_bypass_tests, []),
    ("SspmpSmMmodeAccess", _generate_mmode_indirect_access_tests, []),
    ("SspmpSmMpmpdeleg", _generate_mpmpdeleg_tests, []),
    ("SspmpSmSpmpen", _generate_spmpen_tests, ["Sspmpen"]),
    ("SspmpSmSfence", _generate_sfence_ordering_tests, []),
    ("SspmpSmSatpBare", _generate_satp_bare_spmp_tests, []),
]


def _generate_single_test(
    name: str,
    generator_fn: Callable[[TestData], list[str]],
    output_dir: Path,
    extra_required_extensions: list[str] | None = None,
) -> None:
    """Generate a single Sspmp sub-test .S file."""
    required_exts = ["Sm", "S", "Zicsr", "Smcsrind", "Sscsrind", "Sspmp", "Smpmpdeleg"]
    if extra_required_extensions:
        required_exts = required_exts + list(extra_required_extensions)
    test_config = TestConfig(
        xlen=0,
        flen=64,
        testsuite=name,
        E_ext=False,
        required_extensions=required_exts,
        # Zifencei is needed by SspmpSmSum / SspmpSmPermUmode which use fence.i
        # to sync the icache after writing the jalr target for fetch-fault tests.
        # It is harmless for sub-tests that do not issue fence.i.
        march_extensions=["Zicsr", "Zifencei"],
        extra_params=["NUM_PMP_ENTRIES: '>=8'"],
    )

    test_data = TestData(test_config)
    tc = test_data.begin_test_chunk()
    test_data.int_regs.consume_registers([1])
    seed(reproducible_hash(name))

    # Every standalone test exercises the Smpmpdeleg sharing profile and needs
    # a resident entry before it returns to S-mode.
    body_lines = _spmp_preamble(test_data) + generator_fn(test_data)

    test_data.int_regs.return_register(1)
    tc.code.extend(body_lines)
    tc = test_data.end_test_chunk()

    # Assemble the .S file
    filename = f"{name}.S"
    sigupd_count = _SIGUPD_MARGIN + tc.sigupd_count

    test_file_relative = Path("Sspmp") / filename
    # SKIP_MEPC enables the trap handler's fetch-fault recovery path used by
    # EnforceNoX / U-mode exec-fault tests (x4 = 0xACCE sentinel + jalr).  It
    # is a no-op unless the test sets x4 = 0xACCE immediately before the
    # faulting fetch, so it is safe to include globally.
    extra_defines = ["#define RVTEST_PRIV_TEST", "#define SKIP_MEPC"]
    header = insert_header_template(test_config, test_file_relative, sigupd_count, extra_defines)

    body = "\n".join(indent_asm(line) for line in "\n".join(tc.code).split("\n"))

    test_data_section = generate_test_data_section(list(tc.data_values), test_config.xlen, test_config.flen)
    test_string_section = generate_test_string_section(list(tc.data_strings))
    footer = insert_footer_template(test_data_section, test_string_section)

    test_string = f"{header}\n{body}\n{footer}"
    test_file = output_dir / filename
    if not test_file.exists() or test_file.read_text() != test_string:
        test_file.write_text(test_string)

    test_data.destroy()


def generate_sspmp_tests(output_dir: Path) -> None:
    """Generate all Sspmp sub-tests as individual .S files under *output_dir*/priv/Sspmp/."""
    sspmp_dir = output_dir / "priv" / "Sspmp"
    sspmp_dir.mkdir(parents=True, exist_ok=True)
    for name, gen_fn, extra_exts in _SSPMP_SUB_TESTS:
        _generate_single_test(name, gen_fn, sspmp_dir, extra_exts)
    print(f"Generated {len(_SSPMP_SUB_TESTS)} Sspmp test files in {sspmp_dir}")


# Run: uv run python generators/testgen/src/testgen/priv/extensions/SspmpSm.py tests
# This will generate separate .S files for each Sspmp sub-test under tests/priv/Sspmp/.
if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests")
    generate_sspmp_tests(output)
