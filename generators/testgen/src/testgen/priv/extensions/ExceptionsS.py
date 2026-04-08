##################################
# priv/extensions/ExceptionsS.py
#
# ExceptionsS test generator.
# jgong@g.hmc.edu 3/9/2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exceptions S-mode test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_instr_adr_misaligned_branch_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_instr_adr_misaligned_branch"
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

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


def _generate_instr_adr_misaligned_branch_nottaken(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_instr_adr_misaligned_branch_nottaken"
    temp_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Branch to unaligned address NOT taken"),
        ".align 2",
        f"LI(x{temp_reg}, 1)",
        f"LI(x{check_reg}, 1)",
        test_data.add_testcase("nottaken_branch_pc_6", coverpoint, covergroup),
    ]

    branches = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]
    for branch in branches:
        if branch in ("beq", "bge", "bgeu"):
            rs1, rs2 = "x0", f"x{temp_reg}"
        elif branch == "bne":
            rs1, rs2 = "x0", "x0"
        else:  # blt, bltu
            rs1, rs2 = f"x{temp_reg}", "x0"
        lines.append(f"{branch} {rs1}, {rs2}, .+6")

    lines.append(write_sigupd(check_reg, test_data))
    test_data.int_regs.return_registers([temp_reg, check_reg])
    return lines


def _generate_instr_adr_misaligned_jal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_instr_adr_misaligned_jal"

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JAL"),
        test_data.add_testcase("jal_misaligned", coverpoint, covergroup),
        "jal x0, .+6",
        "# branch by 6 lands in upper half of next instruction 0x0001 which is generated into a c.nop",
        "addi x0, x2, 0",
        "nop",
    ]

    return lines


def _generate_instr_adr_misaligned_jalr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_instr_adr_misaligned_jalr"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Instruction Address Misaligned JALR"),
    ]

    # Test all 16 combinations of rs1[1:0] and offset[1:0] for JALR
    offsets_for_lsb = {0: 8, 1: 5, 2: 6, 3: 7}

    for rs1_lsb in range(4):
        for offset_lsb in range(4):
            base_off = offsets_for_lsb[rs1_lsb]
            jalr_off = offsets_for_lsb[offset_lsb]

            lines.extend(
                [
                    f"\n# rs1[1:0]={rs1_lsb:02b}, offset[1:0]={offset_lsb:02b}",
                    ".align 2",
                    # AUIPC gets the aligned PC, then ADDI sets addr_reg[1:0] = rs1_lsb
                    f"auipc x{addr_reg}, 0",
                    f"addi x{addr_reg}, x{addr_reg}, {base_off}",
                    test_data.add_testcase(f"jalr_rs1_{rs1_lsb}_off_{offset_lsb}", coverpoint, covergroup),
                    # JALR jumps to (addr_reg + jalr_off) & ~1
                    f"jalr x1, {jalr_off}(x{addr_reg})",
                    "nop",
                ]
            )

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
    covergroup, coverpoint = "ExceptionsS_cg", "cp_instr_access_fault"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0, 4])

    lines = [
        comment_banner(coverpoint, "Instruction Access Fault"),
        f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        "LI(x4, 0xACCE)",
        test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
        f"jalr x1, 0(x{addr_reg})",
        "nop",
    ]

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_illegal_instruction_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_illegal_instruction"

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
    covergroup, coverpoint = "ExceptionsS_cg", "cp_illegal_instruction_seed"
    dest_regs = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Illegal Instruction"),
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
    covergroup, coverpoint = "ExceptionsS_cg", "cp_breakpoint"

    lines = [
        comment_banner(coverpoint, "Breakpoint"),
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak",
        "nop",
    ]
    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_load_access_fault"
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Load Access Fault")]

    load_ops = ["lb", "lbu", "lh", "lhu", "lw"]

    for op in load_ops:
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{check_reg}, 0xB0BACAFE)",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{check_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(check_reg, test_data),
            ]
        )

    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f" LI(x{check_reg}, 0xB0BACAFE)",
            test_data.add_testcase("lwu_fault", coverpoint, covergroup),
            f" lwu x{check_reg}, 0(x{addr_reg})",
            " nop",
            write_sigupd(check_reg, test_data),
            f" LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f" LI(x{check_reg}, 0xB0BACAFE)",
            test_data.add_testcase("ld_fault", coverpoint, covergroup),
            f" ld x{check_reg}, 0(x{addr_reg})",
            " nop",
            write_sigupd(check_reg, test_data),
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
        f"LI(x{check_reg}, 0xB0BACAFE)",
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
        # Read back scratch to verify store result
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
    covergroup, coverpoint = "ExceptionsS_cg", "cp_load_address_misaligned"

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
    covergroup, coverpoint = "ExceptionsS_cg", "cp_store_address_misaligned"

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
    covergroup, coverpoint = "ExceptionsS_cg", "cp_store_access_fault"
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


