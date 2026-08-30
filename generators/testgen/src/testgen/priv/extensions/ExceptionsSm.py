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


_MEDELEG_WALK = (
    [0]
    + [1 << i for i in range(9)]  # bits 0-8 walking 1s
    + [1 << i for i in range(10, 16)]  # bits 10-15 walking 1s
    + [0b1011_0001_1111_1111]
)


def _generate_medeleg_msu_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    """Runs 10 exception tests x 17 medeleg values for one privilege mode."""
    covergroup = _CG
    coverpoint = "cp_medeleg_msu"

    addr_reg, data_reg, check_reg, medeleg_reg, medeleg_orig = test_data.int_regs.get_registers(5)
    goto_mode = {3: [], 1: ["RVTEST_TSBI_GOTO_SMODE"], 0: ["RVTEST_TSBI_GOTO_UMODE"]}[priv_mode]
    goto_back = ["RVTEST_TSBI_GOTO_MMODE"] if priv_mode != 3 else []

    lines = [f"csrr x{medeleg_orig}, medeleg  # save original medeleg value"]

    for medeleg_val in _MEDELEG_WALK:
        tag = f"mdlg_{medeleg_val:#06x}_{mode_tag}"
        lines.append(f"\n# --- medeleg={medeleg_val:#06x}, {mode_tag} ---")

        # set medeleg in M-mode, then enter the mode under test
        lines.extend([f"LI(x{medeleg_reg}, {medeleg_val})", f"csrw medeleg, x{medeleg_reg}", *goto_mode])

        # Instruction misaligned: one aligned and one misaligned jalr target next to the access-fault
        # address.  Also tests priority of misaligned and access faults.  Simple misalignment tests
        # are in the ExceptionsCommon generator and are not repeated here.
        lines.extend(
            [
                "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                test_data.add_testcase(f"instrmisaligned_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"jalr x1, 0(x{addr_reg})  # aligned target",
                f"jalr x1, 2(x{addr_reg})  # misaligned target",
                "#endif",
            ]
        )

        # Instruction access fault
        lines.extend(
            [
                "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                test_data.add_testcase(f"instraccessfault_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"jalr x1, 0(x{addr_reg})",
                "#endif",
            ]
        )

        # Illegal instruction zeros
        lines.extend(
            [
                test_data.add_testcase(f"illegalinstr_zeros_{tag}", coverpoint, covergroup),
                ".p2align 2",
                ".word 0x00000000",
            ]
        )

        # Illegal instruction ones
        lines.extend(
            [
                test_data.add_testcase(f"illegalinstr_ones_{tag}", coverpoint, covergroup),
                ".p2align 2",
                ".word 0xFFFFFFFF",
            ]
        )

        # Ebreak
        lines.extend(
            [
                test_data.add_testcase(f"ebreak_{tag}", coverpoint, covergroup),
                "ebreak",
            ]
        )

        # Load misaligned
        lines.extend(
            [test_data.add_testcase(f"loadmisaligned_{tag}", coverpoint, covergroup), f"LA(x{addr_reg}, scratch)"]
        )
        for offset in range(8):
            for op in ["lw", "lh", "lhu", "lb", "lbu"]:
                lines.append(f"{op} x{check_reg}, {offset}(x{addr_reg})")
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f" ld x{check_reg}, {offset}(x{addr_reg})",
                    f" lwu x{check_reg}, {offset}(x{addr_reg})",
                    "#endif",
                ]
            )

        # Load access fault
        lines.append("#ifdef RVMODEL_ACCESS_FAULT_ADDRESS")
        lines.extend(
            [
                test_data.add_testcase(f"loadaccessfault_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            ]
        )
        for op in ["lw", "lh", "lhu", "lb", "lbu"]:
            lines.append(f"{op} x{check_reg}, 0(x{addr_reg})")
        lines.extend(
            [
                "#if __riscv_xlen == 64",
                f" ld x{check_reg}, 0(x{addr_reg})",
                f" lwu x{check_reg}, 0(x{addr_reg})",
                "#endif",
                "#endif",
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
                lines.append(f"{op} x{data_reg}, {offset}(x{addr_reg})")
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f" sd x{data_reg}, {offset}(x{addr_reg})",
                    "#endif",
                ]
            )

        # Store access fault
        lines.append("#ifdef RVMODEL_ACCESS_FAULT_ADDRESS")
        lines.extend(
            [
                test_data.add_testcase(f"storeaccessfault_{tag}", coverpoint, covergroup),
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{data_reg}, 0xADDEDCAB)",
            ]
        )
        for op in ["sw", "sh", "sb"]:
            lines.append(f"{op} x{data_reg}, 0(x{addr_reg})")
        lines.extend(
            [
                "#if __riscv_xlen == 64",
                f" sd x{data_reg}, 0(x{addr_reg})",
                "#endif",
                "#endif",
            ]
        )

        lines.extend(
            [
                test_data.add_testcase(f"ecall_{tag}", coverpoint, covergroup),
                "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
                "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
                write_sigupd(10, test_data),
            ]
        )

        # Return to M-mode.  With ecall-from-U delegated (medeleg bit 8), a GOTO_MMODE from U-mode is
        # forwarded by the S-mode handler and the caller resumes in U-mode (handler returns into the
        # forwarding stub, whose sret drops to SPP=U), so hop to S-mode first and go to M from there.
        if priv_mode == 0 and medeleg_val & (1 << 8):
            lines.extend(["RVTEST_TSBI_GOTO_SMODE", "RVTEST_TSBI_GOTO_MMODE"])
        else:
            lines.extend(goto_back)

    # Set medeleg to return to default state (in M-mode)
    lines.extend([f"csrw medeleg, x{medeleg_orig}"])

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg, medeleg_reg, medeleg_orig])
    return lines


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


