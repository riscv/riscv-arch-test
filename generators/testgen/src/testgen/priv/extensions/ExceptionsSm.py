##################################
# priv/extensions/ExceptionsSm.py
#
# ExceptionsSm test generator
# jgong@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exceptions Sm test generator (refactored, calls ExceptionsCommon)."""

from testgen.asm.helpers import comment_banner, write_sigupd
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
    save_reg, mask_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, "Mstatus Interrupt Enable"),
        f"csrr x{save_reg}, mstatus",
        f"LI(x{mask_reg}, 0x8)",
        "",
        "# Test ecall with mstatus.MIE = 0",
        f"csrrc x0, mstatus, x{mask_reg}",
        test_data.add_testcase("ecall_mie_0", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
        "# ecall returns mepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
        write_sigupd(10, test_data),
        "",
        "# Test ecall with mstatus.MIE = 1",
        f"csrrs x0, mstatus, x{mask_reg}",
        test_data.add_testcase("ecall_mie_1", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
        "# ecall returns mepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
        write_sigupd(10, test_data),
        f"csrw mstatus, x{save_reg}",
    ]

    test_data.int_regs.return_registers([save_reg, mask_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsSm",
    required_extensions=["Sm"],
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

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
