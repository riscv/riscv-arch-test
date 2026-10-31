##################################
# priv/extensions/Zawrs.py
#
# Zawrs privileged extension test generators for the Sm, S, U and H groups.
# ellyu@hmc.edu July 2026
# The H group's TW/VTW, hedeleg and VSSIP cases come from riscv-arch-test PR 2915 by Wei Shen.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zawrs test generators. Each group runs in one privilege mode; the H group runs in VS-mode and VU-mode."""

from testgen.asm.csr import write_stce
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import write_vtw
from testgen.priv.registry import add_priv_test_generator


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
        tsbi_call_or_direct(f"{'csrs' if value else 'csrc'} sstatus, x{r_temp}", priv),
    ]
    if priv == "U":
        return ["#ifdef S_SUPPORTED", *lines, "#endif"]
    return lines


def _disable_interrupts(priv: str, r_temp: int) -> list[str]:
    """mie = 0, mstatus.MIE = MPIE = 0, and SPIE/SIE = 0 where it exists."""
    lines = [
        "# Disable all interrupts in mie",
        tsbi_call_or_direct("csrw mie, zero", priv),
        "# mstatus.MPIE, SPIE, MIE, AND SIE = 0",
        f"LI(x{r_temp}, 0xAA)",
        tsbi_call_or_direct(f"csrc mstatus, x{r_temp}", priv),
    ]
    return lines