def _generate_ecall_s_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_ecall_s"

    lines = [
        comment_banner(coverpoint, "Ecall"),
        test_data.add_testcase("ecall_s", coverpoint, covergroup),
        "ecall",
        "nop",
    ]

    return lines


def _generate_misaligned_priority_load_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_misaligned_priority"
    addr_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 1])

    lines = [comment_banner(coverpoint, "Misaligned Priority Tests")]
    load_ops_base = ["lh", "lhu", "lw", "lb", "lbu"]
    load_ops_64 = ["lwu", "ld"]

    lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) Misaligned Access fault")
        lines.append(f"addi x{temp_reg}, x{addr_reg}, {offset}")

        for op in load_ops_base:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_load_off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{check_reg}, 0(x{temp_reg})",
                    "nop",
                ]
            )

        lines.append("#if __riscv_xlen == 64")
        for op in load_ops_64:
            lines.extend(
                [
                    test_data.add_testcase(f"{op}_load_off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{check_reg}, 0(x{temp_reg})",
                    "nop",
                ]
            )
        lines.append("#endif")

    test_data.int_regs.return_registers([temp_reg, addr_reg, check_reg])
    return lines


def _generate_misaligned_priority_store_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_misaligned_priority"
    addr_reg, data_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Store")]
    store_ops_base = ["sb", "sh", "sw"]

    for offset in range(8):
        lines.append(f"\n# Offset {offset} (LSBs: {offset:03b}) Misaligned Access fault")
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
                    test_data.add_testcase(f"{op}_store_off{offset}_priority", coverpoint, covergroup),
                    f"{op} x{data_reg}, 0(x{addr_reg})",
                    "nop",
                ]
            )

        lines.extend(
            [
                "#if __riscv_xlen == 64",
                test_data.add_testcase(f"sd_store_off{offset}_priority", coverpoint, covergroup),
                f"sd x{data_reg}, 0(x{addr_reg})",
                "nop",
                "#endif",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


def _generate_misaligned_priority_fetch_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_misaligned_priority"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [comment_banner(coverpoint, "Misaligned Priority Fetch")]

    target_label = f"misaligned_fetch_target_{test_data.test_count + 1}"
    lines.extend(
        [
            "\n# misaligned fetch - existent address",
            f"LA(x{addr_reg}, {target_label})",
            f"addi x{addr_reg}, x{addr_reg}, 2",
            "LI(x4, 0xACCE)",
            test_data.add_testcase("fetch_misaligned_existent_priority", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
            ".align 4",
            f"{target_label}:",
            "nop",
            "\n# misaligned fetch - non-existent (fault) address",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"addi x{addr_reg}, x{addr_reg}, 2",
            "LI(x4, 0xACCE)",
            test_data.add_testcase("fetch_misaligned_nonexistent_priority", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
        ]
    )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_illegal_instruction_csr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_illegal_instruction_csr"
    dest_regs = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "Illegal Instruction"),
    ]

    csr_tests = [
        ("csrrs_0x000", f"csrrs x{dest_regs[1]}, 0x000, x{dest_regs[0]}"),
        ("csrrc_0x000", f"csrrc x{dest_regs[1]}, 0x000, x{dest_regs[0]}"),
        ("csrrsi_0x000", f"csrrsi x{dest_regs[1]}, 0x000, 1"),
        ("csrrci_0x000", f"csrrci x{dest_regs[1]}, 0x000, 1"),
    ]

    for test_name, instr in csr_tests:
        lines.extend(
            [
                f"LI(x{dest_regs[1]}, 0xB0BACAFE)",
                test_data.add_testcase(test_name, coverpoint, covergroup),
                f" {instr}",
                " nop",
                write_sigupd(dest_regs[1], test_data),
            ]
        )

    test_data.int_regs.return_registers(dest_regs)
    return lines


def _add_jalr_misaligned_test_fault_addr(
    rs1_lsb: int,
    addr_reg: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    tag_prefix: str = "",
) -> list[str]:

    offsets_for_lsb = {0: [0, 1, 2, 3], 1: [0, 1, 2, -1], 2: [0, 1, -2, -1], 3: [0, -3, -2, -1]}

    label = f"{tag_prefix}_jalr_rs1_{rs1_lsb}" if tag_prefix else f"jalr_rs1_{rs1_lsb}"

    t_lines = [test_data.add_testcase(label, coverpoint, covergroup)]

    for off in offsets_for_lsb[rs1_lsb]:
        t_lines.extend([f"jalr x1, {off}(x{addr_reg})", "nop"])

    return t_lines


_MEDELEG_WALK = (
    [0]
    + [1 << i for i in range(9)]  # bits 0-8 walking 1s
    + [1 << i for i in range(10, 16)]  # bits 10-15 walking 1s
    + [0b1011_0001_1111_1111]
)


def _generate_medeleg_msu_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    """
    Runs 9 exception tests x 14 medeleg values for one privilege mode.
    Assumes caller has already entered the correct privilege mode.
    Sets medeleg itself for each iteration by returning to M-mode temporarily.
    """
    covergroup = "ExceptionsS_cg"
    coverpoint = "cp_medeleg_msu"

    # excluding x6, x7, x9 since TVTEST_GOTO_LOWER_MODE may clobber these registers
    addr_reg, data_reg, check_reg, medeleg_reg = test_data.int_regs.get_registers(4, exclude_regs=[0, 1, 6, 7, 9])

    lines = []

    for medeleg_val in _MEDELEG_WALK:
        tag = f"mdlg_{medeleg_val:#06x}_{mode_tag}"
        lines.append(f"\n# --- medeleg={medeleg_val:#06x}, {mode_tag} ---")

        # set medeleg in M-mode
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                f"LI(x{medeleg_reg}, {medeleg_val})",
                f"csrw medeleg, x{medeleg_reg}",
            ]
        )

        if priv_mode == 1:
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")
        elif priv_mode == 0:
            lines.append("RVTEST_GOTO_LOWER_MODE Umode")
        else:
            lines.append("RVTEST_GOTO_MMODE")

        # Instruction misaligned
        lines.extend(
            [
                test_data.add_testcase(f"instrmisaligned_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                "LI(x4, 0xACCE)",
            ]
        )
        for rs1_lsb in range(4):
            if rs1_lsb > 0:
                lines.append(f"addi x{addr_reg}, x{addr_reg}, 1")
            lines.extend(
                _add_jalr_misaligned_test_fault_addr(
                    rs1_lsb, addr_reg, test_data, coverpoint, covergroup, tag_prefix=tag
                )
            )
        lines.append("nop")

        # Instruction access fault
        lines.extend(
            [
                test_data.add_testcase(f"instraccessfault_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                "LI(x4, 0xACCE)",
                f"jalr x1, 0(x{addr_reg})",
                "nop",
            ]
        )

        # Illegal instruction zeros
        lines.extend(
            [
                test_data.add_testcase(f"illegalinstr_zeros_{tag}", coverpoint, covergroup),
                ".align 2",
                ".word 0x00000000",
                "nop",
            ]
        )

        # Illegal instruction ones
        lines.extend(
            [
                test_data.add_testcase(f"illegalinstr_ones_{tag}", coverpoint, covergroup),
                ".align 2",
                ".word 0xFFFFFFFF",
                "nop",
            ]
        )

        # Ebreak
        lines.extend(
            [
                test_data.add_testcase(f"ebreak_{tag}", coverpoint, covergroup),
                "ebreak",
                "nop",
            ]
        )

        # Load misaligned
        lines.extend(
            [test_data.add_testcase(f"loadmisaligned_{tag}", coverpoint, covergroup), f"LA(x{addr_reg}, scratch)"]
        )
        for offset in range(8):
            for op in ["lw", "lh", "lhu", "lb", "lbu"]:
                lines.extend([f"{op} x{check_reg}, {offset}(x{addr_reg})", "nop"])
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f" ld x{check_reg}, {offset}(x{addr_reg})",
                    " nop",
                    f" lwu x{check_reg}, {offset}(x{addr_reg})",
                    " nop",
                    "#endif",
                ]
            )
        lines.append("nop")

        # Load access fault
        lines.extend(
            [
                test_data.add_testcase(f"loadaccessfault_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            ]
        )
        for op in ["lw", "lh", "lhu", "lb", "lbu"]:
            lines.extend([f"{op} x{check_reg}, 0(x{addr_reg})", "nop"])
        lines.extend(
            [
                "#if __riscv_xlen == 64",
                f" ld x{check_reg}, 0(x{addr_reg})",
                " nop",
                f" lwu x{check_reg}, 0(x{addr_reg})",
                " nop",
                "#endif",
                "nop",
            ]
        )

        # Store misaligned
        lines.extend(
            [
                test_data.add_testcase(f"storemisaligned_{tag}", coverpoint, covergroup),
                f"LI(x{data_reg}, 0xDECAFCAB)",
                f"LA(x{addr_reg}, scratch)",
            ]
        )
        for offset in range(8):
            for op in ["sw", "sh", "sb"]:
                lines.extend([f"{op} x{data_reg}, {offset}(x{addr_reg})", "nop"])
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f" sd x{data_reg}, {offset}(x{addr_reg})",
                    " nop",
                    "#endif",
                ]
            )
        lines.append("nop")

        # Store access fault
        lines.extend(
            [
                test_data.add_testcase(f"storeaccessfault_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{data_reg}, 0xADDEDCAB)",
            ]
        )
        for op in ["sw", "sh", "sb"]:
            lines.extend([f"{op} x{data_reg}, 0(x{addr_reg})", "nop"])
        lines.extend(
            [
                "#if __riscv_xlen == 64",
                f" sd x{data_reg}, 0(x{addr_reg})",
                " nop",
                "#endif",
                "nop",
            ]
        )

        # Ecall
        lines.extend(
            [
                test_data.add_testcase(f"ecall_{tag}", coverpoint, covergroup),
                "ecall",
                "nop",
                "nop",
            ]
        )

        # Return to M-mode
        if priv_mode == 3:
            pass
        elif priv_mode == 1:  # S-mode
            lines.append("RVTEST_GOTO_MMODE")
        else:  # U-mode
            if medeleg_val & (1 << 8):
                # trap to S-mode first
                lines.extend(["RVTEST_GOTO_SMODE", "RVTEST_GOTO_MMODE"])
            else:
                lines.append("RVTEST_GOTO_MMODE")

    # Clear medeleg
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            f"LI(x{medeleg_reg}, 0)",
            f"csrw medeleg, x{medeleg_reg}",
        ]
    )

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg, medeleg_reg])
    return lines


