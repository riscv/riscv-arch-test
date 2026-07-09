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
    _wrs_no_mie_helper,
    _wrs_no_res_helper,
    _wrs_resume_helper,
    _wrs_timeout_helper,
    _zawrs_define_helper,
    _zawrs_trap_handler,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsSm_cg"


def _generate_wrs_sto_timeout_tests(
    test_data: TestData, r_cause: int, r_scratch: int, r_temp: int, r_temp2: int
) -> list[str]:
    """Generate wrs.sto timeout tests.

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
        ),
        "",
    ]

    lines.extend(_wrs_timeout_helper(test_data, ["M"], coverpoint, covergroup, r_cause, r_scratch, r_temp, r_temp2))
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
    coverpoint = "cp_wrs_no_res"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            _generate_wrs_no_res_tests.__doc__,
        ),
        "",
    ]

    lines.extend(_wrs_no_res_helper(test_data, "M", covergroup))
    return lines


def _generate_wrs_resume_tests(
    test_data: TestData, r_cause: int, r_scratch: int, r_temp: int, r_timecmp: int, r_temp2: int
) -> list[str]:
    """Generate WRS instruction resume when interrupt pending tests

    For DUTs that supports S mode but do not have Sstc, the WRS resume behavior
    can not be tested with stimer interrupt

    cross lr instruction to set up reservation.
    mstatus.TW = 0
    cross with mie.MTIE=1
    mstatus.MIE = {0/1}
    (if S supported: mstatus.SIE = {0/1})
    Set up timer to interrupt soon
    execute WRS.NTO in {S/U} mode
    2 x 2 x 2 bins
    """

    lines = [
        comment_banner(
            "cp_wrs_resume",
            _generate_wrs_resume_tests.__doc__,
        ),
        "",
    ]

    lines.extend(_wrs_resume_helper(test_data, "M", covergroup, r_cause, r_scratch, r_temp, r_timecmp, r_temp2))
    return lines


def _generate_wrs_no_mie_tests(
    test_data: TestData, r_cause: int, r_scratch: int, r_temp: int, r_timecmp: int, r_temp2: int
) -> list[str]:
    """Generate wrs tests with mie = all 0s.

    cross lr instruction to set up reservation
    mstatus.MIE = 1
    mie = all 0s
    mstatus.TW = 0
    mip.mtip = {MSIP + MEIP + MTIP}
    execute WRS.STO in M mode
    1 bin
    """
    lines = []

    lines.extend(_wrs_no_mie_helper(test_data, "M", covergroup, r_cause, r_scratch, r_temp, r_timecmp, r_temp2))
    return lines


@add_priv_test_generator("ZawrsSm", required_extensions=["Sm", "Zawrs", "Zalrsc"])
def make_zawrssm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZawrsSm WRS instructions at machine-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_wrs_no_res_tests(test_data))

    r_cause, r_scratch, r_temp, r_temp2, r_timecmp = test_data.int_regs.get_registers(5)
    tc.code.extend(_zawrs_define_helper("M"))
    tc.code.extend(_zawrs_trap_handler(r_cause, r_scratch, True, r_temp, r_timecmp, r_temp2))
    tc.code.extend(_zawrs_trap_handler(r_cause, r_scratch, False, r_temp, r_timecmp, r_temp2))

    tc.code.extend(_generate_wrs_sto_timeout_tests(test_data, r_cause, r_scratch, r_temp, r_temp2))
    tc.code.extend(_generate_wrs_resume_tests(test_data, r_cause, r_scratch, r_temp, r_timecmp, r_temp2))
    tc.code.extend(_generate_wrs_no_mie_tests(test_data, r_cause, r_scratch, r_temp, r_timecmp, r_temp2))
    test_data.int_regs.return_registers([r_cause, r_scratch, r_temp, r_temp2, r_timecmp])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
