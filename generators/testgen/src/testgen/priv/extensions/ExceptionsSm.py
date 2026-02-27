##################################
# priv/extensions/ExceptionsSm.py
#
# ExceptionsSm extension exception test generator.
# jgong@hmc.edu Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exceptions Sm test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_instr_adr_misaligned_branch_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_branch"
    temp_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Instruction Address Misaligned branch")]

    lines.extend(
        [f" li x{temp_reg}, 1", " .align 2", test_data.add_testcase("taken_branch_pc_6", coverpoint, covergroup)]
    )

    branches = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    for branch in branches:
        if branch in ("bge", "bgeu"):
            rs1 = f"x{temp_reg}"
            rs2 = "x0"
        elif branch == "beq":
            rs1 = "x0"
            rs2 = "x0"
        else:  # bne, blt, bltu
            rs1 = "x0"
            rs2 = f"x{temp_reg}"

        lines.extend(
            [
                f" {branch} {rs1}, {rs2}, .+6",
                "# branch by 6 lands in upper half of next instruction 0x0001 which is a c.nop",
                " addi x0, x2, 0",
            ]
        )

    lines.extend(
        [
            f" CSRR(x{check_reg}, mcause)",
            write_sigupd(check_reg, test_data),
        ]
    )

    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def _generate_instr_adr_misaligned_branch_nottaken(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_branch_nottaken"
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Branch to an unaligned address is NOT taken (PC+6). Should not cause an exception"),
        " .align 2",
        f" li x{temp_reg}, 1",
        test_data.add_testcase("nottaken_branch_pc_6", coverpoint, covergroup),
    ]

    branches = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    for branch in branches:
        if branch in ("beq", "bge", "bgeu"):
            rs1 = "x0"
            rs2 = f"x{temp_reg}"
        elif branch == "bne":
            rs1 = "x0"
            rs2 = "x0"  # 0 == 0, so bne not taken
        else:  # blt, bltu
            rs1 = f"x{temp_reg}"
            rs2 = "x0"
        lines.append(f" {branch} {rs1}, {rs2}, .+6")

    test_data.int_regs.return_registers([temp_reg])
    return lines


def _generate_instr_adr_misaligned_jal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_jal"

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JAL"),
        test_data.add_testcase("jal_misaligned", coverpoint, covergroup),
        " jal x0, .+6",
        "# branch by 6 lands in upper half of next instruction 0x0001 which is a c.nop",
        " addi x0, x2, 0",
        " nop",
    ]

    return lines


def _generate_instr_adr_misaligned_jalr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_adr_misaligned_jalr"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JALR"),
    ]

    # rs1 is set to PC + base_offset for rs1[1:0]
    # jalr controls the offset[1:0], which covers all 16 combinations of (rs1+offset)[1:0]
    rs1_base_offsets = {0: 8, 1: 5, 2: 6, 3: 7}
    jalr_offsets = {0: 8, 1: 5, 2: 6, 3: 7}

    for rs1_lsb in range(4):
        for offset_lsb in range(4):
            base_off = rs1_base_offsets[rs1_lsb]
            jalr_off = jalr_offsets[offset_lsb]

            lines.extend(
                [
                    f"\n# rs1[1:0]={rs1_lsb:02b}, offset[1:0]={offset_lsb:02b}",
                    " .align 2",
                    f" auipc x{addr_reg}, 0",
                    f" addi x{addr_reg}, x{addr_reg}, {base_off}",
                    test_data.add_testcase(f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", coverpoint, covergroup),
                    f" jalr x1, {jalr_off}(x{addr_reg})",
                    " nop",
                ]
            )

            if rs1_lsb & 1:
                lines.append(" nop")

            lines.extend(
                [
                    "# branch by 6 lands in upper half of next instruction 0x0001 which is a c.nop",
                    "addi x0, x2, 0",
                ]
            )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_instr_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_instr_access_fault"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Access Fault"),
        f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        "LI(x4, 0xACCE)",  # trap handler to use ra as return address
        test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
        f" jalr x1, 0(x{addr_reg})",
        " nop",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_illegal_instruction"

    lines = [
        comment_banner(coverpoint, "Illegal Instruction"),
        " .align 2",
        test_data.add_testcase("illegal_0x00000000", coverpoint, covergroup),
        " .word 0x00000000",
        " nop",
        " .align 2",
        test_data.add_testcase("illegal_0xFFFFFFFF", coverpoint, covergroup),
        " .word 0xFFFFFFFF",
        " nop",
    ]
    return lines


