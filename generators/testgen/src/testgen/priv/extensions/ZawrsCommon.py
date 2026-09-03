##################################
# priv/extensions/ZawrsCommon.py
#
# Shared Zawrs tests generation
# ellyu@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zawrs tests in all priv modes"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import (
    clr_mtimer_int,
    set_menvcfg_stce,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimecmp_max,
    set_stimer_int_soon_sstc,
    set_stimer_mmode,
)
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData


def m_csr(priv: str, instr: str) -> str:
    """M-mode CSR instruction; a T-SBI call when the test runs below M-mode."""
    return instr if priv == "M" else tsbi_call(instr)


def s_csr(priv: str, instr: str) -> str:
    """S-mode CSR instruction; a T-SBI call when the test runs in U-mode."""
    return instr if priv != "U" else tsbi_call(instr)


def _read_trap_count_helper(r_temp: int) -> list[str]:
    """Read trap count into r_temp"""
    return [f"# Read trap count into x{r_temp}", f"LA(x{r_temp}, rvtest_trap_count)", f"LREG x{r_temp}, 0(x{r_temp})"]


def _sstatus_sie(priv: str, r_temp: int, value: int) -> list[str]:
    """sstatus.SIE = value, for tests running below M-mode.

    SPIE is written along with SIE so the value survives the sret of the S-mode
    T-SBI handler when the test runs in U-mode.
    """
    lines = [
        f"# sstatus.SIE = {value}",
        f"LI(x{r_temp}, 0x22)",
        s_csr(priv, f"{'csrs' if value else 'csrc'} sstatus, x{r_temp}"),
    ]
    if priv == "U":
        return ["#ifdef S_SUPPORTED", *lines, "#endif"]
    return lines