def wrs_resume_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
    mode: str | None = None,
) -> list[str]:
    """wrs resume when interrupt

    mode: VS or VU to run the WRS in that mode, entered from priv (HS-mode). There the supervisor or machine
    timer interrupt is taken whatever mstatus.MIE and SIE are, so the WRS always ends with a trap.
    """

    mode = mode or priv
    virtual = mode != priv
    ######################################
    coverpoint = "cp_wrs_resume_h" if virtual else "cp_wrs_resume"
    ######################################

    r_cause, r_temp, r_temp2 = test_data.int_regs.get_registers(3)

    lower = priv != "M"
    # The resume is triggered by a timer interrupt: Sstc below M-mode when it is implemented, otherwise a machine
    # timer interrupt
    guard = "#if defined(SSTC_SUPPORTED) || defined(UDB_MTI_INTR_IMPL)" if lower else "#ifdef UDB_MTI_INTR_IMPL"
    lines = [
        comment_banner(coverpoint, f"Generate {mode} mode WRS instruction resume when interrupt pending tests"),
        guard,
    ]
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
                *write_stce(test_data, True, priv),
                f"RVTEST_CLR_SSTC_INT_{priv}",
                "#endif",
            ]
        )
    # VS-mode and VU-mode arm the timer after entering the mode, through T-SBI
    arm = "U" if virtual else priv
    arm_timer = [
        "#ifdef SSTC_SUPPORTED",
        "# Set stimer interrupt soon",
        f"RVTEST_SET_SSTC_INT_SOON_{arm}",
        "#else",
        "# Set mtimer interrupt soon",
        f"RVTEST_SET_MTIME_INT_SOON_{arm}",
        "#endif",
    ]
    prefix = f"{mode}_" if virtual else ""
    for op in ["WRS.NTO", "WRS.STO"]:
        for tw_val in tw_list:
            for sie_val in sie_list:
                for mie_val in [0, 1]:
                    lines.extend(
                        [
                            "#### Setup ####",
                            f"# mstatus.MPIE and mstatus.MIE = {mie_val}",
                            f"LI(x{r_temp}, 0x88)",
                            tsbi_call_or_direct(f"{'csrs' if mie_val else 'csrc'} mstatus, x{r_temp}", priv),
                            "# Write mstatus.TW",
                            f"LI(x{r_temp}, 0x200000)",
                            tsbi_call_or_direct(f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}", priv),
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
                                tsbi_call_or_direct(f"csrs sie, x{r_temp}", priv),
                                "#else",
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                tsbi_call_or_direct(f"csrs mie, x{r_temp}", priv),
                                "#endif",
                                *([*write_vtw(r_temp, False, priv), f"RVTEST_TSBI_GOTO_{mode}MODE"] if virtual else []),
                                *arm_timer,
                                "# Read the trap count after the T-SBI calls above, which trap as well",
                                *_read_trap_count_helper(r_cause),
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                "# Read the trap count before arming the timer, so an early interrupt is counted",
                                *_read_trap_count_helper(r_cause),
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                f"csrs mie, x{r_temp}",
                                "# Set mtimer interrupt soon",
                                "RVTEST_SET_MTIME_INT_SOON_M",
                            ]
                        )

                    lines.extend(
                        [
                            "# lr.w to set up reservation",
                            f"LA(x{r_temp}, scratch)",
                            f"lr.w x{r_temp2}, (x{r_temp})",
                            test_data.add_testcase(
                                f"{prefix}tw_{tw_val}_mie_{mie_val}_sie_{sie_val}_{op}", coverpoint, covergroup
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
                    if (mode == "S") & (sie_val == 0):
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
                    if virtual:
                        lines.append(f"RVTEST_TSBI_GOTO_{priv}MODE")
                    # Disarm timers so no pending interrupt carries into the next testcase
                    lines.append(f"RVTEST_CLR_MTIME_INT_{priv}")
                    if lower:
                        lines.extend(
                            [
                                "#ifdef SSTC_SUPPORTED",
                                f"RVTEST_CLR_SSTC_INT_{priv}",
                                "#endif",
                            ]
                        )

    if lower:
        lines.extend(
            [
                "#ifdef SSTC_SUPPORTED",
                "# Restore the boot value of menvcfg.STCE so mip.STIP is writable again",
                *write_stce(test_data, False, priv),
                "#endif",
            ]
        )
    lines.append("#endif")

    test_data.int_regs.return_registers([r_cause, r_temp, r_temp2])
    return lines


def wrs_interrupt_helper(test_data: TestData, covergroup: str) -> list[str]:
    """A pending VS-level interrupt that vsie enables ends a VS-mode WRS even though vsstatus.SIE = 0."""

    ######################################
    coverpoint = "cp_wrs_interrupt_h"
    ######################################

    r_count, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    description = [
        "Generate VS mode WRS tests with a pending, locally enabled, globally disabled interrupt.",
        "",
        "mstatus.TW = 0, hstatus.VTW = 0",
        "hideleg.VSSIP = 1, hie.VSSIE (vsie.SSIE) = 1, hvip.VSSIP = 1",
        "vsstatus.SIE = 0",
        "cross lr instruction to set up reservation",
        "execute {WRS.NTO/WRS.STO} in VS mode: it completes without taking the interrupt, and vsip.SSIP stays set",
        "2 bins",
    ]
    lines = [comment_banner(coverpoint, "\n".join(description))]
    for op in ["WRS.NTO", "WRS.STO"]:
        lines.extend(
            [
                "###### Setup ######",
                *_disable_interrupts("S", r_temp),
                "# mstatus.TW = 0",
                f"LI(x{r_temp}, 0x200000)",
                tsbi_call_or_direct(f"csrc mstatus, x{r_temp}", "S"),
                *write_vtw(r_temp, False, "S"),
                "# vsstatus.SIE = 0",
                f"LI(x{r_temp}, 0x2)",
                f"csrc vsstatus, x{r_temp}",
                "# Delegate VSSIP to VS-mode, enable it in hie (vsie.SSIE in VS-mode), then raise it through hvip",
                f"LI(x{r_temp}, 0x4)",
                f"csrs hideleg, x{r_temp}",
                f"csrs hie, x{r_temp}",
                "RVTEST_SET_VSSW_INT_S",
                "RVTEST_TSBI_GOTO_VSMODE",
                *_read_trap_count_helper(r_count),
                "# lr.w to set up reservation",
                f"LA(x{r_temp}, scratch)",
                f"lr.w x{r_temp2}, (x{r_temp})",
                test_data.add_testcase(f"VS_{op}", coverpoint, covergroup),
                f"{op}",
                *_read_trap_count_helper(r_temp),
                "# Number of traps since the WRS: 0, the interrupt was not taken",
                f"sub x{r_temp}, x{r_temp}, x{r_count}",
                write_sigupd(r_temp, test_data),
                "# vsip.SSIP (sip in VS-mode) is still pending",
                f"csrr x{r_temp}, sip",
                f"andi x{r_temp}, x{r_temp}, 0x2",
                write_sigupd(r_temp, test_data),
                "RVTEST_TSBI_GOTO_SMODE",
                "#### Clean up ####",
                "RVTEST_CLR_VSSW_INT_S",
                f"LI(x{r_temp}, 0x4)",
                f"csrc hie, x{r_temp}",
                f"csrc hideleg, x{r_temp}",
            ]
        )
    test_data.int_regs.return_registers([r_count, r_temp, r_temp2])
    return lines


def wrs_no_mie_helper(
    test_data: TestData,
    priv: str,
    covergroup: str,
    mode: str | None = None,
) -> list[str]:
    """when mie = all 0s, pending interrupt does not cause WRS to resume

    mode: VS or VU to run the WRS in that mode, entered from priv (HS-mode), with the VS-level interrupts
    pending as well.
    """

    mode = mode or priv
    virtual = mode != priv
    ######################################
    coverpoint = "cp_wrs_no_mie_h" if virtual else "cp_wrs_no_mie"
    ######################################

    r_cause, r_temp, r_temp2 = test_data.int_regs.get_registers(3)

    lower = priv != "M"
    description = [
        f"Generate {mode} mode wrs tests with mie = all 0s.",
        "",
        "cross lr instruction to set up reservation",
        "mstatus.MIE = 1",
        *([f"mstatus.SIE = 1{' (if S supported)' if priv == 'U' else ''}"] if lower else []),
        "mie = all 0s",
        "mstatus.TW = 1" if lower else "mstatus.TW = 0",
        *(["hstatus.VTW = 0"] if virtual else []),
        "mip = {SSIP + SEIP + STIP + MSIP + MEIP + MTIP}" if lower else "mip = {MSIP + MEIP + MTIP}",
        *(["hvip = {VSSIP + VSTIP + VSEIP}"] if virtual else []),
        f"execute {{WRS.NTO/WRS.STO}} in {mode} mode" if lower else "execute WRS.STO in M mode",
        "2 bins" if lower else "1 bin",
    ]
    # Needs an interrupt that can be made pending, S-mode interrupts can be set through mip.
    # The VS-level interrupts are always there to raise through hvip.
    guard = "#if defined(UDB_MEI_INTR_IMPL) || defined(UDB_MSI_INTR_IMPL) || defined(UDB_MTI_INTR_IMPL)"
    if lower:
        guard += " || defined(S_SUPPORTED)"
    lines = [comment_banner(coverpoint, "\n".join(description)), *([] if virtual else [guard])]
    # wrs.nto can only be tested in non-M mode using TW = 1
    wrs_list = ["WRS.STO", "WRS.NTO"] if lower else ["WRS.STO"]

    for op in wrs_list:
        lines.extend(
            [
                "###### Setup ######",
                "# Disable all interrupts in mie",
                tsbi_call_or_direct("csrw mie, zero", priv),
                "# mstatus.MIE, SIE, MPIE, and SPIE = 1",
                f"LI(x{r_temp}, 0xAA)",
                tsbi_call_or_direct(f"csrs mstatus, x{r_temp}", priv),
                "# Set all M mode interrupts pending",
                "#ifdef UDB_MEI_INTR_IMPL",
                f"RVTEST_SET_MEXT_INT_{priv}",
                "#endif",
                "#ifdef UDB_MSI_INTR_IMPL",
                f"RVTEST_SET_MSW_INT_{priv}",
                "#endif",
                "#ifdef UDB_MTI_INTR_IMPL",
                f"RVTEST_SET_MTIME_INT_{priv}",
                "#endif",
            ]
        )
        if lower:
            lines.extend(
                [
                    "# Set the S mode interrupts if supported",
                    "#ifdef S_SUPPORTED",
                    f"RVTEST_SET_STIME_INT_{priv}",
                    "# set SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    tsbi_call_or_direct(f"csrs mip, x{r_temp}", priv),
                    "#endif",
                    "",
                    "# Set TW bit",
                    f"LI(x{r_temp}, 0x200000)",
                    tsbi_call_or_direct(f"csrs mstatus, x{r_temp}", priv),
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
        if virtual:
            lines.extend(
                [
                    "# Set the VS-level interrupts pending",
                    "RVTEST_SET_VSSW_INT_S",
                    "RVTEST_SET_VSTIME_INT_S",
                    "RVTEST_SET_VSEXT_INT_S",
                    *write_vtw(r_temp, False, priv),
                    f"RVTEST_TSBI_GOTO_{mode}MODE",
                ]
            )
        lines.extend(
            [
                *_read_trap_count_helper(r_cause),
                "# lr.w to set up reservation",
                f"LA(x{r_temp}, scratch)",
                f"lr.w x{r_temp2}, (x{r_temp})",
                test_data.add_testcase(f"{mode}_{op}" if virtual else f"{op}", coverpoint, covergroup),
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
                *([f"RVTEST_TSBI_GOTO_{priv}MODE"] if virtual else []),
                "#### Clean up ####",
            ]
        )
        if virtual:
            lines.extend(
                [
                    "# Clear the VS-level interrupts",
                    "RVTEST_CLR_VSSW_INT_S",
                    "RVTEST_CLR_VSTIME_INT_S",
                    "RVTEST_CLR_VSEXT_INT_S",
                ]
            )
        if lower:
            lines.extend(
                [
                    "# Clear S mode interrupts",
                    "#ifdef S_SUPPORTED",
                    "# clear SSI, STI and SEI through mip, the way they were set",
                    f"LI(x{r_temp}, 0x222)",
                    tsbi_call_or_direct(f"csrc mip, x{r_temp}", priv),
                    "#endif",
                ]
            )
        lines.extend(
            [
                "# Clear M mode interrupts",
                "#ifdef UDB_MEI_INTR_IMPL",
                f"RVTEST_CLR_MEXT_INT_{priv}",
                "#endif",
                "#ifdef UDB_MSI_INTR_IMPL",
                f"RVTEST_CLR_MSW_INT_{priv}",
                "#endif",
                "#ifdef UDB_MTI_INTR_IMPL",
                f"RVTEST_CLR_MTIME_INT_{priv}",
                "#endif",
            ]
        )
    if not virtual:
        lines.append("#endif")
    test_data.int_regs.return_registers([r_cause, r_temp, r_temp2])
    return lines


def wrs_no_res_helper(test_data: TestData, priv: str, covergroup: str, mode: str | None = None) -> list[str]:
    """Helper function for generating WRS instruction no reservation tests

    mode: VS or VU to run the WRS in that mode, entered from priv (HS-mode), with hstatus.VTW = 0.
    """

    mode = mode or priv
    virtual = mode != priv
    r_scratch, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    ######################################
    coverpoint = "cp_wrs_no_res_h" if virtual else "cp_wrs_no_res"
    ######################################
    lower = priv != "M"
    description = [
        f"Generate {mode} mode WRS instruction no reservation tests",
        "",
        "mstatus.TW = 0" if lower else "mstatus.TW = {0/1}",
        *(["hstatus.VTW = 0"] if virtual else []),
        "mstatus.MIE = 0",
        *([f"mstatus.SIE = 0{' (if S supported)' if priv == 'U' else ''}"] if lower else []),
        "mie = all 0s to disable interrupts",
        f"Clear all reservation with sc.w, then execute {{WRS.STO, WRS.NTO}} with no reservation created in {mode} mode",
        "2 bins" if lower else "2 x 2 bins",
    ]
    lines = [comment_banner(coverpoint, "\n".join(description))]

    tw_list = [0] if lower else [0, 1]
    prefix = f"{mode}_" if virtual else ""

    for tw_val in tw_list:
        for wrs_op in ["WRS.STO", "WRS.NTO"]:
            lines.extend(
                [
                    "#### Setup ####",
                    *_disable_interrupts(priv, r_temp),
                    "# Write mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    tsbi_call_or_direct(f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}", priv),
                    *([*write_vtw(r_temp, False, priv), f"RVTEST_TSBI_GOTO_{mode}MODE"] if virtual else []),
                    "",
                    "# sc.w to clear reservation",
                    f"LA(x{r_scratch}, scratch)",
                    f"sc.w x{r_temp}, x{r_temp2}, (x{r_scratch})",
                    test_data.add_testcase(
                        f"{prefix}tw_{tw_val}_{'STO' if wrs_op == 'WRS.STO' else 'NTO'}",
                        coverpoint,
                        covergroup,
                    ),
                    f"{wrs_op}",
                    *([f"RVTEST_TSBI_GOTO_{priv}MODE"] if virtual else []),
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
    mode: str | None = None,
) -> list[str]:
    """WRS timeout behavior with interrupts disabled.

    Args:
        timeout: "short" tests WRS.STO, which times out on its own;
                 "no" tests WRS.NTO, which only ends through the mstatus.TW illegal-instruction trap
                 (or, in VS-mode and VU-mode, the hstatus.VTW virtual-instruction trap)
        mode: VS or VU to run the WRS in that mode, entered from priv (HS-mode).  WRS.STO is then crossed with
              mstatus.TW and hstatus.VTW.  WRS.NTO raises illegal instruction with TW = 1 whatever VTW is, taken in
              HS-mode or, with hedeleg[2] = 1, in VS-mode; with TW = 0 and VTW = 1 it raises virtual instruction.
    """
    if timeout not in ("short", "no"):
        raise ValueError(f"timeout must be 'short' or 'no', got {timeout!r}")
    mode = mode or priv
    virtual = mode != priv

    r_cause, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    op = "WRS.STO" if timeout == "short" else "WRS.NTO"

    sie0 = f"mstatus.SIE = 0{' (if S supported)' if priv == 'U' else ''}"
    # (mstatus.TW, hstatus.VTW, hedeleg[2], coverpoint) for each case; VTW and hedeleg are only written in VS/VU
    if virtual and op == "WRS.STO":
        banner = "cp_wrs_sto_timeout_h"
        description = [
            f"Generate {mode} mode wrs.sto timeout tests.",
            "",
            "cross lr instruction to set up reservation.",
            "mstatus.TW = {0/1}",
            "hstatus.VTW = {0/1}",
            "mstatus.MIE = 0",
            "mstatus.SIE = 0",
            "mie = all 0s to disable interrupts",
            f"Execute WRS.STO in {mode} mode: neither TW nor VTW makes it trap",
            "2 x 2 bins",
        ]
        cases = [(tw, vtw, 0, banner) for tw in (0, 1) for vtw in (0, 1)]
    elif virtual:
        banner = "cp_wrs_nto_tw_h / cp_wrs_nto_vtw_h"
        description = [
            f"Generate {mode} mode WRS.NTO timeout tests",
            "",
            "cross lr instruction to set up reservation.",
            "mstatus.MIE = 0",
            "mstatus.SIE = 0",
            "mie = all 0s to disable interrupts",
            f"execute WRS.NTO in {mode} mode",
            "cp_wrs_nto_tw_h: mstatus.TW = 1, hstatus.VTW = {0/1}, hedeleg[2] = {0/1}:",
            "    illegal instruction, taken in HS-mode or (hedeleg[2] = 1) VS-mode, 2 x 2 bins",
            "cp_wrs_nto_vtw_h: mstatus.TW = 0, hstatus.VTW = 1: virtual instruction, taken in HS-mode, 1 bin",
        ]
        cases = [(1, vtw, deleg, "cp_wrs_nto_tw_h") for vtw in (0, 1) for deleg in (0, 1)]
        cases.append((0, 1, 0, "cp_wrs_nto_vtw_h"))
    elif op == "WRS.STO":
        banner = "cp_wrs_sto_timeout"
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
        cases = [(tw, 0, 0, banner) for tw in (0, 1)]
    else:
        banner = "cp_wrs_nto_timeout"
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
        cases = [(1, 0, 0, banner)]
    lines = [comment_banner(banner, "\n".join(description))]

    for tw_val, vtw, deleg, coverpoint in cases:
        lines.extend(
            [
                "###### Setup ######",
                *_disable_interrupts(priv, r_temp),
                "# Write mstatus.TW",
                f"LI(x{r_temp}, 0x200000)",
                tsbi_call_or_direct(f"{'csrs' if tw_val else 'csrc'} mstatus, x{r_temp}", priv),
            ]
        )
        if virtual:
            lines.extend(
                [
                    *write_vtw(r_temp, bool(vtw), priv),
                    f"# hedeleg[2] = {deleg}: illegal-instruction traps from VS/VU go to {'VS' if deleg else 'HS'}-mode",
                    f"LI(x{r_temp}, 0x4)",
                    f"{'csrs' if deleg else 'csrc'} hedeleg, x{r_temp}",
                    f"RVTEST_TSBI_GOTO_{mode}MODE",
                ]
            )
        label = f"tw_{tw_val}_vtw_{vtw}_hedeleg_{deleg}_{mode}_{op}" if virtual else f"tw_{tw_val}_{mode}_{op}"
        lines.extend(
            [
                *_read_trap_count_helper(r_cause),
                "# lr.w to set up reservation",
                f"LA(x{r_temp}, scratch)",
                f"lr.w x{r_temp2}, (x{r_temp})",
                test_data.add_testcase(label, coverpoint, covergroup),
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
        if virtual:
            lines.append(f"RVTEST_TSBI_GOTO_{priv}MODE")

    if virtual:
        lines.extend(
            [
                *write_vtw(r_temp, False, priv),
                "# hedeleg[2] = 0",
                f"LI(x{r_temp}, 0x4)",
                f"csrc hedeleg, x{r_temp}",
            ]
        )
    test_data.int_regs.return_registers([r_cause, r_temp, r_temp2])
    return lines


@add_priv_test_generator(
    "Zawrs",
    required_extensions=["Sm", "Zawrs", "Zalrsc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zawrssm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions at machine-mode."""

    covergroup = "Zawrs_Sm_cg"
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Sm")
    tc.code.extend(wrs_no_res_helper(test_data, "M", covergroup))
    tc.code.extend(wrs_timeout_helper(test_data, "M", covergroup, timeout="short"))
    tc.code.extend(wrs_resume_helper(test_data, "M", covergroup))
    tc.code.extend(wrs_no_mie_helper(test_data, "M", covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Zawrs",
    required_extensions=["S", "Zawrs", "Zalrsc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zawrss(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions at S-mode."""

    covergroup = "Zawrs_S_cg"
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("S")
    tc.code.extend(wrs_no_res_helper(test_data, "S", covergroup))
    tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="short"))
    tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="no"))
    tc.code.extend(wrs_no_mie_helper(test_data, "S", covergroup))
    tc.code.extend(wrs_resume_helper(test_data, "S", covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Zawrs",
    required_extensions=["U", "Zawrs", "Zalrsc"],
)
def make_zawrsu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions at user-mode."""

    covergroup = "Zawrs_U_cg"
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("U")
    tc.code.extend(wrs_no_res_helper(test_data, "U", covergroup))
    tc.code.extend(wrs_timeout_helper(test_data, "U", covergroup, timeout="short"))
    tc.code.extend(wrs_timeout_helper(test_data, "U", covergroup, timeout="no"))
    tc.code.extend(wrs_no_mie_helper(test_data, "U", covergroup))
    tc.code.extend(wrs_resume_helper(test_data, "U", covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Zawrs",
    required_extensions=["H", "Zawrs", "Zalrsc"],
    march_extensions=["H", "Zawrs", "Zalrsc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zawrsh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions in VS-mode and VU-mode, entered from HS-mode."""

    covergroup = "Zawrs_H_cg"
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("H")
    for mode in ["VS", "VU"]:
        tc.code.extend(wrs_no_res_helper(test_data, "S", covergroup, mode))
        tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="short", mode=mode))
        tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="no", mode=mode))
        tc.code.extend(wrs_no_mie_helper(test_data, "S", covergroup, mode))
        tc.code.extend(wrs_resume_helper(test_data, "S", covergroup, mode))
    tc.code.extend(wrs_interrupt_helper(test_data, covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
