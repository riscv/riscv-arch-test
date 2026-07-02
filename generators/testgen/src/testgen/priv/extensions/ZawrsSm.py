##################################
# priv/extensions/ZawrsSm.py
#
# ZawrsSm privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""ZawrsSm privileged extension test generator for machine-mode."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import clr_mtimer_int, set_mtimer_int, set_mtimer_int_soon
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _zawrs_resume_trap_handler_m(test_data: TestData, r_cause: int, r_temp: int, r_mtimecmp: int) -> list[str]:
    """Trap handler for the M-mode wrs.nto resume-on-interrupt test (mie=1 bin).

    SIGUPD mcause and clears timer interrupt, then return to the test

    Inline code: the `j 4f` guard skips it in
    straight-line flow, and `.align 2` keeps it 4-byte aligned so mtvec can
    address it in direct mode (MODE=0).
    """
    return [
        "# ---- Local trap handler for WRS.NTO resume, mie=1 (direct mode) ----",
        "j 4f                             # skip handler in straight-line code",
        ".option push",
        ".option norvc",
        ".align 2                         # direct-mode mtvec target must be 4-byte aligned",
        "zawrs_resume_trap_handler:",
        f"csrr x{r_cause}, mcause          # mcause: nonzero => trap fired (loop sentinel) + SIGUPD value",
        write_sigupd(r_cause, test_data),
        *clr_mtimer_int(r_temp, r_mtimecmp),
        "mret                             # return to instruction after WRS.NTO",
        ".option pop",
        "4:",
        "",
    ]


def _generate_wrs_sto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate wrs.sto timeout tests.

    Cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    mstatus.MIE = 0
    mie=all 0s to disable interrupts
    Execute WRS.STO in M mode
    2 bins
    """
    ######################################
    covergroup = "ZawrsSm_cg"
    coverpoint = "cp_wrs_sto_timeout"
    ######################################

    r_scratch, r_temp = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            "cp_wrs_sto_timeout",
            _generate_wrs_sto_timeout_tests.__doc__,
        ),
        "",
    ]
    for tw_val in [0, 1]:
        lines.extend(
            [
                "#### Setup ####",
                "# Disable all interrupts in mie",
                "CSRW mie, zero",
                "# mstatus.MIE = 0",
                "csrci mstatus, 8",
                f"# {'Set' if tw_val else 'Clear'} mstatus.TW",
                f"LI(x{r_temp}, 0x200000)",
                f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
            ]
        )

        lines.extend(
            [
                "# lr.w to set up reservation",
                f"LA(x{r_scratch}, scratch)",
                f"lr.w x{r_temp}, (x{r_scratch})",
                test_data.add_testcase(f"tw_{tw_val}", coverpoint, covergroup),
                "WRS.STO",
                "",
            ]
        )

    test_data.int_regs.return_registers([r_scratch, r_temp])
    return lines


def _generate_wrs_no_res_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction no reservation tests

    mstatus.TW ={0/1}
    mstatus.MIE = 0
    mie=all 0s to disable interrupts
    Clear all reservation with sc.w, then execute {WRS.STO/ WRS.NTO} with no reservation created in M mode
    2 x 2 bins
    """

    ######################################
    covergroup = "ZawrsSm_cg"
    coverpoint = "cp_wrs_no_res"
    ######################################

    r_scratch, r_temp, r_temp2 = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            "cp_wrs_no_res",
            _generate_wrs_no_res_tests.__doc__,
        ),
        "",
    ]

    for wrs_ops in ["WRS.STO", "WRS.NTO"]:
        for tw_val in [0, 1]:
            lines.extend(
                [
                    "#### Setup ####",
                    "# Disable all interrupts in mie",
                    "CSRW mie, zero",
                    "# mstatus.MIE = 0",
                    "csrci mstatus, 8",
                    f"# {'Set' if tw_val else 'Clear'} mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
                ]
            )

            lines.extend(
                [
                    "# sc.w to clear reservation",
                    f"LA(x{r_scratch}, scratch)",
                    f"sc.w x{r_temp}, x{r_temp2}, (x{r_scratch})",
                    test_data.add_testcase(
                        f"tw_{tw_val}_{'STO' if wrs_ops == 'WRS.STO' else 'NTO'}", coverpoint, covergroup
                    ),
                    f"{wrs_ops}",
                    "",
                ]
            )
    test_data.int_regs.return_registers([r_scratch, r_temp, r_temp2])

    return lines


