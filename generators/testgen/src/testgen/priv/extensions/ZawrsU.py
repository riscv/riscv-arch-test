##################################
# priv/extensions/ZawrsSU.py
#
# ZawrsSU privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZawrsSU privileged extension test generator for user-mode (and Supervisor mode and H extension if supported)."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import (
    clr_mtimer_int,
    set_mtimer_int_soon,
)
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZawrsHelper import (
    _timeout_helper,
    _wrs_no_mie_helper,
    _wrs_no_res_helper,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsU_cg"


def _zawrs_resume_trap_handler_u(
    test_data: TestData, r_cause: int, r_temp: int, r_mtimecmp: int, r_scratch: int
) -> list[str]:
    """Local trap handlers for the WRS resume-on-interrupt tests.

    Two handlers are emitted:
      * zawrs_resume_trap_handler_m - always present; used by the U-mode tests,
        whose timer interrupt is taken in M mode (mtvec).
      * zawrs_resume_trap_handler_s - only when S_SUPPORTED; used by the S-mode
        tests, whose Sstc timer interrupt is taken in S mode (stvec).

    Each handler records xcause into r_cause (nonzero => trap fired: the loop
    sentinel), SIGUPDs it, clears the timer, and RESTORES the framework trap
    vector from r_scratch before returning. The restore is essential: the test
    then issues RVTEST_GOTO_MMODE, which returns to M mode via an ecall that
    traps through xtvec - that ecall must land in the framework handler, not
    here.

    The `j` guard skips the handler in straight-line flow; `.align 2` keeps it
    addressable by mtvec/stvec in direct mode (MODE=0).
    """
    lines = [
        "# ---- M-mode WRS resume handler (U-mode tests) ----",
        "j 4f                             # skip handler in straight-line code",
        ".option push",
        ".option norvc",
        ".align 2                         # direct-mode mtvec target must be 4-byte aligned",
        "zawrs_resume_trap_handler_u:",
        f"csrr x{r_cause}, mcause          # nonzero => trap fired (loop sentinel) + SIGUPD value",
        write_sigupd(r_cause, test_data),
        *clr_mtimer_int(r_temp, r_mtimecmp),
        f"csrw mtvec, x{r_scratch}         # restore framework M trap vector before returning",
        "mret                             # return to instruction after WRS.NTO",
        ".option pop",
        "4:",
        "",
    ]

    return lines


def _generate_wrs_sto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate wrs.sto timeout tests.

    cross lr instruction to set up reservation.
    mstatus.TW = {0/1}
    mstatus.MIE = 0
    mie=all zeros 0 to disable interrupts
    Execute WRS.STO in U mode
    2 bins
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
    lines.extend(_timeout_helper(test_data, coverpoint, covergroup, ["U"], [0, 1], "WRS.STO"))

    return lines


def _generate_wrs_no_res_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction no reservation tests

    mstatus.TW =0
    mstatus.MIE = 0
    mstatus.SIE = 0
    mie= all 0s to disable interrupts
    Clear all reservation with sc.w, then execute {WRS.STO, WRS.NTO} with no reservation created in U mode
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

    lines.extend(_wrs_no_res_helper(test_data, coverpoint, ["U"], covergroup))

    return lines


# DO THIS ONE INDIVIDUALLY FOR S AND U
def _generate_wrs_resume_tests(test_data: TestData) -> list[str]:
    """Generate WRS instruction resume when interrupt pending tests

    cross lr instruction to set up reservation.
    mstatus.TW = 0
    cross with mie.MTIE=1
    mstatus.MIE = {0/1}
    Set up timer to interrupt soon
    execute WRS.NTO in U mode
    2 x 2 bins
    """

    ######################################
    coverpoint = "cp_wrs_resume"
    ######################################

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch, r_cause = test_data.int_regs.get_registers(7)

    lines = [
        comment_banner(
            "cp_wrs_resume",
            _generate_wrs_resume_tests.__doc__,
        ),
        "",
    ]

    for mie_val in [0, 1]:
        # ---- Setup (M mode) ----
        lines.extend(
            [
                "#### Setup (M mode) ####",
                f"# mstatus.MPIE = {mie_val} (becomes MIE after entering the lower mode)",
                f"LI(x{r_temp}, 0x80)",
                f"{'CSRS' if mie_val else 'CSRC'}(mstatus, x{r_temp})",
                "# Set mie.MTIE (mie_mtie_one coverpoint)",
                f"LI(x{r_temp}, 0x80)",
                f"CSRS(mie, x{r_temp})",
                "# Clear mstatus.TW",
                f"LI(x{r_temp}, 0x200000)",
                f"CSRC(mstatus, x{r_temp})",
                "",
            ]
        )
        # U-mode: machine timer, taken in M mode. The M handler runs
        # in M and restores mtvec itself (U-mode cannot write mtvec).
        lines.extend(
            [
                "# U-mode uses the machine timer (taken in M); install M handler in mtvec",
                f"# save old mtvec in x{r_scratch}",
                f"LA(x{r_temp}, zawrs_resume_trap_handler_u)",
                f"csrrw x{r_scratch}, mtvec, x{r_temp}",
                *set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_cause),
            ]
        )
        # ---- Execute WRS.NTO in the lower mode ----
        lines.extend(
            [
                "",
                "# Go down to U mode to execute the instruction",
                "RVTEST_GOTO_LOWER_MODE Umode",
                test_data.add_testcase(f"mie_{mie_val}_Umode", coverpoint, covergroup),
                ".option push",
                ".option norvc",
                f"li x{r_cause}, 0                 # sentinel: nonzero => trap was taken",
                "# lr.w to set up reservation",
                f"LA(x{r_temp}, scratch)",
                f"lr.w x{r_temp2}, (x{r_temp})",
                "1:",
                "WRS.NTO",
                f"beqz x{r_cause}, 1b              # retry until the timer interrupt is taken",
                ".option pop",
                "# the handler restored the trap vector and cleared the timer before returning",
                "RVTEST_GOTO_MMODE",
            ]
        )

    lines.extend(_zawrs_resume_trap_handler_u(test_data, r_cause, r_temp, r_mtimecmp, r_scratch))

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch, r_cause])
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

    lines.extend(_wrs_no_mie_helper(test_data, ["U"], covergroup, coverpoint))
    return lines


