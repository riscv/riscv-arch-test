##################################
# priv/extensions/ExceptionsSm.py
#
# ExceptionsSm test generator
# jgong@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exceptions Sm test generator (refactored, calls ExceptionsCommon)."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
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

_CG = "ExceptionsSm_cg"


def _generate_mstatus_ie_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = _CG, "cp_mstatus_ie"
    save_reg, mask_reg, arg_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(coverpoint, "Mstatus Interrupt Enable"),
        f"csrr x{save_reg}, mstatus",
        f"LI(x{mask_reg}, 0x8)",
        "",
        "# Test ecall with mstatus.MIE = 0",
        f"csrrc x0, mstatus, x{mask_reg}",
        f"LI(x{arg_reg}, 3)",
        test_data.add_testcase("ecall_mie_0", coverpoint, covergroup),
        "ecall",
        "nop",
        "",
        "# Test ecall with mstatus.MIE = 1",
        f"csrrs x0, mstatus, x{mask_reg}",
        f"LI(x{arg_reg}, 3)",
        test_data.add_testcase("ecall_mie_1", coverpoint, covergroup),
        "ecall",
        "nop",
        f"csrw mstatus, x{save_reg}",
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg, arg_reg])
    return lines


def _generate_minstret_trap_tests(test_data: TestData) -> list[str]:
    """minstret must NOT increment for instructions that trap before retiring."""
    covergroup = _CG
    r_before, r_after, r_diff, r_tmp = test_data.int_regs.get_registers(4)

    lines = []

    ######################################
    # Ensure counters are running
    ######################################
    lines.append(comment_banner("Enable Counters", "Ensure mcountinhibit is 0 so counters can run"))
    lines.extend(
        [
            f"LI(x{r_tmp}, 0)                      # Load 0 (enable all counters)",
            f"csrw mcountinhibit, x{r_tmp}        # Clear inhibit register",
            "nop\nnop\nnop",
        ]
    )

    ######################################
    coverpoint = "cp_minstret_ecall"
    ######################################
    lines.append(comment_banner(coverpoint, "ecall: traps before retiring, minstret must not increment"))
    lines.extend(
        [
            "",
            test_data.add_testcase("ecall", coverpoint, covergroup),
            f"csrr x{r_before}, minstret",
            "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
            f"csrr x{r_after}, minstret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_minstret_ebreak"
    ######################################
    lines.append(comment_banner(coverpoint, "ebreak: traps before retiring, minstret must not increment"))
    lines.extend(
        [
            "",
            test_data.add_testcase("ebreak", coverpoint, covergroup),
            f"csrr x{r_before}, minstret",
            "ebreak",
            "nop",
            f"csrr x{r_after}, minstret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_minstret_illegal"
    ######################################
    lines.append(comment_banner(coverpoint, "Illegal instruction: traps before retiring, minstret must not increment"))
    lines.extend(
        [
            "",
            ".p2align 2",
            test_data.add_testcase("illegal", coverpoint, covergroup),
            f"csrr x{r_before}, minstret",
            ".word 0xFFFFFFFF",
            "nop",
            f"csrr x{r_after}, minstret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_minstret_load_fault"
    ######################################
    lines.append(comment_banner(coverpoint, "Load access fault: traps before retiring, minstret must not increment"))
    r_addr = test_data.int_regs.get_register()
    lines.extend(
        [
            "",
            "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
            test_data.add_testcase("load_access_fault", coverpoint, covergroup),
            f"LA(x{r_addr}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"csrr x{r_before}, minstret",
            f"lw x{r_tmp}, 0(x{r_addr})",
            f"csrr x{r_after}, minstret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
            "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
        ]
    )
    test_data.int_regs.return_registers([r_addr])

    ######################################
    coverpoint = "cp_minstret_load_misaligned"
    ######################################
    lines.append(
        comment_banner(coverpoint, "Load address misaligned: traps before retiring, minstret must not increment")
    )
    r_addr = test_data.int_regs.get_register()
    lines.extend(
        [
            "",
            test_data.add_testcase("load_misaligned", coverpoint, covergroup),
            f"LA(x{r_addr}, scratch)",
            f"addi x{r_addr}, x{r_addr}, 1  # misalign by 1 byte",
            f"csrr x{r_before}, minstret",
            f"lw x{r_tmp}, 0(x{r_addr})",
            f"csrr x{r_after}, minstret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )
    test_data.int_regs.return_registers([r_addr])

    test_data.int_regs.return_registers([r_before, r_after, r_diff, r_tmp])
    return lines


@add_priv_test_generator(
    "ExceptionsSm",
    required_extensions=["Sm"],
    extra_defines=["#define SKIP_MEPC"],
)
def make_exceptionssm(test_data: TestData) -> list[TestChunk]:
    """Main entry point for Sm exception test generation (refactored)."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(generate_instr_adr_misaligned_branch_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_branch_nottaken(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_jal_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_jalr_tests(test_data, _CG))
    tc.code.extend(generate_instr_access_fault_tests(test_data, _CG))
    tc.code.extend(generate_load_address_misaligned_tests(test_data, _CG, use_sentinel=False))
    tc.code.extend(generate_load_access_fault_tests(test_data, _CG, use_sigupd=False))
    tc.code.extend(generate_store_address_misaligned_tests(test_data, _CG))
    tc.code.extend(generate_store_access_fault_tests(test_data, _CG))
    tc.code.extend(
        generate_misaligned_priority_load_tests(test_data, _CG, "cp_misaligned_priority_load", name_infix="_")
    )
    tc.code.extend(
        generate_misaligned_priority_store_tests(test_data, _CG, "cp_misaligned_priority_store", name_infix="_")
    )
    tc.code.extend(
        generate_misaligned_priority_fetch_tests(
            test_data, _CG, "cp_misaligned_priority_fetch", name_prefix="", name_suffix=""
        )
    )
    tc.code.extend(generate_illegal_instruction_seed_tests(test_data, _CG))
    tc.code.extend(generate_breakpoint_tests(test_data, _CG))
    tc.code.extend(generate_illegal_instruction_tests(test_data, _CG))
    tc.code.extend(generate_ecall_tests(test_data, _CG, "cp_ecall_m", "ecall_m", "Ecall Machine Mode"))
    tc.code.extend(_generate_mstatus_ie_tests(test_data))
    tc.code.extend(_generate_minstret_trap_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
