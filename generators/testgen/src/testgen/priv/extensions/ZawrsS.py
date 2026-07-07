##################################
# priv/extensions/ZawrsS.py
#
# ZawrsS privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZawrsS privileged extension test generator for S-mode (and H extension if supported)."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZawrsHelper import (
    _exception_helper,
    _timeout_helper,
    _wrs_no_mie_helper,
    _wrs_no_res_helper,
    _wrs_resume_helper,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsSU_cg"


def _generate_wrs_sto_timeout_tests(test_data: TestData, r_cause: int, r_scratch: int) -> list[str]:
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
    lines.extend(_timeout_helper(test_data, coverpoint, covergroup, ["S", "U"], [0, 1], "WRS.STO", r_cause, r_scratch))

    return lines


def _generate_wrs_no_res_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction no reservation tests

    mstatus.TW =0
    mstatus.MIE = 0
    mstatus.SIE = 0
    mie= all 0s to disable interrupts
    Clear all reservation with sc.w, then execute {WRS.STO, WRS.NTO} with no reservation created in {S/U} mode
    2 x 2 x 2 bins
    """

    ######################################
    coverpoint = "cp_wrs_no_res"
    ######################################

    lines = [
        comment_banner(
            "cp_wrs_no_res",
            _generate_wrs_no_res_tests.__doc__,
        ),
        "",
    ]

    lines.extend(_wrs_no_res_helper(test_data, coverpoint, ["S", "U"], covergroup))

    return lines


def _generate_wrs_resume_tests(test_data: TestData) -> list[str]:
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

    lines.extend(_wrs_resume_helper(test_data, ["U", "S"], covergroup))
    return lines


def _generate_wrs_no_mie_tests(test_data: TestData, r_cause: int, r_scratch: int) -> list[str]:
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
    coverpoint = "cp_wrs_no_mie"
    ######################################

    lines = [
        comment_banner(
            "cp_wrs_no_mie",
            _generate_wrs_no_mie_tests.__doc__,
        ),
        "",
    ]

    lines.extend(_wrs_no_mie_helper(test_data, ["S", "U"], covergroup, coverpoint, r_cause, r_scratch))
    return lines


def _generate_wrs_nto_timeout_tests(test_data: TestData, r_cause: int, r_scratch: int) -> list[str]:
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
    lines.extend(_timeout_helper(test_data, coverpoint, covergroup, ["S", "U"], [1], "WRS.NTO", r_cause, r_scratch))
    return lines


def _generate_wrs_nto_timeout_h_tests(test_data: TestData, r_cause: int, r_scratch: int) -> list[str]:
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

    lines.extend(
        _timeout_helper(test_data, coverpoint, covergroup, ["VS", "VU"], [0, 1], "WRS.NTO", r_cause, r_scratch)
    )

    return lines


@add_priv_test_generator(
    "ZawrsSU", required_extensions=["U", "Zawrs", "Zalrsc"], march_extensions=["H", "S", "Zawrs", "Zalrsc"]
)
def make_zawrssu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZawrSU WRS instructions at user-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    # r_cause/r_scratch are the two registers baked into the shared WRS exception
    # handlers (emitted once by _exception_helper): every coverpoint that traps into
    # them must use those same two registers. Emit the handlers up front and hold
    # the registers across the group of coverpoints that use them (the timeout and
    # no_mie tests), then release them for the register-hungry resume test.
    r_cause, r_scratch = test_data.int_regs.get_registers(2)
    tc.code.extend(_exception_helper(test_data, r_cause, r_scratch))

    # ---- coverpoints that trap into the shared handler (hold r_cause/r_scratch) ----
    tc.code.extend(_generate_wrs_sto_timeout_tests(test_data, r_cause, r_scratch))

    # This refers to Spike, QEMU and Whisper:
    # for any coverpoint with TW = 1, the DUTs trigger illegal instruction on WRS.NTO immediately if TW = 1 but sail just treats WRS.NTO as NOP
    # NTO is_nop = true is set for the DUTs since they all treat WRS.NTO as NOP unless TW = 1
    tc.code.extend(_generate_wrs_nto_timeout_tests(test_data, r_cause, r_scratch))
    tc.code.extend(_generate_wrs_nto_timeout_h_tests(test_data, r_cause, r_scratch))
    tc.code.extend(_generate_wrs_no_mie_tests(test_data, r_cause, r_scratch))

    test_data.int_regs.return_registers([r_cause, r_scratch])

    # ---- coverpoints with their own handler / that need the full register pool ----
    tc.code.extend(_generate_wrs_no_res_tests(test_data))
    tc.code.extend(_generate_wrs_resume_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
