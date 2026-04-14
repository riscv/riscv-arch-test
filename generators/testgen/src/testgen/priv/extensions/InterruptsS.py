"""Supervisor-mode interrupt test generator for RISC-V privileged architecture.

This module generates tests for supervisor-mode interrupts (STIP, SSIP, SEIP),
covering both non-delegated (fires in M-mode) and delegated (fires in S-mode)
interrupt handling across a wide range of mideleg, mie, and mstatus configurations.
"""

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_int,
    clr_stimer_mmode,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimer_int,
    set_stimer_mmode,
)
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
    """Generate STIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    and mie = 1s (all interrupt enables), trigger STIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sti"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_sti",
            "Trigger STIP (supervisor timer interrupt)\n"
            "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}\n"
            "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}\n"
            "With mstatus.MIE=0, mie=all 1s",
        ),
        "",
    ]

    # Cross: mideleg x SIE
    for mideleg_val in [0, 1]:
    for mideleg_val in [0, 1]:
        for sie_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]
            sie_name = f"sie_{sie_val}"
            binname = f"{mideleg_name}_{sie_name}"

            # === M-MODE SETUP (safe order) ===
            # === M-MODE SETUP (safe order) ===
            lines.extend(
                [
                    "",
                    "# M-mode setup",
                    "CSRW(mie, zero)",  # 1. Disable ALL interrupts first
                    "csrci mstatus, 8",  # 2. MIE=0
                    "csrci mstatus, 2",  # 3. SIE=0 (clear first)
                    "CSRW(mie, zero)",  # 1. Disable ALL interrupts first
                    "csrci mstatus, 8",  # 2. MIE=0
                    "csrci mstatus, 2",  # 3. SIE=0 (clear first)
                ]
            )

            # Clear timers
            # Clear timers
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # 4. Set mideleg
            # 4. Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",  # Delegate STI+SEI+SSI
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # 5. Enable all interrupts in mie (but MIE still 0)
            # 5. Enable all interrupts in mie (but MIE still 0)
            lines.extend(
                [
                    f"LI(x{r_scratch}, -1)",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # 6. Read STCE (needed for timer functions)
            # 6. Read STCE (needed for timer functions)
            lines.extend(
                [
                    f"CSRR x{r_stce}, menvcfg",
                    "#if __riscv_xlen == 64",
                    f"    srli x{r_stce}, x{r_stce}, 63",
                    "#else",
                    f"    srli x{r_stce}, x{r_stce}, 31",
                    "#endif",
                    f"andi x{r_stce}, x{r_stce}, 0x1",
                ]
            )

            # 7. Set SIE in mstatus (last step before STIP)
            # 7. Set SIE in mstatus (last step before STIP)
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",  # SIE bit
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                ]
            )

            # 8. Set STIP using timer functions
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
            lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))

            lines.extend(
                [
                    f"    LI(x{r_scratch}, 2500)",  # 2500 iterations × 2 instructions = 5000 cycles
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
                ]
            )

            # 9. Enter S-mode
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "nop",
                    "nop",
                    "nop",
                ]
            )

            # 10. Return and cleanup
            # 10. Return and cleanup
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "# Complete state cleanup",
                    "csrci mstatus, 8",  # Clear MIE
                    "csrci mstatus, 2",  # Clear SIE
                    "CSRW(mideleg, zero)",  # Clear delegation
                    "CSRW(mie, zero)",  # Clear all interrupt enables
                ]
            )

            # Clear timer
            # Clear timer
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_mip_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    and mie = 1s (all interrupt enables), trigger SSIP and change to supervisor mode.
    Cross: mideleg x SIE/MIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_ssi_mip",
            "Trigger SSIP (supervisor software interrupt)\n"
            "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE/MIE={0/1}\n"
            "With mstatus.MIE=0 (delegated) or MIE={0/1} (not delegated), mie=all 1s",
        ),
        "",
    ]

    # Cross: mideleg x SIE/MIE
    for mideleg_val in [0, 1]:
        for int_enable_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]

            if mideleg_val == 1:
                # Delegated: cp_trigger_ssi_mip, vary SIE
                coverpoint = "cp_trigger_ssi_mip"
                enable_name = f"sie_{int_enable_val}"
            else:
                # Not delegated: cp_trigger_ssi_mip2, vary MIE
                coverpoint = "cp_trigger_ssi_mip2"
                enable_name = f"mie_{int_enable_val}"

            binname = f"{mideleg_name}_{enable_name}"

            # === M-MODE SETUP (safe order) ===
            lines.extend(
                [
                    "",
                    "# M-mode setup",
                    "RVTEST_GOTO_MMODE",
                    "CSRW(mie, zero)",  # 1. Disable ALL interrupts first
                    "csrci mstatus, 8",  # 2. MIE=0
                    "csrci mstatus, 2",  # 3. SIE=0 (clear first)
                ]
            )

            # Clear interrupts
            lines.extend(clr_stimer_mmode(r_scratch))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Prevent machine timer from firing during test
            lines.extend(
                [
                    f"LA(x{r_temp}, RVMODEL_MTIMECMP_ADDRESS)",
                    f"LI(x{r_scratch}, -1)",
                    f"SREG x{r_scratch}, 0(x{r_temp})",
                ]
            )

            # 4. Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",  # Delegate STI+SEI+SSI
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # 5. Enable all interrupts in mie (but MIE still 0)
            lines.extend(
                [
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Set mip.SSIP",
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mip, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "    nop",
                    "    nop",
                ]
            )

            # 9. Return and cleanup
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    "# Clear mip.SSIP",
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_sip_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger tests via sip.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    write sip.SSIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_ssi_sip"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_ssi_sip",
            "Trigger SSIP via sip.SSIP\nCross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}",
        ),
        "",
    ]

    for mideleg_val in [0, 1]:
        for sie_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]
            sie_name = f"sie_{sie_val}"
            binname = f"{mideleg_name}_{sie_name}"

            lines.extend(
                [
                    "",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",
                ]
            )

            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",  # SIE bit
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, -1)",  # ✅ FIXED: All interrupt enables
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Write sip.SSIP from S-mode",
                    f"LI(x{r_scratch}, 0x02)",
                    f"csrs sip, x{r_scratch}",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "# Clear sip.SSIP",
                    f"csrc sip, x{r_scratch}",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_trigger_sei_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {STI+SEI+SSI},
    and mie = 1s, trigger SEIP via PLIC/EIC and change to supervisor mode.
    Cross: SIE (2 bins - only delegated case since coverpoint has mideleg_ones)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_sei",
            "Trigger SEIP (supervisor external interrupt)\n"
            "Cross: mstatus.SIE={0/1}\n"
            "With mstatus.MIE=0, mideleg=STI+SEI+SSI, mie=all 1s",
        ),
        "",
    ]

    # Only delegated case (coverpoint has mideleg_ones)
    for sie_val in [0, 1]:
        sie_name = f"sie_{sie_val}"
        binname = f"deleg_{sie_name}"

        # === M-MODE SETUP ===
        lines.extend(
            [
                "",
                "# M-mode setup",
                "CSRW(mie, zero)",  # Disable all interrupts
                "csrci mstatus, 8",  # MIE=0
                "csrci mstatus, 2",  # SIE=0
            ]
        )

        # Clear SEIP
        lines.append("RVTEST_CLR_SEXT_INT")

        # Set mideleg (delegate STI+SEI+SSI)
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x222)",
                f"CSRW(mideleg, x{r_scratch})",
            ]
        )

        # Enable all interrupts in mie
        lines.extend(
            [
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Set SIE in mstatus
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x02)",  # SIE bit
                f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
            ]
        )

        # Set SEIP in M-mode using macro
        lines.extend(
            [
                test_data.add_testcase(binname, coverpoint, covergroup),
                "RVTEST_SET_SEXT_INT",
                "nop",
            ]
        )

        # Enter S-mode (SEIP already pending)
        lines.extend(
            [
                "RVTEST_GOTO_LOWER_MODE Smode",
            ]
        )

        # NOPs in S-mode for SEIP=1 coverage
        lines.extend(
            [
                f"    LI(x{r_scratch}, 5000)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
            ]
        )

        # Return and cleanup
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                "# Complete state cleanup",
                "csrci mstatus, 8",  # Clear MIE
                "csrci mstatus, 2",  # Clear SIE
                "CSRW(mideleg, zero)",  # Clear delegation
                "CSRW(mie, zero)",  # Clear all interrupt enables
            ]
        )

        # Clear SEIP
        lines.append("RVTEST_CLR_SEXT_INT")

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_trigger_sei_seip_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger tests via sip write.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {STI+SEI+SSI},
    and mie = 1s, write sip.SEIP and change to supervisor mode.
    Cross: SIE (2 bins - only delegated case)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei_seip"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_sei_seip",
            "Trigger SEIP via sip.SEIP write\n"
            "Cross: mstatus.SIE={0/1}\n"
            "With mstatus.MIE=0, mideleg=STI+SEI+SSI, mie=all 1s",
        ),
        "",
    ]

    # Only delegated case
    for sie_val in [0, 1]:
        sie_name = f"sie_{sie_val}"
        binname = f"deleg_{sie_name}"

        # === M-MODE SETUP ===
        lines.extend(
            [
                "",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",  # MIE=0
                "csrci mstatus, 2",  # SIE=0
            ]
        )

        # Set mideleg (delegate STI+SEI+SSI)
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x222)",
                f"CSRW(mideleg, x{r_scratch})",
            ]
        )

        # Set SIE
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x02)",
                f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
            ]
        )

        # Enable all interrupts in mie
        lines.extend(
            [
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Enter S-mode
        lines.extend(
            [
                "RVTEST_GOTO_LOWER_MODE Smode",
                test_data.add_testcase(binname, coverpoint, covergroup),
                "# Write sip.SEIP from S-mode",
                f"LI(x{r_scratch}, 0x200)",  # SEIP bit (bit 9)
                f"csrs sip, x{r_scratch}",
                "RVTEST_IDLE_FOR_INTERRUPT",
                "# Clear sip.SEIP",
                f"csrc sip, x{r_scratch}",
            ]
        )

        # Return and cleanup
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
            ]
        )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_changingtos_sti_tests(test_data: TestData) -> list[str]:
    """Generate STIP trigger test when changing to S-mode and enabling SIE.

    With mstatus.MIE=0, mstatus.SIE=0, mideleg={STI+SEI+SSI}, mie=1s,
    set STIP, enter S-mode, then write sstatus.SIE=1 to trigger interrupt.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_changingtos_sti"

    r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_changingtos_sti",
            "Trigger STIP when enabling SIE in S-mode\n"
            "Set STIP in M-mode, enter S-mode with SIE=0, then set sstatus.SIE=1",
        ),
        "",
        "# M-mode setup",
        "CSRW(mie, zero)",
        "csrci mstatus, 8",  # MIE=0
        "csrci mstatus, 2",  # SIE=0 (critical: must be 0!)
    ]

    # Clear timers
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg (delegate STI+SEI+SSI)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x222)",
            f"CSRW(mideleg, x{r_scratch})",
        ]
    )

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Read STCE
    lines.extend(
        [
            f"CSRR x{r_stce}, menvcfg",
            "#if __riscv_xlen == 64",
            f"    srli x{r_stce}, x{r_stce}, 63",
            "#else",
            f"    srli x{r_stce}, x{r_stce}, 31",
            "#endif",
            f"andi x{r_stce}, x{r_stce}, 0x1",
        ]
    )

    # Set STIP in M-mode
    lines.append(test_data.add_testcase("changingtos_sti", coverpoint, covergroup))
    lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))

    # Enter S-mode (SIE=0, so no trap yet despite STIP=1)
    lines.extend(
        [
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    # In S-mode with STIP=1, SIE=0
    # Use CSRRS to set sstatus.SIE=1 (interrupt should fire immediately)
    lines.extend(
        [
            f"    LI(x{r_scratch}, 0x02)",  # SIE bit
            f"    csrrs x0, sstatus, x{r_scratch}",  # CSRRS sets SIE=1
            "    nop",
        ]
    )

    # Cleanup
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
        ]
    )

    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_changingtos_ssi_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger test when changing to S-mode and enabling SIE.

    With mstatus.MIE=0, mstatus.SIE=0, mideleg={STI+SEI+SSI}, mie=1s,
    set SSIP, enter S-mode, then write sstatus.SIE=1 to trigger interrupt.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_changingtos_ssi"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_changingtos_ssi",
            "Trigger SSIP when enabling SIE in S-mode\n"
            "Set SSIP in M-mode, enter S-mode with SIE=0, then set sstatus.SIE=1",
        ),
        "",
        f"LI(x{r_scratch}, 0x222)",
        f"CSRW(mideleg, x{r_scratch})",
        f"LI(x{r_scratch}, -1)",
        f"CSRW(mie, x{r_scratch})",
        "csrci mstatus, 8",
        f"LI(x{r_scratch}, 0x20)",
        f"CSRC(mstatus, x{r_scratch})",
        test_data.add_testcase("ssi_changingtos", coverpoint, covergroup),
        f"LI(x{r_scratch}, 0x02)",
        f"CSRS(mip, x{r_scratch})",
        "RVTEST_GOTO_LOWER_MODE Smode",
        "csrsi sstatus, 2",
        "RVTEST_IDLE_FOR_INTERRUPT",
        "RVTEST_GOTO_MMODE",
        "nop",
        f"LI(x{r_scratch}, 0x02)",
        f"CSRC(mip, x{r_scratch})",
    ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_changingtos_sei_tests(test_data: TestData) -> list[str]:
    """Generate SEI interrupt trigger when changing to S-mode."""
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_changingtos_sei"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_changingtos_sei",
            "Trigger SEIP when changing to S-mode",
        ),
        "",
        f"LI(x{r_scratch}, 0x222)",
        f"CSRW(mideleg, x{r_scratch})",
        f"LI(x{r_scratch}, -1)",
        f"CSRW(mie, x{r_scratch})",
        "csrci mstatus, 8",
        f"LI(x{r_scratch}, 0x20)",
        f"CSRC(mstatus, x{r_scratch})",
        test_data.add_testcase("sei_changingtos", coverpoint, covergroup),
        f"LI(x{r_scratch}, 0x200)",
        f"CSRS(mip, x{r_scratch})",
        "RVTEST_GOTO_LOWER_MODE Smode",
        "csrsi sstatus, 2",
        "RVTEST_IDLE_FOR_INTERRUPT",
        "RVTEST_GOTO_MMODE",
        "nop",
        f"LI(x{r_scratch}, 0x200)",
        f"CSRC(mip, x{r_scratch})",
    ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_interrupts_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt tests with walking 1s in mip and mie.

    Tests: mideleg={0, 0x222} × 6 mip × 6 mie = 72 combinations
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_interrupts_s"

    r_mtime, r_stimecmp, r_temp, r_temp2, r_mie_val, r_scratch = test_data.int_regs.get_registers(
        6, exclude_regs=[0, 2]
    )

    lines = [
        comment_banner(
            "cp_interrupts_s",
            "Test interrupts with walking 1s in mip and mie\nmideleg={0, 0x222} × 6 mip × 6 mie = 72 tests",
        ),
        "",
    ]

    # mideleg: 0 (no delegation) or 1 (delegate all S-interrupts)
    for mideleg_val in [0, 1]:
        mideleg_name = ["nodeleg", "deleg"][mideleg_val]

        for mip_name, mip_bit, mip_set, mip_clr, mip_timer in mip_interrupts:
            for mie_name, mie_bit in mie_bits:
                binname = f"{mideleg_name}_{mip_name}_{mie_name}"

                # === M-MODE SETUP ===
                lines.extend(
                    [
                        "",
                        f"# Test: mideleg={mideleg_name}, mip={mip_name}, mie={mie_name}",
                        "CSRW(mie, zero)",
                        "csrci mstatus, 8",  # MIE=0
                        "csrci mstatus, 2",  # SIE=0
                    ]
                )

        if mideleg_val:
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x222)",
                    f"CSRW(mideleg, x{r_scratch})",
                ]
            )
        else:
            lines.append("CSRW(mideleg, zero)")

        # 6 walking 1s in mie: SSIE, STIE, SEIE and combinations
        for s1 in range(6):
            # s1: 0=none, 1=SSIE, 2=STIE, 3=SSIE+STIE, 4=SEIE, 5=SSIE+SEIE
            mie_bits = 0
            if s1 & 1:
                mie_bits |= 0x02  # SSIE
            if s1 & 2:
                mie_bits |= 0x20  # STIE
            if s1 & 4:
                mie_bits |= 0x200  # SEIE

            lines.extend(
                [
                    f"LI(x{r_mie_val}, {mie_bits})",
                    f"CSRW(mie, x{r_mie_val})",
                ]
            )

            # 6 walking 1s in mip: SSIP, STIP, SEIP and combinations
            for s2 in range(6):
                binname = f"{mideleg_name}_mie_{s1:03b}_mip_{s2:03b}"

                lines.extend(
                    [
                        "",
                        "CSRW(mie, zero)",  # Disable while setting interrupts
                        test_data.add_testcase(binname, coverpoint, covergroup),
                    ]
                )

                # Set interrupt pending bits based on s2
                if s2 & 1:  # SSIP
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x02)",
                            f"CSRS(mip, x{r_scratch})",
                        ]
                    )
                if s2 & 2:  # STIP
                    lines.extend(
                        [
                            f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
                            f"LA(x{r_stimecmp}, RVMODEL_STIMECMP_ADDRESS)",
                            *set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2),
                        ]
                    )
                if s2 & 4:  # SEIP
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x200)",
                            f"CSRS(mip, x{r_scratch})",
                        ]
                    )

                # Settling delay
                for _ in range(5):
                    lines.append("    nop")

                # Enable interrupts and enter S-mode
                lines.extend(
                    [
                        f"CSRW(mie, x{r_mie_val})",
                        "RVTEST_GOTO_LOWER_MODE Smode",
                        "RVTEST_IDLE_FOR_INTERRUPT",
                        "RVTEST_GOTO_MMODE",
                        "nop",
                    ]
                )

                # Clear all interrupts
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x202)",  # Clear SSIP and SEIP
                        f"CSRC(mip, x{r_scratch})",
                        *clr_mtimer_int(r_temp, r_stimecmp),
                    ]
                )

    test_data.int_regs.return_registers([r_mtime, r_stimecmp, r_temp, r_temp2, r_mie_val, r_scratch])
    return lines


