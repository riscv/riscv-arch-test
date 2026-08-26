##################################
# priv/extensions/ZawrsCommon.py
#
# Shared Zawrs tests generation
# ellyu@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zawrs tests in all priv modes"""

import re

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_int,
    set_menvcfg_stce,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimecmp_max,
    set_stimer_int_soon_sstc,
    set_stimer_mmode,
)
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

# CSRs that need M-mode, and CSRs that need at least S-mode.
_M_CSRS = {"mstatus", "mie", "mip", "menvcfg", "menvcfgh"}
_S_CSRS = {"sstatus", "sie", "sip", "stimecmp", "stimecmph"}
_CSR_RE = re.compile(r"^\s*(csrr[sc]?|csrw|csrs|csrc)\s+([^,\s]+)\s*,\s*([^,\s]+)(?:\s*,\s*([^,\s]+))?")
_RMW_TO_WRITE = {"csrrs": "csrs", "csrrc": "csrc"}


def _csr(priv: str, instr: str) -> str:
    """Emit a CSR instruction, through a T-SBI call when the CSR needs more privilege than the test runs in."""
    match = _CSR_RE.match(instr)
    if priv == "M" or match is None:
        return instr
    mnemonic, first, second, third = match.groups()
    csr = (first if mnemonic in ("csrw", "csrs", "csrc") else second).lower()
    if csr not in _M_CSRS and not (priv == "U" and csr in _S_CSRS):
        return instr
    if mnemonic in _RMW_TO_WRITE:
        # No Zawrs helper uses the value read back, so the T-SBI form only writes.
        instr = f"{_RMW_TO_WRITE[mnemonic]} {second}, {third}"
    return tsbi_call(instr.strip())


def _csrs(priv: str, lines: list[str]) -> list[str]:
    return [_csr(priv, line) for line in lines]


def _mstatus(priv: str, r_temp: int, mask: int, set_bits: bool, comment: str) -> list[str]:
    return [comment, f"LI(x{r_temp}, 0x{mask:X})", _csr(priv, f"{'csrs' if set_bits else 'csrc'} mstatus, x{r_temp}")]


def _sie(priv: str, r_temp: int, value: int) -> list[str]:
    """Write mstatus.SIE through its sstatus shadow.

    SPIE is written along with SIE so the value survives the sret of the S-mode
    T-SBI handler when the test runs in U-mode.
    """
    lines = [
        f"# sstatus.SIE = {value}",
        f"LI(x{r_temp}, 0x22)",
        _csr(priv, f"{'csrs' if value else 'csrc'} sstatus, x{r_temp}"),
    ]
    if priv == "U":
        return ["#ifdef S_SUPPORTED", *lines, "#endif"]
    return lines


def _disable_interrupts(priv: str, r_temp: int) -> list[str]:
    """mie = 0, mstatus.MIE = MPIE = 0, and SIE = 0 where it exists."""
    lines = ["# Disable all interrupts in mie", _csr(priv, "csrw mie, zero")]
    if priv == "M":
        lines.extend(_mstatus(priv, r_temp, 0x8A, False, "# mstatus.MPIE, SIE and MIE = 0"))
    else:
        lines.extend(_mstatus(priv, r_temp, 0x88, False, "# mstatus.MPIE and MIE = 0"))
        lines.extend(_sie(priv, r_temp, 0))
    return lines


