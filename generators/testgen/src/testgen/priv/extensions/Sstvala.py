##################################
# priv/extensions/Sstvala.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Sstvala test generator
# ayesha.anwaar2005@gmail.com Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstvala S-mode test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.extensions.ExceptionsCommon import (
    generate_illegal_instruction_tests,
    generate_instr_access_fault_tests,
    generate_instr_adr_misaligned_jalr_tests,
    generate_load_access_fault_tests,
    generate_load_address_misaligned_tests,
    generate_store_access_fault_tests,
    generate_store_address_misaligned_tests,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "Sstvala_cg"


# ---------------------------------------------------------------------------
# Page-fault test generators
#
# Strategy differs by XLEN:
#   RV64 (Sv39): 3-level page table
#   RV32 (Sv32): 2-level page table
#
# PTE permission strategies (same for both modes):
#   • Load page fault  – PTE has W but NOT R  (write-only; reserved encoding)
#   • Store page fault – PTE has R|X but NOT W (read-execute only)
#   • Instr page fault – PTE has R|W but NOT X (read-write only)
#
# Page-table labels:
#   rvtest_Sroot_pg_tbl  — root PT (emitted by framework via rvtest_strap_routine)
#   rvtest_slvl1_pg_tbl  — L1 intermediate PT (Sv39 only)
#   rvtest_slvl0_pg_tbl  — leaf PT
#   rvtest_pf_data       — physical backing page mapped by leaf PTE
#
# ---------------------------------------------------------------------------

# Virtual address for RV64/Sv39 page-fault tests (canonical, page-aligned)
_VA_PF_PAGE_RV64 = 0x140300000

# Virtual address for RV32/Sv32 page-fault tests (fits in 32 bits, page-aligned)
_VA_PF_PAGE_RV32 = 0xC0300000


def _generate_page_table_data_section() -> list[str]:
    """
    Inject three additional page-table labels into the .data section using
    .pushsection / .popsection so they can appear anywhere in the code stream.

    rvtest_Sroot_pg_tbl is already emitted by the framework when
    rvtest_strap_routine is defined — we do NOT redeclare it here.

    Labels declared:
        rvtest_slvl1_pg_tbl  — Sv39 L1 intermediate page table
        rvtest_slvl0_pg_tbl  — Sv39/Sv32 leaf page table
        rvtest_pf_data       — physical backing page for the fault VA
    """
    return [
        "",
        "# -----------------------------------------------------------------------",
        "# Additional page-table labels injected into .data via .pushsection.",
        "# rvtest_Sroot_pg_tbl is already declared by the framework.",
        "# -----------------------------------------------------------------------",
        ".pushsection .data",
        ".align 12",
        "rvtest_slvl1_pg_tbl:",
        "    .fill 512, 8, 0",
        ".align 12",
        "rvtest_slvl0_pg_tbl:",
        "    .fill 512, 8, 0",
        ".align 12",
        "rvtest_pf_data:",
        "    .fill 512, 8, 0",
        ".popsection",
        "",
    ]


def _pf_pte_setup_sv39(va: int, pte_flags: str) -> list[str]:
    """
    Emit Sv39 page-table wiring with AUIPC-based 1 GiB identity map for
    code+data region — portable to any load address, not hardcoded to 0x80000000.
    """
    return [
        "# RV64/Sv39: AUIPC-based 1 GiB superpage identity map (portable)",
        "auipc t0, 0",  # t0 = current PC
        "li t1, ~((1 << 30) - 1)",  # 1 GiB alignment mask
        "and t0, t0, t1",  # t0 = 1 GiB-aligned superpage base PA
        "srli t0, t0, 12",  # t0 = PPN
        "slli t0, t0, 10",  # t0 = PPN in PTE field position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # t0 = leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",  # t2 = root page table base
        "LA(t1, rvtest_code_begin)",  # t1 = rvtest_code_begin address
        "srli t1, t1, 30",  # VPN[2]
        "andi t1, t1, 0x1FF",
        "slli t1, t1, 3",  # byte offset (8 bytes/entry)
        "add t2, t2, t1",
        "sd t0, 0(t2)",  # write leaf PTE
        "sfence.vma",
        f"PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), {hex(va)}, LEVEL2)",
        f"PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va)}, LEVEL1)",
        f"PTE_SETUP_SV39(rvtest_pf_data, ({pte_flags}), {hex(va)}, LEVEL0)",
        "sfence.vma",
    ]


