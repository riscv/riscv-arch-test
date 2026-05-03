##################################
# priv/extensions/Ssccptr.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssccptr test generator
# ayesha.anwaar2005@gmail.com Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssccptr S-mode test generator.

Ssccptr: Main memory supports hardware page-table walker (HPTW) reads.

The coverpoint cp_ssccptr verifies that when Sv virtual memory is active
(satp ≠ 0), the HPTW can successfully read PTEs from main memory and
translate virtual addresses to physical addresses for both loads and stores.

Test strategy
-------------
For both RV64 (Sv39) and RV32 (Sv32):

  1. In M-mode, set up a minimal identity-mapped page table for the
     code+data region using a superpage entry so the trap handler
     remains reachable under VM.
  2. Enable VM (satp) and drop to S-mode.
  3. Run several lw and sw testcases through the virtual address space:
       - lw from scratch  (HPTW reads PTEs for a load translation)
       - sw to scratch    (HPTW reads PTEs for a store translation)
       - lw result check  (verify the stored value round-trips correctly)
       - lw of byte/half  (lb, lh — additional load widths)
       - sw of byte/half  (sb, sh — additional store widths)
     Each access succeeds (no fault), proving the HPTW read PTEs from
     main memory.
  4. Return to M-mode and disable VM.

Page-table infrastructure
-------------------------
Same labels as Sstvala — rvtest_Sroot_pg_tbl (emitted by framework via
rvtest_strap_routine) plus rvtest_slvl1_pg_tbl / rvtest_slvl0_pg_tbl
injected via .pushsection into .data.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

covergroup = "Ssccptr_cg"


# ---------------------------------------------------------------------------
# Page-table helpers (mirrors Sstvala pattern exactly)
# ---------------------------------------------------------------------------


def _generate_page_table_data_section() -> list[str]:
    """
    Inject page-table labels into .data via .pushsection / .popsection.

    rvtest_Sroot_pg_tbl is already emitted by the framework when
    rvtest_strap_routine is defined.  We only declare:
        rvtest_slvl1_pg_tbl — Sv39 L1 intermediate page table
        rvtest_slvl0_pg_tbl — Sv39/Sv32 leaf page table
    """
    return [
        "",
        "# -----------------------------------------------------------------------",
        "# Page-table labels injected into .data via .pushsection.",
        "# rvtest_Sroot_pg_tbl is already declared by the framework.",
        "# -----------------------------------------------------------------------",
        ".pushsection .data",
        ".align 12",
        "rvtest_slvl1_pg_tbl:",
        "    .fill 512, 8, 0",
        ".align 12",
        "rvtest_slvl0_pg_tbl:",
        "    .fill 512, 8, 0",
        ".popsection",
        "",
    ]


def _setup_sv39_identity_map() -> list[str]:
    """
    Set up a minimal Sv39 identity map using a LEVEL2 superpage (1 GiB).

    Uses AUIPC to find where the program actually loaded (portable, not
    hardcoded to 0x80000000), computes the 1 GiB-aligned superpage base,
    then manually wires the root page table entry.
    """
    return [
        "# RV64/Sv39: AUIPC-based superpage identity map — portable to any load address",
        "auipc t0, 0",  # t0 = current PC
        "li t1, ~((1 << 30) - 1)",  # 1 GiB alignment mask
        "and t0, t0, t1",  # t0 = 1 GiB-aligned superpage base PA
        "srli t0, t0, 12",  # t0 = PPN
        "slli t0, t0, 10",  # t0 = PPN in PTE field position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # t0 = leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",  # t2 = root page table base
        "# Compute VPN[2] index = (rvtest_code_begin >> 30) & 0x1FF, scaled by 8",
        "LA(t1, rvtest_code_begin)",  # t1 = rvtest_code_begin address
        "srli t1, t1, 30",  # t1 = VPN[2]
        "andi t1, t1, 0x1FF",  # t1 = VPN[2] masked
        "slli t1, t1, 3",  # t1 = byte offset (8 bytes per entry)
        "add t2, t2, t1",  # t2 = address of PTE slot
        "sd t0, 0(t2)",  # write the leaf PTE
        "sfence.vma",
    ]


