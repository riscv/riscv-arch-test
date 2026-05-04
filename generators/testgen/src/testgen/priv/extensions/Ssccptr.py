##################################
# priv/extensions/Ssccptr.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssccptr test generator
# ayesha.anwaar2005@gmail.com Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssccptr S-mode test generator.

Ssccptr: Main memory supports hardware page-table walker (HPTW) reads.

A single lw from virtual memory after sfence.vma suffices to prove
the HPTW can read PTEs from main memory for a valid VA→PA translation.

Test strategy
-------------
For both RV64 (Sv39) and RV32 (Sv32):

  1. In M-mode, set up a minimal identity-mapped page table for the
     code+data region using a superpage entry so the trap handler
     remains reachable under VM.
  2. Enable VM (satp) and drop to S-mode.
  3. Run a single lw from scratch through the virtual address space.
     A successful load proves the HPTW read PTEs from main memory.
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
# Page-table helpers
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
# Single lw testcase under VM — RV64
# ---------------------------------------------------------------------------


def _generate_ssccptr_lw_rv64(test_data: TestData) -> list[str]:
    """Generate a single lw under Sv39 VM to prove HPTW reads PTEs from main memory."""
    coverpoint = "cp_ssccptr"
    # x0 is always excluded by the framework; no need to pass exclude_regs=[0]
    addr_reg, data_reg = test_data.int_regs.get_registers(2)

    lines = _setup_sv39_identity_map()
    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            "SATP_SETUP_RV64(sv39)",
            "sfence.vma",
            comment_banner(coverpoint, "HPTW Read: lw under Sv39 VM (RV64)"),
            f"LA(x{addr_reg}, scratch)",
            test_data.add_testcase("lw_under_vm_rv64", coverpoint, covergroup),
            f"lw x{data_reg}, 0(x{addr_reg})",
            write_sigupd(data_reg, test_data),
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


# ---------------------------------------------------------------------------
# Single lw testcase under VM — RV32
# ---------------------------------------------------------------------------


def _generate_ssccptr_lw_rv32(test_data: TestData) -> list[str]:
    """Generate a single lw under Sv32 VM to prove HPTW reads PTEs from main memory."""
    coverpoint = "cp_ssccptr"
    # x0 is always excluded by the framework; no need to pass exclude_regs=[0]
    addr_reg, data_reg = test_data.int_regs.get_registers(2)

    lines = _setup_sv32_identity_map()
    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            "SATP_SETUP_SV32",
            "sfence.vma",
            comment_banner(coverpoint, "HPTW Read: lw under Sv32 VM (RV32)"),
            f"LA(x{addr_reg}, scratch)",
            test_data.add_testcase("lw_under_vm_rv32", coverpoint, covergroup),
            f"lw x{data_reg}, 0(x{addr_reg})",
            write_sigupd(data_reg, test_data),
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


# ---------------------------------------------------------------------------
# Top-level test generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Ssccptr",
    required_extensions=["Ssccptr"],
    march_extensions=["S", "Zicsr"],
    extra_defines=[
        "#define SKIP_MEPC",
    ],
)
def _generate_ssccptr_main(test_data: TestData) -> list[str]:
    """Generate all Ssccptr tests running in S-mode."""
    lines = []

    # Initialize scratch memory with known sentinel value so the lw
    # result is deterministic and the signature check is meaningful.
    lines.extend(
        [
            "# Initialize scratch memory with known sentinel value",
            "LA(x10, scratch)",
            "LI(x11, 0xDEADBEEF)",
            "sw x11, 0(x10)",
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
    lines.extend(_generate_ssccptr_lw_rv64(test_data))
    lines.extend(
        [
            "",
            "#else",
        ]
    )
    lines.extend(_generate_ssccptr_lw_rv32(test_data))
    lines.extend(
        [
            "",
            "#endif",
        ]
    )

    return lines
