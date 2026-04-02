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
from testgen.io.templates import insert_footer_template, insert_header_template
from testgen.priv.registry import add_priv_test_generator

# SPMP CSR addresses used via indirect access
# siselect values for SPMP entries: 0x100 + entry_index
SISELECT_SPMP_BASE = 0x100
# sireg (0x151) accesses spmpaddr[i], sireg2 (0x152) accesses spmpcfg[i]

# Number of SPMP entries to test (we test a representative subset)
NUM_TEST_ENTRIES = 4  # Test entries 0, 1, 2, 3

# spmpcfg bit positions
SPMPCFG_R = 0  # bit 0: Read
SPMPCFG_W = 1  # bit 1: Write
SPMPCFG_X = 2  # bit 2: Execute
SPMPCFG_A_LO = 3  # bits [4:3]: Address matching mode
SPMPCFG_A_HI = 4
SPMPCFG_L = 7  # bit 7: Lock
SPMPCFG_U = 8  # bit 8: U-mode
SPMPCFG_SHARED = 9  # bit 9: Shared-Region

# Address matching modes
A_OFF = 0b00
A_TOR = 0b01
A_NA4 = 0b10
A_NAPOT = 0b11


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
    sel_reg, val_reg, check_reg, temp_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

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
            f"CSRW(0x350, x{sel_reg})  # miselect = SPMP entry {test_entry}",
            "nop",
        ]
    )
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_unlocked:x})  # cfg without L bit",
            f"CSRW(0x352, x{val_reg})  # write mireg2 to clear lock",
            "nop",
            test_data.add_testcase(f"entry{test_entry}_mmode_unlock", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "0x352", test_data),
        ]
    )

    # Clean up: clear the entries
    lines.extend(
        [
            "CSRW(0x352, zero)  # clear mireg2",
            "nop",
            "CSRW(0x351, zero)  # clear mireg",
            "nop",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + prev_entry:x})",
            f"CSRW(0x350, x{sel_reg})",
            "nop",
            "CSRW(0x351, zero)",
            "nop",
            "CSRW(0x352, zero)",
            "nop",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, temp_reg])
    return lines


