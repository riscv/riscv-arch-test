##################################
# priv/extensions/ExceptionsU.py
#
# ExceptionsU extension exception test generator.
# huahuang@hmc.edu Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsU test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_instr_adr_misaligned_branch_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_branch"
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned branch"),
        f"LI(x{temp_reg}, 1)",
        ".align 2",
        test_data.add_testcase("taken_branch_pc_6", coverpoint, covergroup),
    ]

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
                f"{branch} {rs1}, {rs2}, .+6",
                "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
                "addi x0, x2, 0",
                ".word 0x00010013",
            ]
        )

    test_data.int_regs.return_registers([temp_reg])
    return lines


def _generate_instr_adr_misaligned_branch_nottaken(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_branch_nottaken"
    temp_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Branch to an unaligned address is NOT taken (PC+6). Should not cause an exception"),
        ".align 2",
        f"LI(x{temp_reg}, 1)",
        f"LI(x{check_reg}, 1)",
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
        lines.append(f"{branch} {rs1}, {rs2}, .+6")

    lines.append(write_sigupd(check_reg, test_data))
    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def _generate_instr_adr_misaligned_jal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_jal"

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JAL"),
        test_data.add_testcase("jal_misaligned", coverpoint, covergroup),
        "jal x0, .+6",
        "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
        "addi x0, x2, 0",
        ".word 0x00010013",
    ]

    return lines


def _generate_instr_adr_misaligned_jalr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_jalr"
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
                    ".align 2",
                    f"auipc x{addr_reg}, 0",
                    f"addi x{addr_reg}, x{addr_reg}, {base_off}",
                    test_data.add_testcase(f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", coverpoint, covergroup),
                    f"jalr x1, {jalr_off}(x{addr_reg})",
                    ".word 0x00010013",
                ]
            )

            # conditional nop ensures addi below is always 8 bytes after jalr so trap handler returns correctly
            if rs1_lsb & 1:
                lines.append("nop")

            lines.extend(
                [
                    "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
                    "addi x0, x2, 0",
                ]
            )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_instr_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_access_fault"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Access Fault"),
        f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        "LI(x4, 0xACCE)",  # trap handler checks x4 value and determines to use x1 (ra) as return address instead of mepc
        test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
        f"jalr x1, 0(x{addr_reg})",
        " nop",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_illegal_instruction"

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


def _generate_illegal_instruction_seed_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_illegal_instruction_seed"
    dest_regs = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Illegal Instruction Seed"),
        test_data.add_testcase("seed_csrrs", coverpoint, covergroup),
        f" csrrs x{dest_regs[0]}, seed, x0",
        " nop",
        test_data.add_testcase("seed_csrrc", coverpoint, covergroup),
        f" csrrc x{dest_regs[1]}, seed, x0",
        " nop",
        test_data.add_testcase("seed_csrrsi", coverpoint, covergroup),
        f" csrrsi x{dest_regs[2]}, seed, 0",
        " nop",
        test_data.add_testcase("seed_csrrci", coverpoint, covergroup),
        f" csrrci x{dest_regs[3]}, seed, 0",
        " nop",
    ]

    test_data.int_regs.return_registers(dest_regs)
    return lines


def _generate_breakpoint_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "Breakpoint"),
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak",
        "nop",
    ]
    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Load Access Fault")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for op in load_ops:
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{check_reg}, 0(x{addr_reg})",
                "nop",
            ]
        )

    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            test_data.add_testcase("lwu_fault", coverpoint, covergroup),
            f" lwu x{check_reg}, 0(x{addr_reg})",
            " nop",
            f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            test_data.add_testcase("ld_fault", coverpoint, covergroup),
            f" ld x{check_reg}, 0(x{addr_reg})",
            " nop",
            "#endif",
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
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f"{op} x{check_reg}, 0(x{addr_reg})",
        "nop",
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


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_load_address_misaligned"

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
    covergroup, coverpoint = "ExceptionsU_cg", "cp_store_address_misaligned"

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
    covergroup, coverpoint = "ExceptionsU_cg", "cp_store_access_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Store Access Fault")]

    store_ops = ["sb", "sh", "sw"]
    test_values = {"sb": "0xAB", "sh": "0xBEAD", "sw": "0xADDEDCAB", "sd": "0xADDEDCABADDEDCAB"}

    for op in store_ops:
        lines.extend(
            [
                f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{data_reg}, {test_values[op]})",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{data_reg}, 0(x{addr_reg})",
                " nop",
            ]
        )

    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"LI(x{data_reg}, {test_values['sd']})",
            test_data.add_testcase("sd_fault", coverpoint, covergroup),
            f"sd x{data_reg}, 0(x{addr_reg})",
            "nop",
            "#endif",
        ]
    )
    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_ecall_u_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_ecall_u"

    lines = [
        comment_banner(coverpoint, "Ecall User Mode"),
        test_data.add_testcase("ecall_u", coverpoint, covergroup),
        "ecall",
        "nop",
    ]

    return lines


