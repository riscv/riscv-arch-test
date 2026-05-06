##################################
# priv/extensions/Ssccptr.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssccptr test generator
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssccptr S-mode test generator.

Ssccptr: Main memory supports hardware page-table walker (HPTW) reads.

A single lw from virtual memory after sfence.vma suffices to prove
the HPTW can read PTEs from main memory for a valid VA->PA translation.

Test strategy
-------------
  1. In M-mode, set up a minimal identity-mapped page table for the
     code+data region using a superpage entry so the trap handler
     remains reachable under VM.
  2. Enable VM (satp) and drop to S-mode.
  3. Run a single lw from scratch through the virtual address space.
     A successful load proves the HPTW read PTEs from main memory.
  4. Return to M-mode and disable VM.

Page-table infrastructure
-------------------------
rvtest_Sroot_pg_tbl is defined inside RVTEST_DATA_BEGIN in
tests/env/rvtest_setup.h when S-mode is enabled (S_SUPPORTED).
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

covergroup = "Ssccptr_cg"
_SENTINEL = "0xC0FFEE42"


# ---------------------------------------------------------------------------
# Page-table helpers
# ---------------------------------------------------------------------------


def _setup_identity_map(test_data: TestData) -> list[str]:
    """
    Set up a minimal identity map using a superpage entry — portable to
    any load address via AUIPC.

    Registers are allocated via get_registers() so the register allocator
    remains in control rather than assuming t0/t1/t2 are free.

    RV64: 1 GiB superpage, 8 bytes per PTE, sd to write.
    RV32: 4 MiB superpage, 4 bytes per PTE, sw to write.
    The xlen guard selects the correct shift, mask, and store instruction.
    """
    r0, r1, r2 = test_data.int_regs.get_registers(3)

    lines = [
        "# AUIPC-based superpage identity map — portable to any load address",
        f"auipc x{r0}, 0",  # r0 = current PC
        "#if __riscv_xlen == 64",
        f"li x{r1}, ~((1 << 30) - 1)",  # 1 GiB alignment mask
        "#else",
        f"li x{r1}, ~((1 << 22) - 1)",  # 4 MiB alignment mask
        "#endif",
        f"and x{r0}, x{r0}, x{r1}",  # r0 = superpage-aligned base PA
        f"srli x{r0}, x{r0}, 12",  # r0 = PPN
        f"slli x{r0}, x{r0}, 10",  # r0 = PPN in PTE field position
        f"li x{r1}, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        f"or x{r0}, x{r0}, x{r1}",  # r0 = leaf PTE value
        f"LA(x{r2}, rvtest_Sroot_pg_tbl)",  # r2 = root page table base
        f"LA(x{r1}, rvtest_code_begin)",  # r1 = code base address
        "#if __riscv_xlen == 64",
        f"srli x{r1}, x{r1}, 30",  # VPN[2]
        f"andi x{r1}, x{r1}, 0x1FF",
        f"slli x{r1}, x{r1}, 3",  # 8 bytes per PTE
        "#else",
        f"srli x{r1}, x{r1}, 22",  # VPN[1]
        f"andi x{r1}, x{r1}, 0x3FF",
        f"slli x{r1}, x{r1}, 2",  # 4 bytes per PTE
        "#endif",
        f"add x{r2}, x{r2}, x{r1}",  # r2 = address of PTE slot
        "#if __riscv_xlen == 64",
        f"sd x{r0}, 0(x{r2})",  # write PTE (RV64)
        "#else",
        f"sw x{r0}, 0(x{r2})",  # write PTE (RV32)
        "#endif",
        "sfence.vma",
    ]

    test_data.int_regs.return_registers([r0, r1, r2])
    return lines


# ---------------------------------------------------------------------------
# Single lw testcase under virtual memory
# ---------------------------------------------------------------------------


def _generate_ssccptr_lw(test_data: TestData) -> list[str]:
    """
    Generate a single lw under virtual memory to prove HPTW reads PTEs
    from main memory.

    Registers are allocated AFTER page-table setup and SATP/GOTO macros
    to avoid clobbering registers used by those macros internally.
    The SATP setup is guarded by __riscv_xlen; everything else is generic.

    Note: returning to M-mode and disabling VM is handled by the framework.
    """
    coverpoint = "cp_ssccptr"

    lines = _setup_identity_map(test_data)
    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            "#if __riscv_xlen == 64",
            "SATP_SETUP_RV64(sv39)",
            "#else",
            "SATP_SETUP_SV32",
            "#endif",
            "sfence.vma",
        ]
    )

    addr_reg, data_reg = test_data.int_regs.get_registers(2)

    lines.extend(
        [
            comment_banner(coverpoint, "HPTW Read: lw under virtual memory"),
            f"LA(x{addr_reg}, scratch)",
            test_data.add_testcase("lw_under_vm", coverpoint, covergroup),
            f"lw x{data_reg}, 0(x{addr_reg})",
            write_sigupd(data_reg, test_data),
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
    march_extensions=["S"],
)
def _generate_ssccptr_main(test_data: TestData) -> list[str]:
    """Generate all Ssccptr tests running in S-mode."""
    lines = []

    # Initialize scratch memory with a known sentinel value so the lw
    # result is deterministic and the signature check is meaningful.
    # Use get_registers to avoid assuming which registers are free.
    scratch_reg, val_reg = test_data.int_regs.get_registers(2)
    lines.extend(
        [
            "# Initialize scratch memory with known sentinel value",
            f"LA(x{scratch_reg}, scratch)",
            f"LI(x{val_reg}, {_SENTINEL})",
            f"sw x{val_reg}, 0(x{scratch_reg})",
            "",
        ]
    )
    test_data.int_regs.return_registers([scratch_reg, val_reg])

    # Must be in M-mode for page-table setup.
    lines.append("RVTEST_GOTO_MMODE")

    lines.extend(_generate_ssccptr_lw(test_data))

    return lines
