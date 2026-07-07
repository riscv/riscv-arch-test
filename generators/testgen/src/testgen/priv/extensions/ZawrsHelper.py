##################################
# priv/extensions/ZawrsHelper.py
#
# Shared Zawrs tests generation
# ellyu@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Common Zawrs test generation"""

from testgen.asm.helpers import write_sigupd
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_int,
    clr_stimer_mmode,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimer_int_soon_sstc,
    set_stimer_mmode,
)
from testgen.data.state import TestData


def _zawrs_resume_trap_handler_su(
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
        "zawrs_resume_trap_handler_m:",
        f"csrr x{r_cause}, mcause          # nonzero => trap fired (loop sentinel) + SIGUPD value",
        write_sigupd(r_cause, test_data),
        *clr_mtimer_int(r_temp, r_mtimecmp),
        f"csrw mtvec, x{r_scratch}         # restore framework M trap vector before returning",
        "mret                             # return to instruction after WRS.NTO",
        ".option pop",
        "4:",
        "",
    ]

    lines.extend(
        [
            "#ifdef S_SUPPORTED",
            "# ---- S-mode WRS resume handler (S-mode / Sstc tests) ----",
            "j 5f                             # skip handler in straight-line code",
            ".option push",
            ".option norvc",
            ".align 2                         # direct-mode stvec target must be 4-byte aligned",
            "zawrs_resume_trap_handler_s:",
            f"csrr x{r_cause}, scause          # nonzero => trap fired (loop sentinel) + SIGUPD value",
            write_sigupd(r_cause, test_data),
            "# Clear supervisor timer (Sstc); STCE=1 in a reg so clr_stimer_int takes the Sstc path",
            f"LI(x{r_cause}, 1)",
            *clr_stimer_int(r_temp, r_mtimecmp, r_mtimecmp, r_cause),
            "sret                             # return to instruction after WRS.NTO",
            ".option pop",
            "5:",
            "#endif",
            "",
        ]
    )
    return lines


def _exception_helper(test_data: TestData, r_cause: int, r_scratch: int) -> list[str]:
    """Shared WRS illegal-instruction trap handlers.

    Each handler records the trap cause in r_cause (nonzero => trap fired: the
    loop sentinel) and restores the framework trap vector from r_scratch before
    returning. The SIGUPD is done by the caller after the retry loop (where a
    valid per-testcase label is in scope), so both the M and S paths are covered.
    """
    lines = []
    lines.extend(
        [
            "# ---- M-mode WRS illegal-instruction handler ----",
            "j 4f                             # skip handler in straight-line code",
            ".option push",
            ".option norvc",
            ".align 2                         # direct-mode mtvec target must be 4-byte aligned",
            "zawrs_exceptions_handler_m:",
            f"csrr x{r_cause}, mcause          # nonzero => trap fired (loop sentinel)",
            f"csrw mtvec, x{r_scratch}         # restore framework M trap vector before returning",
            "mret                             # return to instruction after WRS.NTO",
            ".option pop",
            "4:",
            "",
        ]
    )
    lines.extend(
        [
            "#ifdef S_SUPPORTED",
            "# ---- S-mode WRS illegal-instruction handler ----",
            "j 5f                             # skip handler in straight-line code",
            ".option push",
            ".option norvc",
            ".align 2",
            "zawrs_exceptions_handler_s:",
            f"csrr x{r_cause}, scause          # nonzero => trap fired (loop sentinel)",
            f"csrw stvec, x{r_scratch}         # restore framework S trap vector before returning",
            "sret                             # return to instruction after WRS.NTO",
            ".option pop",
            "5:",
            "#endif",
            "",
        ]
    )

    return lines


