##################################
# priv/extensions/ZawrsSU.py
#
# ZawrsSU privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZawrsSU privileged extension test generator for user-mode (and Supervisor mode and H extension if supported)."""

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_mmode,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimer_mmode,
)
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _timeout_helper(
    test_data: TestData, coverpoint: str, priv_list: list[str], tw_list: list[int], wrs_op: str
) -> list[str]:
    """helper function for generating timeout tests"""

    r_scratch, r_temp = test_data.int_regs.get_registers(2)

    lines = []
    for priv_mode in priv_list:
        for tw_val in tw_list:
            lines.extend(
                [
                    "#### Setup (M mode) ####",
                    "# Disable all interrupts in mie",
                    "CSRW mie, zero",
                    "# mstatus.MPIE = 0",
                    f"LI(x{r_temp}, 0x80)",
                    f"CSRC(mstatus, x{r_temp})",
                    f"# {'Set' if tw_val else 'Clear'} mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
                    "",
                    "# clear SIE",
                    "#ifdef S_SUPPORTED",
                    "csrci mstatus, 2",
                    "#endif",
                ]
            )
            if coverpoint == "cp_wrs_nto_timeout_h":
                lines.extend(
                    [
                        "#ifdef H_SUPPORTED",
                        "# Set hstatus.VTW",
                        f"LI(x{r_temp}, 0x200000)",
                        f"CSRS(hstatus, x{r_temp})",
                    ]
                )

            if priv_mode == "S":
                lines.append("#ifdef S_SUPPORTED")

            lines.extend(
                [
                    f"# Go down to {priv_mode} mode to execute the instruction",
                    f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                    "# lr.w to set up reservation",
                    f"LA(x{r_scratch}, scratch)",
                    f"lr.w x{r_temp}, (x{r_scratch})",
                    test_data.add_testcase(f"tw_{tw_val}_{priv_mode}_{wrs_op}", coverpoint, "ZawrsSU_cg"),
                    f"{wrs_op}",
                    "",
                    "RVTEST_GOTO_MMODE",
                ]
            )
            if coverpoint == "cp_wrs_nto_timeout_h":
                lines.append("#endif")
            if priv_mode == "S":
                lines.append("#endif")

    test_data.int_regs.return_registers([r_scratch, r_temp])
    return lines


def _generate_wrs_sto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate wrs.sto timeout tests.

    cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    mstatus.MIE = 0
    mstatus.SIE = 0 (if S mode supported)
    mie=all zeros 0 to disable interrupts
    Execute WRS.STO in {S/U} mode
    2 x 2 bins
    """
    ######################################
    coverpoint = "cp_wrs_sto_timeout"
    ######################################

    lines = [
        comment_banner(
            "cp_wrs_sto_timeout",
            _generate_wrs_sto_timeout_tests.__doc__,
        ),
        "",
    ]
    lines.extend(_timeout_helper(test_data, coverpoint, ["S", "U"], [0, 1], "WRS.STO"))

    return lines


def _generate_wrs_no_res_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction no reservation tests

    mstatus.TW ={0/1}
    mstatus.MIE = 0
    mstatus.SIE = 0
    mie= all 0s to disable interrupts
    Clear all reservation with sc.w, then execute {WRS.STO, WRS.NTO} with no reservation created in {S/U} mode
    2 x 2 x 2 bins
    """

    ######################################
    covergroup = "ZawrsSU_cg"
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

    for priv_mode in ["S", "U"]:
        for wrs_ops in ["WRS.STO", "WRS.NTO"]:
            for tw_val in [0, 1]:
                lines.extend(
                    [
                        "#### Setup (M mode) ####",
                        "# Disable all interrupts in mie",
                        "CSRW mie, zero",
                        "# mstatus.MPIE = 0",
                        f"LI(x{r_temp}, 0x80)",
                        f"CSRC(mstatus, x{r_temp})",
                        f"# {'Set' if tw_val else 'Clear'} mstatus.TW",
                        f"LI(x{r_temp}, 0x200000)",
                        f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_temp})",
                        "",
                        "# clear SIE",
                        "#ifdef S_SUPPORTED",
                        "csrci mstatus, 2",
                        "#endif",
                    ]
                )

                if priv_mode == "S":
                    lines.append("#ifdef S_SUPPORTED")

                lines.extend(
                    [
                        f"# Go down to {priv_mode} mode to execute the instruction",
                        f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                        "# sc.w to clear reservation",
                        f"LA(x{r_scratch}, scratch)",
                        f"sc.w x{r_temp}, x{r_temp2}, (x{r_scratch})",
                        test_data.add_testcase(
                            f"tw_{tw_val}_{'STO' if wrs_ops == 'WRS.STO' else 'NTO'}_{priv_mode}",
                            coverpoint,
                            covergroup,
                        ),
                        f"{wrs_ops}",
                        "",
                        "RVTEST_GOTO_MMODE",
                    ]
                )
                if priv_mode == "S":
                    lines.append("#endif")

    test_data.int_regs.return_registers([r_scratch, r_temp, r_temp2])

    return lines