def _generate_wrs_resume_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction resume when interrupt pending tests

    cross lr instruction to set up reservation.
    mstatus.TW = 0
    mstatus.MIE = {0/1}
    cross with mie.MTIE=1
    Set up timer to interrupt soon
    execute WRS.NTO in M mode
    2 bins
    """

    ######################################
    covergroup = "ZawrsSm_cg"
    coverpoint = "cp_wrs_resume"
    ######################################

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch, r_cause = test_data.int_regs.get_registers(7)

    lines = [
        comment_banner(
            "cp_wrs_resume",
            _generate_wrs_resume_tests.__doc__,
        ),
        "",
    ]

    for mie_val in [0, 1]:
        lines.extend(
            [
                "#### Setup ####",
                f"# mstatus.MIE = {mie_val}",
                f"{'csrsi' if mie_val else 'csrci'} mstatus, 8",
                "# Set mie.MTIE",
                f"LI(x{r_temp}, 0x80)",
                f"CSRS(mie, x{r_temp})",
                "",
                "# Clear mstatus.TW",
                f"LI(x{r_temp}, 0x200000)",
                f"CSRC(mstatus, x{r_temp})",
                "",
                f"# Install local trap handler in mtvec (direct mode); save old mtvec in x{r_scratch}",
                f"LA(x{r_temp}, zawrs_resume_trap_handler)",
                f"csrrw x{r_scratch}, mtvec, x{r_temp}",
            ]
        )

        lines.extend(
            [
                # r_cause is a safe scratch here (reset to sentinel below before it is read).
                *set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_cause),
                "",
                "",
                test_data.add_testcase(f"mie_{mie_val}", coverpoint, covergroup),
                ".option push",
                ".option norvc",
                f"li x{r_cause}, 0                 # sentinel: nonzero means the trap was taken",
                "# lr.w to set up reservation",
                f"LA(x{r_temp}, scratch)",
                f"lr.w x{r_temp2}, (x{r_temp})",
                "1:",
                "WRS.NTO",
                f"bnez x{r_cause}, 2f              # MIE=1: handler recorded mcause -> done",
                "# Only moves on if MIE = 0 and mip.MTIP = 1, expect no interrupt should be taken",
                f"csrr x{r_temp}, mip",
                f"andi x{r_temp}, x{r_temp}, 0x80  # Extract mip.MTIP",
                f"csrr x{r_temp2}, mstatus",
                f"andi x{r_temp2}, x{r_temp2}, 0x8  # Extract mstatus.MIE",
                f"bnez x{r_temp2}, 1b              # MIE = 1 -> retry",
                f"beqz x{r_temp}, 1b              # No interrupt pending -> retry",
                "2:",
                ".option pop",
                "# Restore the framework trap handler",
                f"csrw mtvec, x{r_scratch}",
                *clr_mtimer_int(r_temp, r_mtimecmp),
                "",
            ]
        )
    # Emit the shared local trap handler AFTER the loop: write_sigupd is evaluated
    # here (generation time), so it binds to the last testcase label, mie_1. Both
    # mie bins point mtvec at this label via a forward reference.
    lines.extend(_zawrs_resume_trap_handler_m(test_data, r_cause, r_temp, r_mtimecmp))

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch, r_cause])
    return lines


def _generate_wrs_no_mie_tests(test_data: TestData) -> list[str]:
    """Generate wrs tests with mie = all 0s.

    cross lr instruction to set up reservation
    mstatus.MIE = 1
    mie = all 0s
    mstatus.TW = 0
    mip.mtip = {MSIP + MEIP + MTIP}
    execute WRS.STO in M mode
    1 bin
    """
    ######################################
    covergroup = "ZawrsSm_cg"
    coverpoint = "cp_wrs_no_mie"
    ######################################

    r_temp, r_temp2, r_mtime, r_mtimecmp = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            "cp_wrs_no_mie",
            _generate_wrs_no_mie_tests.__doc__,
        ),
        "",
    ]

    lines.extend(
        [
            "#### Setup ####",
            "# Disable all interrupts in mie",
            "CSRW mie, zero",
            "# mstatus.MIE = 1",
            "csrsi mstatus, 8",
            "# Clear mstatus.TW",
            f"LI(x{r_temp}, 0x200000)",
            f"CSRC(mstatus, x{r_temp})",
        ]
    )

    lines.extend(
        [
            "# Set all M mode interrupts pending",
            "RVTEST_SET_MEXT_INT",
            "RVTEST_SET_MSW_INT",
            *set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2),
        ]
    )

    lines.extend(
        [
            "# lr.w to set up reservation",
            f"LA(x{r_temp2}, scratch)",
            f"lr.w x{r_temp}, (x{r_temp2})",
            test_data.add_testcase("wrs_sto", coverpoint, covergroup),
            "WRS.STO",
            "",
        ]
    )

    lines.extend(
        [
            "# Clean up",
            "RVTEST_CLR_MEXT_INT",
            "RVTEST_CLR_MSW_INT",
            *clr_mtimer_int(r_temp, r_mtimecmp),
        ]
    )
    test_data.int_regs.return_registers([r_temp, r_temp2, r_mtime, r_mtimecmp])
    return lines


@add_priv_test_generator("ZawrsSm", required_extensions=["Sm", "Zawrs", "Zalrsc"])
def make_zawrssm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZawrSm WRS instructions at machine-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_wrs_sto_timeout_tests(test_data))
    tc.code.extend(_generate_wrs_no_res_tests(test_data))
    tc.code.extend(_generate_wrs_resume_tests(test_data))
    tc.code.extend(_generate_wrs_no_mie_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