def _timeout_helper(
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    priv_list: list[str],
    tw_list: list[int],
    wrs_op: str,
    r_cause: int,
    r_scratch: int,
) -> list[str]:
    """helper function for generating timeout tests.

    WRS.NTO paths trap into the shared WRS exception handler (emitted once by
    _exception_helper); r_cause/r_scratch must be the SAME registers passed there.
    WRS.STO never traps, so it neither installs a handler nor spins.
    """

    is_nto = wrs_op == "WRS.NTO"
    r_temp, r_temp2 = test_data.int_regs.get_registers(2)

    lines = []

    if coverpoint == "cp_wrs_nto_timeout_h":
        lines.append("#ifdef H_SUPPORTED")
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

            # WRS.NTO with TW=1 below M mode traps illegal-instruction on targets
            # that define UDB_ZAWRS_NTO_IS_NOP; install the shared handler where the
            # trap is delivered (S if supported, else M), saving the framework vector.
            if is_nto:
                lines.extend(
                    [
                        "#ifdef UDB_ZAWRS_NTO_IS_NOP",
                        "#ifdef S_SUPPORTED",
                        "# trap delegated to S: install S handler, save framework stvec",
                        f"LA(x{r_temp}, zawrs_exceptions_handler_s)",
                        f"csrrw x{r_scratch}, stvec, x{r_temp}",
                        "#else",
                        "# no S mode: trap taken in M; install M handler, save framework mtvec",
                        f"LA(x{r_temp}, zawrs_exceptions_handler_m)",
                        f"csrrw x{r_scratch}, mtvec, x{r_temp}",
                        "#endif",
                        "#endif",
                    ]
                )

            lines.extend(
                [
                    f"# Go down to {priv_mode} mode to execute the instruction",
                    f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                    "# lr.w to set up reservation",
                    f"LA(x{r_temp2}, scratch)",
                    f"lr.w x{r_temp}, (x{r_temp2})",
                    test_data.add_testcase(f"tw_{tw_val}_{priv_mode}_{wrs_op}", coverpoint, covergroup),
                ]
            )

            if is_nto:
                # Retry WRS.NTO until the illegal-instruction trap fires: the shared
                # handler records the cause in r_cause and SIGUPDs it. Only on targets
                # that trap (UDB_ZAWRS_NTO_IS_NOP); elsewhere WRS.NTO is a NOP and
                # looping would spin forever.
                lines.extend(
                    [
                        "#ifdef UDB_ZAWRS_NTO_IS_NOP",
                        ".option push",
                        ".option norvc",
                        f"li x{r_cause}, 0                 # sentinel: nonzero => trap was taken",
                        "1:",
                        "#endif",
                        f"{wrs_op}",
                        "#ifdef UDB_ZAWRS_NTO_IS_NOP",
                        f"beqz x{r_cause}, 1b              # retry until the illegal-instruction trap is taken",
                        ".option pop",
                        write_sigupd(r_cause, test_data),
                        "#endif",
                    ]
                )
            else:
                lines.append(f"{wrs_op}")

            lines.append("RVTEST_GOTO_MMODE")
            if coverpoint == "cp_wrs_nto_timeout_h":
                lines.append("#endif")
    if coverpoint == "cp_wrs_nto_timeout_h":
        lines.append("#endif")
    test_data.int_regs.return_registers([r_temp, r_temp2])
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


def _wrs_resume_helper(test_data: TestData, priv_list: list[str], covergroup: str) -> list[str]:
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

    ######################################
    coverpoint = "cp_wrs_resume"
    ######################################

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch, r_cause = test_data.int_regs.get_registers(7)

    lines = []

    for priv_mode in priv_list:
        for sie_val in [0, 1]:
            for mie_val in [0, 1]:
                # S-mode with SIE=0 leaves the timer interrupt masked, so no trap
                # fires: we let WRS simply complete and pass. Every other case
                # (all U-mode, and S-mode with SIE=1) is expected to trap.
                expect_trap = not (priv_mode == "S" and sie_val == 0)

                if priv_mode == "S":
                    lines.append("#ifdef S_SUPPORTED")
                    lines.append("#ifdef SSTC_SUPPORTED")

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
                        "#ifdef S_SUPPORTED",
                        "# Set mie.STIE and mstatus.SIE (S-mode delivery / coverage sampling)",
                        f"LI(x{r_temp}, 0x20)",
                        f"CSRS(mie, x{r_temp})",
                        f"# mstatus.SIE = {sie_val}",
                        f"{'csrsi' if sie_val else 'csrci'} mstatus, 2",
                        "#endif",
                        "",
                    ]
                )

                if priv_mode == "U":
                    # U-mode: machine timer, taken in M mode. The M handler runs
                    # in M and restores mtvec itself (U-mode cannot write mtvec).
                    lines.extend(
                        [
                            "# U-mode uses the machine timer (taken in M); install M handler in mtvec",
                            f"# save old mtvec in x{r_scratch}",
                            f"LA(x{r_temp}, zawrs_resume_trap_handler_m)",
                            f"csrrw x{r_scratch}, mtvec, x{r_temp}",
                            *set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_cause),
                        ]
                    )
                else:  # priv_mode == "S" (inside S_SUPPORTED / SSTC_SUPPORTED)
                    # S-mode: Sstc supervisor timer, taken in S mode.
                    lines.extend(
                        [
                            "# S-mode uses the Sstc supervisor timer (taken in S); install S handler in stvec",
                            f"# save old stvec in x{r_scratch}",
                            f"LA(x{r_temp}, zawrs_resume_trap_handler_s)",
                            f"csrrw x{r_scratch}, stvec, x{r_temp}",
                            *set_stimer_int_soon_sstc(r_mtime, r_temp, r_temp2, r_temp3, r_cause),
                        ]
                    )

                # ---- Execute WRS.NTO in the lower mode ----
                lines.extend(
                    [
                        "",
                        f"# Go down to {priv_mode} mode to execute the instruction",
                        f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                        test_data.add_testcase(f"mie_{mie_val}_sie_{sie_val}_{priv_mode}", coverpoint, covergroup),
                        ".option push",
                        ".option norvc",
                        f"li x{r_cause}, 0                 # sentinel: nonzero => trap was taken",
                        "# lr.w to set up reservation",
                        f"LA(x{r_temp}, scratch)",
                        f"lr.w x{r_temp2}, (x{r_temp})",
                        "1:",
                        "WRS.NTO",
                    ]
                )

                if expect_trap:
                    lines.extend(
                        [
                            f"beqz x{r_cause}, 1b              # retry until the timer interrupt is taken",
                            ".option pop",
                            "# the handler restored the trap vector and cleared the timer before returning",
                            "RVTEST_GOTO_MMODE",
                        ]
                    )
                else:
                    # priv S, SIE=0: no trap. We are still in S mode here, so
                    # restore stvec and disarm the Sstc timer before returning.
                    lines.extend(
                        [
                            ".option pop",
                            "# SIE=0 masks the timer: no trap taken -> pass",
                            f"csrw stvec, x{r_scratch}         # restore framework S trap vector (no trap did it)",
                            f"LI(x{r_cause}, 1)                # STCE=1 (Sstc present)",
                            *clr_stimer_int(r_temp, r_temp2, r_scratch, r_cause),
                            "RVTEST_GOTO_MMODE",
                        ]
                    )

                if priv_mode == "S":
                    lines.append("#endif")  # SSTC_SUPPORTED
                    lines.append("#endif")  # S_SUPPORTED
                lines.append("")

    lines.extend(_zawrs_resume_trap_handler_su(test_data, r_cause, r_temp, r_mtimecmp, r_scratch))

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_temp3, r_scratch, r_cause])
    return lines


