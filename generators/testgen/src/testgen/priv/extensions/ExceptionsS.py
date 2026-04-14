##################################
# priv/extensions/ExceptionsS.py
#
# ExceptionsS test generator
# jgong@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exceptions S-mode test generator (refactored, calls ExceptionsCommon)."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.ExceptionsCommon import (
    generate_breakpoint_tests,
    generate_ecall_tests,
    generate_illegal_instruction_seed_tests,
    generate_illegal_instruction_tests,
    generate_instr_access_fault_tests,
    generate_instr_adr_misaligned_branch_nottaken,
    generate_instr_adr_misaligned_branch_tests,
    generate_instr_adr_misaligned_jal_tests,
    generate_instr_adr_misaligned_jalr_tests,
    generate_load_access_fault_tests,
    generate_load_address_misaligned_tests,
    generate_misaligned_priority_fetch_tests,
    generate_misaligned_priority_load_tests,
    generate_misaligned_priority_store_tests,
    generate_store_access_fault_tests,
    generate_store_address_misaligned_tests,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsS_cg"


def _generate_illegal_instruction_csr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = _CG, "cp_illegal_instruction_csr"
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
    Runs 10 exception tests x 17 medeleg values for one privilege mode.
    Assumes caller has already entered the correct privilege mode.
    Sets medeleg itself for each iteration by returning to M-mode temporarily.
    """
    covergroup = _CG
    coverpoint = "cp_medeleg_msu"

    # excluding x6, x7, x9 since RVTEST_GOTO_LOWER_MODE may clobber these registers
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
    covergroup, coverpoint = _CG, "cp_stvec"
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
    covergroup, coverpoint = _CG, "cp_xstatus_ie"
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
    """Main entry point for S-mode exception test generation (refactored)."""
    lines: list[str] = []

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

    lines.extend(["RVTEST_GOTO_LOWER_MODE Smode  # use S-mode"])
    lines.extend(generate_instr_adr_misaligned_jal_tests(test_data, _CG))
    lines.extend(generate_instr_adr_misaligned_jalr_tests(test_data, _CG))
    lines.extend(generate_instr_adr_misaligned_branch_tests(test_data, _CG))
    lines.extend(generate_instr_adr_misaligned_branch_nottaken(test_data, _CG))
    lines.extend(generate_instr_access_fault_tests(test_data, _CG))
    lines.extend(generate_illegal_instruction_tests(test_data, _CG))
    lines.extend(generate_illegal_instruction_seed_tests(test_data, _CG))
    lines.extend(generate_breakpoint_tests(test_data, _CG))
    lines.extend(generate_load_address_misaligned_tests(test_data, _CG, use_sentinel=True))
    lines.extend(generate_load_access_fault_tests(test_data, _CG, use_sigupd=True))
    lines.extend(generate_store_address_misaligned_tests(test_data, _CG))
    lines.extend(generate_store_access_fault_tests(test_data, _CG))
    lines.extend(generate_misaligned_priority_load_tests(test_data, _CG, "cp_misaligned_priority", name_infix="_load_"))
    lines.extend(
        generate_misaligned_priority_store_tests(test_data, _CG, "cp_misaligned_priority", name_infix="_store_")
    )
    lines.extend(
        generate_misaligned_priority_fetch_tests(
            test_data, _CG, "cp_misaligned_priority", name_prefix="fetch_", name_suffix="_priority"
        )
    )
    lines.extend(generate_ecall_tests(test_data, _CG, "cp_ecall_s", "ecall_s", "Ecall"))
    lines.extend(_generate_illegal_instruction_csr_tests(test_data))
    lines.extend(_generate_medeleg_msu_tests(test_data, "mode_m", priv_mode=3))
    lines.extend(_generate_medeleg_msu_tests(test_data, "mode_s", priv_mode=1))
    lines.extend(_generate_medeleg_msu_tests(test_data, "mode_u", priv_mode=0))
    lines.extend(_generate_stvec_tests(test_data, "mode_s", priv_mode=1))
    lines.extend(_generate_stvec_tests(test_data, "mode_u", priv_mode=0))
    lines.extend(_generate_xstatus_ie_tests(test_data, "mode_s", priv_mode=1))
    lines.extend(_generate_xstatus_ie_tests(test_data, "mode_u", priv_mode=0))

    return lines
