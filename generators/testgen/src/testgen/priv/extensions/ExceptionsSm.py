##################################
# priv/extensions/ExceptionsSm.py
#
# ExceptionsSm extension exception test generator.
# jgong@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sm extension exception test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_instr_adr_misaligned_branch_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_branch"
    temp_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    lines = [comment_banner(coverpoint, "Instruction Address Misaligned branch")]
    lines.append(test_data.add_testcase(coverpoint, "taken_branch_pc_6", covergroup))
    branches = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    rs1 = ["x0", "x0", "x0", f"x{temp_reg}", "x0", "x0"]
    rs2 = ["x0", f"x{temp_reg}", f"x{temp_reg}", "x0", f"x{temp_reg}", "x0"]
    lines.append(f"\nli x{temp_reg}, 1")
    lines.append(".align 2")
    for i in range(6):
        lines.append(f"{branches[i]} {rs1[i]}, {rs2[i]}, .+6")
        lines.append(".word 0x00010013")
    lines.append(f"    CSRR(x{check_reg}, mcause)")
    lines.append(write_sigupd(check_reg, test_data))

    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def _generate_instr_adr_misaligned_branch_nottaken(test_data: TestData) -> list[str]:
    """Generate misaligned instruction address?????."""
    lines = [
        comment_banner(
            "cp_instr_adr_misaligned_branch_nottaken",
            "Branch to an unaligned address (PC+6). Should not cause an exception",
        ),
    ]

    covergroup = "ExceptionsSm_cg"
    coverpoint = "cp_instr_adr_misaligned_branch_nottaken"
    check_reg, temp_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    b_op = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    r1 = ["x0", "x0", f"x{temp_reg}", "x0", f"x{temp_reg}", "x0"]
    r2 = [f"x{temp_reg}", "x0", "x0", f"x{temp_reg}", "x0", f"x{temp_reg}"]

    lines.extend(
        [
            ".align 2",
            f"li x{temp_reg}, 1",
            test_data.add_testcase(coverpoint, "nottaken_branch_pc_6", covergroup),
            f"li x{check_reg}, 1",
        ]
    )

    for i in range(6):
        lines.append(f"{b_op[i]} {r1[i]}, {r2[i]}, .+6")
    lines.append(write_sigupd(check_reg, test_data))

    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def _generate_instr_adr_misaligned_jal_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned JAL exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_jal"

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JAL"),
        "#ifndef RV32C",
        "#ifndef RV64C",
        "    .align 2",
        test_data.add_testcase(coverpoint, "jal_misaligned", covergroup),
        "    jal x0, .+6      # Jump to PC+6 (odd multiple of 2)",
        "    .word 0x00010013 # Target instruction (skipped)",
        "#endif",
        "#endif",
        "",
    ]

    return lines