def _setup_sv32_identity_map() -> list[str]:
    """
    Set up a minimal Sv32 identity map using a LEVEL1 superpage (4 MiB).

    Same AUIPC-based approach as Sv39 but for Sv32/RV32.
    Root table index = VPN[1] = VA[31:22], 4 bytes per entry.
    """
    return [
        "# RV32/Sv32: AUIPC-based superpage identity map — portable to any load address",
        "auipc t0, 0",  # t0 = current PC
        "li t1, ~((1 << 22) - 1)",  # 4 MiB alignment mask
        "and t0, t0, t1",  # t0 = 4 MiB-aligned superpage base PA
        "srli t0, t0, 12",  # t0 = PPN
        "slli t0, t0, 10",  # t0 = PPN in PTE field position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # t0 = leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",  # t2 = root page table base
        "# Compute VPN[1] index = (rvtest_code_begin >> 22) & 0x3FF, scaled by 4",
        "LA(t1, rvtest_code_begin)",  # t1 = rvtest_code_begin address
        "srli t1, t1, 22",  # t1 = VPN[1]
        "andi t1, t1, 0x3FF",  # t1 = VPN[1] masked
        "slli t1, t1, 2",  # t1 = byte offset (4 bytes per entry)
        "add t2, t2, t1",  # t2 = address of PTE slot
        "sw t0, 0(t2)",  # write the leaf PTE
        "sfence.vma",
    ]


# ---------------------------------------------------------------------------
# Load testcases under VM
# ---------------------------------------------------------------------------


def _generate_load_tests_under_vm(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    addr_reg: int,
    data_reg: int,
    suffix: str,
) -> list[str]:
    """
    Generate load testcases (lw, lh, lb) from the scratch area under VM.

    suffix is "rv64" or "rv32" to ensure unique testcase symbol names.
    Each successful load proves the HPTW read the PTEs from main memory
    to produce a valid virtual→physical translation.
    """
    lines = [
        comment_banner(coverpoint, "HPTW Read: Load under VM"),
        "",
        "# lw — word load through virtual address (HPTW must walk PTEs)",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase(f"lw_under_vm_{suffix}", coverpoint, covergroup),
        f"lw x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
        "",
        "# lh — halfword load through virtual address",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase(f"lh_under_vm_{suffix}", coverpoint, covergroup),
        f"lh x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
        "",
        "# lb — byte load through virtual address",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase(f"lb_under_vm_{suffix}", coverpoint, covergroup),
        f"lb x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
        "",
        "# lhu — unsigned halfword load through virtual address",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase(f"lhu_under_vm_{suffix}", coverpoint, covergroup),
        f"lhu x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
        "",
        "# lbu — unsigned byte load through virtual address",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase(f"lbu_under_vm_{suffix}", coverpoint, covergroup),
        f"lbu x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
    ]
    return lines


# ---------------------------------------------------------------------------
# Store testcases under VM
# ---------------------------------------------------------------------------


def _generate_store_tests_under_vm(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    addr_reg: int,
    data_reg: int,
    check_reg: int,
    suffix: str,
) -> list[str]:
    """
    Generate store testcases (sw, sh, sb) to the scratch area under VM,
    followed by a load-back to verify the stored value round-trips.

    suffix is "rv64" or "rv32" to ensure unique testcase symbol names.
    Each successful store proves the HPTW read the PTEs from main memory
    to produce a valid virtual→physical translation for the store.
    The load-back proves the written value is physically correct.
    """
    lines = [
        comment_banner(coverpoint, "HPTW Read: Store under VM"),
        "",
        "# sw — word store through virtual address (HPTW must walk PTEs)",
        f"LA(x{addr_reg}, scratch)",
        f"LI(x{data_reg}, 0xC0FFEE00)",
        test_data.add_testcase(f"sw_under_vm_{suffix}", coverpoint, covergroup),
        f"sw x{data_reg}, 0(x{addr_reg})",
        "# Load back and save to signature to confirm store succeeded",
        f"lw x{check_reg}, 0(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        "",
        "# sh — halfword store through virtual address",
        f"LA(x{addr_reg}, scratch)",
        f"LI(x{data_reg}, 0xBEEF)",
        test_data.add_testcase(f"sh_under_vm_{suffix}", coverpoint, covergroup),
        f"sh x{data_reg}, 0(x{addr_reg})",
        f"lh x{check_reg}, 0(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        "",
        "# sb — byte store through virtual address",
        f"LA(x{addr_reg}, scratch)",
        f"LI(x{data_reg}, 0xAB)",
        test_data.add_testcase(f"sb_under_vm_{suffix}", coverpoint, covergroup),
        f"sb x{data_reg}, 0(x{addr_reg})",
        f"lb x{check_reg}, 0(x{addr_reg})",
        write_sigupd(check_reg, test_data),
    ]
    return lines


# ---------------------------------------------------------------------------
# RV64-only load/store testcases
# ---------------------------------------------------------------------------


