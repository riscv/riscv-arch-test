##################################
# priv/extensions/ZawrsSm.py
#
# ZawrsSm privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""ZawrsSm privileged extension test generator for machine-mode."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZawrsCommon import (
    wrs_no_mie_helper,
    wrs_no_res_helper,
    wrs_resume_helper,
    wrs_timeout_helper,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsSm_cg"


def _generate_wrs_sto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate M mode wrs.sto timeout tests.

    Cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    mstatus.MIE = 0
    mie=all 0s to disable interrupts
    Execute WRS.STO in M mode
    2 bins
    """
    ######################################
    coverpoint = "cp_wrs_sto_timeout"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_sto_timeout_tests.__doc__,
        )
    ]

    lines.extend(wrs_timeout_helper(test_data, ["M"], coverpoint, covergroup))
    return lines


def _generate_wrs_no_res_tests(test_data: TestData) -> list[str]:
    """Generate M mode WRS instruction no reservation tests

    mstatus.TW ={0/1}
    mstatus.MIE = 0
    mie=all 0s to disable interrupts
    Clear all reservation with sc.w, then execute {WRS.STO/ WRS.NTO} with no reservation created in M mode
    2 x 2 bins
    """

    ######################################
    coverpoint = "cp_wrs_no_res"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_no_res_tests.__doc__,
        )
    ]

    lines.extend(wrs_no_res_helper(test_data, "M", covergroup))
    return lines


def _generate_wrs_resume_tests(test_data: TestData) -> list[str]:
    """Generate M mode WRS instruction resume when interrupt pending tests

    cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    cross with mie.MTIE=1
    mstatus.MIE = {0/1}
    Set up timer to interrupt soon
    execute {WRS.NTO/WRS.STO} in mode
    2 x 2 x 2 bins
    """
    ######################################
    coverpoint = "cp_wrs_resume"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_resume_tests.__doc__,
        )
    ]

    lines.extend(wrs_resume_helper(test_data, "M", covergroup))
    return lines


def _generate_wrs_no_mie_tests(test_data: TestData) -> list[str]:
    """Generate M mode wrs tests with mie = all 0s.

    cross lr instruction to set up reservation
    mstatus.MIE = 1
    mie = all 0s
    mstatus.TW = 0
    mip.mtip = {MSIP + MEIP + MTIP}
    execute WRS.STO in M mode
    1 bin
    """
    ######################################
    coverpoint = "cp_wrs_no_mie"
    ######################################
    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_no_mie_tests.__doc__,
        )
    ]

    lines.extend(wrs_no_mie_helper(test_data, "M", covergroup))
    return lines


@add_priv_test_generator(
    "ZawrsSm",
    required_extensions=["Sm", "Zawrs", "Zalrsc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zawrssm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZawrsSm WRS instructions at machine-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_wrs_no_res_tests(test_data))
    tc.code.extend(_generate_wrs_sto_timeout_tests(test_data))
    tc.code.extend(_generate_wrs_resume_tests(test_data))
    tc.code.extend(_generate_wrs_no_mie_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