def _generate_instr_adr_misaligned_jalr_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned JALR exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_jalr"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JALR"),
        "#ifndef RV32C",
        "#ifndef RV64C",
    ]

    # Base offsets to achieve rs1[1:0] values
    rs1_base_offsets = {0: 8, 1: 5, 2: 6, 3: 7}
    # JALR immediate offsets to achieve offset[1:0] values
    jalr_offsets = {0: 8, 1: 5, 2: 6, 3: 7}

    for rs1_lsb in range(4):
        for offset_lsb in range(4):
            base_off = rs1_base_offsets[rs1_lsb]
            jalr_off = jalr_offsets[offset_lsb]

            lines.extend(
                [
                    f"\n# rs1[1:0]={rs1_lsb:02b}, offset[1:0]={offset_lsb:02b}",
                    "    .align 2",
                    test_data.add_testcase(coverpoint, f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", covergroup),
                    f"    auipc x{addr_reg}, 0",
                    f"    addi x{addr_reg}, x{addr_reg}, {base_off}",
                    f"    jalr x1, {jalr_off}(x{addr_reg})",
                ]
            )

            # From original: add nop only when rs1[0] is set
            if rs1_lsb & 1:
                lines.append("    nop")

            lines.append("    .word 0x00010013")

    lines.extend(
        [
            "#endif",
            "#endif",
            "",
        ]
    )

    test_data.int_regs.return_registers([addr_reg])
    return lines


# def _generate_instr_access_fault_tests(test_data: TestData) -> list[str]:
#     """Generate instruction access fault exception tests."""
#     covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_access_fault"
#     addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

#     lines = [
#         comment_banner(coverpoint, "Instruction Access Fault"),
#         test_data.add_testcase(coverpoint, "instr_access_fault", covergroup),
#         f"    li x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
#         f"    jalr x1, 0(x{addr_reg})",
#         "    nop",
#         "    nop",
#         "",
#     ]

#     test_data.int_regs.return_registers([addr_reg])
#     return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    """Generate illegal instruction exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_illegal_instruction"

    lines = [
        comment_banner(coverpoint, "Illegal Instruction"),
        "    .align 2",
        test_data.add_testcase(coverpoint, "illegal_0x00000000", covergroup),
        "    .word 0x00000000",
        "    nop",
        "",
        "    .align 2",
        test_data.add_testcase(coverpoint, "illegal_0xFFFFFFFF", covergroup),
        "    .word 0xFFFFFFFF",
        "    nop",
        "",
    ]

    return lines


def _generate_illegal_instruction_seed_tests(test_data: TestData) -> list[str]:
    """Generate illegal instruction seed exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_illegal_instruction_seed"
    dest_regs = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Illegal Instruction Seed"),
        test_data.add_testcase(coverpoint, "seed_readonly_access", covergroup),
        f"    csrrs x{dest_regs[0]}, seed, x0",
        "nop",
        f"    csrrc x{dest_regs[1]}, seed, x0",
        "nop",
        f"    csrrsi x{dest_regs[2]}, seed, 0",
        "nop",
        f"    csrrci x{dest_regs[3]}, seed, 0",
        "nop",
        "",
    ]

    test_data.int_regs.return_registers(dest_regs)
    return lines


def _generate_breakpoint_tests(test_data: TestData) -> list[str]:
    """Generate breakpoint exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "Breakpoint"),
        test_data.add_testcase(coverpoint, "ebreak", covergroup),
        "    ebreak",
        "",
    ]

    return lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate load address misaligned exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_load_address_misaligned"

    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Load Address Misaligned")]

    # Define load operations based on XLEN
    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]
    if test_data.xlen == 64:
        load_ops.extend(["lwu", "ld"])

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")

        lines.extend(
            [
                f"    LA(x{addr_reg}, scratch)",
                f"    addi x{addr_reg}, x{addr_reg}, {offset}",
            ]
        )

        for op in load_ops:
            lines.extend(
                [
                    test_data.add_testcase(coverpoint, f"{op}_off{offset}", covergroup),
                    f"    {op} x{check_reg}, 0(x{addr_reg})",
                ]
            )

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate load access fault exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_load_access_fault"
    addr_reg, check_regs = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Load Access Fault"),
        "    .align 2",
        test_data.add_testcase(coverpoint, "load_access_fault", covergroup),
        f"    li x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
    ]

    # Define load operations - all use the same destination register
    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]
    if test_data.xlen == 64:
        load_ops.extend(["lwu", "ld"])

    for op in load_ops:
        lines.append(f"    {op} x{check_regs}, 0(x{addr_reg})")

    lines.append("")

    test_data.int_regs.return_registers([addr_reg, check_regs])
    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate store address misaligned exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_store_address_misaligned"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Store Address Misaligned")]

    # Define store operations based on XLEN
    store_ops = ["sb", "sh", "sw"]
    if test_data.xlen == 64:
        store_ops.append("sd")

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")

        lines.extend(
            [
                f"    LA(x{addr_reg}, scratch)",
                f"    addi x{addr_reg}, x{addr_reg}, {offset}",
                f"    li x{data_reg}, 0xDECAFCAB",  # Match original test value
            ]
        )

        for op in store_ops:
            lines.extend(
                [
                    test_data.add_testcase(coverpoint, f"{op}_off{offset}", covergroup),
                    f"    {op} x{data_reg}, 0(x{addr_reg})",
                ]
            )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_store_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate store access fault exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_store_access_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Store Access Fault"),
        "    .align 2",
        f"    li x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
    ]

    store_ops = ["sb", "sh", "sw"]
    if test_data.xlen == 64:
        store_ops.append("sd")

    # Different test values for each store
    test_values = {"sb": "0xAB", "sh": "0xBEAD", "sw": "0xADDEDCAB", "sd": "0xDEADBEEFDEADBEEF"}

    for op in store_ops:
        lines.extend(
            [
                test_data.add_testcase(coverpoint, f"{op}_fault", covergroup),
                f"    li x{data_reg}, {test_values[op]}",
                f"    {op} x{data_reg}, 0(x{addr_reg})",
            ]
        )

    lines.append("")

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_ecall_m_tests(test_data: TestData) -> list[str]:
    """Generate ecall machine mode tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_ecall_m"

    lines = [
        comment_banner(coverpoint, "Ecall Machine Mode"),
        test_data.add_testcase(coverpoint, "ecall_m", covergroup),
        "    ecall",
        "    nop",
        "",
    ]

    return lines


def _generate_misaligned_priority_load_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned JAL exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_misaligned_priority_load"
    addr_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 1])

    lines = [comment_banner(coverpoint, "Misaligned Priority Load")]

    load_ops = ["lh", "lhu", "lw", "lb", "lbu"]
    if test_data.xlen == 64:
        load_ops.extend(["lwu", "ld"])
    lines.append(f"    la x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS")
    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) - Access fault + Misaligned")

        lines.extend(
            [
                f"    addi x{temp_reg}, x{addr_reg}, {offset}",
            ]
        )

        for op in load_ops:
            lines.extend(
                [
                    test_data.add_testcase(coverpoint, f"{op}_off{offset}_priority", covergroup),
                    f"    {op} x{check_reg}, 0(x{temp_reg})",
                    "   nop",
                ]
            )

    test_data.int_regs.return_registers([temp_reg, addr_reg, check_reg])
    return lines


def _generate_misaligned_priority_store_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned JAL exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_misaligned_priority_store"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Store")]

    store_ops = ["sb", "sh", "sw"]
    if test_data.xlen == 64:
        store_ops.append("sd")

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) - Access fault + Misaligned")

        # Load fault address, compute offset, and load data ONCE per iteration
        lines.extend(
            [
                f"    la x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
                f"    addi x{addr_reg}, x{addr_reg}, {offset}",
                f"    li x{data_reg}, 0xDECAFCAB",  # Match original value
            ]
        )

        for op in store_ops:
            lines.extend(
                [
                    test_data.add_testcase(coverpoint, f"{op}_off{offset}_priority", covergroup),
                    f"    {op} x{data_reg}, 0(x{addr_reg})",
                    "   nop",
                ]
            )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_misaligned_priority_fetch_tests(test_data: TestData) -> list[str]:
    """Generate instruction address misaligned JAL exception tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_misaligned_priority_fetch"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Misaligned Priority Fetch"),
        "#ifndef RV32C",
        "#ifndef RV64C",
        "    .align 2",
        test_data.add_testcase(coverpoint, "fetch_priority", covergroup),
        f"    li x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS",
        f"    addi x{addr_reg}, x{addr_reg}, 2",  # Make it misaligned
        f"    jalr x0, 0(x{addr_reg})",
        "    nop",
        "    nop",
        "#endif",
        "#endif",
        "",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_mstatus_ie_tests(test_data: TestData) -> list[str]:
    """Generate mstatus interrupt enable tests."""
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_mstatus_ie"
    save_reg, mask_reg, arg_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Mstatus Interrupt Enable"),
        "# Save original mstatus and prepare MIE mask",
        f"    csrr x{save_reg}, mstatus",  # Save original
        f"    li x{mask_reg}, 0x8",  # MIE bit mask (bit 3)
        "",
        "# Test ecall with mstatus.MIE = 0",
        test_data.add_testcase(coverpoint, "ecall_mie_0", covergroup),
        f"    csrrc x0, mstatus, x{mask_reg}",  # Clear MIE bit
        f"    li x{arg_reg}, 3",  # Syscall argument
        "    ecall",
        "",
        "# Test ecall with mstatus.MIE = 1",
        test_data.add_testcase(coverpoint, "ecall_mie_1", covergroup),
        f"    csrrs x0, mstatus, x{mask_reg}",  # Set MIE bit
        f"    li x{arg_reg}, 3",  # Syscall argument
        "    ecall",
        "",
        "# Restore original mstatus",
        f"    csrw mstatus, x{save_reg}",
        "",
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg, arg_reg])
    return lines


