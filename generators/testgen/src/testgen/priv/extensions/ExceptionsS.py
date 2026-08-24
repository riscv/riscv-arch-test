##################################
# priv/extensions/ExceptionsS.py
#
# ExceptionsS test generator
# jgong@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Exceptions S-mode test generator (refactored, calls ExceptionsCommon)."""

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
    dest_regs = test_data.int_regs.get_registers(2)

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
                write_sigupd(dest_regs[1], test_data),
            ]
        )

    test_data.int_regs.return_registers(dest_regs)
    return lines


def _generate_stvec_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    """Delegated illegal-instruction exceptions in S/U-mode trap through stvec (cp_stvec crosses illegalops)."""
    covergroup, coverpoint = _CG, "cp_stvec"

    lines = [
        comment_banner(coverpoint, "delegated illegal instruction in S/U mode goes to stvec"),
    ]

    if priv_mode == 1:
        lines.append("RVTEST_TSBI_GOTO_SMODE")
    elif priv_mode == 0:
        lines.append("RVTEST_TSBI_GOTO_UMODE")

    for name, word in (("zeros", "0x00000000"), ("ones", "0xFFFFFFFF")):
        lines.extend(
            [
                f"# Illegal instruction ({name}) should trap through stvec",
                test_data.add_testcase(f"stvec_illegalinstr_{name}_{mode_tag}", coverpoint, covergroup),
                ".p2align 2",
                f".word {word}",
            ]
        )
    if priv_mode == 0:
        lines.append("RVTEST_TSBI_GOTO_SMODE  # back to S-mode for the tests that follow")

    return lines


def _generate_xstatus_ie_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    covergroup, coverpoint = _CG, "cp_xstatus_ie"
    save_reg, mask_mie, mask_sie = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(coverpoint, "xstatus Interrupt Enable"),
        "# Save mstatus before modifying it",
        tsbi_call(f"csrr x{save_reg}, mstatus"),
    ]
    if priv_mode == 0:
        lines.append("RVTEST_TSBI_GOTO_UMODE")

    for mie in (0, 1):
        for sie in (0, 1):
            tag = f"{mode_tag}_mie_{mie}_sie_{sie}"
            lines.extend(
                [
                    f"\n# {tag}",
                    f"LI(x{mask_mie}, 0x88)",  # MPIE | MIE: mret in the T-SBI handler copies MPIE into MIE
                    f"LI(x{mask_sie}, 0x22)",  # SPIE | SIE: likewise if the handler returns with sret
                    # Set MPIE and MIE so mret goes to the proper MIE in the next mode
                    tsbi_call(f"{'csrs' if mie else 'csrc'} mstatus, x{mask_mie}"),
                ]
            )

            sie_cmd = f"{'csrs' if sie else 'csrc'} sstatus, x{mask_sie}"
            if priv_mode == 1:
                lines.append(sie_cmd)
            else:  # sstatus is not accessible from U-mode
                lines.append(tsbi_call(sie_cmd))

            lines.extend(
                [
                    test_data.add_testcase(tag, coverpoint, covergroup),
                    "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
                    "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
                    write_sigupd(10, test_data),
                ]
            )

    lines.extend(
        [
            "\n# Restore mstatus",
            tsbi_call(f"csrw mstatus, x{save_reg}"),
        ]
    )
    if priv_mode == 0:
        lines.append("RVTEST_TSBI_GOTO_SMODE")

    test_data.int_regs.return_registers([save_reg, mask_mie, mask_sie])
    return lines


@add_priv_test_generator(
    "ExceptionsS",
    required_extensions=["S"],
    extra_defines=[
        "#define TRAP_SIGUPD_COUNT 3000",
        "#define BOOT_TO_SMODE",
    ],
)
def make_exceptionss(test_data: TestData) -> list[TestChunk]:
    """Main entry point for S-mode exception test generation (refactored)."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(generate_instr_adr_misaligned_jal_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_jalr_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_branch_tests(test_data, _CG))
    tc.code.extend(generate_instr_adr_misaligned_branch_nottaken(test_data, _CG))
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
    tc.code.extend(
        generate_misaligned_priority_fetch_tests(
            test_data, _CG, "cp_misaligned_priority", name_prefix="fetch_", name_suffix="_priority"
        )
    )
    tc.code.extend(generate_ecall_tests(test_data, _CG, "cp_ecall_s", "ecall_s", "Ecall"))
    tc.code.extend(_generate_illegal_instruction_csr_tests(test_data))
    tc.code.extend(_generate_stvec_tests(test_data, "mode_s", priv_mode=1))
    tc.code.extend(_generate_stvec_tests(test_data, "mode_u", priv_mode=0))
    tc.code.extend(_generate_xstatus_ie_tests(test_data, "mode_s", priv_mode=1))
    tc.code.extend(_generate_xstatus_ie_tests(test_data, "mode_u", priv_mode=0))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