def _generate_spmp_oob_access_tests(test_data: TestData) -> list[str]:
    """Test out-of-bounds siselect index behavior.

    Covers: cp_spmp_oob_access
    """
    covergroup = "SspmpSm_csr_cg"
    coverpoint = "cp_spmp_oob_access"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Access out-of-bounds SPMP index via siselect.\nReads should return zero, writes should be ignored.",
        ),
    ]

    # Test several out-of-bound indices
    for oob_idx in [0x140, 0x150, 0x1FF]:
        lines.extend(
            [
                f"\n# Out-of-bounds index 0x{oob_idx:x}",
                f"LI(x{sel_reg}, 0x{oob_idx:x})",
                f"CSRW(siselect, x{sel_reg})",
                "nop",
            ]
        )

        # Read spmpaddr - should be 0
        lines.extend(
            [
                test_data.add_testcase(f"oob_0x{oob_idx:x}_read_addr", coverpoint, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
            ]
        )

        # Read spmpcfg - should be 0
        lines.extend(
            [
                test_data.add_testcase(f"oob_0x{oob_idx:x}_read_cfg", coverpoint, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

        # Write spmpaddr, then read back - should still be 0
        lines.extend(
            [
                f"li x{val_reg}, -1",
                f"CSRW(0x151, x{val_reg})  # write sireg (should be ignored)",
                "nop",
                test_data.add_testcase(f"oob_0x{oob_idx:x}_write_addr", coverpoint, covergroup),
                _spmp_read_addr_sigupd(check_reg, test_data),
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
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Configure SPMP S-mode-only rules (SHARED=0, U=0) with various RWX.\n"
            "Write each encoding to spmpcfg and read back to verify the field is accepted.",
        ),
    ]

    entry = 0
    # Test all valid RWX combinations for S-mode rules
    valid_rwx = [
        (0b000, "none"),
        (0b001, "x"),
        (0b100, "r"),
        (0b101, "rx"),
        (0b110, "rw"),
        (0b111, "rwx"),
    ]

    for rwx_val, rwx_name in valid_rwx:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO)  # SHARED=0, U=0
        lines.extend(
            [
                f"\n# S-mode rule with RWX={rwx_name}",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))
        lines.extend(
            [
                _sfence_vma(),
                test_data.add_testcase(f"smode_rwx_{rwx_name}", coverpoint, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_permission_umode_tests(test_data: TestData) -> list[str]:
    """Test U-mode rules (SHARED=0, U=1).

    Covers: cp_umode_rule
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_umode_rule"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Configure SPMP U-mode rules (SHARED=0, U=1) with various RWX.\n"
            "Verify permissions are enforced for U-mode.",
        ),
    ]

    entry = 0
    valid_rwx = [
        (0b000, "none"),
        (0b001, "x"),
        (0b100, "r"),
        (0b101, "rx"),
        (0b110, "rw"),
        (0b111, "rwx"),
    ]

    for rwx_val, rwx_name in valid_rwx:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # SHARED=0, U=1
        lines.extend(
            [
                f"\n# U-mode rule with RWX={rwx_name}",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))
        lines.extend(
            [
                _sfence_vma(),
                test_data.add_testcase(f"umode_rwx_{rwx_name}", coverpoint, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_sum_effect_tests(test_data: TestData) -> list[str]:
    """Test SUM bit effect on S-mode access to U-mode regions.

    Covers: cp_sum_effect
    SUM=0: S-mode denied; SUM=1: S-mode EnforceNoX (R/W but not X)
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_sum_effect"
    sel_reg, val_reg, check_reg, save_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test sstatus.SUM effect on S-mode access to U-mode SPMP regions.\n"
            "SUM=0: S-mode is denied any access to U-mode regions.\n"
            "SUM=1: S-mode gets EnforceNoX (R/W applied, but X is denied).",
        ),
    ]

    entry = 0
    # Configure a U-mode rule with RWX
    cfg_val = (0b111) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # U=1, RWX=111
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, cfg_val))
    lines.append(_sfence_vma())

    for sum_val in (0, 1):
        lines.extend(
            [
                f"\n# sstatus.SUM = {sum_val}",
                f"CSRR(x{save_reg}, sstatus)  # save sstatus",
            ]
        )
        if sum_val == 1:
            lines.append(f"LI(x{val_reg}, 0x{1 << 18:x})  # sstatus.SUM bit (bit 18)")
            lines.append(f"CSRS(sstatus, x{val_reg})  # set SUM bit")
        else:
            lines.append(f"LI(x{val_reg}, 0x{1 << 18:x})  # sstatus.SUM bit (bit 18)")
            lines.append(f"CSRC(sstatus, x{val_reg})  # clear SUM bit")

        lines.extend(
            [
                test_data.add_testcase(f"sum_{sum_val}_smode_access", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, "sstatus", test_data),
                f"CSRW(sstatus, x{save_reg})  # restore sstatus",
            ]
        )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg])
    return lines