@add_priv_test_generator("ExceptionsSm", required_extensions=["I", "Zicsr", "Sm"], march_extensions=[""])
def make_exceptionssm(test_data: TestData) -> list[str]:
    """Main entry point for Sm exception test generation."""
    lines = []

    lines.extend(
        [
            "# Initialize scratch memory with test data",
            "    LA(x10, scratch)",
            "    LI(x11, 0xDEADBEEF)",
            "    sw x11, 0(x10)",
            "    sw x11, 4(x10)",
            "    sw x11, 8(x10)",
            "    sw x11, 12(x10)",
            "",
        ]
    )

    lines.extend(_generate_instr_adr_misaligned_branch_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_branch_nottaken(test_data))
    lines.extend(_generate_instr_adr_misaligned_jal_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_jalr_tests(test_data))
    # lines.extend(_generate_instr_access_fault_tests(test_data))
    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    lines.extend(_generate_ecall_m_tests(test_data))
    lines.extend(_generate_misaligned_priority_load_tests(test_data))
    lines.extend(_generate_misaligned_priority_store_tests(test_data))
    lines.extend(_generate_misaligned_priority_fetch_tests(test_data))
    lines.extend(_generate_mstatus_ie_tests(test_data))
    lines.extend(_generate_illegal_instruction_seed_tests(test_data))
    lines.extend(_generate_breakpoint_tests(test_data))
    lines.extend(_generate_illegal_instruction_tests(test_data))

    return lines
