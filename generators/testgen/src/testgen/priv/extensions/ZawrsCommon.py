##################################
# priv/extensions/ZawrsCommon.py
#
# Shared Zawrs tests generation
# ellyu@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zawrs tests in all priv modes"""

from testgen.asm.helpers import write_sigupd
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_int,
    set_menvcfg_stce,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimer_int_soon_sstc,
    set_stimer_mmode,
)
from testgen.data.state import TestData


def _read_trap_count_helper(r_temp: int) -> list[str]:
    """Read trap count into r_temp"""
    return [f"# Read trap count into x{r_temp}", f"LA(x{r_temp}, rvtest_trap_count)", f"LREG x{r_temp}, 0(x{r_temp})"]


def wrs_resume_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
) -> list[str]:
    """wrs resume when interrupt"""

    ######################################
    coverpoint = "cp_wrs_resume"
    ######################################

    r_time, r_temp3, r_cause, r_temp, r_temp2, r_timecmp = test_data.int_regs.get_registers(6)

    lines = []
    if priv != "M":
        sie_list = [0, 1]
        tw_list = [0]
    else:  # if test is for M mode
        sie_list = [0]  # SIE value does not matter for M mode, just set to 0
        tw_list = [0, 1]

    if priv != "M":
        lines.extend(
            [
                "#ifdef SSTC_SUPPORTED",
                "# Enable Sstc (menvcfg.STCE) so stimecmp drives sip.STIP",
                *set_menvcfg_stce(r_temp, True),
                "# Delegate supervisor timer interrupt (STI) to S-mode",
                f"LI(x{r_temp}, 0x20)",
                f"csrs mideleg, x{r_temp}",
                "#endif",
            ]
        )
    for op in ["WRS.NTO", "WRS.STO"]:
        for tw_val in tw_list:
            for sie_val in sie_list:
                for mie_val in [0, 1]:
                    lines.extend(
                        [
                            "#### Setup ####",
                            f"# mstatus.MPIE and mstatus.MIE = {mie_val}",
                            f"LI(x{r_temp}, 0x88)",
                            f"{'csrs' if mie_val else 'csrc'} mstatus, x{r_temp}",
                            "# Write mstatus.TW",
                            f"LI(x{r_temp}, 0x200000)",
                            f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}",
                            "",
                        ]
                    )

                    if priv != "M":
                        lines.extend(
                            [
                                "#ifdef S_SUPPORTED",
                                f"# sstatus.SIE = {sie_val}",
                                f"{'csrsi' if sie_val else 'csrci'} sstatus, 2",
                                "#endif",
                                "#ifdef SSTC_SUPPORTED",
                                "# Set sie.STIE",
                                f"LI(x{r_temp}, 0x20)",
                                f"csrs sie, x{r_temp}",
                                "# Set stimer interrupt soon",
                                *set_stimer_int_soon_sstc(r_time, r_temp, r_temp2, r_temp3, r_cause),
                                "#else",
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                f"csrs mie, x{r_temp}",
                                "# Set mtimer interrupt soon",
                                *set_mtimer_int_soon(
                                    r_time,
                                    r_timecmp,
                                    r_temp,
                                    r_temp2,
                                    r_temp3,
                                    r_cause,
                                    delay="(RVMODEL_TIMER_INT_SOON_DELAY * 8)",
                                ),
                                "#endif",
                                f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                f"csrs mie, x{r_temp}",
                                "# Set mtimer interrupt soon",
                                *set_mtimer_int_soon(r_time, r_timecmp, r_temp, r_temp2, r_temp3, r_cause),
                            ]
                        )

                    lines.extend(
                        [
                            f"# the test could hang if timer fires before x{r_cause} is initialized",
                            *_read_trap_count_helper(r_cause),
                            "# lr.w to set up reservation",
                            f"LA(x{r_temp}, scratch)",
                            f"lr.w x{r_temp2}, (x{r_temp})",
                            test_data.add_testcase(
                                f"tw_{tw_val}_mie_{mie_val}_sie_{sie_val}_{op}", coverpoint, covergroup
                            ),
                            "1:",
                            f"{op}",
                            *_read_trap_count_helper(r_temp),
                            f"bne x{r_cause}, x{r_temp}, 2f              # MIE=1: trap count increased -> done",
                        ]
                    )
                    # Since wrs instructions can terminate early, in order to test the resume behavior of wrs instructions,
                    # the test repeats the instruction until timer interrupt fires. For the case where interrupt is not expected
                    # to fire, the test repeats wrs instruction until interrupts becomes pending
                    # Two cases where the interrupt is not expected to fire are listed below:
                    ################## The test runs in M mode with mstatus.MIE = 0 ######################################
                    if (priv == "M") & (mie_val == 0):
                        lines.extend(
                            [
                                "# Only moves on if mstatus.MIE = 0 and mip.MTIP = 1, expect no interrupt should be taken",
                                f"csrr x{r_temp}, mip",
                                f"andi x{r_temp}, x{r_temp}, 0x80  # Extract mip.MTIP",
                                f"bnez x{r_temp}, 2f              # Interrupt pending -> done",
                            ]
                        )
                    ################## The test runs in S mode with mstatus.SIE = 0 ######################################
                    if (priv == "S") & (sie_val == 0):
                        lines.extend(
                            [
                                "#ifdef SSTC_SUPPORTED",
                                "# Only moves on if SIE = 0 and sip.STIP = 1, expect no interrupt should be taken",
                                f"csrr x{r_temp}, sip",
                                f"andi x{r_temp}, x{r_temp}, 0x20  # Extract mip.MTIP",
                                f"bnez x{r_temp}, 2f              # No interrupt pending -> retry",
                                "#endif",
                            ]
                        )
                    lines.extend(
                        [
                            "j 1b",
                            "2:",
                            write_sigupd(r_cause, test_data),
                        ]
                    )
                    if priv != "M":
                        lines.extend(
                            [
                                "RVTEST_GOTO_MMODE",
                            ]
                        )

    test_data.int_regs.return_registers([r_time, r_temp3, r_cause, r_temp, r_temp2, r_timecmp])
    return lines


