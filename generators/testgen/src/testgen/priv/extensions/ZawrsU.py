##################################
# priv/extensions/ZawrsU.py
#
# ZawrsU privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZawrsU privileged extension test generator for user-mode."""

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

covergroup = "ZawrsU_cg"


def _generate_wrs_sto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate U mode wrs.sto timeout tests.

    cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    mstatus.MIE = 0
    mstatus.SIE = 0 (if S supported)
    mie=all zeros 0 to disable interrupts
    Execute WRS.STO in U mode
    2 bins
    """
    ######################################
    coverpoint = "cp_wrs_sto_timeout"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_sto_timeout_tests.__doc__,
        ),
        "",
    ]
    lines.extend(wrs_timeout_helper(test_data, ["U"], coverpoint, covergroup))

    return lines


def _generate_wrs_no_res_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction no reservation tests

    mstatus.TW =0
    mstatus.MIE = 0
    mstatus.SIE = 0 (if S supported)
    mie= all 0s to disable interrupts
    Clear all reservation with sc.w, then execute {WRS.STO, WRS.NTO} with no reservation created in U mode
    2 bins
    """

    ######################################
    coverpoint = "cp_wrs_no_res"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_no_res_tests.__doc__,
        ),
        "",
    ]

    lines.extend(wrs_no_res_helper(test_data, "U", covergroup))

    return lines


def _generate_wrs_resume_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction resume when interrupt pending tests

    For DUTs that supports S mode but do not have Sstc, the WRS resume behavior
    is tested with MTIP

    cross lr instruction to set up reservation.
    mstatus.TW = 0
    cross with mie.MTIE=1
    (if SSTC supporrted use STIP, cross menvcfg.STCE = 1)
    mstatus.MIE = {0/1}
    (if S supported: mstatus.SIE = {0/1})
    Set up timer to interrupt soon
    execute {WRS.NTO/WRS.STO} in U mode
    2 x 2 x 2 bins
    """

    ######################################
    coverpoint = "cp_wrs_resume"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_resume_tests.__doc__,
        ),
        "",
    ]

    lines.extend(wrs_resume_helper(test_data, "U", covergroup))
    return lines


def _generate_wrs_no_mie_tests(test_data: TestData) -> list[str]:
    """Generate wrs tests with mie = all 0s.

    cross lr instruction to set up reservation
    mstatus.MIE = 1
    mstatus.SIE = 1
    mie = all 0s
    mstatus.TW = 1
    mip.mtip = {SSIP + SEIP + STIP + MSIP + MEIP + MTIP}
    execute {WRS.NTO/WRS.STO} in U mode
    2 bins
    """
    ######################################
    coverpoint = "cp_wrs_no_mie"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_no_mie_tests.__doc__,
        ),
    ]

    lines.extend(wrs_no_mie_helper(test_data, "U", covergroup))
    return lines


def _generate_wrs_nto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate WRS.NTO timeout test in U mode

    cross lr instruction to set up reservation.
    mstatus.TW = 1
    mstatus.MIE = 0
    mstatus.SIE = 0 (if S supported)
    mie=all 0s to disable interrupts
    execute WRS.NTO in U mode"
    1 bin
    """

    ######################################
    coverpoint = "cp_wrs_nto_timeout"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_nto_timeout_tests.__doc__,
        ),
        "",
    ]
    lines.extend(wrs_timeout_helper(test_data, ["U"], coverpoint, covergroup))
    return lines


@add_priv_test_generator(
    "ZawrsU",
    required_extensions=["U", "Zawrs", "Zalrsc"],
    # TODO: Remove BOOT_TO_MMODE when converting this test to T-SBI.
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zawrsu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions at user-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_wrs_no_res_tests(test_data))
    tc.code.extend(_generate_wrs_sto_timeout_tests(test_data))
    tc.code.extend(_generate_wrs_nto_timeout_tests(test_data))

    tc.code.extend(_generate_wrs_no_mie_tests(test_data))
    tc.code.extend(_generate_wrs_resume_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