def _generate_xstatus_ie_tests(test_data: TestData, mode_tag: str, priv_mode: int) -> list[str]:
    """
    ecall from S/U-mode with every combination of medeleg[8] (ecall-from-U delegated) and mstatus.MIE
    and .SIE.  Runs from M-mode: medeleg and both mstatus bits are written directly (MPIE/SPIE alongside
    MIE/SIE, so the mret/sret of the T-SBI hop that drops into the mode under test carries them
    through), then RVTEST_TSBI_GOTO_SMODE/UMODE, ecall, and RVTEST_TSBI_GOTO_MMODE back.  With
    medeleg[8] set, a GOTO_MMODE from U-mode is forwarded by the S-mode handler and the caller would
    resume in U-mode, so that case hops to S-mode first.
    """
    covergroup, coverpoint = _CG, "cp_xstatus_ie"
    save_reg, mask_mie, mask_sie, medeleg_reg = test_data.int_regs.get_registers(4)
    goto_mode = "RVTEST_TSBI_GOTO_SMODE" if priv_mode == 1 else "RVTEST_TSBI_GOTO_UMODE"

    lines = [
        comment_banner(
            coverpoint, f"xstatus Interrupt Enable: ecall from {mode_tag} with medeleg[8], MIE, SIE 0 and 1"
        ),
        "# Save mstatus before modifying it",
        f"csrr x{save_reg}, mstatus",
        f"LI(x{mask_mie}, 0x88)",  # MPIE | MIE: the hop's mret copies MPIE into MIE
        f"LI(x{mask_sie}, 0x22)",  # SPIE | SIE: likewise for a handler that returns with sret
        f"LI(x{medeleg_reg}, 1 << 8)",  # medeleg.ecall_from_U
    ]

    for medeleg_b8 in (0, 1):
        lines.append(f"{'csrs' if medeleg_b8 else 'csrc'} medeleg, x{medeleg_reg}")
        goto_back = (
            ["RVTEST_TSBI_GOTO_SMODE", "RVTEST_TSBI_GOTO_MMODE"]
            if priv_mode == 0 and medeleg_b8
            else ["RVTEST_TSBI_GOTO_MMODE"]
        )
        for mie in (0, 1):
            for sie in (0, 1):
                tag = f"{mode_tag}_mdlg_{medeleg_b8}_mie_{mie}_sie_{sie}"
                lines.extend(
                    [
                        f"\n# {tag}",
                        f"{'csrs' if mie else 'csrc'} mstatus, x{mask_mie}",
                        f"{'csrs' if sie else 'csrc'} mstatus, x{mask_sie}",
                        goto_mode,
                        test_data.add_testcase(tag, coverpoint, covergroup),
                        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
                        "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
                        write_sigupd(10, test_data),
                        *goto_back,
                    ]
                )

    lines.extend(["\n# Restore mstatus and medeleg", f"csrw mstatus, x{save_reg}", f"csrc medeleg, x{medeleg_reg}"])

    test_data.int_regs.return_registers([save_reg, mask_mie, mask_sie, medeleg_reg])
    return lines


@add_priv_test_generator(
    "ExceptionsSm",
    required_extensions=["Sm"],
    extra_defines=[
        "#define BOOT_TO_MMODE",
        "#define TRAP_SIGUPD_COUNT 3000",
    ],
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
    tc.code.append("#ifdef S_SUPPORTED")
    tc.code.extend(_generate_xstatus_ie_tests(test_data, "mode_s", priv_mode=1))
    tc.code.extend(_generate_xstatus_ie_tests(test_data, "mode_u", priv_mode=0))
    tc.code.append("#endif // S_SUPPORTED")
    test_chunks.append(test_data.end_test_chunk())

    # medeleg only exists with S-mode; walk it from M-, S- and U-mode.  One file per mode: each walk
    # records 306 trap signatures of up to 6 words, ~1.8k words of the TRAP_SIGUPD_COUNT area.
    for mode_tag, priv_mode in (("mode_m", 3), ("mode_s", 1), ("mode_u", 0)):
        tc = test_data.begin_test_chunk(f"medeleg_{mode_tag[-1]}")
        tc.code.append("#ifdef S_SUPPORTED")
        tc.code.extend(_generate_medeleg_msu_tests(test_data, mode_tag, priv_mode))
        tc.code.append("#endif // S_SUPPORTED")
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