def _generate_wrs_nto_timeout_tests(test_data: TestData) -> list[str]:
    """Generate WRS.NTO timeout test in U mode

    cross lr instruction to set up reservation.
    mstatus.TW = 1
    mstatus.MIE = 0
    mstatus.SIE = 0
    mie=all 0s to disable interrupts
    execute WRS.NTO in U mode"
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
    lines.extend(_timeout_helper(test_data, coverpoint, covergroup, ["U"], [1], "WRS.NTO"))
    return lines


@add_priv_test_generator("ZawrsU", required_extensions=["U", "Zawrs", "Zalrsc"])
def make_zawrsu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions at user-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        [
            "# No delegation",
            "CSRW(medeleg, zero)",
        ]
    )

    tc.code.extend(_generate_wrs_sto_timeout_tests(test_data))
    tc.code.extend(_generate_wrs_no_res_tests(test_data))
    tc.code.extend(_generate_wrs_resume_tests(test_data))

    # This refers to Spike, QEMU and Whisper:
    # for any coverpoint with TW = 1, the DUTs trigger illegal instruction on WRS.NTO immediately if TW = 1 but sail just treats WRS.NTO as NOP
    # NTO is_nop = true is set for the DUTs since they all treat WRS.NTO as NOP unless TW = 1

    tc.code.extend(_generate_wrs_nto_timeout_tests(test_data))
    tc.code.extend(_generate_wrs_no_mie_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
