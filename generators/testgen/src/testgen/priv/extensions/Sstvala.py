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
# Page-fault test infrastructure
#
# Each page-fault test:
#   1. Builds a small page table with an identity superpage for code/data and
#      a single 4 KiB leaf entry for `_VA_PF_PAGE_*`.
#   2. The leaf PTE permissions are chosen to provoke the desired fault:
#         load page fault  – W only (reserved encoding, no R)
#         store page fault – R|X    (no W)
#         instr page fault – R|W    (no X)
#   3. Drops to S-mode, performs the access, then returns to M-mode and
#      disables translation.
#
# Page-table labels (declared in _generate_page_table_data_section):
#   rvtest_Sroot_pg_tbl  — root PT (emitted by the framework)
#   rvtest_slvl1_pg_tbl  — Sv39 L1 intermediate PT
#   rvtest_slvl0_pg_tbl  — Sv39/Sv32 leaf PT
#   rvtest_pf_data       — physical backing page for the fault VA
# ---------------------------------------------------------------------------

# Virtual address for RV64/Sv39 page-fault tests (canonical, page-aligned)
_VA_PF_PAGE_RV64 = 0x140300000

# Virtual address for RV32/Sv32 page-fault tests (fits in 32 bits, page-aligned)
_VA_PF_PAGE_RV32 = 0xC0300000


def _generate_page_table_data_section() -> list[str]:
    """Inject the additional page-table labels needed by `PTE_SETUP_SV*` macros.

    `rvtest_Sroot_pg_tbl` is already emitted by the framework (RVTEST_DATA_END),
    so we only declare the intermediate Sv39 PT, the shared leaf PT, and the
    physical backing page for the fault VA. All three are 4 KiB and 4 KiB-aligned.
    """
    return [
        "",
        "# Page-table labels for Sstvala page-fault tests (rvtest_Sroot_pg_tbl is",
        "# already declared by the framework). Injected into .data via .pushsection.",
        ".pushsection .data",
        ".align 12",
        "rvtest_slvl1_pg_tbl: .zero 4096   # Sv39 L1 intermediate PT (unused on Sv32)",
        ".align 12",
        "rvtest_slvl0_pg_tbl: .zero 4096   # leaf PT (Sv39/Sv32)",
        ".align 12",
        "rvtest_pf_data:      .zero 4096   # physical backing page for the fault VA",
        ".popsection",
        "",
    ]


def _pf_identity_map_sv39() -> list[str]:
    """Sv39 1 GiB identity superpage covering the code/data region.

    Hand-rolled (rather than `SUPERPAGE_PTE_SETUP_SV39`) because the framework
    macro requires the VA to be a constant immediate, but we need to map
    whatever PA the linker chose for `rvtest_code_begin` back to itself.
    """
    return [
        "# Sv39: 1 GiB identity superpage for code+data (PC-relative, link-address agnostic)",
        "auipc t0, 0",
        "li t1, ~((1 << 30) - 1)",  # 1 GiB alignment mask
        "and t0, t0, t1",  # t0 = superpage base PA
        "srli t0, t0, 12",
        "slli t0, t0, 10",  # PPN in PTE position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",
        "LA(t1, rvtest_code_begin)",
        "srli t1, t1, 30",  # VPN[2]
        "andi t1, t1, 0x1FF",
        "slli t1, t1, 3",  # 8 bytes/entry
        "add t2, t2, t1",
        "sd t0, 0(t2)",
        "sfence.vma",
    ]


def _pf_identity_map_sv32() -> list[str]:
    """Sv32 4 MiB identity superpage covering the code/data region.

    Hand-rolled for the same reason as the Sv39 variant above.
    """
    return [
        "# Sv32: 4 MiB identity superpage for code+data (PC-relative, link-address agnostic)",
        "auipc t0, 0",
        "li t1, ~((1 << 22) - 1)",  # 4 MiB alignment mask
        "and t0, t0, t1",  # t0 = superpage base PA
        "srli t0, t0, 12",
        "slli t0, t0, 10",  # PPN in PTE position
        "li t1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V)",
        "or t0, t0, t1",  # leaf PTE value
        "LA(t2, rvtest_Sroot_pg_tbl)",
        "LA(t1, rvtest_code_begin)",
        "srli t1, t1, 22",  # VPN[1]
        "andi t1, t1, 0x3FF",
        "slli t1, t1, 2",  # 4 bytes/entry
        "add t2, t2, t1",
        "sw t0, 0(t2)",
        "sfence.vma",
    ]


def _pf_pte_setup_sv39(va: int, pte_flags: str) -> list[str]:
    """Wire up the Sv39 page-table chain that maps `va` to a leaf with `pte_flags`."""
    return [
        *_pf_identity_map_sv39(),
        f"PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), {hex(va)}, LEVEL2)",
        f"PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va)}, LEVEL1)",
        f"PTE_SETUP_SV39(rvtest_pf_data, ({pte_flags}), {hex(va)}, LEVEL0)",
        "sfence.vma",
    ]


def _pf_pte_setup_sv32(va: int, pte_flags: str) -> list[str]:
    """Wire up the Sv32 page-table chain that maps `va` to a leaf with `pte_flags`."""
    return [
        *_pf_identity_map_sv32(),
        f"PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), {hex(va)}, LEVEL1)",
        f"PTE_SETUP_SV32(rvtest_pf_data, ({pte_flags}), {hex(va)}, LEVEL0)",
        "sfence.vma",
    ]