def _pf_pte_setup_sv32(va: int, pte_flags: str) -> list[str]:
    """
    Emit Sv32 page-table wiring with AUIPC-based 4 MiB identity map for
    code+data region — portable to any load address, not hardcoded to 0x80000000.
    """
    return [
        "# RV32/Sv32: AUIPC-based 4 MiB superpage identity map (portable)",
        "auipc t0, 0",  # t0 = current PC
        "li t1, ~((1 << 22) - 1)",  # 4 MiB alignment mask
        "and t0, t0, t1",  # t0 = 4 MiB-aligned superpage base PA
        "srli t0, t0, 12",  # t0 = PPN
        "slli t0, t0, 10",  # t0 = PPN in PTE field position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # t0 = leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",  # t2 = root page table base
        "LA(t1, rvtest_code_begin)",  # t1 = rvtest_code_begin address
        "srli t1, t1, 22",  # VPN[1]
        "andi t1, t1, 0x3FF",
        "slli t1, t1, 2",  # byte offset (4 bytes/entry)
        "add t2, t2, t1",
        "sw t0, 0(t2)",  # write leaf PTE
        "sfence.vma",
        f"PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va)}, LEVEL1)",
        f"PTE_SETUP_SV32(rvtest_pf_data, ({pte_flags}), {hex(va)}, LEVEL0)",
        "sfence.vma",
    ]