def _generate_vectored_s_tests(test_data: TestData) -> list[str]:
    """Generate vectored interrupt mode tests.

    Cross of stvec.MODE = 00/01, mstatus.MIE=0, mstatus.SIE = 1, mie = 1s,
    mideleg = {STI+SEI+SSI}, 6 different interrupts walking in mip.
    (2 x 6 = 12 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_vectored_s"

    r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_csr_tmp = test_data.int_regs.get_registers(
        6, exclude_regs=[0, 2]
    )

    lines = [
        comment_banner(
            "cp_priority_both_s",
            "Test interrupt priority with mip == mie\nSame pattern in both mip and mie for priority testing",
        ),
        "",
    ]

    # Test both mideleg values
    for mideleg_val in [0, 1]:
        mideleg_name = ["nodeleg", "deleg"][mideleg_val]

        # S-mode: all 8 patterns (including 000)
        for pattern in range(8):
            ssip = (pattern >> 0) & 1
            stip = (pattern >> 1) & 1
            seip = (pattern >> 2) & 1

            # Set same pattern in both mip and mie
            mie_val = (ssip << 1) | (stip << 5) | (seip << 9)

            binname = f"{mideleg_name}_s_both_{pattern:03b}"

        lines.extend(
            [
                "",
                f"# stvec.MODE = {mode:02b} ({mode_name})",
                "# Setup: delegate all S-interrupts, enable all",
                f"LI(x{r_scratch}, 0x222)",
                f"CSRW(mideleg, x{r_scratch})",
                "csrci mstatus, 8",  # MIE=0
                f"LI(x{r_scratch}, 0x20)",  # SPIE=1 (SIE will be 1 in S-mode)
                f"CSRS(mstatus, x{r_scratch})",
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
                "# Set stvec.MODE",
                "csrci stvec, 3",
                f"csrsi stvec, {mode}",
            ]
        )

        # 6 interrupt types: SSIP, STIP, SEIP, SSIP+STIP, SSIP+SEIP, STIP+SEIP
        for s2 in range(6):
            int_name = f"int_{s2:03b}"
            binname = f"{mode_name}_{int_name}"

            lines.extend(
                [
                    "",
                    "CSRW(mie, zero)",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                ]
            )

            # Trigger interrupts based on s2
            if s2 & 1:  # SSIP
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x02)",
                        f"CSRS(mip, x{r_scratch})",
                    ]
                )
            if s2 & 2:  # STIP
                lines.extend(
                    [
                        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
                        f"LA(x{r_stimecmp}, RVMODEL_STIMECMP_ADDRESS)",
                        *set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2),
                    ]
                )
            if s2 & 4:  # SEIP
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x200)",
                        f"CSRS(mip, x{r_scratch})",
                    ]
                )

            # Settling delay
            for _ in range(5):
                lines.append("    nop")

            # Enable all S-interrupts and enter S-mode
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x222)",
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x202)",
                    f"CSRC(mip, x{r_scratch})",
                    *clr_mtimer_int(r_temp, r_stimecmp),
                ]
            )

        # Restore stvec.MODE to direct
        lines.append("csrci stvec, 1")

    test_data.int_regs.return_registers([r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_csr_tmp])
    return lines


@add_priv_test_generator("InterruptsS", required_extensions=["Sm", "S", "I", "Zicsr"])
def make_interruptss_s(test_data: TestData) -> list[str]:
    """Generate supervisor-mode interrupt tests.

    Covers STIP, SSIP, and SEIP across S-mode, M-mode, and U-mode scenarios,
    including trigger conditions, delegation, priority, vectoring, and WFI.
    Individual test groups are enabled incrementally as they are validated.
    """
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "InterruptsS_S",
            "Supervisor-mode interrupt tests\nTests S-mode interrupts (STIP, SSIP, SEIP) with M→S delegation",
        ),
        "",
        "# Initial setup - clear mideleg (no U-mode delegation)",
        "CSRW(mideleg, zero)",
        f"LI(x{r_temp}, 0x200000)",  # Clear TW bit
        f"CSRC(mstatus, x{r_temp})",
        "",
    ]

    test_data.int_regs.return_registers([r_temp])

    # -----------------------------------------------------------------------
    # S-mode interrupt tests (STIP, SSIP, SEIP with mideleg)
    # -----------------------------------------------------------------------
    lines.extend(_generate_trigger_sti_tests(test_data))
    lines.extend(_generate_trigger_ssi_mip_tests(test_data))
    lines.extend(_generate_trigger_ssi_sip_tests(test_data))
    lines.extend(_generate_trigger_sei_tests(test_data))
    lines.extend(_generate_trigger_sei_seip_tests(test_data))
    lines.extend(_generate_changingtos_sti_tests(test_data))
    lines.extend(_generate_changingtos_ssi_tests(test_data))
    lines.extend(_generate_changingtos_sei_tests(test_data))
    lines.extend(_generate_interrupts_s_tests(test_data))
    lines.extend(_generate_vectored_s_tests(test_data))
    lines.extend(_generate_priority_mip_s_tests(test_data))
    lines.extend(_generate_priority_mie_s_tests(test_data))
    lines.extend(_generate_priority_both_s_tests(test_data))
    lines.extend(_generate_priority_mideleg_m_tests(test_data))
    lines.extend(_generate_priority_mideleg_s_tests(test_data))
    lines.extend(_generate_wfi_s_tests(test_data))
    lines.extend(_generate_wfi_timeout_s_tests(test_data))

    # -----------------------------------------------------------------------
    # M-mode interrupt tests (non-delegated and delegated S-interrupts)
    # -----------------------------------------------------------------------
    lines.extend(_generate_interrupts_m_tests(test_data))
    lines.extend(_generate_vectored_m_tests(test_data))
    lines.extend(_generate_priority_mip_m_tests(test_data))
    lines.extend(_generate_priority_mie_m_tests(test_data))
    lines.extend(_generate_wfi_m_tests(test_data))
    lines.extend(_generate_trigger_mti_m_tests(test_data))
    lines.extend(_generate_trigger_ssi_sip_m_tests(test_data))
    lines.extend(_generate_trigger_msi_m_tests(test_data))
    lines.extend(_generate_trigger_mei_m_tests(test_data))
    lines.extend(_generate_trigger_sti_m_tests(test_data))
    lines.extend(_generate_trigger_ssi_m_tests(test_data))
    lines.extend(_generate_trigger_sei_m_tests(test_data))
    lines.extend(_generate_sei_interaction_tests(test_data))
    lines.extend(_generate_global_ie_tests(test_data))

    # -----------------------------------------------------------------------
    # U-mode interrupt tests
    # -----------------------------------------------------------------------
    lines.extend(_generate_user_mti_tests(test_data))
    lines.extend(_generate_user_msi_tests(test_data))
    lines.extend(_generate_user_mei_tests(test_data))
    lines.extend(_generate_user_sei_tests(test_data))
    lines.extend(_generate_wfi_u_tests(test_data))
    lines.extend(_generate_wfi_timeout_u_tests(test_data))

    return lines
