##################################
# priv/extensions/ExceptionsU.py
#
# ExceptionsU extension exception test generator.
# huahuang@hmc.edu Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsU test generator."""

from testgen.asm.helpers import comment_banner
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
        # "RVTEST_GOTO_MMODE",
        # f"csrr x{save_reg}, mstatus",
        tsbi_call(f"csrr x{save_reg}, mstatus"),
        f"LI(x{mask_reg}, 0x88) # mstatus.MIE=0, mstatus.MPIE=0",
        # f"csrc mstatus, x{mask_reg}",
        tsbi_call(f"csrc mstatus, x{mask_reg}"),
        # RVTEST_GOTO_LOWER_MODE Umode",
        test_data.add_testcase("ecall_mie_0", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST",
        # "RVTEST_GOTO_MMODE",
        f"LI(x{mask_reg}, 0x80) # mstatus.MIE=0, mstatus.MPIE=1, then when returning from SBI call, mstatus.MIE becomes 1",
        tsbi_call(f"csrs mstatus, x{mask_reg}"),
        # f"csrrs x0, mstatus, x{mask_reg}",
        # "RVTEST_GOTO_LOWER_MODE Umode",
        test_data.add_testcase("ecall_mie_1", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST",
        # "RVTEST_GOTO_MMODE",
        # f"csrw mstatus, x{save_reg}",
        tsbi_call(f"csrw mstatus, x{save_reg}"),
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsU",
    required_extensions=["U"],
    extra_defines=["#define BOOT_TO_UMODE"],
)
def make_exceptionsu(test_data: TestData) -> list[TestChunk]:
    """Main entry point for U exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

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
    tc.code.extend(_generate_mstatus_ie_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
