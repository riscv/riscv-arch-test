##################################
# priv/extensions/ZawrsHelper.py
#
# Shared Zawrs tests generation
# ellyu@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Common Zawrs test generation"""

from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_mmode,
    set_mtimer_int,
    set_stimer_mmode,
)
from testgen.data.state import TestData


def _timeout_helper(
    test_data: TestData, coverpoint: str, covergroup: str, priv_list: list[str], tw_list: list[int], wrs_op: str
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
                    test_data.add_testcase(f"tw_{tw_val}_{priv_mode}_{wrs_op}", coverpoint, covergroup),
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


def _wrs_no_res_helper(test_data: TestData, coverpoint: str, priv_list: list[str], covergroup: str) -> list[str]:
    """Helper function for generating WRS instruction no reservation tests"""

    r_scratch, r_temp, r_temp2 = test_data.int_regs.get_registers(3)

    lines = []

    for priv_mode in priv_list:
        for wrs_ops in ["WRS.STO", "WRS.NTO"]:
            lines.extend(
                [
                    "#### Setup (M mode) ####",
                    "# Disable all interrupts in mie",
                    "CSRW mie, zero",
                    "# mstatus.MPIE = 0",
                    f"LI(x{r_temp}, 0x80)",
                    f"CSRC(mstatus, x{r_temp})",
                    "# Clear mstatus.TW",
                    f"LI(x{r_temp}, 0x200000)",
                    f"CSRC(mstatus, x{r_temp})",
                    "",
                    "# clear SIE",
                    "#ifdef S_SUPPORTED",
                    "csrci mstatus, 2",
                    "#endif",
                ]
            )

            lines.extend(
                [
                    f"# Go down to {priv_mode} mode to execute the instruction",
                    f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                    "# sc.w to clear reservation",
                    f"LA(x{r_scratch}, scratch)",
                    f"sc.w x{r_temp}, x{r_temp2}, (x{r_scratch})",
                    test_data.add_testcase(
                        f"tw_0_{'STO' if wrs_ops == 'WRS.STO' else 'NTO'}_{priv_mode}",
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


def _wrs_no_mie_helper(test_data: TestData, priv_list: list[str], covergroup: str, coverpoint: str) -> list[str]:
    """Generate wrs tests with mie = all 0s"""

    r_temp, r_temp2, r_mtime, r_mtimecmp = test_data.int_regs.get_registers(4)

    lines = []

    for wrs_ops in ["WRS.STO", "WRS.NTO"]:
        for priv_mode in priv_list:
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

    test_data.int_regs.return_registers([r_temp, r_temp2, r_mtime, r_mtimecmp])
    return lines
