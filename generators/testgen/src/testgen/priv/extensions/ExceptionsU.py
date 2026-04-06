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
        comment_banner(
            coverpoint,
            "Branch to an misaligned address is taken (PC+6) and should cause an exception unless compressed instructions are supported",
        ),
        f"LI(x{temp_reg}, 1)",
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
            ]
        )
    test_data.int_regs.return_registers([temp_reg])
    return lines


def _generate_instr_adr_misaligned_branch_nottaken(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_branch_nottaken"
    temp_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Branch to an misaligned address is not taken (PC+6) so no exception"),
        ".align 2",
        f"LI(x{temp_reg}, 1)",
        f"LI(x{check_reg}, 1)",
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
        lines.extend(
            [
                test_data.add_testcase(f"nottaken_branch_pc_6_{branch}", coverpoint, covergroup),
                f"{branch} {rs1}, {rs2}, .+6",
                "nop",
            ]
        )
    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def _generate_instr_adr_misaligned_jal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_jal"

    lines = [
        comment_banner(
            coverpoint,
            "jal to a misaligned address (PC+6) which should cause an exception unless compressed instructions are supported",
        ),
        test_data.add_testcase("jal_misaligned", coverpoint, covergroup),
        "jal x0, .+6",
        "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
        "addi x0, x2, 0",
    ]

    return lines


def _generate_instr_adr_misaligned_jalr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_adr_misaligned_jalr"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "jalr to a misaligned address. Should cause an exception unless compressed instructions are supported",
        ),
    ]

    offsets = [8, 5, 6, 7]
    # rs1 is set to PC + base_offset for rs1[1:0]
    for rs1_lsb in range(4):
        # jalr controls the offset[1:0], which covers all 16 combinations of (rs1+offset)[1:0]
        for offset_lsb in range(4):
            base_off = offsets[rs1_lsb]
            jalr_off = offsets[offset_lsb]

            lines.extend(
                [
                    "",
                    f"# rs1[1:0]={rs1_lsb:02b}, offset[1:0]={offset_lsb:02b}",
                    ".align 2",
                    f"auipc x{addr_reg}, 0",
                    f"addi x{addr_reg}, x{addr_reg}, {base_off}",
                    test_data.add_testcase(f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", coverpoint, covergroup),
                    f"jalr x1, {jalr_off}(x{addr_reg})",
                    "addi x0, x2, 0",
                ]
            )
    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_instr_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_instr_access_fault"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 4])

    lines = [
        comment_banner(
            coverpoint, "Instruction Access Fault when fetching from an address that causes an access fault"
        ),
        f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        "LI(x4, 0xACCE)",  # trap handler checks x4 value and determines to use x1 (ra) as return address instead of mepc
        test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
        f"jalr x1, 0(x{addr_reg})",
        "nop",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_illegal_instruction"

    lines = [
        comment_banner(coverpoint, "executing an illegal instruction should cause an illegal instruction exception"),
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
    dest_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint, "Illegal instruction on seed CSR which should cause an illegal instruction exception"
        ),
        "#ifdef ZKR_SUPPORTED",
        test_data.add_testcase("seed_csrrs", coverpoint, covergroup),
        f"csrrs x{dest_reg}, seed, x0",
        "nop",
        write_sigupd(dest_reg, test_data),
        test_data.add_testcase("seed_csrrc", coverpoint, covergroup),
        f"csrrc x{dest_reg}, seed, x0",
        "nop",
        write_sigupd(dest_reg, test_data),
        test_data.add_testcase("seed_csrrsi", coverpoint, covergroup),
        f"csrrsi x{dest_reg}, seed, 0",
        "nop",
        write_sigupd(dest_reg, test_data),
        test_data.add_testcase("seed_csrrci", coverpoint, covergroup),
        f"csrrci x{dest_reg}, seed, 0",
        "nop",
        write_sigupd(dest_reg, test_data),
        "#endif",
    ]

    test_data.int_regs.return_registers([dest_reg])
    return lines


def _generate_breakpoint_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "ebreak should cause a breakpoint exception in user mode"),
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak",
        "nop",
    ]
    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Load from an address that causes an access fault. Should throw load access fault")
    ]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for op in load_ops:
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{check_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(check_reg, test_data),
            ]
        )

    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            test_data.add_testcase("lwu_fault", coverpoint, covergroup),
            f"lwu x{check_reg}, 0(x{addr_reg})",
            " nop",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            test_data.add_testcase("ld_fault", coverpoint, covergroup),
            f"ld x{check_reg}, 0(x{addr_reg})",
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
        f"LI(x{data_reg}, 0xDECAFCA{offset})",
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

    lines = [comment_banner(coverpoint, "test load instructions from addresses with lsbs 0-7might not cause exception")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for offset in range(8):
        lines.append(f"\n#Offset {offset} (LSBs: {offset:03b})")
        for op in load_ops:
            lines.extend(_add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        for op in ["lwu", "ld"]:
            lines.extend(_add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_store_address_misaligned"

    lines = [
        comment_banner(coverpoint, "test store instructions from addresses with lsbs 0-7might not cause exception")
    ]

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

    lines = [comment_banner(coverpoint, "Store to an address that causes a store access fault")]

    store_ops = ["sb", "sh", "sw"]
    test_values = {"sb": "0xAB", "sh": "0xBEAD", "sw": "0xADDEDCAB", "sd": "0xADDEDCABADDEDCAB"}

    for op in store_ops:
        lines.extend(
            [
                f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{data_reg}, {test_values[op]})",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{data_reg}, 0(x{addr_reg})",
                "nop",
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
        comment_banner(coverpoint, "ecall from user mode and should throw ecall user exception"),
        test_data.add_testcase("ecall_u", coverpoint, covergroup),
        "ecall",
        "nop",
    ]
    return lines


def _generate_misaligned_priority_load_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_misaligned_priority_load"
    addr_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 1])

    lines = [comment_banner(coverpoint, "Load from access fault \nThrow access fault or misaligned exception")]
    load_ops_base = ["lh", "lhu", "lw", "lb", "lbu"]
    load_ops_64 = ["lwu", "ld"]

    lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")

    for offset in range(8):
        lines.extend(
            [
                "",
                f"# Offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned",
                f"addi x{temp_reg}, x{addr_reg}, {offset}",
            ]
        )

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

    lines = [
        comment_banner(
            coverpoint,
            "Store to an access fault address with misaligned offset\n"
            "Should throw access fault or misaligned exception",
        )
    ]
    store_ops_base = ["sb", "sh", "sw"]

    for offset in range(8):
        lines.extend(
            [
                "",
                f"# Offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned",
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
        comment_banner(coverpoint, "ecall from user mode with MIE=0 vs MIE=1"),
        f"csrr x{save_reg}, mstatus",
        f"LI(x{mask_reg}, 0x8)",
        f"csrrc x0, mstatus, x{mask_reg}",
        "RVTEST_GOTO_LOWER_MODE Umode",
        test_data.add_testcase("ecall_mie_0", coverpoint, covergroup),
        "ecall",
        "nop",
        "RVTEST_GOTO_MMODE",
        f"LI(x{mask_reg}, 0x80)",
        f"csrrs x0, mstatus, x{mask_reg}",
        "RVTEST_GOTO_LOWER_MODE Umode",
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
    extra_defines=["#define SKIP_MEPC"],  # hangs otherwise
)
def make_exceptionsu(test_data: TestData) -> list[str]:
    """Main entry point for U exception test generation."""
    lines = []

    lines.append("RVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")

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