def _generate_load_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """
    cp_stval_load_page_fault
    ------------------------
    Trigger a load page fault by mapping the page with W but NOT R.
    Reserved PTE encoding → load page fault on lw/ld.
    stval must equal the faulting virtual address (virt_adr_d).
    """
    coverpoint = "cp_stval_load_page_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    pte_flags = "PTE_D | PTE_A | PTE_W | PTE_V"

    lines = [
        comment_banner(coverpoint, "Load Page Fault (W-only PTE, no R)"),
        "",
        "#if __riscv_xlen == 64",
        "# RV64: Sv39",
        "SATP_SETUP_RV64(sv39)",
        "sfence.vma",
    ]
    lines.extend(_pf_pte_setup_sv39(_VA_PF_PAGE_RV64, pte_flags))
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines.extend(
        [
            "\n# Testcase: lw load page fault RV64",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV64)})",
            test_data.add_testcase("lw_load_page_fault_rv64", coverpoint, covergroup),
            f"lw x{data_reg}, 0(x{addr_reg})",
            "nop",
            "\n# Testcase: ld load page fault RV64",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV64)})",
            test_data.add_testcase("ld_load_page_fault_rv64", coverpoint, covergroup),
            f"ld x{data_reg}, 0(x{addr_reg})",
            "nop",
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            "",
            "#else",
            "# RV32: Sv32",
            "SATP_SETUP_SV32",
            "sfence.vma",
        ]
    )
    lines.extend(_pf_pte_setup_sv32(_VA_PF_PAGE_RV32, pte_flags))
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines.extend(
        [
            "\n# Testcase: lw load page fault RV32",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV32)})",
            test_data.add_testcase("lw_load_page_fault_rv32", coverpoint, covergroup),
            f"lw x{data_reg}, 0(x{addr_reg})",
            "nop",
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            "",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_store_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """
    cp_stval_store_page_fault
    -------------------------
    Trigger a store page fault by mapping the page with R|X but NOT W.
    stval must equal the faulting virtual address (virt_adr_d).
    """
    coverpoint = "cp_stval_store_page_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    pte_flags = "PTE_D | PTE_A | PTE_R | PTE_X | PTE_V"

    lines = [
        comment_banner(coverpoint, "Store Page Fault (R|X PTE, no W)"),
        "",
        "#if __riscv_xlen == 64",
        "# RV64: Sv39",
        "SATP_SETUP_RV64(sv39)",
        "sfence.vma",
    ]
    lines.extend(_pf_pte_setup_sv39(_VA_PF_PAGE_RV64, pte_flags))
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines.extend(
        [
            "\n# Testcase: sw store page fault RV64",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV64)})",
            f"LI(x{data_reg}, 0xDEADBEEF)",
            test_data.add_testcase("sw_store_page_fault_rv64", coverpoint, covergroup),
            f"sw x{data_reg}, 0(x{addr_reg})",
            "nop",
            "\n# Testcase: sd store page fault RV64",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV64)})",
            f"LI(x{data_reg}, 0xDEADBEEFDEADBEEF)",
            test_data.add_testcase("sd_store_page_fault_rv64", coverpoint, covergroup),
            f"sd x{data_reg}, 0(x{addr_reg})",
            "nop",
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            "",
            "#else",
            "# RV32: Sv32",
            "SATP_SETUP_SV32",
            "sfence.vma",
        ]
    )
    lines.extend(_pf_pte_setup_sv32(_VA_PF_PAGE_RV32, pte_flags))
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    lines.extend(
        [
            "\n# Testcase: sw store page fault RV32",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV32)})",
            f"LI(x{data_reg}, 0xDEADBEEF)",
            test_data.add_testcase("sw_store_page_fault_rv32", coverpoint, covergroup),
            f"sw x{data_reg}, 0(x{addr_reg})",
            "nop",
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            "",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_instr_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """
    cp_stval_instr_page_fault
    -------------------------
    Trigger an instruction page fault by mapping the page with R|W but NOT X.
    stval must equal the faulting PC (virt_adr_i = jalr target address).
    x4 = 0xACCE signals the trap handler to use ra (x1) as return address.
    """
    coverpoint = "cp_stval_instr_page_fault"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 1, 4])

    pte_flags = "PTE_D | PTE_A | PTE_R | PTE_W | PTE_V"

    lines = [
        comment_banner(coverpoint, "Instruction Page Fault (R|W PTE, no X)"),
        "",
        "#if __riscv_xlen == 64",
        "# RV64: Sv39",
        "SATP_SETUP_RV64(sv39)",
        "sfence.vma",
    ]
    lines.extend(_pf_pte_setup_sv39(_VA_PF_PAGE_RV64, pte_flags))
    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            "\n# Testcase: jalr instr page fault RV64",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV64)})",
            "LI(x4, 0xACCE)",
            test_data.add_testcase("jalr_instr_page_fault_rv64", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            "",
            "#else",
            "# RV32: Sv32",
            "SATP_SETUP_SV32",
            "sfence.vma",
        ]
    )
    lines.extend(_pf_pte_setup_sv32(_VA_PF_PAGE_RV32, pte_flags))
    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
            "\n# Testcase: jalr instr page fault RV32",
            f"LI(x{addr_reg}, {hex(_VA_PF_PAGE_RV32)})",
            "LI(x4, 0xACCE)",
            test_data.add_testcase("jalr_instr_page_fault_rv32", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            "",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([addr_reg])
    return lines


@add_priv_test_generator(
    "Sstvala",
    required_extensions=["S", "Zicsr", "Sstvala"],
    extra_defines=[
        "#define SKIP_MEPC",
        "#define rvtest_strap_routine",  # causes framework to emit rvtest_Sroot_pg_tbl
    ],
)
def _generate_sstvala_tests(test_data: TestData) -> list[str]:
    """Generate all Sstvala tests running in S-mode."""
    lines = []

    lines.extend(
        [
            "# Initialize scratch memory with test data",
            "LA(x10, scratch)",
            "LI(x11, 0xDEADBEEF)",
            "sw x11, 0(x10)",
            "sw x11, 4(x10)",
            "sw x11, 8(x10)",
            "sw x11, 12(x10)",
            "",
        ]
    )

    lines.extend(_generate_page_table_data_section())

    # Delegate exceptions to S-mode via medeleg.
    # 0xB0F7 = bits {15,13,12,7,6,5,4,2,1,0}
    medeleg_reg = test_data.int_regs.get_register(exclude_regs=[0])
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            f"LI(x{medeleg_reg}, 0xB0F7)",
            f"csrw medeleg, x{medeleg_reg}",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )
    test_data.int_regs.return_registers([medeleg_reg])

    # Use shared helpers from ExceptionsCommon wherever possible.
    # The coverpoint names in ExceptionsCommon differ slightly from the original
    # Sstvala names (e.g. cp_load_access_fault vs cp_stval_load_access_fault).
    # Per the reviewer's guidance either naming is acceptable; we keep the
    # ExceptionsCommon names here so the coverage file and test plan can be
    # updated to match rather than duplicating generator code.
    lines.extend(generate_load_access_fault_tests(test_data, covergroup))
    lines.extend(generate_store_access_fault_tests(test_data, covergroup))
    lines.extend(generate_instr_access_fault_tests(test_data, covergroup))
    lines.extend(generate_load_address_misaligned_tests(test_data, covergroup))
    lines.extend(generate_store_address_misaligned_tests(test_data, covergroup))
    lines.extend(generate_instr_adr_misaligned_jalr_tests(test_data, covergroup))
    lines.extend(generate_illegal_instruction_tests(test_data, covergroup))

    lines.extend(["", "# --- Page-fault tests (VM required) ---", "RVTEST_GOTO_MMODE"])

    lines.extend(_generate_load_page_fault_tests(test_data, covergroup))
    lines.extend(_generate_store_page_fault_tests(test_data, covergroup))
    lines.extend(_generate_instr_page_fault_tests(test_data, covergroup))

    medeleg_reg = test_data.int_regs.get_register(exclude_regs=[0])
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "csrwi satp, 0",
            "sfence.vma",
            f"LI(x{medeleg_reg}, 0)",
            f"csrw medeleg, x{medeleg_reg}",
        ]
    )
    test_data.int_regs.return_registers([medeleg_reg])

    return lines