def _disable_interrupts(priv: str, r_temp: int) -> list[str]:
    """mie = 0, mstatus.MIE = MPIE = 0, and SIE = 0 where it exists."""
    lines = [
        "# Disable all interrupts in mie",
        m_csr(priv, "csrw mie, zero"),
    ]
    if priv == "M":
        lines.extend(
            [
                "# mstatus.MPIE, SIE and MIE = 0",
                f"LI(x{r_temp}, 0x8A)",
                f"csrc mstatus, x{r_temp}",
            ]
        )
    else:
        lines.extend(
            [
                "# mstatus.MPIE and MIE = 0",
                f"LI(x{r_temp}, 0x88)",
                m_csr(priv, f"csrc mstatus, x{r_temp}"),
                *_sstatus_sie(priv, r_temp, 0),
            ]
        )
    return lines


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

    lower = priv != "M"
    description = [
        f"Generate {priv} mode WRS instruction resume when interrupt pending tests",
        "",
        *(
            ["For DUTs that support S mode but do not have Sstc, the WRS resume behavior is tested with MTIP", ""]
            if lower
            else []
        ),
        "cross lr instruction to set up reservation.",
        "mstatus.TW = 0" if lower else "mstatus.TW = {0/1}",
        "cross with mie.MTIE = 1" + (" (if Sstc supported use STIP, cross menvcfg.STCE = 1)" if lower else ""),
        "mstatus.MIE = {0/1}",
        *([f"mstatus.SIE = {{0/1}}{' (if S supported)' if priv == 'U' else ''}"] if lower else []),
        "Set up timer to interrupt soon",
        f"execute {{WRS.NTO/WRS.STO}} in {priv} mode",
        "2 x 2 x 2 bins",
    ]
    lines = [comment_banner(coverpoint, "\n".join(description))]
    if lower:
        sie_list = [0, 1]
        tw_list = [0]
    else:  # if test is for M mode
        sie_list = [0]  # SIE value does not matter for M mode, just set to 0
        tw_list = [0, 1]

    if lower:
        lines.extend(
            [
                "#ifdef SSTC_SUPPORTED",
                "# Enable Sstc (menvcfg.STCE) so stimecmp drives sip.STIP, then disarm the comparator",
                "# so whatever stimecmp held before does not raise STIP once STIE is set",
                *set_menvcfg_stce(r_temp, True, tsbi=True),
                *set_stimecmp_max(r_temp, tsbi=priv == "U"),
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
                            m_csr(priv, f"{'csrs' if mie_val else 'csrc'} mstatus, x{r_temp}"),
                            "# Write mstatus.TW",
                            f"LI(x{r_temp}, 0x200000)",
                            m_csr(priv, f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}"),
                            "",
                        ]
                    )

                    if lower:
                        lines.extend(
                            [
                                *_sstatus_sie(priv, r_temp, sie_val),
                                "#ifdef SSTC_SUPPORTED",
                                "# Set sie.STIE",
                                f"LI(x{r_temp}, 0x20)",
                                s_csr(priv, f"csrs sie, x{r_temp}"),
                                "# Set stimer interrupt soon; from U-mode the stimecmp write is a T-SBI call, so",
                                "# leave enough delay for that round trip on DUTs whose time ticks once per instruction",
                                *set_stimer_int_soon_sstc(
                                    r_time,
                                    r_temp,
                                    r_temp2,
                                    r_temp3,
                                    r_cause,
                                    delay="(RVMODEL_TIMER_INT_SOON_DELAY * 16)" if priv == "U" else None,
                                    tsbi=priv == "U",
                                ),
                                "#else",
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                m_csr(priv, f"csrs mie, x{r_temp}"),
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
                    ################## The test runs in S mode with sstatus.SIE = 0 ######################################
                    if (priv == "S") & (sie_val == 0):
                        lines.extend(
                            [
                                "#ifdef SSTC_SUPPORTED",
                                "# Only moves on if SIE = 0 and sip.STIP = 1, expect no interrupt should be taken",
                                f"csrr x{r_temp}, sip",
                                f"andi x{r_temp}, x{r_temp}, 0x20  # Extract sip.STIP",
                                f"bnez x{r_temp}, 2f              # Interrupt pending -> done",
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
                    # Disarm timers so no pending interrupt carries into the next testcase
                    lines.extend(clr_mtimer_int(r_temp, r_timecmp))
                    if lower:
                        lines.extend(
                            [
                                "#ifdef SSTC_SUPPORTED",
                                *set_stimecmp_max(r_temp, tsbi=priv == "U"),
                                "#endif",
                            ]
                        )

    test_data.int_regs.return_registers([r_time, r_temp3, r_cause, r_temp, r_temp2, r_timecmp])
    return lines


def wrs_no_mie_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
) -> list[str]:
    """when mie = all 0s, pending interrupt does not cause WRS to resume"""

    ######################################
    coverpoint = "cp_wrs_no_mie"
    ######################################

    r_time, r_cause, r_temp, r_temp2, r_timecmp = test_data.int_regs.get_registers(5)

    lower = priv != "M"
    description = [
        f"Generate {priv} mode wrs tests with mie = all 0s.",
        "",
        "cross lr instruction to set up reservation",
        "mstatus.MIE = 1",
        *([f"mstatus.SIE = 1{' (if S supported)' if priv == 'U' else ''}"] if lower else []),
        "mie = all 0s",
        "mstatus.TW = 1" if lower else "mstatus.TW = 0",
        "mip = {SSIP + SEIP + STIP + MSIP + MEIP + MTIP}" if lower else "mip = {MSIP + MEIP + MTIP}",
        f"execute {{WRS.NTO/WRS.STO}} in {priv} mode" if lower else "execute WRS.STO in M mode",
        "2 bins" if lower else "1 bin",
    ]
    lines = [comment_banner(coverpoint, "\n".join(description))]
    # wrs.nto can only be tested in non-M mode using TW = 1
    wrs_list = ["WRS.STO", "WRS.NTO"] if lower else ["WRS.STO"]

    for op in wrs_list:
        lines.extend(
            [
                "###### Setup ######",
                "# Disable all interrupts in mie",
                m_csr(priv, "csrw mie, zero"),
            ]
        )
        if lower:
            lines.extend(
                [
                    "# mstatus.MIE and MPIE = 1",
                    f"LI(x{r_temp}, 0x88)",
                    m_csr(priv, f"csrs mstatus, x{r_temp}"),
                    *_sstatus_sie(priv, r_temp, 1),
                ]
            )
        else:
            lines.extend(
                [
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
        if lower:
            lines.extend(
                [
                    "# Set the S mode interrupts if supported",
                    "#ifdef S_SUPPORTED",
                    *set_stimer_mmode(r_temp, tsbi=True),
                    "# set SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    m_csr(priv, f"csrs mip, x{r_temp}"),
                    "#endif",
                    "",
                    "# Set TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    m_csr(priv, f"csrs mstatus, x{r_temp}"),
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
        if lower:
            lines.extend(
                [
                    "# Clear S mode interrupts",
                    "#ifdef S_SUPPORTED",
                    "# clear SSI, STI and SEI through mip, the way they were set",
                    f"LI(x{r_temp}, 0x222)",
                    m_csr(priv, f"csrc mip, x{r_temp}"),
                    "#endif",
                ]
            )
        lines.extend(
            [
                "# Clear M mode interrupts",
                "RVTEST_CLR_MEXT_INT",
                "RVTEST_CLR_MSW_INT",
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
    lower = priv != "M"
    description = [
        f"Generate {priv} mode WRS instruction no reservation tests",
        "",
        "mstatus.TW = 0" if lower else "mstatus.TW = {0/1}",
        "mstatus.MIE = 0",
        *([f"mstatus.SIE = 0{' (if S supported)' if priv == 'U' else ''}"] if lower else []),
        "mie = all 0s to disable interrupts",
        f"Clear all reservation with sc.w, then execute {{WRS.STO, WRS.NTO}} with no reservation created in {priv} mode",
        "2 bins" if lower else "2 x 2 bins",
    ]
    lines = [comment_banner(coverpoint, "\n".join(description))]

    tw_list = [0] if lower else [0, 1]

    for tw_val in tw_list:
        for wrs_op in ["WRS.STO", "WRS.NTO"]:
            lines.extend(
                [
                    "#### Setup ####",
                    *_disable_interrupts(priv, r_temp),
                    "# Write mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    m_csr(priv, f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}"),
                    "",
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
                ]
            )

    test_data.int_regs.return_registers([r_scratch, r_temp, r_temp2])

    return lines


def wrs_timeout_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
    timeout: str,
    virtualized: bool = False,
) -> list[str]:
    """WRS timeout behavior with interrupts disabled.

    Args:
        timeout: "short" tests WRS.STO, which times out on its own;
                 "no" tests WRS.NTO, which only ends through the mstatus.TW illegal-instruction trap
        virtualized: run the WRS.NTO test in VS and VU mode from an S-mode test, with hstatus.VTW = 1
    """
    if timeout not in ("short", "no"):
        raise ValueError(f"timeout must be 'short' or 'no', got {timeout!r}")
    if virtualized and (timeout != "no" or priv != "S"):
        raise ValueError("virtualized timeout tests are WRS.NTO tests generated from the S-mode suite")

    r_cause, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    op = "WRS.STO" if timeout == "short" else "WRS.NTO"

    sie0 = f"mstatus.SIE = 0{' (if S supported)' if priv == 'U' else ''}"
    if virtualized:
        coverpoint = "cp_wrs_nto_timeout_h"
        description = [
            "Generate WRS.NTO timeout test in VS/VU mode",
            "",
            "cross lr instruction to set up reservation.",
            "mstatus.TW = {0/1}",
            "mstatus.MIE = 0",
            "mstatus.SIE = 0",
            "hstatus.VTW = 1",
            "hedeleg = all 0s",
            "mie = all 0s to disable interrupts",
            "execute WRS.NTO in VS/VU mode",
            "2 x 2 bins",
        ]
        tw_list = [0, 1]
        mode_list = ["VS", "VU"]
    elif op == "WRS.STO":
        coverpoint = "cp_wrs_sto_timeout"
        description = [
            f"Generate {priv} mode wrs.sto timeout tests.",
            "",
            "cross lr instruction to set up reservation.",
            "mstatus.TW = {0/1}",
            "mstatus.MIE = 0",
            *([sie0] if priv != "M" else []),
            "mie = all 0s to disable interrupts",
            f"Execute WRS.STO in {priv} mode",
            "2 bins",
        ]
        tw_list = [0, 1]
        mode_list = [priv]
    else:
        coverpoint = "cp_wrs_nto_timeout"
        description = [
            f"Generate {priv} mode WRS.NTO timeout test",
            "",
            "cross lr instruction to set up reservation.",
            "mstatus.TW = 1",
            "mstatus.MIE = 0",
            sie0,
            "mie = all 0s to disable interrupts",
            f"execute WRS.NTO in {priv} mode",
            "1 bin",
        ]
        tw_list = [1]
        mode_list = [priv]
    lines = [comment_banner(coverpoint, "\n".join(description))]

    if virtualized:
        lines.append("#ifdef H_SUPPORTED")
    for mode in mode_list:
        for tw_val in tw_list:
            lines.extend(
                [
                    "###### Setup ######",
                    *_disable_interrupts(priv, r_temp),
                    "# Write mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    m_csr(priv, f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}"),
                ]
            )
            if virtualized:
                lines.extend(
                    [
                        "# Set VTW",
                        f"LI(x{r_temp}, 0x200000)",
                        f"csrs hstatus, x{r_temp}",
                        "# No delegation in hedeleg",
                        "csrw hedeleg, zero",
                    ]
                )
            if mode != priv:
                lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
            lines.extend(
                [
                    *_read_trap_count_helper(r_cause),
                    "# lr.w to set up reservation",
                    f"LA(x{r_temp}, scratch)",
                    f"lr.w x{r_temp2}, (x{r_temp})",
                    test_data.add_testcase(f"tw_{tw_val}_{mode}_{op}", coverpoint, covergroup),
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
            if mode != priv:
                lines.append(f"RVTEST_TSBI_GOTO_{priv}MODE")

    if virtualized:
        lines.append("#endif // H_SUPPORTED")
    test_data.int_regs.return_registers([r_cause, r_temp, r_temp2])
    return lines