def _generate_misaligned_priority_load_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_misaligned_priority_load"
    addr_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 1])

    lines = [comment_banner(coverpoint, "Misaligned Priority Load")]
    load_ops_base = ["lh", "lhu", "lw", "lb", "lbu"]
    load_ops_64 = ["lwu", "ld"]

    lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned")
        lines.append(f"addi x{temp_reg}, x{addr_reg}, {offset}")

        for op in load_ops_base:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{check_reg}, 0(x{temp_reg})",
                    "nop",
                ]
            )

        lines.append("#if __riscv_xlen == 64")
        for op in load_ops_64:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{check_reg}, 0(x{temp_reg})",
                    "nop",
                ]
            )
        lines.append("#endif")

    test_data.int_regs.return_registers([temp_reg, addr_reg, check_reg])
    return lines


def _generate_misaligned_priority_store_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_misaligned_priority_store"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Store")]
    store_ops_base = ["sb", "sh", "sw"]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned")
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"addi x{addr_reg}, x{addr_reg}, {offset}",
                f"LI(x{data_reg}, 0xDECAFCAB)",
            ]
        )

        for op in store_ops_base:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{data_reg}, 0(x{addr_reg})",
                    "nop",
                ]
            )

        lines.extend(
            [
                "#if __riscv_xlen == 64",
                test_data.add_testcase(f"sd_off{offset}_priority", coverpoint, covergroup),
                f"sd x{data_reg}, 0(x{addr_reg})",
                "nop",
                "#endif",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_mstatus_ie_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_mstatus_ie"
    save_reg, mask_reg, arg_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Mstatus Interrupt Enable"),
        f"csrr x{save_reg}, mstatus",
        f"LI(x{mask_reg}, 0x8)",
        f"csrrc x0, mstatus, x{mask_reg}",
        "\tRVTEST_GOTO_LOWER_MODE Umode",
        test_data.add_testcase("ecall_mie_0", coverpoint, covergroup),
        "ecall",
        "nop",
        "\tRVTEST_GOTO_MMODE",
        f"LI(x{mask_reg}, 0x88)",
        f"csrrs x0, mstatus, x{mask_reg}",
        "\tRVTEST_GOTO_LOWER_MODE Umode",
        test_data.add_testcase("ecall_mie_1", coverpoint, covergroup),
        "ecall",
        "nop",
        f"csrw mstatus, x{save_reg}",
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg, arg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsU",
    required_extensions=["I", "Zicsr", "Sm", "U"],
    march_extensions=["I", "Zicsr"],
    extra_defines=["#define SKIP_MEPC"],
)
def make_exceptionsu(test_data: TestData) -> list[str]:
    """Main entry point for U exception test generation."""
    lines = []

    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n"])

    lines.extend(_generate_instr_adr_misaligned_branch_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_branch_nottaken(test_data))
    lines.extend(_generate_instr_adr_misaligned_jal_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_jalr_tests(test_data))
    lines.extend(_generate_instr_access_fault_tests(test_data))
    lines.extend(_generate_illegal_instruction_tests(test_data))
    lines.extend(_generate_illegal_instruction_seed_tests(test_data))
    lines.extend(_generate_breakpoint_tests(test_data))
    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    lines.extend(_generate_ecall_u_tests(test_data))
    lines.extend(_generate_misaligned_priority_load_tests(test_data))
    lines.extend(_generate_misaligned_priority_store_tests(test_data))
    lines.extend(_generate_mstatus_ie_tests(test_data))

    return lines