def _generate_wrs_resume_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction resume when interrupt pending tests

    cross lr instruction to set up reservation.
    mstatus.TW = 0
    cross with mie.MTIE=1
    mstatus.MIE = {0/1}
    (if S supported: mstatus.SIE = {0/1})
    Set up timer to interrupt soon
    execute WRS.NTO in {S/U} mode
    2 x 2 x 2 bins
    """

    ######################################
    covergroup = "ZawrsSU_cg"
    coverpoint = "cp_wrs_resume"
    ######################################

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_wrs_resume",
            _generate_wrs_resume_tests.__doc__,
        ),
        "",
    ]

    for priv_mode in ["U", "S"]:
        for sie_val in [0, 1]:
            for mie_val in [0, 1]:
                lines.extend(
                    [
                        "#### Setup (M mode) ####",
                        f"# mstatus.MPIE = {mie_val}",
                        f"LI(x{r_temp}, 0x80)",
                        f"{'CSRS' if mie_val else 'CSRC'}(mstatus, x{r_temp})",
                        "# Set mie.MTIE",
                        f"LI(x{r_temp}, 0x80)",
                        f"CSRS(mie, x{r_temp})",
                        "",
                        "# Clear mstatus.TW",
                        f"LI(x{r_temp}, 0x200000)",
                        f"CSRC(mstatus, x{r_temp})",
                        "",
                        "#ifdef S_SUPPORTED",
                        f"# mstatus.SIE = {sie_val}",
                        f"{'csrsi' if sie_val else 'csrci'} mstatus, 2",
                        "#endif",
                    ]
                )

                if priv_mode == "S":
                    lines.append("#ifdef S_SUPPORTED")

                lines.extend(
                    [
                        *set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch),
                        f"# Go down to {priv_mode} mode to execute the instruction",
                        f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                        "",
                        "# lr.w to set up reservation",
                        f"LA(x{r_scratch}, scratch)",
                        f"lr.w x{r_temp}, (x{r_scratch})",
                        test_data.add_testcase(f"mie_{mie_val}_sie_{sie_val}_{priv_mode}", coverpoint, covergroup),
                        "WRS.NTO",
                        "# clean up",
                        "RVTEST_GOTO_MMODE",
                        *clr_mtimer_int(r_temp, r_mtimecmp),
                    ]
                )

                if priv_mode == "S":
                    lines.append("#endif")

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch])
    return lines


def _generate_wrs_no_mie_tests(test_data: TestData) -> list[str]:
    """Generate wrs tests with mie = all 0s.

    cross lr instruction to set up reservation
    mstatus.MIE = 1
    mstatus.SIE = 1
    mie = all 0s
    mstatus.TW = 1
    mip.mtip = {SSIP + SEIP + STIP + MSIP + MEIP + MTIP}
    execute {WRS.NTO/WRS.STO} in {S/U} mode
    2 x 2 bins
    """
    ######################################
    covergroup = "ZawrsSU_cg"
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

    for wrs_ops in ["WRS.STO", "WRS.NTO"]:
        for priv_mode in ["S", "U"]:
            lines.extend(
                [
                    "#### Setup (M mode) ####",
                    "# Disable all interrupts in mie",
                    "CSRW mie, zero",
                    "",
                    "# mstatus.MPIE = 1",
                    f"LI(x{r_temp}, 0x80)",
                    f"CSRS(mstatus, x{r_temp})",
                    "",
                    "# Set mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    f"CSRS(mstatus, x{r_temp})",
                    "",
                    "#ifdef S_SUPPORTED",
                    "# mstatus.SIE = 1",
                    "csrsi mstatus, 2",
                    "#endif",
                ]
            )

            if priv_mode == "S":
                lines.append("#ifdef S_SUPPORTED")

            lines.extend(
                [
                    "# Set all 6 interrupts pending",
                    "RVTEST_SET_MEXT_INT",
                    "RVTEST_SET_MSW_INT",
                    *set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2),
                    *set_stimer_mmode(r_temp),
                    "# set SSI and SEI through mip",
                    f"LI(x{r_temp}, 0x202)",
                    f"CSRS(mip, x{r_temp})",
                ]
            )

            lines.extend(
                [
                    f"# Go down to {priv_mode} mode to execute the instruction",
                    f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                    "# lr.w to set up reservation",
                    f"LA(x{r_temp2}, scratch)",
                    f"lr.w x{r_temp}, (x{r_temp2})",
                    test_data.add_testcase(
                        f"{'STO' if wrs_ops == 'WRS.STO' else 'NTO'}_{priv_mode}", coverpoint, covergroup
                    ),
                    f"{wrs_ops}",
                    "",
                ]
            )

            lines.extend(
                [
                    "# Clean up",
                    "RVTEST_GOTO_MMODE",
                    "RVTEST_CLR_MEXT_INT",
                    "RVTEST_CLR_MSW_INT",
                    *clr_mtimer_int(r_temp, r_mtimecmp),
                    *clr_stimer_mmode(r_temp),
                    "# Clear SSIP and SEIP in mip",
                    f"LI(x{r_temp}, 0x202)",
                    f"CSRC(mip, x{r_temp})",
                ]
            )
            if priv_mode == "S":
                lines.append("#endif")

    test_data.int_regs.return_registers([r_temp, r_temp2, r_mtime, r_mtimecmp])
    return lines


def _generate_wrs_nto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate WRS.NTO timeout test in S/U mode

    cross lr instruction to set up reservation.
    mstatus.TW = 1
    mstatus.MIE = 0
    mstatus.SIE = 0
    mie=all 0s to disable interrupts
    execute WRS.NTO in S/U mode"
    2 bins
    """

    ######################################
    coverpoint = "cp_wrs_nto_timeout"
    ######################################

    lines = [
        comment_banner(
            "cp_wrs_nto_timeout",
            _generate_wrs_nto_timeout_tests.__doc__,
        ),
        "",
    ]
    lines.extend(_timeout_helper(test_data, coverpoint, ["S", "U"], [1], "WRS.NTO"))
    return lines


