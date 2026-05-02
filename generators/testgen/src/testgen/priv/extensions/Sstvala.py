##################################
# priv/extensions/Sstvala.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Sstvala test generator
# ayesha.anwaar2005@gmail.com Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstvala S-mode test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

covergroup = "Sstvala_cg"


def _generate_load_access_fault_tests(
    test_data: TestData,
    covergroup: str,
    *,
    use_sigupd: bool = True,
) -> list[str]:
    """Generate load-access-fault testcases."""
    coverpoint = "cp_stval_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = ["#ifdef RVMODEL_ACCESS_FAULT_ADDRESS", comment_banner(coverpoint, "Load Access Fault")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for op in load_ops:
        lines.append(f"\n# Testcase: {op} access fault")
        # LA is correct: RVMODEL_ACCESS_FAULT_ADDRESS is an assembler symbol.
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        if use_sigupd:
            lines.append(f"LI(x{check_reg}, 0xB0BACAFE)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{check_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )
        if use_sigupd:
            lines.append(write_sigupd(check_reg, test_data))

    lines.extend(["", "#if __riscv_xlen == 64"])
    for op in ["lwu", "ld"]:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        if use_sigupd:
            lines.append(f"LI(x{check_reg}, 0xB0BACAFE)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{check_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )
        if use_sigupd:
            lines.append(write_sigupd(check_reg, test_data))
    lines.extend(["", "#endif", "#endif"])

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def _generate_store_access_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_stval_store_access_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = ["#ifdef RVMODEL_ACCESS_FAULT_ADDRESS", comment_banner(coverpoint, "Store Access Fault")]

    store_ops = ["sb", "sh", "sw"]
    test_values = {"sb": "0xAB", "sh": "0xBEAD", "sw": "0xADDEDCAB", "sd": "0xADDEDCABADDEDCAB"}

    for op in store_ops:
        lines.extend(
            [
                f"\n# Testcase: {op} access fault",
                # FIX: LA instead of LI — RVMODEL_ACCESS_FAULT_ADDRESS is an
                # assembler symbol, not a plain numeric constant.
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{data_reg}, {test_values[op]})",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{data_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )

    lines.extend(
        [
            "",
            "#if __riscv_xlen == 64",
            "\n# Testcase: sd access fault",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"LI(x{data_reg}, {test_values['sd']})",
            test_data.add_testcase("sd_fault", coverpoint, covergroup),
            f"sd x{data_reg}, 0(x{addr_reg})",
            "nop",
            "",
            "#endif",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_instr_access_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_stval_instr_access_fault"
    # Exclude x4 since it contains 0xACCE used by the trap handler
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 4])

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(coverpoint, "Instruction Access Fault"),
        f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        "LI(x4, 0xACCE)",  # trap handler checks x4 and uses x1 (ra) as return address
        test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
        f"jalr x1, 0(x{addr_reg})",
        "nop",
        "#endif",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def add_load_misaligned_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    *,
    use_sentinel: bool = True,
) -> list[str]:
    """Generate a single load-misaligned testcase."""
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    t_lines: list[str] = [
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
    ]
    if use_sentinel:
        t_lines.append(f"LI(x{check_reg}, 0xB0BACAFE)")
    t_lines.extend(
        [
            test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
            f"{op} x{check_reg}, 0(x{addr_reg})",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return t_lines


def _generate_load_address_misaligned_tests(
    test_data: TestData,
    covergroup: str,
    *,
    use_sentinel: bool = True,
) -> list[str]:
    """Generate load-misaligned testcases for all load ops and offsets 0-7."""
    coverpoint = "cp_stval_load_misaligned_fault"
    lines = [comment_banner(coverpoint, "Load Address Misaligned")]

    load_ops = ["lw"]

    for offset in range(8):
        for op in load_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(
                add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup, use_sentinel=use_sentinel)
            )

    return lines


def add_store_misaligned_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, data_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    t_lines = [
        f"LI(x{data_reg}, 0xDEADBEEF)",
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f"{op} x{data_reg}, 0(x{addr_reg})",
        "nop",
        # Read back scratch memory to verify store result
        f"LA(x{addr_reg}, scratch)",
        f"lw x{check_reg}, 0(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        f"lw x{check_reg}, 4(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        f"lw x{check_reg}, 8(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        f"lw x{check_reg}, 12(x{addr_reg})",
        write_sigupd(check_reg, test_data),
    ]

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg])
    return t_lines


def _generate_store_address_misaligned_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_stval_store_misaligned_fault"
    lines = [comment_banner(coverpoint, "Store Address Misaligned")]

    store_ops = ["sw"]

    for offset in range(8):
        for op in store_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("\n#if __riscv_xlen == 64")
        lines.append(f"\n# Testcase: sd with offset {offset} (LSBs: {offset:03b})")
        lines.extend(add_store_misaligned_test("sd", offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

    return lines


def _generate_instr_adr_misaligned_jalr_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_stval_instr_misaligned_fault"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JALR"),
    ]

    offsets_for_lsb = {0: 8, 1: 9, 2: 6, 3: 7}

    for rs1_lsb in range(4):
        for offset_lsb in range(4):
            base_off = offsets_for_lsb[rs1_lsb]
            jalr_off = offsets_for_lsb[offset_lsb]

            lines.extend(
                [
                    f"\n# rs1[1:0]={rs1_lsb:02b}, offset[1:0]={offset_lsb:02b}",
                    ".align 2",
                    f"auipc x{addr_reg}, 0",
                    f"addi x{addr_reg}, x{addr_reg}, {base_off}",
                    test_data.add_testcase(f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", coverpoint, covergroup),
                    f"jalr x1, {jalr_off}(x{addr_reg})",
                    "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
                    "addi x0, x2, 0",
                ]
            )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_illegal_instruction_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_stval_illegal_instr"

    lines = [
        comment_banner(coverpoint, "Illegal Instruction"),
        ".align 2",
        test_data.add_testcase("illegal_0x00000000", coverpoint, covergroup),
        ".word 0x00000000",
        "nop",
        ".align 2",
        test_data.add_testcase("illegal_0xFFFFFFFF", coverpoint, covergroup),
        ".word 0xFFFFFFFF",
        "nop",
    ]
    return lines


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
    """Emit Sv39 page-table wiring with 1 GiB identity map for code+data region."""
    return [
        # Identity-map the 1 GiB region at 0x80000000 using a LEVEL2 superpage.
        # This covers code (0x80000440), trap handler (0x800034C0),
        # and all data/page-table pages (0x8000D000 etc.) in one entry.
        "SUPERPAGE_PTE_SETUP_SV39(rvtest_code_begin, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V), 0x80000000, LEVEL2)",
        # Wire L2 → L1 for fault VA
        f"PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), {hex(va)}, LEVEL2)",
        # Wire L1 → L0 for fault VA
        f"PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va)}, LEVEL1)",
        # Leaf PTE with caller-supplied permission flags
        f"PTE_SETUP_SV39(rvtest_pf_data, ({pte_flags}), {hex(va)}, LEVEL0)",
        "sfence.vma",
    ]


def _pf_pte_setup_sv32(va: int, pte_flags: str) -> list[str]:
    """
    Emit Sv32 page-table wiring for a single 4 KiB mapping at *va*.

    Also adds a superpage identity map for the code region (0x80000000)
    so the S-mode trap handler at 0x80002180 (Strampoline) remains
    reachable after VM is enabled.  Without this, any trap under VM
    causes a fetch-page-fault on the handler itself → infinite loop.

    SUPERPAGE_PTE_SETUP_SV32 writes a leaf PTE directly into the root
    page table (rvtest_Sroot_pg_tbl) at the VPN[1] index, mapping a
    full 4 MiB superpage PA→VA identity.
    """
    return [
        # Identity-map the 4 MiB superpage at 0x80000000 (covers trap handler,
        # code, and data regions) with RWX so all accesses succeed under VM.
        "SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V), 0x80000000, LEVEL1)",
        # Wire root → leaf page table for the fault VA
        f"PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va)}, LEVEL1)",
        # Leaf PTE with caller-supplied permission flags
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

    # PTE_D|PTE_A|PTE_W|PTE_V — no R bit → reserved; load page fault
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

    # PTE_D|PTE_A|PTE_R|PTE_X|PTE_V — no W bit → store page fault
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
    # Exclude x4 (trap-handler sentinel) and x1 (jalr link register)
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 1, 4])

    # PTE_D|PTE_A|PTE_R|PTE_W|PTE_V — no X bit → instruction page fault
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
    required_extensions=["S", "Zicsr"],
    extra_defines=[
        "#define SKIP_MEPC",
        "#define rvtest_strap_routine",  # causes framework to emit rvtest_Sroot_pg_tbl
    ],
)
def _generate_sstvala_tests(test_data: TestData) -> list[str]:
    """Generate all Sstvala tests running in S-mode."""
    lines = []

    # Initialize scratch memory in M-mode (we start in M-mode)
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

    # -----------------------------------------------------------------------
    # Inject additional page-table labels into .data via .pushsection.
    # Must be done before any PTE_SETUP_* macro references them.
    # rvtest_Sroot_pg_tbl is already emitted by the framework via
    # rvtest_strap_routine; we only declare the three additional labels here.
    # -----------------------------------------------------------------------
    lines.extend(_generate_page_table_data_section())

    # -----------------------------------------------------------------------
    # Delegate exceptions to S-mode via medeleg.
    # Bits: instr-misaligned(0), instr-AF(1), illegal(2),
    #       load-misaligned(4), load-AF(5), store-misaligned(6), store-AF(7),
    #       instr-PF(12), load-PF(13), store-PF(15)
    # 0xB0F7 = bits {15,13,12,7,6,5,4,2,1,0}
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Non-VM fault tests (run in S-mode with medeleg already set)
    # -----------------------------------------------------------------------
    lines.extend(_generate_load_access_fault_tests(test_data, covergroup))
    lines.extend(_generate_store_access_fault_tests(test_data, covergroup))
    lines.extend(_generate_instr_access_fault_tests(test_data, covergroup))
    lines.extend(_generate_load_address_misaligned_tests(test_data, covergroup))
    lines.extend(_generate_store_address_misaligned_tests(test_data, covergroup))
    lines.extend(_generate_instr_adr_misaligned_jalr_tests(test_data, covergroup))
    lines.extend(_generate_illegal_instruction_tests(test_data, covergroup))

    # -----------------------------------------------------------------------
    # Page-fault tests — each function handles both RV64 (Sv39) and RV32
    # (Sv32) via #if __riscv_xlen == 64 / #else guards, enables VM, runs
    # its fault category, then disables VM. Must be in M-mode on entry.
    # -----------------------------------------------------------------------
    lines.extend(["", "# --- Page-fault tests (VM required) ---", "RVTEST_GOTO_MMODE"])

    lines.extend(_generate_load_page_fault_tests(test_data, covergroup))
    lines.extend(_generate_store_page_fault_tests(test_data, covergroup))
    lines.extend(_generate_instr_page_fault_tests(test_data, covergroup))

    # -----------------------------------------------------------------------
    # Tear-down: return to M-mode, clear medeleg, ensure VM is off
    # -----------------------------------------------------------------------
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