def wrs_no_mie_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
) -> list[str]:
    """when mie = all 0s, pendng interrupt does not cause WRS to resume"""

    ######################################
    coverpoint = "cp_wrs_no_mie"
    ######################################

    r_time, r_cause, r_temp, r_temp2, r_timecmp = test_data.int_regs.get_registers(5)

    lines = []
    # wrs.nto can only be tested in non-M mode using TW = 1
    wrs_list = ["WRS.STO", "WRS.NTO"] if priv != "M" else ["WRS.STO"]

    for op in wrs_list:
        lines.extend(
            [
                "###### Setup (M Mode) ######",
                "# Disable all interrupts in mie",
                "csrw mie, zero",
                "# mstatus.MIE, SIE and MPIE = 1",
                f"LI(x{r_temp}, 0x8A)",
                f"csrs mstatus, x{r_temp}",
            ]
        )
        lines.extend(
            [
                "# Set all M mode interrupts pending",
                "RVTEST_SET_MEXT_INT",
                "RVTEST_SET_MSW_INT",
                *set_mtimer_int(r_time, r_timecmp, r_temp, r_temp2),
            ]
        )
        if priv != "M":
            lines.extend(
                [
                    "# Set the S mode interrupts if supported",
                    "#ifdef S_SUPPORTED",
                    *set_stimer_mmode(r_temp),
                    "# set SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    f"csrs mip, x{r_temp}",
                    "#endif",
                    "",
                    "# Set TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    f"csrs mstatus, x{r_temp}",
                    f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                ]
            )
        else:
            lines.extend(
                [
                    "# Clear TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    f"csrc mstatus, x{r_temp}",
                ]
            )
        lines.extend(
            [
                *_read_trap_count_helper(r_cause),
                "# lr.w to set up reservation",
                f"LA(x{r_temp}, scratch)",
                f"lr.w x{r_temp2}, (x{r_temp})",
                test_data.add_testcase(f"{op}", coverpoint, covergroup),
                "1:",
                f"{op}",
            ]
        )
        if op == "WRS.NTO":
            lines.extend(
                [
                    "#ifndef UDB_ZAWRS_NTO_IS_NOP",
                    "# trap count didn't change, no trap happened",
                    *_read_trap_count_helper(r_temp),
                    f"beq x{r_cause}, x{r_temp}, 1b",
                    "#endif",
                ]
            )
        lines.extend(
            [
                write_sigupd(r_cause, test_data),
                "#### Clean up ####",
            ]
        )
        if priv != "M":
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "# Clear S mode interrupts",
                    "#ifdef S_SUPPORTED",
                    *clr_stimer_int(r_temp, r_timecmp, r_temp2, r_cause),
                    "# clear SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    f"csrc mip, x{r_temp}",
                    "#endif",
                ]
            )
        lines.extend(
            [
                "# Clear M mode interrupts",
                "RVTEST_SET_MEXT_INT",
                "RVTEST_SET_MSW_INT",
                *clr_mtimer_int(r_temp, r_temp2),
            ]
        )
    test_data.int_regs.return_registers([r_time, r_cause, r_temp, r_temp2, r_timecmp])
    return lines