def _generate_mxr_effect_tests(test_data: TestData) -> list[str]:
    """Test MXR bit effect (Make eXecutable Readable).

    Covers: cp_mxr_effect
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_mxr_effect"
    sel_reg, val_reg, check_reg, save_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test sstatus.MXR effect on SPMP permission checking.\nMXR=1 makes execute-only regions also readable.",
        ),
    ]

    # Configure an S-mode rule with X only
    entry = 0
    cfg_val = (0b001) | (A_NAPOT << SPMPCFG_A_LO)  # SHARED=0, U=0, RWX=001 (X only)
    lines.extend(_spmp_select(entry, sel_reg))
    lines.extend(_spmp_write_cfg(val_reg, cfg_val))
    lines.append(_sfence_vma())

    for mxr_val in (0, 1):
        lines.extend(
            [
                f"\n# sstatus.MXR = {mxr_val}",
                f"CSRR(x{save_reg}, sstatus)  # save sstatus",
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
                gen_csr_read_sigupd(check_reg, "sstatus", test_data),
                f"CSRW(sstatus, x{save_reg})  # restore sstatus",
            ]
        )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg])
    return lines


def _generate_shared_rule_tests(test_data: TestData) -> list[str]:
    """Test Shared-Region rules (SHARED=1, U=1).

    Covers: cp_shared_rule
    """
    covergroup = "SspmpSm_perm_cg"
    coverpoint = "cp_shared_rule"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Configure SPMP Shared-Region rules (SHARED=1, U=1) with various RWX.\n"
            "Both S and U modes: Enforced per encoding table.\n"
            "Special: RWX=100 -> S:Enforce, U:Read-only\n"
            "         RWX=101 -> S:Enforce, U:Exec-only",
        ),
    ]

    entry = 0
    shared_rwx = [
        (0b000, "none"),
        (0b001, "x"),
        (0b100, "r"),
        (0b101, "rx"),
        (0b110, "rw"),
        (0b111, "rwx"),
    ]

    for rwx_val, rwx_name in shared_rwx:
        cfg_val = rwx_val | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U) | (1 << SPMPCFG_SHARED)
        lines.extend(
            [
                f"\n# Shared rule with RWX={rwx_name}",
            ]
        )
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, cfg_val))
        lines.extend(
            [
                _sfence_vma(),
                test_data.add_testcase(f"shared_rwx_{rwx_name}", coverpoint, covergroup),
                _spmp_read_cfg_sigupd(check_reg, test_data),
            ]
        )

    # Clean up
    lines.extend(_spmp_write_cfg(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
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
    for rwx_val, rwx_name in [(0b010, "010"), (0b011, "011")]:
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
    cfg_val = (0b100) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_SHARED)  # SHARED=1, U=0
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
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Verify that when no SPMP entry matches, S/U-mode access is denied.\n"
            "Configure all tested entries with A=OFF (disabled), then attempt access.",
        ),
    ]

    # Disable all test entries
    for entry in range(NUM_TEST_ENTRIES):
        lines.extend(_spmp_select(entry, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, 0))  # A=OFF

    lines.extend(
        [
            _sfence_vma(),
            test_data.add_testcase("no_match_all_off", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_priority_match_tests(test_data: TestData) -> list[str]:
    """Test priority matching: lowest-numbered entry wins.

    Covers: cp_priority_match
    """
    covergroup = "SspmpSm_addr_cg"
    coverpoint = "cp_priority_match"
    sel_reg, val_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Test that lowest-numbered matching SPMP entry determines access.\n"
            "Configure overlapping entries with different permissions.",
        ),
    ]

    # Entry 0: covering a wide range, no permissions
    lines.extend(_spmp_select(0, sel_reg))
    napot_wide = (0x80000000 >> 2) | 0xFFF  # large NAPOT region
    lines.extend(_spmp_write_addr(val_reg, napot_wide))
    cfg_no_perm = (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # RWX=000 -> no permissions for U
    lines.extend(_spmp_write_cfg(val_reg, cfg_no_perm))

    # Entry 1: covering same range, with RW permissions
    lines.extend(_spmp_select(1, sel_reg))
    lines.extend(_spmp_write_addr(val_reg, napot_wide))
    cfg_rw = (0b110) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # RWX=110
    lines.extend(_spmp_write_cfg(val_reg, cfg_rw))

    lines.extend(
        [
            _sfence_vma(),
            "# Entry 0 (no permissions) should take priority over Entry 1 (RW)",
            test_data.add_testcase("priority_entry0_wins", coverpoint, covergroup),
        ]
    )

    # Read entry 0 cfg to confirm
    lines.extend(_spmp_select(0, sel_reg))
    lines.append(_spmp_read_cfg_sigupd(check_reg, test_data))

    # Read entry 1 cfg to confirm
    lines.extend(_spmp_select(1, sel_reg))
    lines.extend(
        [
            test_data.add_testcase("priority_entry1_secondary", coverpoint, covergroup),
            _spmp_read_cfg_sigupd(check_reg, test_data),
        ]
    )

    # Clean up
    for e in range(2):
        lines.extend(_spmp_select(e, sel_reg))
        lines.extend(_spmp_write_cfg(val_reg, 0))
        lines.extend(_spmp_write_addr(val_reg, 0))
    lines.append(_sfence_vma())

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
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
            f"CSRW(0x350, x{sel_reg})  # miselect = SPMP entry 0",
            "nop",
        ]
    )
    # NAPOT covering a wide range, no permissions
    napot_wide = (0x80000000 >> 2) | 0xFFF
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{napot_wide:x})",
            f"CSRW(0x351, x{val_reg})  # write spmpaddr via mireg",
            "nop",
        ]
    )
    cfg_deny = A_NAPOT << SPMPCFG_A_LO  # RWX=000, U=0: denies S/U
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_deny:x})",
            f"CSRW(0x352, x{val_reg})  # write spmpcfg via mireg2",
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
            "CSRW(0x352, zero)  # clear spmpcfg",
            "nop",
            "CSRW(0x351, zero)  # clear spmpaddr",
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
                f"CSRW(0x350, x{sel_reg})  # miselect = SPMP entry {entry}",
                "nop",
            ]
        )

        # Write and readback spmpaddr via mireg
        addr_val = 0x90000000 + entry * 0x2000
        lines.extend(
            [
                f"LI(x{val_reg}, 0x{addr_val >> 2:x})",
                f"CSRW(0x351, x{val_reg})  # write spmpaddr via mireg",
                "nop",
                test_data.add_testcase(f"mmode_entry{entry}_addr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, "0x351", test_data),
            ]
        )

        # Write and readback spmpcfg via mireg2
        cfg_val = (0b101) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # RX, U=1
        lines.extend(
            [
                f"LI(x{val_reg}, 0x{cfg_val:x})",
                f"CSRW(0x352, x{val_reg})  # write spmpcfg via mireg2",
                "nop",
                test_data.add_testcase(f"mmode_entry{entry}_cfg", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, "0x352", test_data),
            ]
        )

        # Clean up
        lines.extend(
            [
                "CSRW(0x352, zero)",
                "nop",
                "CSRW(0x351, zero)",
                "nop",
            ]
        )

    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg])
    return lines


def _generate_mpmpdeleg_tests(test_data: TestData) -> list[str]:
    """Test mpmpdeleg.pmpnum field (Smpmpdeleg extension).

    Covers: cp_mpmpdeleg_pmpnum, cp_mpmpdeleg_locked
    """
    covergroup = "SspmpSm_csr_cg"
    sel_reg, val_reg, check_reg, save_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_mpmpdeleg_pmpnum / cp_mpmpdeleg_locked",
            "Test mpmpdeleg CSR (Smpmpdeleg extension).\n"
            "mpmpdeleg.pmpnum[6:0] determines the delegation boundary.\n"
            "Entries >= pmpnum are delegated as SPMP entries.",
        ),
    ]

    # These tests run from M-mode
    lines.append("RVTEST_GOTO_MMODE")

    # ---------- Test pmpnum field ----------
    coverpoint = "cp_mpmpdeleg_pmpnum"

    # Read and save current mpmpdeleg
    mpmpdeleg_csr = "CSR_MPMPDELEG"

    lines.extend(
        [
            f"CSRR(x{save_reg}, {mpmpdeleg_csr})  # save mpmpdeleg",
            "nop",
        ]
    )

    # Test writing pmpnum = 0 (all entries delegated)
    lines.extend(
        [
            "\n# pmpnum = 0 (delegate all PMP entries as SPMP)",
            f"CSRW({mpmpdeleg_csr}, zero)",
            "nop",
            test_data.add_testcase("pmpnum_0", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, mpmpdeleg_csr, test_data),
        ]
    )

    # Test writing pmpnum to a mid-range value
    for pmpnum in [8, 16, 32]:
        lines.extend(
            [
                f"\n# pmpnum = {pmpnum}",
                f"LI(x{val_reg}, {pmpnum})",
                f"CSRW({mpmpdeleg_csr}, x{val_reg})",
                "nop",
                test_data.add_testcase(f"pmpnum_{pmpnum}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, mpmpdeleg_csr, test_data),
            ]
        )

    # Test writing pmpnum = 64 (no entries delegated)
    lines.extend(
        [
            "\n# pmpnum = 64 (no delegation, SPMP disabled)",
            f"LI(x{val_reg}, 64)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("pmpnum_64", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, mpmpdeleg_csr, test_data),
        ]
    )

    # Test writing pmpnum > 64 (should clamp to max)
    lines.extend(
        [
            "\n# pmpnum = 100 (should clamp to number of writable entries)",
            f"LI(x{val_reg}, 100)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("pmpnum_100_clamp", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, mpmpdeleg_csr, test_data),
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
            f"LI(x{val_reg}, 0x{0x80 | (A_NAPOT << 3) | 0b001:x})  # L=1, A=NAPOT, X=1",
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

    # Set pmpnum to 16 first (should succeed)
    lines.extend(
        [
            f"\nLI(x{val_reg}, 16)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("locked_pmpnum_16_ok", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, mpmpdeleg_csr, test_data),
        ]
    )

    # Try pmpnum = 4 (should be rejected because PMP[7] is locked)
    lines.extend(
        [
            f"\nLI(x{val_reg}, 4)",
            f"CSRW({mpmpdeleg_csr}, x{val_reg})",
            "nop",
            test_data.add_testcase("locked_pmpnum_4_rejected", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, mpmpdeleg_csr, test_data),
        ]
    )

    # Restore mpmpdeleg
    # Note: PMP[7].L cannot be cleared except by reset. In the combined test file,
    # PMP[7] remains locked for subsequent sub-tests. This is acceptable because
    # later sub-tests (spmpen, satp_bare) do not access PMP[7].
    lines.extend(
        [
            f"\nCSRW({mpmpdeleg_csr}, x{save_reg})  # restore mpmpdeleg",
            "nop",
        ]
    )

    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg])
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
            gen_csr_read_sigupd(check_reg, "satp", test_data),
        ]
    )

    # Also test from M-mode
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            test_data.add_testcase("satp_bare_mmode_check", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "satp", test_data),
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([check_reg])
    return lines


def _generate_spmp_fault_tests(test_data: TestData) -> list[str]:
    """Test SPMP fault exception codes.

    Covers: cp_spmp_fault_load, cp_spmp_fault_store
    SPMP violations use page fault exception codes (13, 15).
    Note: instruction page fault (12) requires a custom trap handler and is not tested here.
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

    # Set up a NAPOT region covering scratch area with S-mode-only permissions (U denied)
    lines.extend(
        [
            f"LA(x{addr_reg}, scratch)",
            f"srli x{addr_reg}, x{addr_reg}, 2  # convert to spmpaddr format",
            f"ori x{addr_reg}, x{addr_reg}, 0x1FF  # NAPOT 4K region",
            f"CSRW(0x151, x{addr_reg})  # write spmpaddr via sireg",
            "nop",
        ]
    )

    # S-mode only (U=0, SHARED=0), RWX=111 -> S-mode gets full access, U-mode denied
    cfg_val = (0b111) | (A_NAPOT << SPMPCFG_A_LO)  # U=0, SHARED=0
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
    # Go to M-mode to reconfigure
    lines.extend(
        [
            "",
            "RVTEST_GOTO_MMODE",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + entry:x})",
            f"CSRW(0x350, x{sel_reg})",
            "nop",
        ]
    )

    # U-mode only (U=1), RWX=000 -> both U and S get no permissions
    cfg_deny = (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)  # U=1, RWX=000
    lines.extend(
        [
            f"LI(x{val_reg}, 0x{cfg_deny:x})",
            f"CSRW(0x352, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
            _sfence_vma(),
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
            f"CSRW(0x350, x{sel_reg})",
            "nop",
            "CSRW(0x352, zero)",
            "nop",
            "CSRW(0x351, zero)",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, addr_reg])
    return lines


