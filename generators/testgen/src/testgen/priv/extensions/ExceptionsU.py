##################################
# priv/extensions/ExceptionsU.py
#
# ExceptionsU extension exception test generator.
# huahuang@hmc.edu Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsU test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
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
    generate_misaligned_priority_load_tests,
    generate_misaligned_priority_store_tests,
    generate_store_access_fault_tests,
    generate_store_address_misaligned_tests,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsU_cg"


def _generate_mstatus_ie_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsU_cg", "cp_mstatus_ie"
    save_reg, mask_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, "ecall from user mode with MIE=0 vs MIE=1"),
        "RVTEST_GOTO_MMODE",
        f"csrr x{save_reg}, mstatus",
        f"LI(x{mask_reg}, 0x88)",
        f"csrc mstatus, x{mask_reg}",
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
        "RVTEST_GOTO_MMODE",
        f"csrw mstatus, x{save_reg}",
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg])
    return lines


def _generate_uinstret_trap_tests(test_data: TestData) -> list[str]:
    """instret delta checks from U-mode for instructions that trap before retiring."""
    covergroup = _CG
    r_before, r_after, r_diff, r_tmp = test_data.int_regs.get_registers(4)

    lines = ["", "#ifdef ZICNTR_SUPPORTED"]

    ######################################
    coverpoint = "cp_uinstret_ecall"
    ######################################
    lines.append(comment_banner(coverpoint, "ecall from U-mode: traps before retiring, instret must not increment"))
    lines.extend(
        [
            "",
            test_data.add_testcase("ecall", coverpoint, covergroup),
            f"csrr x{r_before}, instret",
            "RVTEST_TSBI_ECALL_TEST               # traps, resumes right after this line back in U-mode",
            f"csrr x{r_after}, instret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_uinstret_ebreak"
    ######################################
    lines.append(comment_banner(coverpoint, "ebreak from U-mode: traps before retiring, instret must not increment"))
    lines.extend(
        [
            "",
            test_data.add_testcase("ebreak", coverpoint, covergroup),
            f"csrr x{r_before}, instret",
            "ebreak",
            "nop",
            f"csrr x{r_after}, instret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_uinstret_illegal"
    ######################################
    lines.append(
        comment_banner(coverpoint, "Illegal instruction from U-mode: traps before retiring, instret must not increment")
    )
    lines.extend(
        [
            "",
            ".p2align 2",
            test_data.add_testcase("illegal", coverpoint, covergroup),
            f"csrr x{r_before}, instret",
            ".word 0xFFFFFFFF",
            "nop",
            f"csrr x{r_after}, instret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_uinstret_load_fault"
    ######################################
    lines.append(
        comment_banner(coverpoint, "Load access fault from U-mode: traps before retiring, instret must not increment")
    )
    r_addr = test_data.int_regs.get_register()
    lines.extend(
        [
            "",
            "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
            test_data.add_testcase("load_access_fault", coverpoint, covergroup),
            f"LA(x{r_addr}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"csrr x{r_before}, instret",
            f"lw x{r_tmp}, 0(x{r_addr})",
            f"csrr x{r_after}, instret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
            "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
        ]
    )

    ######################################
    coverpoint = "cp_uinstret_load_misaligned"
    ######################################
    lines.append(
        comment_banner(
            coverpoint, "Load address misaligned from U-mode: traps before retiring, instret must not increment"
        )
    )
    lines.extend(
        [
            "",
            test_data.add_testcase("load_misaligned", coverpoint, covergroup),
            f"LA(x{r_addr}, scratch)",
            f"addi x{r_addr}, x{r_addr}, 1        # misalign by 1 byte",
            f"csrr x{r_before}, instret",
            f"lw x{r_tmp}, 0(x{r_addr})",
            f"csrr x{r_after}, instret",
            f"sub x{r_diff}, x{r_after}, x{r_before}",
            write_sigupd(r_diff, test_data),
        ]
    )
    test_data.int_regs.return_registers([r_addr, r_before, r_after, r_diff, r_tmp])

    lines.append("#endif // ZICNTR_SUPPORTED")

    return lines


@add_priv_test_generator(
    "ExceptionsU",
    required_extensions=["U"],
    extra_defines=["#define SKIP_MEPC"],  # hangs otherwise
)
def make_exceptionsu(test_data: TestData) -> list[TestChunk]:
    """Main entry point for U exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.append("RVTEST_GOTO_LOWER_MODE Umode  # Run tests in user mode\n")

    tc.code.extend(generate_instr_adr_misaligned_branch_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_branch_nottaken(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_jal_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_jalr_tests(test_data, _CG))
    tc.code.extend(generate_instr_access_fault_tests(test_data, _CG))
    tc.code.extend(generate_illegal_instruction_tests(test_data, _CG))
    tc.code.extend(generate_illegal_instruction_seed_tests(test_data, _CG))
    tc.code.extend(generate_breakpoint_tests(test_data, _CG))
    tc.code.extend(generate_load_address_misaligned_tests(test_data, _CG, use_sentinel=True))
    tc.code.extend(generate_load_access_fault_tests(test_data, _CG, use_sigupd=True))
    tc.code.extend(generate_store_address_misaligned_tests(test_data, _CG))
    tc.code.extend(generate_store_access_fault_tests(test_data, _CG))
    tc.code.extend(
        generate_misaligned_priority_load_tests(test_data, _CG, "cp_misaligned_priority", name_infix="_load_")
    )
    tc.code.extend(
        generate_misaligned_priority_store_tests(test_data, _CG, "cp_misaligned_priority", name_infix="_store_")
    )
    tc.code.extend(generate_ecall_tests(test_data, _CG, "cp_ecall_u", "ecall_u", "Ecall"))
    tc.code.extend(_generate_uinstret_trap_tests(test_data))
    tc.code.extend(_generate_mstatus_ie_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
