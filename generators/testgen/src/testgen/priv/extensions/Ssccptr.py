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
rvtest_Sroot_pg_tbl (emitted by framework via rvtest_strap_routine)
plus rvtest_slvl1_pg_tbl / rvtest_slvl0_pg_tbl injected via
.pushsection into .data.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

covergroup = "Ssccptr_cg"
_SENTINEL = "0xC0FFEE42"


# ---------------------------------------------------------------------------
# Page-table helpers
# ---------------------------------------------------------------------------


def _generate_page_table_data_section() -> list[str]:
    """
    Inject page-table labels into .data via .pushsection / .popsection.

    rvtest_Sroot_pg_tbl is already emitted by the framework when
    rvtest_strap_routine is defined.  We only declare:
        rvtest_slvl1_pg_tbl — L1 intermediate page table
        rvtest_slvl0_pg_tbl — leaf page table
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


def _setup_identity_map() -> list[str]:
    """
    Set up a minimal identity map using a superpage entry — portable to
    any load address via AUIPC.

    Uses t0/t1/t2 (caller-saved temporaries) so it does not interfere
    with registers allocated for the test via get_registers().

    RV64: 1 GiB superpage, 8 bytes per PTE, sd to write.
    RV32: 4 MiB superpage, 4 bytes per PTE, sw to write.
    The xlen guard selects the correct shift, mask, and store instruction.
    """
    return [
        "# AUIPC-based superpage identity map — portable to any load address",
        "auipc t0, 0",  # t0 = current PC
        "#if __riscv_xlen == 64",
        "li t1, ~((1 << 30) - 1)",  # 1 GiB alignment mask
        "#else",
        "li t1, ~((1 << 22) - 1)",  # 4 MiB alignment mask
        "#endif",
        "and t0, t0, t1",  # t0 = superpage-aligned base PA
        "srli t0, t0, 12",  # t0 = PPN
        "slli t0, t0, 10",  # t0 = PPN in PTE field position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # t0 = leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",  # t2 = root page table base
        "LA(t1, rvtest_code_begin)",  # t1 = code base address
        "#if __riscv_xlen == 64",
        "srli t1, t1, 30",  # VPN[2]
        "andi t1, t1, 0x1FF",
        "slli t1, t1, 3",  # 8 bytes per PTE
        "#else",
        "srli t1, t1, 22",  # VPN[1]
        "andi t1, t1, 0x3FF",
        "slli t1, t1, 2",  # 4 bytes per PTE
        "#endif",
        "add t2, t2, t1",  # t2 = address of PTE slot
        "#if __riscv_xlen == 64",
        "sd t0, 0(t2)",  # write PTE (RV64)
        "#else",
        "sw t0, 0(t2)",  # write PTE (RV32)
        "#endif",
        "sfence.vma",
    ]


# ---------------------------------------------------------------------------
# Single lw testcase under virtual memory
# ---------------------------------------------------------------------------


def _generate_ssccptr_lw(test_data: TestData) -> list[str]:
    """
    Generate a single lw under virtual memory to prove HPTW reads PTEs
    from main memory.

    Registers are allocated AFTER page-table setup and SATP/GOTO macros
    to avoid clobbering x10/x11 used by those macros internally.
    The SATP setup is guarded by __riscv_xlen; everything else is generic.
    """
    coverpoint = "cp_ssccptr"

    lines = _setup_identity_map()
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
)
def _generate_ssccptr_main(test_data: TestData) -> list[str]:
    """Generate all Ssccptr tests running in S-mode."""
    lines = []

    # Initialize scratch memory with a known sentinel value so the lw
    # result is deterministic and the signature check is meaningful.
    lines.extend(
        [
            "# Initialize scratch memory with known sentinel value",
            "LA(x10, scratch)",
            f"LI(x11, {_SENTINEL})",
            "sw x11, 0(x10)",
            "",
        ]
    )

    # Inject page-table labels into .data before any PTE_SETUP_* call.
    lines.extend(_generate_page_table_data_section())

    # Must be in M-mode for page-table setup.
    lines.append("RVTEST_GOTO_MMODE")

    lines.extend(_generate_ssccptr_lw(test_data))

    return lines