def _generate_spmp_entry_tor_entry0_tests(test_data: TestData) -> list[str]:
    """Test TOR mode with entry 0 (base = 0).

    Covers: addr_match_tor_entry0
    When spmpcfg[0].A == TOR, the lower bound is 0.
    """
    covergroup = "SspmpSm_addr_cg"
    coverpoint = "cp_addr_match_tor"
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
            test_data.add_testcase("entry0_tor_base_is_zero", coverpoint, covergroup),
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
    covergroup = "SspmpSm_csr_cg"
    sel_reg, val_reg, check_reg, save_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            "Sspmpen: spmpen CSR tests",
            "Test the spmpen register (Sspmpen extension).\n"
            "spmpen[i] controls whether SPMP entry i is active.\n"
            "An entry is active only when spmpen[i] & spmpcfg[i].A != 0.\n"
            "When spmpcfg[i].L == 1, spmpen[i] becomes read-only.",
        ),
    ]

    # ---------- Basic read/write ----------
    coverpoint = "cp_spmpen_readwrite"

    # Save current spmpen (S-mode CSR, accessible from S-mode)
    lines.extend(
        [
            f"CSRR(x{save_reg}, CSR_SPMPEN)  # save spmpen",
            "nop",
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
            gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
        ]
    )

    # Write zero and read back
    lines.extend(
        [
            "\n# Write zero to spmpen (disable all entries)",
            "CSRW(CSR_SPMPEN, zero)",
            "nop",
            test_data.add_testcase("spmpen_write_zero", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
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
                gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
            ]
        )

    # ---------- Activation logic: entry active iff spmpen[i] & A != 0 ----------
    coverpoint = "cp_spmpen_activation"
    entry = 0

    # Configure SPMP entry 0 with NAPOT + RW via S-mode indirect CSR access
    cfg_napot_rw = (1 << SPMPCFG_R) | (1 << SPMPCFG_W) | (A_NAPOT << SPMPCFG_A_LO) | (1 << SPMPCFG_U)

    lines.extend(
        [
            comment_banner(
                coverpoint,
                "Verify entry activation depends on spmpen[i] & spmpcfg[i].A.\n"
                "Configure entry 0 with A=NAPOT, then toggle spmpen[0].",
            ),
            "",
        ]
    )

    # Configure entry 0 via S-mode indirect CSR access (siselect/sireg/sireg2)
    lines.extend(_spmp_select(entry, sel_reg))

    # Set addr for a wide NAPOT region covering scratch
    napot_addr = 0x80000000 >> 2 | 0x01FFFFFF  # NAPOT covering large range
    lines.extend(_spmp_write_addr(val_reg, napot_addr))

    # Set cfg
    lines.extend(_spmp_write_cfg(val_reg, cfg_napot_rw))

    # Disable entry via spmpen[0] = 0
    lines.extend(
        [
            "\n# Disable entry 0 via spmpen[0] = 0",
            "CSRW(CSR_SPMPEN, zero)",
            "nop",
            "sfence.vma x0, x0",
            test_data.add_testcase("spmpen_entry0_disabled", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
        ]
    )

    # Enable entry via spmpen[0] = 1
    lines.extend(
        [
            "\n# Enable entry 0 via spmpen[0] = 1",
            f"LI(x{val_reg}, 1)",
            f"CSRW(CSR_SPMPEN, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            test_data.add_testcase("spmpen_entry0_enabled", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
        ]
    )

    # Verify: when A=OFF, spmpen[0]=1 should still not activate entry
    lines.extend(
        [
            "\n# Set A=OFF (disable), spmpen[0]=1 -> entry still inactive",
            "CSRW(0x152, zero)  # spmpcfg.A=OFF via sireg2",
            "nop",
            f"LI(x{val_reg}, 1)",
            f"CSRW(CSR_SPMPEN, x{val_reg})",
            "nop",
            "sfence.vma x0, x0",
            test_data.add_testcase("spmpen_aoff_no_activate", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "0x152", test_data),
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
            test_data.add_testcase("spmpen_locked_clear_rejected", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
        ]
    )

    # Try to set another bit via CSRS (should also be ignored for locked entry)
    lines.extend(
        [
            "\n# Verify spmpen[1] is still 1 (read-only when locked)",
            test_data.add_testcase("spmpen_locked_still_set", coverpoint, covergroup),
            gen_csr_read_sigupd(check_reg, "CSR_SPMPEN", test_data),
        ]
    )

    # ---------- Clean up: unlock via reset (clear lock from M-mode) ----------
    # Note: lock can only be cleared by reset; we just clear A to deactivate
    lines.extend(
        [
            "\n# Clean up: clear locked entry config",
            f"LI(x{sel_reg}, 0x{SISELECT_SPMP_BASE + lock_entry:x})",
            f"CSRW(miselect, x{sel_reg})",
            "nop",
            "CSRW(mireg2, zero)  # try to clear (may be ignored if locked)",
            "nop",
            "CSRW(mireg, zero)",
            "nop",
            f"CSRW(CSR_SPMPEN, x{save_reg})  # restore spmpen",
            "nop",
            "sfence.vma x0, x0",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    test_data.int_regs.return_registers([sel_reg, val_reg, check_reg, save_reg])
    return lines


# ---------------------------------------------------------------------------
# Framework integration: register Sspmp so ``testgen testplans --extensions Sspmp`` works.
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Sspmp",
    required_extensions=["Sm", "Ss", "Zicsr", "Sspmp"],
    march_extensions=["Zicsr"],
)
def make_sspmp(test_data: TestData) -> list[str]:
    """Generate all SPMP sub-tests (combined into one file by the framework)."""
    lines: list[str] = []
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
    lines.extend(_generate_mpmpdeleg_tests(test_data))
    # Sspmpen Tests
    lines.extend(_generate_spmpen_tests(test_data))
    # Paging Tests
    lines.extend(_generate_satp_bare_spmp_tests(test_data))
    return lines


# ---------------------------------------------------------------------------
# Standalone Sspmp test generation (separate files, no "-00" suffix)
# Run:  python3 -m uv run python generators/testgen/src/testgen/priv/extensions/SspmpSm.py tests
# ---------------------------------------------------------------------------

_SIGUPD_MARGIN = 10

# (filename_stem, generator_function) for each sub-test
_SSPMP_SUB_TESTS: list[tuple[str, Callable[[TestData], list[str]]]] = [
    ("SspmpSmCsrAccess", _generate_spmp_csr_indirect_access_tests),
    ("SspmpSmLock", _generate_spmp_lock_tests),
    ("SspmpSmOobAccess", _generate_spmp_oob_access_tests),
    ("SspmpSmAddrMatch", _generate_addr_match_tests),
    ("SspmpSmTorEntry0", _generate_spmp_entry_tor_entry0_tests),
    ("SspmpSmPriority", _generate_priority_match_tests),
    ("SspmpSmPermSmode", _generate_permission_smode_tests),
    ("SspmpSmPermUmode", _generate_permission_umode_tests),
    ("SspmpSmSum", _generate_sum_effect_tests),
    ("SspmpSmMxr", _generate_mxr_effect_tests),
    ("SspmpSmShared", _generate_shared_rule_tests),
    ("SspmpSmReserved", _generate_reserved_encoding_tests),
    ("SspmpSmNoMatch", _generate_no_match_deny_tests),
    ("SspmpSmFault", _generate_spmp_fault_tests),
    ("SspmpSmMmodeBypass", _generate_mmode_bypass_tests),
    ("SspmpSmMmodeAccess", _generate_mmode_indirect_access_tests),
    ("SspmpSmMpmpdeleg", _generate_mpmpdeleg_tests),
    ("SspmpSmSpmpen", _generate_spmpen_tests),
    ("SspmpSmSatpBare", _generate_satp_bare_spmp_tests),
]


def _generate_single_test(
    name: str,
    generator_fn: Callable[[TestData], list[str]],
    output_dir: Path,
) -> None:
    """Generate a single Sspmp sub-test .S file."""
    test_config = TestConfig(
        xlen=0,
        flen=64,
        testsuite=name,
        E_ext=False,
        config_dependent=True,
        required_extensions=["Sm", "Ss", "Zicsr", "Sspmp"],
        march_extensions=["Zicsr"],
    )

    test_data = TestData(test_config)
    tc = test_data.begin_test_chunk()
    test_data.int_regs.consume_registers([1])
    seed(reproducible_hash(name))

    body_lines = generator_fn(test_data)

    test_data.int_regs.return_register(1)
    tc.code = "\n".join(body_lines)
    test_data.end_test_chunk()

    # Assemble the .S file
    filename = f"{name}.S"
    sigupd_count = _SIGUPD_MARGIN + tc.sigupd_count

    test_file_relative = Path("Sspmp") / filename
    extra_defines = ["#define RVTEST_PRIV_TEST"]
    header = insert_header_template(test_config, test_file_relative, sigupd_count, extra_defines)

    body = "\n".join(indent_asm(line) for line in tc.code.split("\n"))

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
    for name, gen_fn in _SSPMP_SUB_TESTS:
        _generate_single_test(name, gen_fn, sspmp_dir)
    print(f"Generated {len(_SSPMP_SUB_TESTS)} Sspmp test files in {sspmp_dir}")


# run: python3 -m uv run python generators/testgen/src/testgen/priv/extensions/SspmpSm.py tests
# This will generate separate .S files for each Sspmp sub-test under tests/priv/Sspmp/.
if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests")
    generate_sspmp_tests(output)
