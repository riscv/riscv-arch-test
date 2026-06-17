##################################
# priv/extensions/ZawrsSm.py
#
# ZawrsSm privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""ZawrsSm privileged extension test generator for machine-mode."""

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, set_mtimer_int, set_mtimer_int_soon
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


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

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch = test_data.int_regs.get_registers(6)

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
            ]
        )

        lines.extend(
            [
                *set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch),
                "",
                "# lr.w to set up reservation",
                f"LA(x{r_scratch}, scratch)",
                f"lr.w x{r_temp}, (x{r_scratch})",
                test_data.add_testcase(f"mie_{mie_val}", coverpoint, covergroup),
                "WRS.NTO",
                "",
                *clr_mtimer_int(r_temp, r_mtimecmp),
            ]
        )
    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch])
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
            test_data.add_testcase("Interrupt_pending", coverpoint, covergroup),
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
def make_zawrssm(test_data: TestData) -> list[str]:
    """Generate tests for ZawrSm WRS instructions at machine-mode."""

    lines: list[str] = []

    lines.extend(_generate_wrs_sto_timeout_tests(test_data))
    lines.extend(_generate_wrs_no_res_tests(test_data))
    lines.extend(_generate_wrs_resume_tests(test_data))
    lines.extend(_generate_wrs_no_mie_tests(test_data))

    return lines