def _generate_wrs_nto_timeout_h_tests(test_data: TestData) -> list[str]:
    """Generate WRS.NTO timeout test in VS/VU mode

    cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    mstatus.MIE = 0
    mstatus.SIE = 0
    hstatus.VTW = 1
    mie=all 0s to disable interrupts
    execute WRS.NTO in VS/VU mode"
    2 x 2 bins
    """

    ######################################
    coverpoint = "cp_wrs_nto_timeout_h"
    ######################################

    lines = [
        comment_banner(
            "cp_wrs_nto_timeout_h",
            _generate_wrs_nto_timeout_h_tests.__doc__,
        ),
        "",
    ]

    lines.extend(_timeout_helper(test_data, coverpoint, ["VS", "VU"], [0, 1], "WRS.NTO"))

    return lines


@add_priv_test_generator(
    "ZawrsSU", required_extensions=["U", "Zawrs", "Zalrsc"], march_extensions=["H", "S", "Zawrs", "Zalrsc"]
)
def make_zawrssu(test_data: TestData) -> list[str]:
    """Generate tests for ZawrSU WRS instructions at user-mode."""

    lines: list[str] = [
        "# No delegation",
        "CSRW(medeleg, zero)",
    ]

    lines.extend(_generate_wrs_sto_timeout_tests(test_data))
    lines.extend(_generate_wrs_no_res_tests(test_data))
    lines.extend(_generate_wrs_resume_tests(test_data))
    lines.extend(_generate_wrs_nto_timeout_tests(test_data))
    lines.extend(_generate_wrs_nto_timeout_h_tests(test_data))
    # for the wrs_no_mie_test, spike triggers illegal instruction on WRS.NTO immediately if TW = 1 but sail just treats WRS,NTO as NOP
    # NTO is_nop = true is set for spike since spike treats WRS.NTO as NOP unless TW = 1
    lines.extend(_generate_wrs_no_mie_tests(test_data))

    return lines