def _emit_pf_block(
    test_data: TestData,
    *,
    coverpoint: str,
    covergroup: str,
    pte_flags: str,
    instrs_rv64: list[tuple[str, list[str]]],
    instrs_rv32: list[tuple[str, list[str]]],
    section_title: str,
    extra_setup: list[str] | None = None,
) -> list[str]:
    """Emit one page-fault test section.

    `instrs_*` is a list of (testcase_name, asm_lines) pairs for the inner XLEN block.
    The wrapper takes care of SATP setup, identity map, page-table wiring, dropping
    to S-mode, and tearing the VM back down on the way out.
    """
    extra_setup = extra_setup or []

    def _xlen_block(setup: list[str], pf_setup: list[str], instrs: list[tuple[str, list[str]]]) -> list[str]:
        block: list[str] = [*setup, "sfence.vma", *pf_setup, "RVTEST_GOTO_LOWER_MODE Smode"]
        for name, asm in instrs:
            block.append(f"\n# Testcase: {name}")
            block.extend(extra_setup)
            block.append(test_data.add_testcase(name, coverpoint, covergroup))
            block.extend(asm)
            block.append("nop")
        block.extend(["RVTEST_GOTO_MMODE", "csrwi satp, 0", "sfence.vma", ""])
        return block

    lines = [comment_banner(coverpoint, section_title), ""]
    lines.append("#if __riscv_xlen == 64")
    lines.append("# RV64: Sv39")
    lines.extend(_xlen_block(["SATP_SETUP_RV64(sv39)"], _pf_pte_setup_sv39(_VA_PF_PAGE_RV64, pte_flags), instrs_rv64))
    lines.append("#else")
    lines.append("# RV32: Sv32")
    lines.extend(_xlen_block(["SATP_SETUP_SV32"], _pf_pte_setup_sv32(_VA_PF_PAGE_RV32, pte_flags), instrs_rv32))
    lines.append("#endif")
    return lines


def _generate_load_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """cp_stval_load_page_fault — W-only PTE → load page fault on lw/ld."""
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    def _load(mnemonic: str, va: int, suffix: str) -> tuple[str, list[str]]:
        return (
            f"{mnemonic}_load_page_fault_{suffix}",
            [f"LI(x{addr_reg}, {hex(va)})", f"{mnemonic} x{data_reg}, 0(x{addr_reg})"],
        )

    lines = _emit_pf_block(
        test_data,
        coverpoint="cp_stval_load_page_fault",
        covergroup=covergroup,
        pte_flags="PTE_D | PTE_A | PTE_W | PTE_V",
        instrs_rv64=[_load("lw", _VA_PF_PAGE_RV64, "rv64"), _load("ld", _VA_PF_PAGE_RV64, "rv64")],
        instrs_rv32=[_load("lw", _VA_PF_PAGE_RV32, "rv32")],
        section_title="Load Page Fault (W-only PTE, no R)",
    )
    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_store_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """cp_stval_store_page_fault — R|X PTE (no W) → store page fault on sw/sd."""
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    def _store(mnemonic: str, va: int, value: int, suffix: str) -> tuple[str, list[str]]:
        return (
            f"{mnemonic}_store_page_fault_{suffix}",
            [
                f"LI(x{addr_reg}, {hex(va)})",
                f"LI(x{data_reg}, {hex(value)})",
                f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
            ],
        )

    lines = _emit_pf_block(
        test_data,
        coverpoint="cp_stval_store_page_fault",
        covergroup=covergroup,
        pte_flags="PTE_D | PTE_A | PTE_R | PTE_X | PTE_V",
        instrs_rv64=[
            _store("sw", _VA_PF_PAGE_RV64, 0xDEADBEEF, "rv64"),
            _store("sd", _VA_PF_PAGE_RV64, 0xDEADBEEFDEADBEEF, "rv64"),
        ],
        instrs_rv32=[_store("sw", _VA_PF_PAGE_RV32, 0xDEADBEEF, "rv32")],
        section_title="Store Page Fault (R|X PTE, no W)",
    )
    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_instr_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """cp_stval_instr_page_fault — R|W PTE (no X) → instruction page fault on jalr.

    x4 = 0xACCE signals the trap handler to use ra (x1) as the return address.
    """
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 1, 4])

    def _jalr(va: int, suffix: str) -> tuple[str, list[str]]:
        return (
            f"jalr_instr_page_fault_{suffix}",
            [f"LI(x{addr_reg}, {hex(va)})", f"jalr x1, 0(x{addr_reg})"],
        )

    lines = _emit_pf_block(
        test_data,
        coverpoint="cp_stval_instr_page_fault",
        covergroup=covergroup,
        pte_flags="PTE_D | PTE_A | PTE_R | PTE_W | PTE_V",
        instrs_rv64=[_jalr(_VA_PF_PAGE_RV64, "rv64")],
        instrs_rv32=[_jalr(_VA_PF_PAGE_RV32, "rv32")],
        section_title="Instruction Page Fault (R|W PTE, no X)",
        extra_setup=["LI(x4, 0xACCE)"],
    )
    test_data.int_regs.return_registers([addr_reg])
    return lines


@add_priv_test_generator(
    "Sstvala",
    required_extensions=["Sstvala"],
    march_extensions=["S", "Zicsr"],
    extra_defines=[
        "#define SKIP_MEPC",
    ],
)
def _generate_sstvala_tests(test_data: TestData) -> list[str]:
    """Generate all Sstvala tests running in S-mode."""
    lines = []

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

    # Reuse the shared helpers from ExceptionsCommon. These emit their own
    # coverpoint names (cp_load_access_fault, etc.) — Sstvala_coverage.svh
    # references those names directly.
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
            f"LI(x{medeleg_reg}, 0)",
            f"csrw medeleg, x{medeleg_reg}",
        ]
    )
    test_data.int_regs.return_registers([medeleg_reg])

    return lines
