##################################
# priv/extensions/ExceptionsCommon.py
#
# Shared exception tests generation
# jgong@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Common exception test generation"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData


def generate_instr_adr_misaligned_branch_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_instr_adr_misaligned_branch"
    temp_reg = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned branch (taken)"),
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
                "nop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg])
    return lines


def generate_instr_adr_misaligned_branch_nottaken(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_instr_adr_misaligned_branch_nottaken"
    temp_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[])

    lines = [
        comment_banner(
            coverpoint,
            "Branch to an unaligned address is NOT taken (PC+6). Should not cause an exception",
        ),
        ".align 2",
        f"LI(x{temp_reg}, 1)",
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase("nottaken_branch_pc_6", coverpoint, covergroup),
    ]

    branches = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    for branch in branches:
        if branch in ("beq", "bge", "bgeu"):
            rs1, rs2 = "x0", f"x{temp_reg}"
        elif branch == "bne":
            rs1, rs2 = "x0", "x0"  # 0 == 0, so bne not taken
        else:  # blt, bltu
            rs1, rs2 = f"x{temp_reg}", "x0"
        lines.append(f"{branch} {rs1}, {rs2}, .+6")
        lines.append(f"addi x{check_reg}, x{check_reg}, 1")

    lines.append(write_sigupd(check_reg, test_data))
    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def generate_instr_adr_misaligned_jal_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_instr_adr_misaligned_jal"

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JAL"),
        test_data.add_testcase("jal_misaligned", coverpoint, covergroup),
        "jal x0, .+6",
        "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
        "addi x0, x2, 0",
        "nop",
    ]
    return lines


def generate_instr_adr_misaligned_jalr_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_instr_adr_misaligned_jalr"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JALR"),
    ]

    # jalr_off controls the offset[1:0], covering all 16 combinations of (rs1+offset)[1:0].
    # JALR jumps to (rs1 + offset) with bit 0 cleared.
    # Misaligned exception occurs when bit 1 of the target is set
    offsets_for_lsb = {0: 8, 1: 5, 2: 6, 3: 7}

    for rs1_lsb in range(4):
        for offset_lsb in range(4):
            base_off = offsets_for_lsb[rs1_lsb]
            jalr_off = offsets_for_lsb[offset_lsb]

            lines.extend(
                [
                    f"\n# rs1[1:0]={rs1_lsb:02b}, offset[1:0]={offset_lsb:02b}",
                    ".align 2",
                    f"auipc x{addr_reg}, 0",  # PC+0 addr_reg = PC
                    f"addi x{addr_reg}, x{addr_reg}, {base_off}",  # PC+4 addr_reg[1:0] = rs1_lsb
                    test_data.add_testcase(f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", coverpoint, covergroup),  # PC+8
                    f"jalr x1, {jalr_off}(x{addr_reg})",  # PC+12 jump target is PC + base_off + jalr_off (bit 0 cleared)
                    "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
                    "addi x0, x2, 0",  # PC+16 return for aligned jumps
                ]
            )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def generate_instr_access_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_instr_access_fault"
    # Exclude x4 since contains 0xACCE used by the trap handler
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 4])

    lines = [
        comment_banner(coverpoint, "Instruction Access Fault"),
        f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        "LI(x4, 0xACCE)",  # trap handler checks x4 value and uses x1 (ra) as return address instead of mepc
        test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
        f"jalr x1, 0(x{addr_reg})",
        "nop",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def generate_ecall_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    testcase_name: str,
    description: str = "Ecall",
) -> list[str]:
    """Generate ecall testcase"""
    lines = [
        comment_banner(coverpoint, description),
        test_data.add_testcase(testcase_name, coverpoint, covergroup),
        "ecall",
        "nop",
    ]
    return lines


def generate_illegal_instruction_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_illegal_instruction"

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


def generate_illegal_instruction_seed_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_illegal_instruction_seed"
    dest_regs = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Illegal Instruction Seed"),
        test_data.add_testcase("seed_csrrs", coverpoint, covergroup),
        f"csrrs x{dest_regs[0]}, seed, x0",
        "nop",
        test_data.add_testcase("seed_csrrc", coverpoint, covergroup),
        f"csrrc x{dest_regs[1]}, seed, x0",
        "nop",
        test_data.add_testcase("seed_csrrsi", coverpoint, covergroup),
        f"csrrsi x{dest_regs[2]}, seed, 0",
        "nop",
        test_data.add_testcase("seed_csrrci", coverpoint, covergroup),
        f"csrrci x{dest_regs[3]}, seed, 0",
        "nop",
    ]

    test_data.int_regs.return_registers(dest_regs)
    return lines


def generate_breakpoint_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "Breakpoint"),
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak",
        "nop",
    ]
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


def generate_load_address_misaligned_tests(
    test_data: TestData,
    covergroup: str,
    *,
    use_sentinel: bool = True,
) -> list[str]:
    """Generate load-misaligned testcases for all load ops and offsets 0-7."""
    coverpoint = "cp_load_address_misaligned"
    lines = [comment_banner(coverpoint, "Load Address Misaligned")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for offset in range(8):
        for op in load_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(
                add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup, use_sentinel=use_sentinel)
            )

        lines.append("#if __riscv_xlen == 64")
        for op in ["lwu", "ld"]:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(
                add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup, use_sentinel=use_sentinel)
            )
        lines.append("#endif")

    return lines


