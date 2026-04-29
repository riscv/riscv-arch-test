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
    save_reg, mask_reg, arg_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

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


@add_priv_test_generator(
    "ExceptionsSm",
    required_extensions=["Sm"],
    extra_defines=["#define SKIP_MEPC"],
)
def make_exceptionssm(test_data: TestData) -> list[str]:
    """Main entry point for Sm exception test generation (refactored)."""
    lines: list[str] = []

    lines.extend(
        [
            "# Initialize scratch memory with test data",
            "LA(x10, scratch)",
            "LI(x11, 0xDEADBEEF)",
            "sw x11, 0(x10)",
            "sw x11, 4(x10)",
            "sw x11, 8(x10)",
            "sw x11, 12(x10)",
            "",
        ]
    )

    lines.extend(generate_instr_adr_misaligned_branch_tests(test_data, _CG))
    lines.extend(generate_instr_adr_misaligned_branch_nottaken(test_data, _CG))
    lines.extend(generate_instr_adr_misaligned_jal_tests(test_data, _CG))
    lines.extend(generate_instr_adr_misaligned_jalr_tests(test_data, _CG))
    lines.extend(generate_instr_access_fault_tests(test_data, _CG))
    lines.extend(generate_load_address_misaligned_tests(test_data, _CG, use_sentinel=False))
    lines.extend(generate_load_access_fault_tests(test_data, _CG, use_sigupd=False))
    lines.extend(generate_store_address_misaligned_tests(test_data, _CG))
    lines.extend(generate_store_access_fault_tests(test_data, _CG))
    lines.extend(generate_misaligned_priority_load_tests(test_data, _CG, "cp_misaligned_priority_load", name_infix="_"))
    lines.extend(
        generate_misaligned_priority_store_tests(test_data, _CG, "cp_misaligned_priority_store", name_infix="_")
    )
    lines.extend(
        generate_misaligned_priority_fetch_tests(
            test_data, _CG, "cp_misaligned_priority_fetch", name_prefix="", name_suffix=""
        )
    )
    lines.extend(generate_illegal_instruction_seed_tests(test_data, _CG))
    lines.extend(generate_breakpoint_tests(test_data, _CG))
    lines.extend(generate_illegal_instruction_tests(test_data, _CG))
    lines.extend(generate_ecall_tests(test_data, _CG, "cp_ecall_m", "ecall_m", "Ecall Machine Mode"))
    lines.extend(_generate_mstatus_ie_tests(test_data))

    return lines