def _wrs_no_mie_helper(
    test_data: TestData,
    priv_list: list[str],
    covergroup: str,
    coverpoint: str,
    r_cause: int,
    r_scratch: int,
) -> list[str]:
    """Generate wrs tests with mie = all 0s.

    r_cause and r_scratch must be the SAME registers passed to _exception_helper
    (called once at the start of the test): the shared handler records the trap
    cause in r_cause and restores the framework trap vector from r_scratch.
    """

    r_temp, r_temp2, r_mtime, r_mtimecmp = test_data.int_regs.get_registers(4)

    lines = []

    for wrs_ops in ["WRS.STO", "WRS.NTO"]:
        is_nto = wrs_ops == "WRS.NTO"
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

            # WRS.NTO with TW=1 below M mode takes an illegal-instruction trap on
            # targets that define UDB_ZAWRS_NTO_IS_NOP (the DUTs, which trap when
            # TW=1); other targets (Sail) treat it as a plain NOP, so we neither
            # install a handler nor spin. Install the handler where the trap is
            # delivered: S mode when S is supported (illegal-instruction is
            # delegated in the boot code), otherwise M mode.
            if is_nto:
                lines.extend(
                    [
                        "#ifdef UDB_ZAWRS_NTO_IS_NOP",
                        "#ifdef S_SUPPORTED",
                        "# trap delegated to S: install S handler, save framework stvec",
                        f"LA(x{r_temp}, zawrs_exceptions_handler_s)",
                        f"csrrw x{r_scratch}, stvec, x{r_temp}",
                        "#else",
                        "# no S mode: trap taken in M; install M handler, save framework mtvec",
                        f"LA(x{r_temp}, zawrs_exceptions_handler_m)",
                        f"csrrw x{r_scratch}, mtvec, x{r_temp}",
                        "#endif",
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
                ]
            )

            if is_nto:
                # Retry WRS.NTO until the illegal-instruction trap fires: the shared
                # handler records the cause in r_cause (nonzero => trap taken) and
                # SIGUPDs it. Only on targets that trap (UDB_ZAWRS_NTO_IS_NOP);
                # elsewhere WRS.NTO is a NOP and looping would spin forever.
                lines.extend(
                    [
                        "#ifdef UDB_ZAWRS_NTO_IS_NOP",
                        ".option push",
                        ".option norvc",
                        f"li x{r_cause}, 0                 # sentinel: nonzero => trap was taken",
                        "1:",
                        "#endif",
                        f"{wrs_ops}",
                        "#ifdef UDB_ZAWRS_NTO_IS_NOP",
                        f"beqz x{r_cause}, 1b              # retry until the illegal-instruction trap is taken",
                        ".option pop",
                        write_sigupd(r_cause, test_data),
                        "#endif",
                    ]
                )
            else:
                lines.append(f"{wrs_ops}")

            lines.append("")

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