def wrs_no_res_helper(test_data: TestData, priv: str, covergroup: str) -> list[str]:
    """Helper function for generating WRS instruction no reservation tests"""

    r_scratch, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    ######################################
    coverpoint = "cp_wrs_no_res"
    ######################################
    lines = []

    tw_list = [0] if priv != "M" else [0, 1]

    for tw_val in tw_list:
        for wrs_op in ["WRS.STO", "WRS.NTO"]:
            lines.extend(
                [
                    "#### Setup (M mode) ####",
                    "# Disable all interrupts in mie",
                    "csrw mie, zero",
                    "# mstatus.MPIE, SIE and MIE = 0",
                    f"LI(x{r_temp}, 0x8A)",
                    f"csrc mstatus, x{r_temp}",
                    "# Write mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}",
                    "",
                ]
            )
            if priv != "M":
                lines.extend(
                    [
                        f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                    ]
                )

            lines.extend(
                [
                    "# sc.w to clear reservation",
                    f"LA(x{r_scratch}, scratch)",
                    f"sc.w x{r_temp}, x{r_temp2}, (x{r_scratch})",
                    test_data.add_testcase(
                        f"tw_{tw_val}_{'STO' if wrs_op == 'WRS.STO' else 'NTO'}",
                        coverpoint,
                        covergroup,
                    ),
                    f"{wrs_op}",
                    "",
                    "RVTEST_GOTO_MMODE",
                ]
            )

    test_data.int_regs.return_registers([r_scratch, r_temp, r_temp2])

    return lines


def wrs_timeout_helper(
    test_data: TestData,
    priv_list: list[str],
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    """WRS ops timeout behavior"""
    r_cause, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    lines = []
    op = "WRS.STO" if coverpoint == "cp_wrs_sto_timeout" else "WRS.NTO"

    tw_list = [1] if coverpoint == "cp_wrs_nto_timeout" else [0, 1]

    if coverpoint == "cp_wrs_nto_timeout_h":
        lines.append("#ifdef H_SUPPORTED")
    for priv in priv_list:
        for tw_val in tw_list:
            lines.extend(
                [
                    "###### Setup (M Mode) ######",
                    "# Disable all interrupts in mie",
                    "csrw mie, zero",
                    "# mstatus.MIE, SIE and MPIE = 0",
                    f"LI(x{r_temp}, 0x8A)",
                    f"csrc mstatus, x{r_temp}",
                    "# Write TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}",
                ]
            )
            if coverpoint == "cp_wrs_nto_timeout_h":
                lines.extend(
                    [
                        "# Set VTW",
                        f"LI(x{r_temp}, 0x200000)",
                        f"csrs hstatus, x{r_temp}",
                        "# No delegation in hedeleg",
                        "csrw hedeleg, zero",
                    ]
                )
            if priv != "M":
                lines.extend(
                    [
                        f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                    ]
                )
            lines.extend(
                [
                    *_read_trap_count_helper(r_cause),
                    "# lr.w to set up reservation",
                    f"LA(x{r_temp}, scratch)",
                    f"lr.w x{r_temp2}, (x{r_temp})",
                    test_data.add_testcase(f"tw_{tw_val}_{priv}_{op}", coverpoint, covergroup),
                    "1:",
                    f"{op}",
                ]
            )
            if op == "WRS.NTO":
                lines.extend(
                    [
                        "#ifndef UDB_ZAWRS_NTO_IS_NOP",
                        f"# check if x{r_cause} = 0, WRS.NTO terminated prematurely, repeat until timeout",
                        *_read_trap_count_helper(r_temp),
                        f"beq x{r_cause}, x{r_temp}, 1b",
                        "#endif",
                    ]
                )
            lines.extend(
                [
                    write_sigupd(r_cause, test_data),
                    "#### Clean up ####",
                ]
            )
            if priv != "M":
                lines.extend(
                    [
                        "RVTEST_GOTO_MMODE",
                    ]
                )

    if coverpoint == "cp_wrs_nto_timeout_h":
        lines.append("#endif // H_SUPPORTED")
    test_data.int_regs.return_registers([r_cause, r_temp, r_temp2])
    return lines