def _generate_stvec_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_stvec"
    addr_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, "delegated instr access fault in S/U mode goes to stvec"),
        "RVTEST_GOTO_MMODE",
        "# Delegate instr access fault (medeleg bit 1) to S-mode",
        f"LI(x{addr_reg}, (1 << 1))",
        f"csrw medeleg, x{addr_reg}",
    ]

    if priv_mode == 1:
        lines.append("RVTEST_GOTO_LOWER_MODE Smode")
    elif priv_mode == 0:
        lines.append("RVTEST_GOTO_LOWER_MODE Umode")
    else:
        lines.append("RVTEST_GOTO_MMODE")

    lines.extend(
        [
            "# Instr access fault should trap through stvec",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            "LI(x4, 0xACCE)",
            test_data.add_testcase(f"stvec_iaf_{mode_tag}", coverpoint, covergroup),
            f"jalr x1, 0(x{addr_reg})",
            "nop",
            "nop",
            "RVTEST_GOTO_MMODE",
            "# Restore medeleg to all zeros",
            f"LI(x{addr_reg}, 0)",
            f"csrw medeleg, x{addr_reg}",
        ]
    )

    test_data.int_regs.return_registers([addr_reg])
    return lines


def _generate_xstatus_ie_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    covergroup, coverpoint = "ExceptionsS_cg", "cp_xstatus_ie"
    save_reg, mask_mie, mask_sie, medeleg_reg = test_data.int_regs.get_registers(4, exclude_regs=[0, 6, 7, 9])

    lines = [
        comment_banner(coverpoint, "xstatus Interrupt Enable"),
        "RVTEST_GOTO_MMODE",
        "# Save mstatus before modifying it",
        f"csrr x{save_reg}, mstatus",
    ]

    for medeleg_b8 in (0, 1):
        for mie in (0, 1):
            for sie in (0, 1):
                tag = f"{mode_tag}_mdlg_{medeleg_b8}_mie_{mie}_sie_{sie}"
                lines.extend(
                    [
                        f"\n# {tag}",
                        # Return to M-mode
                        "RVTEST_GOTO_MMODE",
                        f"LI(x{medeleg_reg}, 256)",
                        # Reinitialize masks each iteration: RVTEST_GOTO_LOWER_MODE clobbers
                        # x6/x7/x9 internally, so mask registers may not survive mode switches.
                        f"LI(x{mask_mie}, 0x88)",
                        f"LI(x{mask_sie}, 0x2)",
                        f"{'csrs' if medeleg_b8 else 'csrc'} medeleg, x{medeleg_reg}",
                        # Set MPIE and MIE so mret goes to the proper MIE in the next mode
                        f"{'csrs' if mie else 'csrc'} mstatus, x{mask_mie}",
                    ]
                )

                if priv_mode == 1:
                    lines.append("RVTEST_GOTO_LOWER_MODE Smode")
                    lines.append(f"{'csrsi' if sie else 'csrci'} sstatus, 2")
                elif priv_mode == 0:
                    lines.append(f"{'csrs' if sie else 'csrc'} mstatus, x{mask_sie}")
                    lines.append("RVTEST_GOTO_LOWER_MODE Umode")
                    lines.append("nop")
                else:
                    lines.extend(
                        [
                            f"{'csrs' if sie else 'csrc'} mstatus, x{mask_sie}",
                            "RVTEST_GOTO_MMODE",
                        ]
                    )

                lines.extend(
                    [
                        test_data.add_testcase(tag, coverpoint, covergroup),
                        "ecall",
                        "nop",
                        "RVTEST_GOTO_MMODE",
                    ]
                )

    lines.extend(
        [
            "\n# Restore mstatus and medeleg",
            "RVTEST_GOTO_MMODE",
            f"csrw mstatus, x{save_reg}",
            f"LI(x{medeleg_reg}, 0)",
            f"csrw medeleg, x{medeleg_reg}",
        ]
    )

    test_data.int_regs.return_registers([save_reg, mask_mie, mask_sie, medeleg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsS",
    required_extensions=["I", "S", "Zicsr", "Sm"],
    extra_defines=["#define SKIP_MEPC"],
)
def make_exceptionss(test_data: TestData) -> list[str]:
    """Main entry point for S-mode exception test generation."""
    lines = []

    # Initialize scratch memory
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

    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode  # use S-mode",
        ]
    )
    lines.extend(_generate_instr_adr_misaligned_branch_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_branch_nottaken(test_data))
    lines.extend(_generate_instr_adr_misaligned_jal_tests(test_data))
    lines.extend(_generate_instr_adr_misaligned_jalr_tests(test_data))
    lines.extend(_generate_instr_access_fault_tests(test_data))
    lines.extend(_generate_illegal_instruction_tests(test_data))
    lines.extend(_generate_illegal_instruction_seed_tests(test_data))
    lines.extend(_generate_illegal_instruction_csr_tests(test_data))
    lines.extend(_generate_breakpoint_tests(test_data))
    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    lines.extend(_generate_ecall_s_tests(test_data))
    lines.extend(_generate_misaligned_priority_load_tests(test_data))
    lines.extend(_generate_misaligned_priority_store_tests(test_data))
    lines.extend(_generate_misaligned_priority_fetch_tests(test_data))
    lines.extend(_generate_medeleg_msu_tests(test_data, "mode_m", priv_mode=3))
    lines.extend(_generate_medeleg_msu_tests(test_data, "mode_s", priv_mode=1))
    lines.extend(_generate_medeleg_msu_tests(test_data, "mode_u", priv_mode=0))
    lines.extend(_generate_stvec_tests(test_data, "mode_s", priv_mode=1))
    lines.extend(_generate_stvec_tests(test_data, "mode_u", priv_mode=0))
    lines.extend(_generate_xstatus_ie_tests(test_data, "mode_s", priv_mode=1))
    lines.extend(_generate_xstatus_ie_tests(test_data, "mode_u", priv_mode=0))

    return lines