def _generate_illegal_instruction_seed_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_illegal_instruction_seed"
    dest_regs = test_data.int_regs.get_registers(4, exclude_regs=[0])

    seed_ops = [
        (f"csrrs x{dest_regs[0]}, seed, x0", "seed_csrrs"),
        (f"csrrc x{dest_regs[1]}, seed, x0", "seed_csrrc"),
        (f"csrrsi x{dest_regs[2]}, seed, 0", "seed_csrrsi"),
        (f"csrrci x{dest_regs[3]}, seed, 0", "seed_csrrci"),
    ]

    lines = [comment_banner(coverpoint, "Illegal Instruction Seed")]

    for instr, bin_name in seed_ops:
        lines.extend(
            [
                test_data.add_testcase(bin_name, coverpoint, covergroup),
                f" {instr}",
                " nop",
            ]
        )

    test_data.int_regs.return_registers(dest_regs)
    return lines


def _generate_breakpoint_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "Breakpoint"),
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        " ebreak",
        " nop",
    ]
    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Load Access Fault")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]
    if test_data.xlen == 64:
        load_ops.extend(["lwu", "ld"])

    for op in load_ops:
        lines.extend(
            [
                f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f" {op} x{check_reg}, 0(x{addr_reg})",
                " nop",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def _add_load_misaligned_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    t_lines = [
        f" LA(x{addr_reg}, scratch)",
        f" addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f" {op} x{check_reg}, 0(x{addr_reg})",
        " nop",
        write_sigupd(check_reg, test_data),
    ]

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return t_lines


def _add_store_misaligned_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, data_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    t_lines = [
        f" LI(x{data_reg}, 0xDEADBEEF)",
        f" LA(x{addr_reg}, scratch)",
        f" addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f" {op} x{data_reg}, 0(x{addr_reg})",
        " nop",
    ]

    # Read back scratch memory to verify store result
    t_lines.extend(
        [
            f" LA(x{addr_reg}, scratch)",
            f" lw x{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            f" lw x{check_reg}, 4(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            f" lw x{check_reg}, 8(x{addr_reg})",
            write_sigupd(check_reg, test_data),
            f" lw x{check_reg}, 12(x{addr_reg})",
            write_sigupd(check_reg, test_data),
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg])
    return t_lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_load_address_misaligned"

    lines = [comment_banner(coverpoint, "Load Address Misaligned")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")
        for op in load_ops:
            lines.extend(_add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        for op in ["lwu", "ld"]:
            lines.extend(_add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_store_address_misaligned"

    lines = [comment_banner(coverpoint, "Store Address Misaligned")]

    store_ops = ["sb", "sh", "sw"]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b})")
        for op in store_ops:
            lines.extend(_add_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        lines.extend(_add_store_misaligned_test("sd", offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_store_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_store_access_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Store Access Fault")]

    store_ops = ["sb", "sh", "sw"]
    if test_data.xlen == 64:
        store_ops.append("sd")

    test_values = {"sb": "0xAB", "sh": "0xBEAD", "sw": "0xADDEDCAB", "sd": "0xDEADBEEFDEADBEEF"}

    for op in store_ops:
        lines.extend(
            [
                f" LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f" li x{data_reg}, {test_values[op]}",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f" {op} x{data_reg}, 0(x{addr_reg})",
                " nop",
            ]
        )

    lines.append("")
    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_ecall_m_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_ecall_m"

    lines = [
        comment_banner(coverpoint, "Ecall Machine Mode"),
        test_data.add_testcase("ecall_m", coverpoint, covergroup),
        " ecall",
        " nop",
    ]

    return lines


def _generate_misaligned_priority_load_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_misaligned_priority_load"
    addr_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 1])

    lines = [comment_banner(coverpoint, "Misaligned Priority Load")]
    load_ops_base = ["lh", "lhu", "lw", "lb", "lbu"]
    load_ops_64 = ["lwu", "ld"]

    lines.append(f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned")
        lines.append(f" addi x{temp_reg}, x{addr_reg}, {offset}")

        for op in load_ops_base:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_off{offset}_priority", coverpoint, covergroup),
                    f" {op} x{check_reg}, 0(x{temp_reg})",
                    " nop",
                ]
            )

        lines.append("#if __riscv_xlen == 64")
        for op in load_ops_64:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_off{offset}_priority", coverpoint, covergroup),
                    f" {op} x{check_reg}, 0(x{temp_reg})",
                    " nop",
                ]
            )
        lines.append("#endif")

    test_data.int_regs.return_registers([temp_reg, addr_reg, check_reg])
    return lines


def _generate_misaligned_priority_store_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_misaligned_priority_store"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Store")]
    store_ops_base = ["sb", "sh", "sw"]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned")
        lines.extend(
            [
                f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f" addi x{addr_reg}, x{addr_reg}, {offset}",
                f" li x{data_reg}, 0xDECAFCAB",
            ]
        )

        for op in store_ops_base:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_off{offset}_priority", coverpoint, covergroup),
                    f" {op} x{data_reg}, 0(x{addr_reg})",
                    " nop",
                ]
            )

        lines.extend(
            [
                "#if __riscv_xlen == 64",
                test_data.add_testcase(f"sd_off{offset}_priority", coverpoint, covergroup),
                f" sd x{data_reg}, 0(x{addr_reg})",
                " nop",
                "#endif",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_misaligned_priority_fetch_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_misaligned_priority_fetch"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Misaligned Priority Fetch"),
    ]

    target_label = f"misaligned_fetch_target_{test_data.test_count + 1}"
    lines.extend(
        [
            "\n# misaligned existent",
            f" la x{addr_reg}, {target_label}",
            f" addi x{addr_reg}, x{addr_reg}, 2",
            "LI(x4, 0xACCE)",  # trap handler to use ra as return address
            test_data.add_testcase("misaligned_existent", coverpoint, covergroup),
            f" jalr x1, 0(x{addr_reg})",
            " nop",
            " .align 4",
            f"{target_label}:",
            " nop",
        ]
    )

    lines.extend(
        [
            "\n# misaligned nonexistent",
            f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f" addi x{addr_reg}, x{addr_reg}, 2",
            "LI(x4, 0xACCE)",  # trap handler to use ra as return address
            test_data.add_testcase("misaligned_nonexistent", coverpoint, covergroup),
            f" jalr x1, 0(x{addr_reg})",
            " nop",
        ]
    )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_mstatus_ie_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsSm_cg", "cp_mstatus_ie"
    save_reg, mask_reg, arg_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Mstatus Interrupt Enable"),
        f" csrr x{save_reg}, mstatus",
        f" li x{mask_reg}, 0x8",
        "",
        "# Test ecall with mstatus.MIE = 0",
        f" csrrc x0, mstatus, x{mask_reg}",
        f" li x{arg_reg}, 3",
        test_data.add_testcase("ecall_mie_0", coverpoint, covergroup),
        " ecall",
        " nop",
        "",
        "# Test ecall with mstatus.MIE = 1",
        f" csrrs x0, mstatus, x{mask_reg}",
        f" li x{arg_reg}, 3",
        test_data.add_testcase("ecall_mie_1", coverpoint, covergroup),
        " ecall",
        " nop",
        "",
        f" csrw mstatus, x{save_reg}",
        "",
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg, arg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsSm",
    required_extensions=["I", "Zicsr", "Sm"],
    march_extensions=["F"],
    extra_defines=["#define SKIP_MEPC"],
)
def make_exceptionssm(test_data: TestData) -> list[str]:
    """Main entry point for Sm exception test generation."""
    lines = []

    lines.extend(
        [
            "# Initialize scratch memory with test data",
            " LA(x10, scratch)",
            " LI(x11, 0xDEADBEEF)",
            " sw x11, 0(x10)",
            " sw x11, 4(x10)",
            " sw x11, 8(x10)",
            " sw x11, 12(x10)",
            "",
        ]
    )

    lines.extend(_generate_instr_adr_misaligned_branch_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_branch_nottaken(test_data))
    lines.extend(_generate_instr_adr_misaligned_jal_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_jalr_tests(test_data))
    lines.extend(_generate_instr_access_fault_tests(test_data))
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