def generate_store_address_misaligned_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_store_address_misaligned"
    lines = [comment_banner(coverpoint, "Store Address Misaligned")]

    store_ops = ["sb", "sh", "sw"]

    for offset in range(8):
        for op in store_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("\n#if __riscv_xlen == 64")
        lines.append(f"\n# Testcase: sd with offset {offset} (LSBs: {offset:03b})")
        lines.extend(add_store_misaligned_test("sd", offset, test_data, coverpoint, covergroup))
        lines.append("\n#endif")

    return lines


def generate_load_access_fault_tests(
    test_data: TestData,
    covergroup: str,
    *,
    use_sigupd: bool = True,
) -> list[str]:
    """Generate load-access-fault testcases."""
    coverpoint = "cp_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Load Access Fault")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for op in load_ops:
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
    lines.extend(["", "#endif"])

    test_data.int_regs.return_registers([addr_reg, check_reg])
    return lines


def generate_store_access_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    coverpoint = "cp_store_access_fault"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Store Access Fault")]

    store_ops = ["sb", "sh", "sw"]
    test_values = {"sb": "0xAB", "sh": "0xBEAD", "sw": "0xADDEDCAB", "sd": "0xADDEDCABADDEDCAB"}

    for op in store_ops:
        lines.extend(
            [
                f"\n# Testcase: {op} access fault",
                f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
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
            f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"LI(x{data_reg}, {test_values['sd']})",
            test_data.add_testcase("sd_fault", coverpoint, covergroup),
            f"sd x{data_reg}, 0(x{addr_reg})",
            "nop",
            "",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def generate_misaligned_priority_load_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    name_infix: str = "_load_",
) -> list[str]:
    """Generate misaligned-priority load testcases."""
    addr_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 1])

    lines = [comment_banner(coverpoint, "Misaligned Priority Load")]
    load_ops_base = ["lh", "lhu", "lw", "lb", "lbu"]
    load_ops_64 = ["lwu", "ld"]

    lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")

    for offset in range(8):
        lines.append(f"addi x{temp_reg}, x{addr_reg}, {offset}")

        for op in load_ops_base:
            lines.extend(
                [
                    f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned",
                    test_data.add_testcase(f"{op}{name_infix}off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{check_reg}, 0(x{temp_reg})",
                    "nop",
                ]
            )

        lines.append("\n#if __riscv_xlen == 64")
        for op in load_ops_64:
            lines.extend(
                [
                    f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned",
                    test_data.add_testcase(f"{op}{name_infix}off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{check_reg}, 0(x{temp_reg})",
                    "nop",
                ]
            )
        lines.append("\n#endif\n")

    test_data.int_regs.return_registers([temp_reg, addr_reg, check_reg])
    return lines


def generate_misaligned_priority_store_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    name_infix: str = "_store_",
) -> list[str]:
    """Generate misaligned-priority store testcases."""
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Store")]
    store_ops_base = ["sb", "sh", "sw"]

    for offset in range(8):
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
                    f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned",
                    test_data.add_testcase(f"{op}{name_infix}off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{data_reg}, 0(x{addr_reg})",
                    "nop",
                ]
            )

        lines.extend(
            [
                "",
                "#if __riscv_xlen == 64",
                f"\n# Testcase: sd with offset {offset} (LSBs: {offset:03b}) - Access fault Misaligned",
                test_data.add_testcase(f"sd{name_infix}off{offset}_priority", coverpoint, covergroup),
                f"sd x{data_reg}, 0(x{addr_reg})",
                "nop",
                "",
                "#endif",
                "",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def generate_misaligned_priority_fetch_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    name_prefix: str = "fetch_",
    name_suffix: str = "_priority",
) -> list[str]:
    """Generate misaligned-priority fetch testcases."""
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Fetch")]

    target_label = f"misaligned_fetch_target_{test_data.test_count + 1}"
    lines.extend(
        [
            "\n# misaligned fetch - existent address",
            f"LA(x{addr_reg}, {target_label})",
            f"addi x{addr_reg}, x{addr_reg}, 2",
            "LI(x4, 0xACCE)",  # trap handler checks x4 value to use x1 (ra) as return address instead of mepc
            test_data.add_testcase(f"{name_prefix}misaligned_existent{name_suffix}", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
            ".align 4",
            f"{target_label}:",
            "nop",
            "\n# misaligned fetch - non-existent (fault) address",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"addi x{addr_reg}, x{addr_reg}, 2",
            "LI(x4, 0xACCE)",  # trap handler checks x4 value to use x1 (ra) as return address instead of mepc
            test_data.add_testcase(f"{name_prefix}misaligned_nonexistent{name_suffix}", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
        ]
    )

    test_data.int_regs.return_registers([addr_reg])
    return lines