def _generate_rv64_tests_under_vm(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    addr_reg: int,
    data_reg: int,
    check_reg: int,
) -> list[str]:
    """
    Generate RV64-only load/store testcases (ld, sd, lwu) under VM.
    """
    lines = [
        "",
        "#if __riscv_xlen == 64",
        "# ld — doubleword load through virtual address (RV64 only)",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase("ld_under_vm", coverpoint, covergroup),
        f"ld x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
        "",
        "# lwu — unsigned word load through virtual address (RV64 only)",
        f"LA(x{addr_reg}, scratch)",
        test_data.add_testcase("lwu_under_vm", coverpoint, covergroup),
        f"lwu x{data_reg}, 0(x{addr_reg})",
        write_sigupd(data_reg, test_data),
        "",
        "# sd — doubleword store through virtual address (RV64 only)",
        f"LA(x{addr_reg}, scratch)",
        f"LI(x{data_reg}, 0xC0FFEE00DEADBEEF)",
        test_data.add_testcase("sd_under_vm", coverpoint, covergroup),
        f"sd x{data_reg}, 0(x{addr_reg})",
        f"ld x{check_reg}, 0(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        "#endif",
    ]
    return lines


# ---------------------------------------------------------------------------
# Top-level test generator
# ---------------------------------------------------------------------------


def _generate_ssccptr_tests_rv64(test_data: TestData, covergroup: str) -> list[str]:
    """Generate Ssccptr testcases for RV64/Sv39."""
    coverpoint = "cp_ssccptr"
    addr_reg, data_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        "# RV64/Sv39 path",
    ]
    lines.extend(_setup_sv39_identity_map())
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines.extend(
        [
            "# Write satp directly from S-mode: MODE=8 (Sv39) in bits [63:60],",
            "# ASID=0, PPN = physical address of rvtest_Sroot_pg_tbl >> 12.",
            "# Using SATP_SETUP_RV64 macro from S-mode so the coverage model",
            "# sees satp != 0 at every subsequent load/store instruction.",
            "SATP_SETUP_RV64(sv39)",
            "sfence.vma",
        ]
    )
    lines.extend(_generate_load_tests_under_vm(test_data, covergroup, coverpoint, addr_reg, data_reg, "rv64"))
    lines.extend(
        _generate_store_tests_under_vm(test_data, covergroup, coverpoint, addr_reg, data_reg, check_reg, "rv64")
    )
    lines.extend(_generate_rv64_tests_under_vm(test_data, covergroup, coverpoint, addr_reg, data_reg, check_reg))
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg])
    return lines


def _generate_ssccptr_tests_rv32(test_data: TestData, covergroup: str) -> list[str]:
    """Generate Ssccptr testcases for RV32/Sv32."""
    coverpoint = "cp_ssccptr"
    addr_reg, data_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        "# RV32/Sv32 path",
    ]
    lines.extend(_setup_sv32_identity_map())
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines.extend(
        [
            "# Write satp directly from S-mode so the coverage model sees",
            "# satp != 0 at every subsequent load/store instruction.",
            "SATP_SETUP_SV32",
            "sfence.vma",
        ]
    )
    lines.extend(_generate_load_tests_under_vm(test_data, covergroup, coverpoint, addr_reg, data_reg, "rv32"))
    lines.extend(
        _generate_store_tests_under_vm(test_data, covergroup, coverpoint, addr_reg, data_reg, check_reg, "rv32")
    )
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg])
    return lines


@add_priv_test_generator(
    "Ssccptr",
    required_extensions=["S", "Zicsr"],
    extra_defines=[
        "#define SKIP_MEPC",
        "#define rvtest_strap_routine",  # causes framework to emit rvtest_Sroot_pg_tbl
    ],
)
def _generate_ssccptr_main(test_data: TestData) -> list[str]:
    """Generate all Ssccptr tests running in S-mode."""
    lines = []

    # Initialize scratch memory with known sentinel values so load
    # results are deterministic and signature checks are meaningful.
    lines.extend(
        [
            "# Initialize scratch memory with known sentinel values",
            "LA(x10, scratch)",
            "LI(x11, 0xDEADBEEF)",
            "sw x11, 0(x10)",
            "sw x11, 4(x10)",
            "sw x11, 8(x10)",
            "sw x11, 12(x10)",
            "",
        ]
    )

    # Inject page-table labels into .data before any PTE_SETUP_* call.
    lines.extend(_generate_page_table_data_section())

    # Must be in M-mode for page-table setup macros.
    lines.append("RVTEST_GOTO_MMODE")

    # RV64 (Sv39) path / RV32 (Sv32) path — guarded by __riscv_xlen.
    lines.extend(
        [
            "",
            "#if __riscv_xlen == 64",
        ]
    )
    lines.extend(_generate_ssccptr_tests_rv64(test_data, covergroup))
    lines.extend(
        [
            "",
            "#else",
        ]
    )
    lines.extend(_generate_ssccptr_tests_rv32(test_data, covergroup))
    lines.extend(
        [
            "",
            "#endif",
        ]
    )

    return lines