def _tw(priv: str, r_temp: int, tw_val: int) -> list[str]:
    return _mstatus(priv, r_temp, 0x200000, bool(tw_val), "# Write mstatus.TW")


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

    if priv != "M":
        lines.extend(
            [
                "#ifdef SSTC_SUPPORTED",
                "# Enable Sstc (menvcfg.STCE) so stimecmp drives sip.STIP, then disarm the comparator",
                "# so whatever stimecmp held before does not raise STIP once STIE is set",
                *_csrs(priv, set_menvcfg_stce(r_temp, True)),
                *_csrs(priv, set_stimecmp_max(r_temp)),
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
                            *_mstatus(priv, r_temp, 0x88, bool(mie_val), f"# mstatus.MPIE and mstatus.MIE = {mie_val}"),
                            *_tw(priv, r_temp, tw_val),
                            "",
                        ]
                    )

                    if priv != "M":
                        lines.extend(
                            [
                                *_sie(priv, r_temp, sie_val),
                                "#ifdef SSTC_SUPPORTED",
                                "# Set sie.STIE",
                                f"LI(x{r_temp}, 0x20)",
                                _csr(priv, f"csrs sie, x{r_temp}"),
                                "# Set stimer interrupt soon; from U-mode the stimecmp write is a T-SBI call, so",
                                "# leave enough delay for that round trip on DUTs whose time ticks once per instruction",
                                *_csrs(
                                    priv,
                                    set_stimer_int_soon_sstc(
                                        r_time,
                                        r_temp,
                                        r_temp2,
                                        r_temp3,
                                        r_cause,
                                        delay="(RVMODEL_TIMER_INT_SOON_DELAY * 16)" if priv == "U" else None,
                                    ),
                                ),
                                "#else",
                                "# Set mie.MTIE",
                                f"LI(x{r_temp}, 0x80)",
                                _csr(priv, f"csrs mie, x{r_temp}"),
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
                    if priv != "M":
                        lines.extend(
                            [
                                "#ifdef SSTC_SUPPORTED",
                                *_csrs(priv, clr_stimer_int(r_temp, r_timecmp, r_temp2, r_cause)),
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
                _csr(priv, "csrw mie, zero"),
            ]
        )
        if priv == "M":
            lines.extend(_mstatus(priv, r_temp, 0x8A, True, "# mstatus.MIE, SIE and MPIE = 1"))
        else:
            lines.extend(_mstatus(priv, r_temp, 0x88, True, "# mstatus.MIE and MPIE = 1"))
            lines.extend(_sie(priv, r_temp, 1))
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
                    *_csrs(priv, set_stimer_mmode(r_temp)),
                    "# set SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    _csr(priv, f"csrs mip, x{r_temp}"),
                    "#endif",
                    "",
                    *_tw(priv, r_temp, 1),
                ]
            )
        else:
            lines.extend(_tw(priv, r_temp, 0))
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
                    "# Clear S mode interrupts",
                    "#ifdef S_SUPPORTED",
                    "# clear SSI, STI and SEI through mip, the way they were set",
                    f"LI(x{r_temp}, 0x222)",
                    _csr(priv, f"csrc mip, x{r_temp}"),
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
                    *_tw(priv, r_temp, tw_val),
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
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    """WRS ops timeout behavior; cp_wrs_nto_timeout_h runs the test in VS and VU mode from an S-mode test."""
    r_cause, r_temp, r_temp2 = test_data.int_regs.get_registers(3)
    op = "WRS.STO" if coverpoint == "cp_wrs_sto_timeout" else "WRS.NTO"
    hyp = coverpoint == "cp_wrs_nto_timeout_h"

    sie0 = f"mstatus.SIE = 0{' (if S supported)' if priv == 'U' else ''}"
    if hyp:
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
    elif op == "WRS.STO":
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
    else:
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
    lines = [comment_banner(coverpoint, "\n".join(description))]

    tw_list = [1] if coverpoint == "cp_wrs_nto_timeout" else [0, 1]
    mode_list = ["VS", "VU"] if hyp else [priv]

    if hyp:
        lines.append("#ifdef H_SUPPORTED")
    for mode in mode_list:
        for tw_val in tw_list:
            lines.extend(
                [
                    "###### Setup ######",
                    *_disable_interrupts(priv, r_temp),
                    *_tw(priv, r_temp, tw_val),
                ]
            )
            if hyp:
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

    if hyp:
        lines.append("#endif // H_SUPPORTED")
    test_data.int_regs.return_registers([r_cause, r_temp, r_temp2])
    return lines
