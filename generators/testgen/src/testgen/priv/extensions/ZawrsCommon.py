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


def _zawrs_trap_handler(
    r_cause: int, r_scratch: int, is_int: bool, r_temp: int = 0, r_timecmp: int = 0, r_temp2: int = 0
) -> list[str]:
    """Custom trap handler for Zawrs test"""
    lines = []
    lines.extend(
        [
            "# ---- M-mode WRS resume handler (U-mode tests) ----",
            "j 4f                             # skip handler in straight-line code",
            ".option push",
            ".option norvc",
            ".balign 4                         # direct-mode mtvec target must be 4-byte aligned",
        ]
    )
    if is_int:
        lines.append("xt_int_handler:")
    else:
        lines.append("xt_trap_handler:")
        lines.extend(
            [
                "# increment xepc by 4 so it does not land on the same instruction",
                f"CSRR(x{r_temp}, xepc)",
                f"addi x{r_temp}, x{r_temp}, 0x4",
                f"CSRW(xepc, x{r_temp})",
            ]
        )
    lines.extend(
        [
            "# Record xcause, restore xtvec",
            f"csrr x{r_cause}, xcause",
            f"csrw xtvec, x{r_scratch}",
        ]
    )
    if is_int:
        lines.extend(
            [
                "#if defined(S_SUPPORTED) && defined(SSTC_SUPPORTED)",
                f"LI(x{r_scratch}, 1)",
                *clr_stimer_int(r_temp, r_timecmp, r_temp2, r_scratch),
                "#else",
                *clr_mtimer_int(r_temp, r_temp2),
                "#endif",
            ]
        )
    lines.extend(
        [
            "xret",
            ".option pop",
            "4:",
        ]
    )
    return lines


def _zawrs_define_helper(priv: str) -> list[str]:
    """Define the CSRs based on priv mode"""
    lines = []
    if priv != "M":
        lines.extend(
            [
                "#if defined(S_SUPPORTED) && defined(SSTC_SUPPORTED)",
                "#define xt_int_handler st_int_handler",  # test using STIP
                "#define xcause scause",
                "#define xtvec stvec",
                "#define xret sret",
                "#define xt_trap_handler st_trap_handler",
                "#define xepc sepc",
                "#else",
                "#define xt_int_handler mt_int_handler",
                "#define xcause mcause",
                "#define xtvec mtvec",
                "#define xret mret",
                "#define xt_trap_handler mt_trap_handler",
                "#define xepc mepc",
                "#endif",
            ]
        )
    else:  # if test is for M mode
        lines.extend(
            [
                "#define xt_int_handler mt_int_handler",
                "#define xcause mcause",
                "#define xtvec mtvec",
                "#define xret mret",
                "#define xt_trap_handler mt_trap_handler",
                "#define xepc mepc",
            ]
        )
    return lines


def _wrs_resume_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
    r_cause: int,
    r_scratch: int,
    r_temp: int,
    r_timecmp: int,
    r_temp2: int,
) -> list[str]:
    """wrs resume when interrupt"""
    # TODO: FIX THIS PART LATER

    ######################################
    coverpoint = "cp_wrs_resume"
    ######################################

    r_time, r_temp3 = test_data.int_regs.get_registers(2)

    lines = []
    if priv != "M":
        sie_list = [0, 1]
        tw_list = [0]
    else:  # if test is for M mode
        sie_list = [0]  # to ensure that the python for loop does not repeat for sie values
        tw_list = [0, 1]

    for op in ["WRS.NTO", "WRS.STO"]:
        for tw_val in tw_list:
            for sie_val in sie_list:
                for mie_val in [0, 1]:
                    lines.extend(
                        [
                            "#### Setup ####",
                            f"# mstatus.MPIE and mstatus.MIE = {mie_val}",
                            f"LI(x{r_temp}, 0x88)",
                            f"{'CSRS' if mie_val else 'CSRC'}(mstatus, x{r_temp})",
                            "# Write mstatus.TW",
                            f"LI(x{r_temp}, 0x200000)",
                            f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
                            "",
                            f"# Install local trap handler in xtvec (direct mode); save old xtvec in x{r_scratch}",
                            f"LA(x{r_temp}, xt_int_handler)",
                            f"csrrw x{r_scratch}, xtvec, x{r_temp}",
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
                                "#if defined(S_SUPPORTED) && defined(SSTC_SUPPORTED)",
                                "# Enable Sstc (menvcfg.STCE) so stimecmp drives sip.STIP",
                                *set_menvcfg_stce(r_temp, True),
                                "# Delegate supervisor timer interrupt (STI) to S-mode",
                                f"LI(x{r_temp}, 0x20)",
                                f"CSRS(mideleg, x{r_temp})",
                                "# Set sie.STIE",
                                f"LI(x{r_temp}, 0x20)",
                                f"CSRS(sie, x{r_temp})",
                                "# Set stimer interrupt soon",
                                *set_stimer_int_soon_sstc(r_time, r_temp, r_temp2, r_temp3, r_cause),
                                "#else",
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                f"CSRS(mie, x{r_temp})",
                                "# Set mtimer interrupt soon",
                                *set_mtimer_int_soon(r_time, r_timecmp, r_temp, r_temp2, r_temp3, r_cause),
                                "#endif",
                                f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                f"CSRS(mie, x{r_temp})",
                                "# Set mtimer interrupt soon",
                                *set_mtimer_int_soon(r_time, r_timecmp, r_temp, r_temp2, r_temp3, r_cause),
                            ]
                        )

                    lines.extend(
                        [
                            "",
                            f"LI(x{r_cause}, 0)                 # nonzero means the trap was taken",
                            "# lr.w to set up reservation",
                            f"LA(x{r_temp}, scratch)",
                            f"lr.w x{r_temp2}, (x{r_temp})",
                            test_data.add_testcase(
                                f"tw_{tw_val}_mie_{mie_val}_sie_{sie_val}_{op}", coverpoint, covergroup
                            ),
                            "1:",
                            f"{op}",
                            f"bnez x{r_cause}, 2f              # MIE=1: handler recorded mcause -> done",
                        ]
                    )
                    if (priv == "M") & (mie_val == 0):
                        lines.extend(
                            [
                                "# Only moves on if MIE = 0 and mip.MTIP = 1, expect no interrupt should be taken",
                                f"csrr x{r_temp}, mip",
                                f"andi x{r_temp}, x{r_temp}, 0x80  # Extract mip.MTIP",
                                f"bnez x{r_temp}, 2f              # Interrupt pending -> done",
                            ]
                        )
                    if (priv == "S") & (sie_val == 0):
                        lines.extend(
                            [
                                "#if defined(S_SUPPORTED) && defined(SSTC_SUPPORTED)",
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
                    # restore xtvec if interrupt was not taken
                    if (priv == "M") & (mie_val == 0):
                        lines.append(f"csrw mtvec, x{r_scratch}")
                    if (priv == "S") & (sie_val == 0):
                        lines.extend(
                            [
                                "#if defined(S_SUPPORTED) && defined(SSTC_SUPPORTED)",
                                f"csrw stvec, x{r_scratch}",
                                "#endif",
                            ]
                        )

                    if priv != "M":
                        lines.extend(
                            [
                                "RVTEST_GOTO_MMODE",
                            ]
                        )

    test_data.int_regs.return_registers([r_time, r_temp3])
    return lines


def _wrs_no_mie_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
    r_cause: int,
    r_scratch: int,
    r_temp: int,
    r_timecmp: int,
    r_temp2: int,
) -> list[str]:
    """when mie = all 0s, pendng interrupt does not cause WRS to resume"""

    ######################################
    coverpoint = "cp_wrs_no_mie"
    ######################################

    r_time, r_temp3 = test_data.int_regs.get_registers(2)

    lines = []
    # wrs.nto can only be tested in non-M mode using TW = 1
    wrs_list = ["WRS.STO", "WRS.NTO"] if priv != "M" else ["WRS.STO"]

    for op in wrs_list:
        lines.extend(
            [
                "###### Setup (M Mode) ######",
                "# Disable all interrupts in mie",
                "CSRW mie, zero",
                "# mstatus.MIE = 1 and MPIE = 1",
                f"LI(x{r_temp}, 0x88)",
                f"CSRS(mstatus, x{r_temp})",
            ]
        )
        if op == "WRS.NTO":
            lines.extend(
                [
                    # "#ifndef UDB_ZAWRS_NTO_IS_NOP",
                    f"# Install local trap handler in xtvec (direct mode); save old xtvec in x{r_scratch}",
                    f"LA(x{r_temp}, xt_trap_handler)",
                    f"csrrw x{r_scratch}, xtvec, x{r_temp}",
                    # "#endif",
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
                    f"CSRS(mip, x{r_temp})",
                    "# Set mstatus.SIE",
                    "csrsi mstatus, 0x2",
                    "#endif",
                    "",
                    "# Set TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    f"CSRS(mstatus, x{r_temp})",
                    f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                ]
            )
        else:
            lines.extend(
                [
                    "# Clear TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    f"CSRC(mstatus, x{r_temp})",
                ]
            )
        lines.extend(
            [
                "# Initialize r_cause to zero (nonzero indicate trap happened)",
                f"LI(x{r_cause}, 0)",
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
                    # This part commented out because the parameter is not defined yet
                    # "#ifndef UDB_ZAWRS_NTO_IS_NOP",
                    "# r_cause is 0, no trap happened",
                    f"beqz x{r_cause}, 1b",
                    # "#endif",
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
                    *clr_stimer_int(r_temp, r_timecmp, r_temp2, r_scratch),
                    "# clear SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    f"CSRC(mip, x{r_temp})",
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
    test_data.int_regs.return_registers([r_time, r_temp3])
    return lines


def _wrs_no_res_helper(test_data: TestData, priv: str, covergroup: str) -> list[str]:
    """Helper function for generating WRS instruction no reservation tests"""

    r_scratch, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    ######################################
    coverpoint = "cp_wrs_no_res"
    ######################################
    lines = []

    tw_list = [0] if priv != "M" else [0, 1]

    for tw_val in tw_list:
        for wrs_ops in ["WRS.STO", "WRS.NTO"]:
            lines.extend(
                [
                    "#### Setup (M mode) ####",
                    "# Disable all interrupts in mie",
                    "CSRW mie, zero",
                    "# mstatus.MPIE = 0",
                    f"LI(x{r_temp}, 0x80)",
                    f"CSRC(mstatus, x{r_temp})",
                    "# Write mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
                    "",
                ]
            )
            if priv != "M":
                lines.extend(
                    [
                        "# clear SIE",
                        "#ifdef S_SUPPORTED",
                        "csrci mstatus, 2",
                        "#endif",
                        f"# Go down to {priv} mode to execute the instruction",
                        f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                    ]
                )

            lines.extend(
                [
                    "# sc.w to clear reservation",
                    f"LA(x{r_scratch}, scratch)",
                    f"sc.w x{r_temp}, x{r_temp2}, (x{r_scratch})",
                    test_data.add_testcase(
                        f"tw_{tw_val}_{'STO' if wrs_ops == 'WRS.STO' else 'NTO'}",
                        coverpoint,
                        covergroup,
                    ),
                    f"{wrs_ops}",
                    "",
                    "RVTEST_GOTO_MMODE",
                ]
            )

    test_data.int_regs.return_registers([r_scratch, r_temp, r_temp2])

    return lines


def _wrs_timeout_helper(
    test_data: TestData,
    priv_list: list[str],
    coverpoint: str,
    covergroup: str,
    r_cause: int,
    r_scratch: int,
    r_temp: int,
    r_temp2: int,
) -> list[str]:
    """WRS ops timeout behavior"""
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
                    "CSRW mie, zero",
                    "# mstatus.MIE = 0 and MPIE = 0",
                    f"LI(x{r_temp}, 0x88)",
                    f"CSRC(mstatus, x{r_temp})",
                    "# Write TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
                ]
            )
            if priv != "M":
                lines.extend(
                    [
                        "#ifdef S_SUPPORTED",
                        "# Clear mstatus.SIE",
                        "csrci mstatus, 0x2",
                        "#endif",
                    ]
                )
            if coverpoint == "cp_wrs_nto_timeout_h":
                lines.extend(
                    [
                        "# Set VTM",
                        f"LI(x{r_temp}, 0x100000)",
                        f"CSRS(mstatus, x{r_temp})",
                        "# No delegation in hedeleg",
                        "CSRW hedeleg, zero",
                    ]
                )
            if op == "WRS.NTO":  # These are the cases that are expected to trap
                lines.extend(
                    [
                        "# Set up trap handler - will trap to either S or M mode based on what is supported",
                        f"# Install local trap handler in xtvec (direct mode); save old xtvec in x{r_scratch}",
                        f"LA(x{r_temp}, xt_trap_handler)",
                        f"csrrw x{r_scratch}, xtvec, x{r_temp}",
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
                    "# Initialize r_cause to zero (nonzero indicate trap happened)",
                    f"LI(x{r_cause}, 0)",
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
                        # This part commented out because the parameter is not defined yet
                        # "#ifndef UDB_ZAWRS_NTO_IS_NOP",
                        "# r_cause is 0, no trap happened",
                        f"beqz x{r_cause}, 1b",
                        # "#endif",
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
        lines.append("#endif")

    return lines
