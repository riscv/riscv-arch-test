##################################
# priv/extensions/interruptsS.py
#
# InterruptsS privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################


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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_sti",
            _generate_trigger_sti_tests.__doc__,
        ),
        "",
    ]

    lines.append("# Cross: mideleg x SIE")
    for mideleg_val in [0, 1]:
        for sie_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]
            sie_name = f"sie_{sie_val}"
            binname = f"{mideleg_name}_{sie_name}"

            lines.extend(
                [
                    "# === M-MODE SETUP (safe order) ===",
                    "",
                    "# M-mode setup",
                    "CSRW(mie, zero) # 1. Disable ALL interrupts first",
                    "csrci mstatus, 8 # 2. MIE=0",
                    "csrci mstatus, 2 # 3. SIE=0 (clear first)",
                ]
            )

            lines.append("# Clear timers")
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            lines.append("# 4. Set mideleg")
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222) # Delegate STI+SEI+SSI",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            lines.extend(
                [
                    "# 5. Enable all interrupts in mie (but MIE still 0)",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# 6. Read STCE (needed for timer functions)",
                    f"CSRR x{r_stce}, menvcfg",
                    "#if __riscv_xlen == 64",
                    f"    srli x{r_stce}, x{r_stce}, 63",
                    "#else",
                    f"    srli x{r_stce}, x{r_stce}, 31",
                    "#endif",
                    f"andi x{r_stce}, x{r_stce}, 0x1",
                ]
            )

            lines.extend(
                [
                    "# 7. Set SIE in mstatus (last step before STIP)",
                    f"LI(x{r_scratch}, 0x02)  # SIE bit",
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                ]
            )

            lines.append("# 8. Set STIP: stimecmp=0 fires immediately (mtime>0 always); legacy: direct mip write")
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
            lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))

            lines.extend(
                [
                    "# 9. Enter S-mode (STIP already pending)",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "nop",
                    "nop",
                    "nop",
                    "nop",
                ]
            )

            lines.extend(
                [
                    "# 10. Return and cleanup",
                    "RVTEST_GOTO_MMODE",
                    "# Complete state cleanup",
                    "csrci mstatus, 8 # Clear MIE",
                    "csrci mstatus, 2 # Clear SIE",
                    "CSRW(mideleg, zero) # Clear delegation",
                    "CSRW(mie, zero) # Clear all interrupt enables",
                ]
            )

            lines.append("# Clear timer")
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, r_stce))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_mip_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    and mie = 1s (all interrupt enables), trigger SSIP and change to supervisor mode.
    Cross: mideleg x SIE/MIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_ssi_mip",
            _generate_trigger_ssi_mip_tests.__doc__,  # mismatch with testplan
        ),
        "",
    ]

    lines.append("# Cross: mideleg x SIE/MIE")
    for mideleg_val in [0, 1]:
        for int_enable_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]

            if mideleg_val == 1:
                # Delegated: cp_trigger_ssi_mip, vary SIE
                coverpoint = "cp_trigger_ssi_mip"
                enable_name = f"sie_{int_enable_val}"
            else:
                # Not delegated: cp_trigger_ssi_mip_m, vary MIE
                coverpoint = "cp_trigger_ssi_mip_m"
                enable_name = f"mie_{int_enable_val}"

            binname = f"{mideleg_name}_{enable_name}"

            lines.extend(
                [
                    "# === M-MODE SETUP (safe order) ===",
                    "",
                    "# M-mode setup",
                    "RVTEST_GOTO_MMODE",
                    "CSRW(mie, zero) # 1. Disable ALL interrupts first",
                    "csrci mstatus, 8 # 2. MIE=0",
                    "csrci mstatus, 2 # 3. SIE=0 (clear first)",
                ]
            )

            lines.append("# Clear timer interrupts")
            lines.extend(clr_stimer_mmode(r_scratch))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            lines.append("# 4. Set mideleg")
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222) # Delegate STI+SEI+SSI",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            lines.append("# 6. Set SIE (delegated) or MIE (not delegated)")
            if mideleg_val == 1:
                lines.extend(
                    [
                        "# Delegated: set SIE",
                        f"LI(x{r_scratch}, 0x02) # SIE bit",
                        f"{'CSRS' if int_enable_val else 'CSRC'}(mstatus, x{r_scratch})",
                    ]
                )
            else:
                lines.append("# Not delegated: set MIE if MIE should be 1")
                if int_enable_val:
                    lines.append("csrsi mstatus, 8")

            lines.extend(
                [
                    "# 5. Enable all interrupts in mie",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            lines.append("# 7. Set SSIP by writing to mip.SSIP")
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2) # SSIP bit",
                    f"CSRS(mip, x{r_scratch}) # Set via CSR write",
                    "nop",
                    "nop",
                ]
            )

            lines.extend(
                [
                    "# 8. Enter S-mode (interrupt should trigger immediately after if not delegated or if delegated and SIE= 1)",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "    nop",
                    "    nop",
                ]
            )

            lines.extend(
                [
                    "# 9. Return and cleanup",
                    "RVTEST_GOTO_MMODE",
                    "csrci mstatus, 8 # Clear MIE",
                    "csrci mstatus, 2 # Clear SIE",
                    "CSRW(mideleg, zero) # Clear delegation",
                    "CSRW(mie, zero) # Clear all interrupt enables",
                    f"LI(x{r_scratch}, 0x2)",
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

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_trigger_ssi_sip",
            _generate_trigger_ssi_sip_tests.__doc__,
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
                    "# Clearing mie and mstatus.MIE",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",
                ]
            )

            if mideleg_val:
                lines.extend(
                    [
                        "# Delegated case - set mideleg",
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("# Not delegated case - clear mideleg")
                lines.append("CSRW(mideleg, zero)")

            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02) # SIE bit",
                    f"# {'set' if sie_val else 'clear'} mstatus.SIE",
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                    "",
                    "# enable all interrupts in mie",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Write sip.SSIP from S-mode",
                    f"LI(x{r_scratch}, 0x02)",
                    f"csrs sip, x{r_scratch}",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
                    "# Clear sip.SSIP",
                    f"LI(x{r_scratch}, 0x02) # SIE bit",
                    f"csrc sip, x{r_scratch}",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_trigger_sei_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0/STI+SEI+SSI},
    and mie = 1s, trigger SEIP via PLIC/EIC and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei"

    r_scratch, r_temp, r_stimecmp = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            "cp_trigger_sei",
            _generate_trigger_sei_tests.__doc__,
        ),
        "",
    ]

    for mideleg_val in [0, 1]:
        for sie_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]
            sie_name = f"sie_{sie_val}"
            binname = f"{mideleg_name}_{sie_name}"
            effective_coverpoint = coverpoint if mideleg_val else "cp_trigger_sei_m"

            lines.extend(
                [
                    "# === M-MODE SETUP ===",
                    "",
                    "# M-mode setup",
                    "RVTEST_GOTO_MMODE",
                    "CSRW(mie, zero) # Disable all interrupts",
                    "csrci mstatus, 8 # MIE=0",
                    "csrci mstatus, 2 # SIE=0",
                ]
            )

            lines.append("# Clear timer interrupts")
            lines.extend(clr_stimer_mmode(r_scratch))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            lines.append("# Clear SEIP")
            lines.append("RVTEST_CLR_SEXT_INT")

            lines.append("# Write mideleg based on the bin")
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
                    "# Enable all interrupts in mie",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Set SIE in mstatus",
                    f"LI(x{r_scratch}, 0x02)  # SIE bit",
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    test_data.add_testcase(binname, effective_coverpoint, covergroup),
                    "# Set SEIP in M-mode using macro",
                    "RVTEST_SET_SEXT_INT",
                    "nop",
                ]
            )

            lines.extend(
                [
                    "# Enter S-mode (SEIP already pending)",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                ]
            )

            lines.extend(
                [
                    "# NOPs in S-mode — SEIP fires immediately from macro, no spin needed",
                    "    nop",
                    "    nop",
                    "    nop",
                    "    nop",
                ]
            )

            lines.extend(
                [
                    "# Return and cleanup",
                    "RVTEST_GOTO_MMODE",
                    "# Complete state cleanup",
                    "csrci mstatus, 8 # Clear MIE",
                    "csrci mstatus, 2 # Clear SIE",
                    "CSRW(mideleg, zero) # Clear delegation",
                    "CSRW(mie, zero) # Clear all interrupt enables",
                ]
            )

            lines.append("# Clear SEIP")
            lines.append("RVTEST_CLR_SEXT_INT")

    test_data.int_regs.return_registers([r_scratch, r_temp, r_stimecmp])
    return lines


def _generate_trigger_sei_seip_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger tests via sip write.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {STI+SEI+SSI},
    and mie = 1s, write mip.SEIP and change to supervisor mode.
    Cross: SIE (2 bins - only delegated case)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei_seip"

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_trigger_sei_seip",
            _generate_trigger_sei_seip_tests.__doc__,  # mismatch with testplan
        ),
        "",
    ]

    lines.append("# Only delegated case")
    for sie_val in [0, 1]:
        sie_name = f"sie_{sie_val}"
        binname = f"deleg_{sie_name}"

        lines.extend(
            [
                "# === M-MODE SETUP ===",
                "",
                "CSRW(mie, zero)",
                "csrci mstatus, 8 # MIE=0",
                "csrci mstatus, 2 # SIE=0",
            ]
        )

        lines.extend(
            [
                "# Set mideleg (delegate STI+SEI+SSI)",
                f"LI(x{r_scratch}, 0x222)",
                f"CSRW(mideleg, x{r_scratch})",
            ]
        )

        lines.extend(
            [
                "# Set SIE",
                f"LI(x{r_scratch}, 0x02)",
                f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
            ]
        )

        lines.extend(
            [
                "# Enable all interrupts in mie",
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        lines.extend(
            [
                test_data.add_testcase(binname, coverpoint, covergroup),
                "# Write mip.SEIP from M-mode",
                f"LI(x{r_scratch}, 0x200) # SEIP bit (bit 9)",
                f"csrs mip, x{r_scratch}",
                "# Enter S-mode",
                "RVTEST_GOTO_LOWER_MODE Smode",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
            ]
        )

        lines.extend(
            [
                "# Return and cleanup",
                "RVTEST_GOTO_MMODE",
                "# Clear mip.SEIP",
                f"csrc mip, x{r_scratch}",
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_changingtos_sti",
            _generate_changingtos_sti_tests.__doc__,
        ),
        "",
        "# M-mode setup",
        "CSRW(mie, zero)",
        "csrci mstatus, 8 # MIE=0",
        "csrci mstatus, 2 # SIE=0 (critical: must be 0!)",
    ]

    lines.append("# Clear timer interrupt")
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.extend(
        [
            "# Set mideleg (delegate STI+SEI+SSI)",
            f"LI(x{r_scratch}, 0x222)",
            f"CSRW(mideleg, x{r_scratch})",
        ]
    )

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.extend(
        [
            "# Read STCE",
            f"CSRR x{r_stce}, menvcfg",
            "#if __riscv_xlen == 64",
            f"    srli x{r_stce}, x{r_stce}, 63",
            "#else",
            f"    srli x{r_stce}, x{r_stce}, 31",
            "#endif",
            f"andi x{r_stce}, x{r_stce}, 0x1",
        ]
    )

    lines.append("# Set STIP in M-mode")
    lines.append(test_data.add_testcase("changingtos_sti", coverpoint, covergroup))
    lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))

    lines.extend(
        [
            "# Enter S-mode (SIE=0, so no trap yet despite STIP=1)",
            "RVTEST_GOTO_LOWER_MODE Smode",
        ]
    )

    # In S-mode with STIP=1, SIE=0
    lines.extend(
        [
            "# Use CSRRS to set sstatus.SIE=1 (interrupt should fire immediately)",
            f"    LI(x{r_scratch}, 0x02) # SIE bit",
            f"    csrrs x0, sstatus, x{r_scratch} # CSRRS sets SIE=1",
            "    nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
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

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_trigger_changingtos_ssi",
            _generate_changingtos_ssi_tests.__doc__,
        ),
        "",
        "# M-mode setup",
        "CSRW(mie, zero)",
        "csrci mstatus, 8 # MIE=0",
        "csrci mstatus, 2 # SIE=0 (critical!)",
    ]

    lines.extend(
        [
            "# Clear SSIP",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
        ]
    )

    lines.extend(
        [
            "# Set mideleg (delegate STI+SEI+SSI)",
            f"LI(x{r_scratch}, 0x222)",
            f"CSRW(mideleg, x{r_scratch})",
        ]
    )

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.extend(
        [
            "# Set SSIP in M-mode",
            test_data.add_testcase("changingtos_ssi", coverpoint, covergroup),
            f"LI(x{r_scratch}, 0x2) # SSIP bit",
            f"CSRS(mip, x{r_scratch}) # Set via CSR write",
            "nop",
        ]
    )

    lines.append("# Enter S-mode (SIE=0, so no trap yet despite SSIP=1)")
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    lines.extend(
        [
            "# In S-mode: set sstatus.SIE=1 (interrupt should fire immediately after)",
            f"    LI(x{r_scratch}, 0x02) # SIE bit",
            f"    csrrs x0, sstatus, x{r_scratch} # Set SIE=1",
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
        ]
    )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_changingtos_sei_tests(test_data: TestData) -> list[str]:
    """Generate SEI interrupt trigger when changing to S-mode.

    with mstatus.MIE=0, mstatus.SIE=0, mideleg={STI+SEI+SSI}, mie=1s, set mip.SEIP,
    then change to supervisor mode, then write sstatus.SIE=1
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_changingtos_sei"

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_trigger_changingtos_sei",
            _generate_changingtos_sei_tests.__doc__,
        ),
        "",
        "# M-mode setup",
        "CSRW(mie, zero)",
        "csrci mstatus, 8 # MIE=0",
        "csrci mstatus, 2 # SIE=0",
        "# Set mideleg",
        f"LI(x{r_scratch}, 0x222)",
        f"CSRW(mideleg, x{r_scratch})",
        "",
        "# Enable all interrupts in mie",
        f"LI(x{r_scratch}, -1)",
        f"CSRW(mie, x{r_scratch})",
        "",
        test_data.add_testcase("sei_changingtos", coverpoint, covergroup),
        "# set mip.SEIP",
        f"LI(x{r_scratch}, 0x200)",
        f"CSRS(mip, x{r_scratch})",
        "",
        "# Go down to S mode",
        "RVTEST_GOTO_LOWER_MODE Smode",
        "# set SIE in sstatus (interrupt should fire immediately & no need to idle for interrupt)",
        "csrsi sstatus, 2",
        "RVTEST_GOTO_MMODE",
        "nop",
        "# clear mip.SEIP",
        f"LI(x{r_scratch}, 0x200)",
        f"CSRC(mip, x{r_scratch})",
    ]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_interrupts_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt tests with walking 1s in mip and mie.

    Cross of mstatus.MIE = 0, mstatus.SIE = 1, mtvec.MODE = 00, mideleg={0/STI+SEI+SSI},
    6 walking 1s in mie, 6 walking 1s in mip, change to supervisor mode
    Tests: mideleg={0, 0x222} × 6 mip × 6 mie = 72 combinations
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_interrupts_s"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_interrupts_s",
            _generate_interrupts_s_tests.__doc__,
        ),
        "",
    ]

    # ALL 6 interrupt pending bits
    mip_interrupts = [
        ("ssip", 0x002, f"SET_SSW_INT(x{r_temp}, x{r_temp2})", f"CLR_SSW_INT(x{r_temp}, x{r_temp2})", False),
        ("msip", 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("stip", 0x020, None, None, True),
        ("mtip", 0x080, None, None, True),
        ("seip", 0x200, f"SET_SEXT_INT(x{r_temp}, x{r_temp2})", f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})", False),
        ("meip", 0x800, "RVTEST_SET_MEXT_INT", "RVTEST_CLR_MEXT_INT", False),
    ]

    # ALL 6 interrupt enables
    mie_bits = [
        ("ssie", 0x002),
        ("msie", 0x008),
        ("stie", 0x020),
        ("mtie", 0x080),
        ("seie", 0x200),
        ("meie", 0x800),
    ]

    lines.append("# Test BOTH mideleg values")
    for mideleg_val in [0, 1]:
        mideleg_name = ["nodeleg", "deleg"][mideleg_val]

        for mip_name, mip_bit, mip_set, mip_clr, mip_timer in mip_interrupts:
            for mie_name, mie_bit in mie_bits:
                binname = f"{mideleg_name}_{mip_name}_{mie_name}"

                lines.extend(
                    [
                        "# === M-MODE SETUP ===",
                        "",
                        f"# Test: mideleg={mideleg_name}, mip={mip_name}, mie={mie_name}",
                        "CSRW(mie, zero)",
                        "csrci mstatus, 8 # MIE=0",
                        "csrci mstatus, 2 # SIE=0",
                    ]
                )

                lines.extend(
                    [
                        "# Clear all interrupts",
                        "RVTEST_CLR_MSW_INT",
                        f"CLR_SSW_INT(x{r_temp}, x{r_temp2})",
                        f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})",
                        "RVTEST_CLR_MEXT_INT",
                    ]
                )
                lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                lines.extend(
                    [
                        "# Set mtvec.MODE = 0 (direct)",
                        f"CSRR x{r_scratch}, mtvec",
                        f"SRLI x{r_scratch}, x{r_scratch}, 2",
                        f"SLLI x{r_scratch}, x{r_scratch}, 2",
                        f"CSRW(mtvec, x{r_scratch})",
                    ]
                )

                lines.append("# Write mideleg value")
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
                        "# Set walking 1 in mie",
                        f"LI(x{r_scratch}, {hex(mie_bit)})",
                        f"CSRW(mie, x{r_scratch})",
                    ]
                )

                lines.extend(
                    [
                        "# Set SIE=1 (will take effect when entering S-mode)",
                        f"LI(x{r_scratch}, 0x02)",
                        f"CSRS(mstatus, x{r_scratch})",
                    ]
                )

                lines.extend(
                    [
                        "# Ensure MIE is 0",
                        f"LI(x{r_scratch}, 0x80) # MPIE bit",
                        f"CSRC(mstatus, x{r_scratch}) # MPIE=0",
                    ]
                )

                lines.append("# Set interrupt pending")
                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                if mip_timer:
                    lines.append("# Set timer interrupts")
                    if mip_name == "stip":
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
                        lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))
                    else:  # mtip
                        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
                else:
                    lines.extend([mip_set, "nop"])

                lines.append("# Enter S-mode (interrupt fires immediately or when timer matures)")
                lines.append("RVTEST_GOTO_LOWER_MODE Smode")
                lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

                lines.extend(
                    [
                        "# Cleanup",
                        "RVTEST_GOTO_MMODE",
                        "csrci mstatus, 8",
                        "csrci mstatus, 2",
                        "CSRW(mideleg, zero)",
                        "CSRW(mie, zero)",
                    ]
                )

                lines.append("# Clear interrupt")
                if mip_timer:
                    if mip_name == "stip":
                        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                    else:
                        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
                else:
                    lines.append(mip_clr)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_vectored_s_tests(test_data: TestData) -> list[str]:
    """Generate vectored interrupt tests for S-mode.

    In M-mode with MIE=0, set interrupt pending but no trap fires.
    Enter S-mode with SIE=1 - now interrupts can fire (delegated to S, or trap to M).

    Cross of stvec.MODE = 00/01, mstatus.MIE=0, mstatus.SIE = 1, mie = 1s,
    mideleg = {STI+SEI+SSI}, 6 different interrupts walking in mip, change to supervisor mode
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_vectored_s"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_vectored_s",
            _generate_vectored_s_tests.__doc__,
        ),
        "",
    ]

    # ALL 6 interrupts (including M-mode ones!)
    interrupts = [
        ("ssip", 0x002, f"SET_SSW_INT(x{r_temp}, x{r_temp2})", f"CLR_SSW_INT(x{r_temp}, x{r_temp2})", False),
        ("msip", 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("stip", 0x020, None, None, True),
        ("mtip", 0x080, None, None, True),
        ("seip", 0x200, f"SET_SEXT_INT(x{r_temp}, x{r_temp2})", f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})", False),
        ("meip", 0x800, "RVTEST_SET_MEXT_INT", "RVTEST_CLR_MEXT_INT", False),
    ]

    for stvec_mode in [0, 1]:  # direct, vectored
        stvec_mode_name = ["direct", "vectored"][stvec_mode]

        for int_name, int_bit, int_set, int_clr, uses_timer in interrupts:
            binname = f"{stvec_mode_name}_{int_name}"

            lines.extend(
                [
                    "# === M-MODE SETUP ===",
                    "",
                    f"# Test: stvec.MODE={stvec_mode_name}, interrupt={int_name}",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8 # MIE=0 (blocks interrupts in M-mode)",
                    "csrci mstatus, 2 # SIE=0 initially",
                ]
            )

            lines.extend(
                [
                    "# Clear all interrupts",
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                    f"CLR_SSW_INT(x{r_temp}, x{r_temp2})",
                    f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            lines.extend(
                [
                    "# Set stvec.MODE",
                    f"CSRR x{r_scratch}, stvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                    f"CSRW(stvec, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Set mideleg (delegate S-interrupts)",
                    f"LI(x{r_scratch}, 0x222)",
                    f"CSRW(mideleg, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Enable ALL interrupts in mie",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Set SIE=1 (will take effect when entering S-mode)",
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Ensure MIE = 0",
                    f"LI(x{r_scratch}, 0x8) # MIE bit",
                    f"CSRC(mstatus, x{r_scratch}) # MIE=0",
                ]
            )

            lines.append("# Set interrupt in M-mode (MIE=0, so no trap yet)")
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            if uses_timer:
                if int_name == "stip":
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
                    lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))
                else:
                    lines.append("# mtip")
                    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
            else:
                lines.extend([int_set, "nop"])

            lines.append("# Enter S-mode (interrupt fires immediately or when timer matures)")
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")
            lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

            lines.extend(
                [
                    "# Cleanup",
                    "RVTEST_GOTO_MMODE",
                    "csrci mstatus, 8",
                    "csrci mstatus, 2",
                    "CSRW(mideleg, zero)",
                    "CSRW(mie, zero)",
                ]
            )

            lines.append("# Clear interrupts")
            if uses_timer:
                if int_name == "stip":
                    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                else:
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
            else:
                lines.append(int_clr)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


# ======================================================================
# NEXT SET OF TESTS
# ======================================================================


def _generate_priority_mip_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests.

    Set up with mstatus.MIE = 0, mstatus.SIE = 1, then change to supervisor mode after interrupts are set
    cp_priority_mip_s  (S-mode, mideleg=ones): 8 bins for {SEIP,STIP,SSIP} patterns 000-111.
    cp_priority_mip_s_m (M-mode MRET, mideleg=zeros): 7 bins for {MEIP,MTIP,MSIP} patterns 001-111.
    Only the bins each coverpoint actually needs — not all 64 combinations.
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_priority_mip_s / cp_priority_mip_s_m",
            _generate_priority_mip_s_tests.__doc__,
        ),
        "",
    ]

    def _setup(mideleg_hex: str) -> list[str]:
        return [
            "# Clearing all bits in mie, clear MIE and SIE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            "",
            "# Clearing pending interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
            *clr_stimer_mmode(r_scratch),
            *clr_mtimer_int(r_temp, r_stimecmp),
            "",
            "# Set mtvec.MODE = 00",
            f"CSRR x{r_scratch}, mtvec",
            f"SRLI x{r_scratch}, x{r_scratch}, 2",
            f"SLLI x{r_scratch}, x{r_scratch}, 2",
            f"CSRW(mtvec, x{r_scratch})",
            "",
            "# Enable all bits in mie and set mideleg",
            f"LI(x{r_scratch}, {mideleg_hex})",
            f"CSRW(mideleg, x{r_scratch})",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]

    def _enter_and_return() -> list[str]:
        return [
            "# Set SIE to high",
            f"LI(x{r_scratch}, 0x02)",
            f"CSRS(mstatus, x{r_scratch})",
            "RVTEST_GOTO_LOWER_MODE Smode",
            "    nop",
            "    nop",
            "    nop",
            "    nop",
            "# Clear SIE, MIE, mideleg, mie",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
        ]

    # S-mode: 8 {SEIP,STIP,SSIP} patterns — cp_priority_mip_s needs mip_combinations_s (000-111)
    s_patterns = [
        (0, 0, 0, "deleg_s_000"),
        (0, 0, 1, "deleg_s_001"),
        (0, 1, 0, "deleg_s_010"),
        (0, 1, 1, "deleg_s_011"),
        (1, 0, 0, "deleg_s_100"),
        (1, 0, 1, "deleg_s_101"),
        (1, 1, 0, "deleg_s_110"),
        (1, 1, 1, "deleg_s_111"),
    ]
    for seip, stip, ssip, binname in s_patterns:
        lines.extend(["", f"# cp_priority_mip_s: {binname}"])
        lines.extend(_setup("0x222"))
        if ssip:
            lines.append(f"SET_SSW_INT(x{r_temp}, x{r_temp2})")
        if stip:
            lines.extend(set_stimer_mmode(r_scratch))
        if seip:
            lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        lines.append(test_data.add_testcase(binname, "cp_priority_mip_s", covergroup))
        lines.extend(_enter_and_return())
        if ssip:
            lines.append(f"CLR_SSW_INT(x{r_temp}, x{r_temp2})")
        if stip:
            lines.extend(clr_stimer_mmode(r_scratch))
        if seip:
            lines.append(f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})")
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x202)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )

    # M-mode MRET: 7 {MEIP,MTIP,MSIP} patterns — cp_priority_mip_s_m needs mip_combinations_m (001-111)
    m_patterns = [
        (0, 0, 1, "nodeleg_m_001"),
        (0, 1, 0, "nodeleg_m_010"),
        (0, 1, 1, "nodeleg_m_011"),
        (1, 0, 0, "nodeleg_m_100"),
        (1, 0, 1, "nodeleg_m_101"),
        (1, 1, 0, "nodeleg_m_110"),
        (1, 1, 1, "nodeleg_m_111"),
    ]
    for meip, mtip, msip, binname in m_patterns:
        lines.extend(["", f"# cp_priority_mip_s_m: {binname}"])
        lines.extend(_setup("0x0"))
        if msip:
            lines.append("RVTEST_SET_MSW_INT")
        if mtip:
            lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        if meip:
            lines.append("RVTEST_SET_MEXT_INT")
        lines.append(test_data.add_testcase(binname, "cp_priority_mip_s_m", covergroup))
        lines.extend(_enter_and_return())
        if msip:
            lines.append("RVTEST_CLR_MSW_INT")
        if mtip:
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        if meip:
            lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mie_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests.

    Cross of 2^6 permutations of mie, mip=1s, mideleg ={0/STI+SEI+SSI}.
    Set up with mstatus.MIE = 0, mstatus.SIE=1, and change to supervisor
    15 cases: 8 S-mode + 7 M-mode
    """
    covergroup = "InterruptsS_S_cg"
    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)
    lines = [comment_banner("cp_priority_mie_s / cp_priority_mie_s_m", _generate_priority_mie_s_tests.__doc__), ""]

    def _setup(mideleg_hex: str, mie_val: int) -> list[str]:
        return [
            "# Clear mie, mip, MIE, SIE and all interrupts",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
            *clr_stimer_mmode(r_scratch),
            *clr_mtimer_int(r_temp, r_stimecmp),
            "",
            "# Set mtvec.MODE to direct (00)",
            f"CSRR x{r_scratch}, mtvec",
            f"SRLI x{r_scratch}, x{r_scratch}, 2",
            f"SLLI x{r_scratch}, x{r_scratch}, 2",
            f"CSRW(mtvec, x{r_scratch})",
            "",
            "# Write to mideleg and mie based on specific case",
            f"LI(x{r_scratch}, {mideleg_hex})",
            f"CSRW(mideleg, x{r_scratch})",
            f"LI(x{r_scratch}, {hex(mie_val)})",
            f"CSRW(mie, x{r_scratch})",
        ]

    def _enter_and_return() -> list[str]:
        return [
            f"LI(x{r_scratch}, 0x02)",
            f"CSRS(mstatus, x{r_scratch})",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
        ]

    # S-mode: vary mie {SEIE,STIE,SSIE}, mip=all-S-ones (SSIP+STIP+SEIP), mideleg=0x222
    s_patterns = [
        (0, 0, 0, "deleg_mie_s_000"),
        (0, 0, 1, "deleg_mie_s_001"),
        (0, 1, 0, "deleg_mie_s_010"),
        (0, 1, 1, "deleg_mie_s_011"),
        (1, 0, 0, "deleg_mie_s_100"),
        (1, 0, 1, "deleg_mie_s_101"),
        (1, 1, 0, "deleg_mie_s_110"),
        (1, 1, 1, "deleg_mie_s_111"),
    ]
    for seie, stie, ssie, binname in s_patterns:
        mie_val = (seie << 9) | (stie << 5) | (ssie << 1)
        lines.extend(["", f"# cp_priority_mie_s: {binname}"])
        lines.extend(_setup("0x222", mie_val))
        lines.append(f"SET_SSW_INT(x{r_temp}, x{r_temp2})")
        lines.extend(set_stimer_mmode(r_scratch))
        lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        lines.append(test_data.add_testcase(binname, "cp_priority_mie_s", covergroup))
        lines.extend(_enter_and_return())
        lines.append(f"CLR_SSW_INT(x{r_temp}, x{r_temp2})")
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.append(f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})")
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )

    # M-mode MRET: vary mie {MEIE,MTIE,MSIE}, mip=all-M-ones (MSIP+MTIP+MEIP), mideleg=0x0
    m_patterns = [
        (0, 0, 1, "nodeleg_mie_m_001"),
        (0, 1, 0, "nodeleg_mie_m_010"),
        (0, 1, 1, "nodeleg_mie_m_011"),
        (1, 0, 0, "nodeleg_mie_m_100"),
        (1, 0, 1, "nodeleg_mie_m_101"),
        (1, 1, 0, "nodeleg_mie_m_110"),
        (1, 1, 1, "nodeleg_mie_m_111"),
    ]
    for meie, mtie, msie, binname in m_patterns:
        mie_val = (meie << 11) | (mtie << 7) | (msie << 3)
        lines.extend(["", f"# cp_priority_mie_s_m: {binname}"])
        lines.extend(_setup("0x0", mie_val))
        lines.append("RVTEST_SET_MSW_INT")
        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        lines.append("RVTEST_SET_MEXT_INT")
        lines.append(test_data.add_testcase(binname, "cp_priority_mie_s_m", covergroup))
        lines.extend(_enter_and_return())
        lines.append("RVTEST_CLR_MSW_INT")
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_both_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority test

    Cross of 2^6 permutations of mie, mip=mie, mideleg ={0/STI+SEI+SSI}.
    Set up with mstatus.MIE = 0, mstatus.SIE=1, and change to supervisor
    """
    covergroup = "InterruptsS_S_cg"
    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)
    lines = [comment_banner("cp_priority_both_s / cp_priority_both_m", _generate_priority_both_s_tests.__doc__), ""]

    def _setup(mideleg_hex: str, mie_val: int) -> list[str]:
        return [
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
            *clr_stimer_mmode(r_scratch),
            *clr_mtimer_int(r_temp, r_stimecmp),
            f"CSRR x{r_scratch}, mtvec",
            f"SRLI x{r_scratch}, x{r_scratch}, 2",
            f"SLLI x{r_scratch}, x{r_scratch}, 2",
            f"CSRW(mtvec, x{r_scratch})",
            f"LI(x{r_scratch}, {mideleg_hex})",
            f"CSRW(mideleg, x{r_scratch})",
            f"LI(x{r_scratch}, {hex(mie_val)})",
            f"CSRW(mie, x{r_scratch})",
        ]

    def _enter_and_return() -> list[str]:
        return [
            f"LI(x{r_scratch}, 0x02)",
            f"CSRS(mstatus, x{r_scratch})",
            "RVTEST_GOTO_LOWER_MODE Smode",
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrci mstatus, 2",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
        ]

    # S-mode: mip_s == mie_s (same {SEIP,STIP,SSIP} == {SEIE,STIE,SSIE}), mideleg=0x222
    s_patterns = [
        (0, 0, 0, "deleg_both_s_000"),
        (0, 0, 1, "deleg_both_s_001"),
        (0, 1, 0, "deleg_both_s_010"),
        (0, 1, 1, "deleg_both_s_011"),
        (1, 0, 0, "deleg_both_s_100"),
        (1, 0, 1, "deleg_both_s_101"),
        (1, 1, 0, "deleg_both_s_110"),
        (1, 1, 1, "deleg_both_s_111"),
    ]
    for seip, stip, ssip, binname in s_patterns:
        mie_val = (seip << 9) | (stip << 5) | (ssip << 1)
        lines.extend(["", f"# cp_priority_both_s: {binname}"])
        lines.extend(_setup("0x222", mie_val))
        if ssip:
            lines.append(f"SET_SSW_INT(x{r_temp}, x{r_temp2})")
        if stip:
            lines.extend(set_stimer_mmode(r_scratch))
        if seip:
            lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        lines.append(test_data.add_testcase(binname, "cp_priority_both_s", covergroup))
        lines.extend(_enter_and_return())
        if ssip:
            lines.append(f"CLR_SSW_INT(x{r_temp}, x{r_temp2})")
        if stip:
            lines.extend(clr_stimer_mmode(r_scratch))
        if seip:
            lines.append(f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})")

    # M-mode MRET: mip_m == mie_m (same {MEIP,MTIP,MSIP} == {MEIE,MTIE,MSIE}), mideleg=0x0
    m_patterns = [
        (0, 0, 1, "nodeleg_both_m_001"),
        (0, 1, 0, "nodeleg_both_m_010"),
        (0, 1, 1, "nodeleg_both_m_011"),
        (1, 0, 0, "nodeleg_both_m_100"),
        (1, 0, 1, "nodeleg_both_m_101"),
        (1, 1, 0, "nodeleg_both_m_110"),
        (1, 1, 1, "nodeleg_both_m_111"),
    ]
    for meip, mtip, msip, binname in m_patterns:
        mie_val = (meip << 11) | (mtip << 7) | (msip << 3)
        lines.extend(["", f"# cp_priority_both_m: {binname}"])
        lines.extend(_setup("0x0", mie_val))
        if msip:
            lines.append("RVTEST_SET_MSW_INT")
        if mtip:
            lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        if meip:
            lines.append("RVTEST_SET_MEXT_INT")
        lines.append(test_data.add_testcase(binname, "cp_priority_both_m", covergroup))
        lines.extend(_enter_and_return())
        if msip:
            lines.append("RVTEST_CLR_MSW_INT")
        if mtip:
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        if meip:
            lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mideleg_tests(test_data: TestData) -> list[str]:
    """Generate mideleg priority tests (combined M + S behavior).

    Covers:
    - M-mode priority vs delegation (all 8 patterns)
    - S-mode priority within delegated interrupts (patterns 1–7, mie=mideleg)
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_priority_mideleg_combined",
            _generate_priority_mideleg_tests.__doc__,
        ),
        "",
    ]

    # ============================================================
    # PASS 1: M-MODE PRIORITY (original _m_tests)
    # ============================================================
    for mideleg_pattern in range(8):
        ssie = (mideleg_pattern >> 0) & 1
        stie = (mideleg_pattern >> 1) & 1
        seie = (mideleg_pattern >> 2) & 1

        mideleg_val = (ssie << 1) | (stie << 5) | (seie << 9)

        coverpoint = "cp_priority_mideleg_m"

        binname = f"mideleg_m_{mideleg_pattern:03b}"

        lines.extend(
            [
                "",
                f"# M-test: mideleg={mideleg_pattern:03b}",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
            ]
        )

        lines.extend(
            [
                "# Clear",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        lines.extend(
            [
                "# mtvec direct",
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"CSRW(mtvec, x{r_scratch})",
            ]
        )

        lines.extend(
            [
                "# mideleg",
                f"LI(x{r_scratch}, {hex(mideleg_val)})",
                f"CSRW(mideleg, x{r_scratch})",
            ]
        )

        lines.extend(
            [
                "# mie = all",
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

        lines.append("# set all S interrupts")
        lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        lines.append(f"SET_SSW_INT(x{r_temp}, x{r_temp2})")
        lines.extend(set_stimer_mmode(r_mtime))

        lines.extend(
            [
                "# enable SIE",
                f"LI(x{r_scratch}, 0x02)",
                f"CSRS(mstatus, x{r_scratch})",
            ]
        )

        lines.append("RVTEST_GOTO_LOWER_MODE Smode")

        lines.append("# wait")
        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

        lines.extend(
            [
                "# cleanup",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

    # ============================================================
    # PASS 2: S-MODE PRIORITY (original _s_tests)
    # ============================================================
    for mideleg_pattern in range(1, 8):
        ssie = (mideleg_pattern >> 0) & 1
        stie = (mideleg_pattern >> 1) & 1
        seie = (mideleg_pattern >> 2) & 1

        mideleg_val = (ssie << 1) | (stie << 5) | (seie << 9)

        binname = f"mideleg_s_{mideleg_pattern:03b}"

        lines.extend(
            [
                "",
                f"# S-test: mideleg=mie={mideleg_pattern:03b}",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
            ]
        )

        lines.extend(
            [
                "# Clear",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

        lines.extend(
            [
                "# mtvec",
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"CSRW(mtvec, x{r_scratch})",
            ]
        )

        lines.extend(
            [
                "# mideleg + mie (matching)",
                f"LI(x{r_scratch}, {hex(mideleg_val)})",
                f"CSRW(mideleg, x{r_scratch})",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        lines.append("# set all S interrupts")
        lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        lines.append(f"SET_SSW_INT(x{r_temp}, x{r_temp2})")
        lines.extend(set_stimer_mmode(r_mtime))

        lines.extend(
            [
                "# enable SIE",
                f"LI(x{r_scratch}, 0x02)",
                f"CSRS(mstatus, x{r_scratch})",
            ]
        )

        lines.append("RVTEST_GOTO_LOWER_MODE Smode")

        lines.append("# sample in S-mode")
        lines.append(f"    {test_data.add_testcase(binname, 'cp_priority_mideleg_s', covergroup)}")

        lines.append("# wait")
        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

        lines.extend(
            [
                "# cleanup",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])

    return lines


def _generate_wfi_s_tests(test_data: TestData) -> list[str]:
    """Generate S-mode WFI tests.

    Test WFI from S-mode with MTIP.
    Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222}

    - cp_wfi_s: TW=0, WFI executes in S-mode
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_wfi_s",
            _generate_wfi_s_tests.__doc__,
        ),
        "",
    ]

    lines.append("# Cross: MIE × SIE × mideleg")
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mideleg_val in [0, 1]:
                mideleg_name = ["zeros", "ones"][mideleg_val]

                coverpoint = "cp_wfi_s"

                binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}"

                lines.extend(
                    [
                        "",
                        f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}",
                        "RVTEST_GOTO_MMODE",
                        "CSRW(mie, zero)",
                        "csrci mstatus, 8 # MIE=0",
                        "csrci mstatus, 2 # SIE=0",
                    ]
                )

                lines.append("# Clear timer")
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                lines.append("# Write mideleg based on bins")
                if mideleg_val == 1:
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
                        "# Enable MTIE",
                        f"LI(x{r_scratch}, 0x80) # MTIE",
                        f"CSRW(mie, x{r_scratch})",
                        "# Clear TW",
                        f"LI(x{r_scratch}, 0x200000)",
                        f"CSRC(mstatus, x{r_scratch})",
                    ]
                )

                lines.append("# Write MIE based on bins")
                if mie_val:
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x80) # MPIE bit",
                            f"CSRS(mstatus, x{r_scratch})",
                        ]
                    )
                else:
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x8)",
                            f"CSRC(mstatus, x{r_scratch})",
                        ]
                    )

                if sie_val:
                    lines.append("# Set SIE")
                    lines.append("csrsi mstatus, 2")

                lines.append("# Set timer to fire soon (delayed)")
                lines.extend(set_mtimer_int_soon(r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_stce, 100))

                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                lines.extend(
                    [
                        "# Enter S-mode and execute WFI",
                        "RVTEST_GOTO_LOWER_MODE Smode",
                    ]
                )

                lines.extend(
                    [
                        "# TW=0: waits, TW=1: timeout → illegal instruction",
                        "    wfi",
                        "    nop",
                        "    nop",
                    ]
                )

                lines.extend(
                    [
                        "# Cleanup",
                        "RVTEST_GOTO_MMODE",
                        "csrci mstatus, 8",
                        "csrci mstatus, 2",
                        f"LI(x{r_scratch}, 0x200000)",
                        f"CSRC(mstatus, x{r_scratch}) # Clear TW",
                        "CSRW(mideleg, zero)",
                        "CSRW(mie, zero)",
                    ]
                )
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_wfi_timeout_s_tests(test_data: TestData) -> list[str]:
    """Generate S-mode and U-mode WFI timeout tests.

    Test WFI timeout with TW=1, MTIMECMP=max.
    Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × MTIE={0,1} × mode={S,U}
    Total: 2×2×2×2×2 = 32 bins
    """
    covergroup = "InterruptsS_S_cg"

    r_temp, r_stimecmp, r_scratch = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            "cp_wfi_timeout_s",
            _generate_wfi_timeout_s_tests.__doc__,
        ),
        "",
    ]

    lines.append("# Cross: MIE × SIE × mideleg × MTIE × mode")
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mideleg_val in [0, 1]:
                for mtie_val in [0, 1]:
                    for mode in ["Smode", "Umode"]:
                        mideleg_name = ["zeros", "ones"][mideleg_val]
                        mode_short = mode[0].lower()  # 's' or 'u'

                        lines.append("# Select coverpoint based on mode")
                        coverpoint = "cp_wfi_timeout_s" if mode == "Smode" else "cp_wfi_timeout_u_tw"

                        binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}_mtie{mtie_val}_{mode_short}"

                        lines.extend(
                            [
                                "",
                                f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}, MTIE={mtie_val}, mode={mode}",
                                "RVTEST_GOTO_MMODE",
                                "CSRW(mie, zero)",
                                "csrci mstatus, 8 # MIE=0",
                                "csrci mstatus, 2 # SIE=0",
                            ]
                        )

                        lines.extend(
                            [
                                "# Clear all interrupts",
                                f"LI(x{r_scratch}, 0x2)",
                                f"CSRC(mip, x{r_scratch})",
                                "RVTEST_CLR_MSW_INT",
                            ]
                        )
                        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                        lines.append("# Write mideleg value based on bins")
                        if mideleg_val == 1:
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
                                "# Set TW=1 (timeout enabled)",
                                f"LI(x{r_scratch}, 0x200000) # TW bit (bit 21)",
                                f"CSRS(mstatus, x{r_scratch})",
                            ]
                        )

                        lines.append("# Write MTIE value based on bins")
                        if mtie_val:
                            lines.extend(
                                [
                                    f"LI(x{r_scratch}, 0x80) # MTIE",
                                    f"CSRW(mie, x{r_scratch})",
                                ]
                            )
                        else:
                            lines.append("CSRW(mie, zero)")

                        lines.extend(
                            [
                                "# Set MTIMECMP to max (no interrupt)",
                                f"LA(x{r_temp}, RVMODEL_MTIMECMP_ADDRESS)",
                                f"LI(x{r_scratch}, -1)",
                                f"SREG x{r_scratch}, 0(x{r_temp})",
                            ]
                        )

                        if mie_val:
                            lines.extend(
                                [
                                    "# Set MIE+MPIE so MIE=1 persists through MRET into U-mode",
                                    f"LI(x{r_scratch}, 0x88)",
                                    f"CSRS(mstatus, x{r_scratch})",
                                ]
                            )

                        if sie_val:
                            lines.append("# Set SIE")
                            lines.append("csrsi mstatus, 2")

                        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                        lines.extend(
                            [
                                "# Enter target mode and execute WFI",
                                f"RVTEST_GOTO_LOWER_MODE {mode}",
                                "    wfi # TW=1 → illegal instruction",
                                "    nop",
                            ]
                        )

                        lines.extend(
                            [
                                "# Cleanup",
                                "RVTEST_GOTO_MMODE",
                                "csrci mstatus, 8",
                                "csrci mstatus, 2",
                                f"LI(x{r_scratch}, 0x200000)",
                                f"CSRC(mstatus, x{r_scratch}) # Clear TW",
                                "CSRW(mideleg, zero)",
                                "CSRW(mie, zero)",
                            ]
                        )
                        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_temp, r_stimecmp, r_scratch])
    return lines


def _generate_interrupts_m_tests(test_data: TestData) -> list[str]:
    """Generate interrupt tests in M-mode.

    Cross: MIE={0,1} × mideleg={0,0x222} × 6 mip walking × 6 mie walking
    Total: 2 × 2 × 6 × 6 = 144 bins

    Routes to:
    - cp_interrupts_m: Non-delegated (mideleg=0) OR M-interrupts (always M-mode)
    - cp_interrupts_m_deleg: Delegated S-interrupts (mideleg=0x222 + SSIP/STIP/SEIP)
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_interrupts_m",
            _generate_interrupts_m_tests.__doc__,
        ),
        "",
    ]

    # 6 interrupts (walking 1s)
    interrupts = [
        ("ssip", 0x002, 0x002, None, None, False),
        ("msip", 0x008, 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("stip", 0x020, 0x020, None, None, True),
        ("mtip", 0x080, 0x080, None, None, True),
        ("seip", 0x200, 0x200, f"SET_SEXT_INT(x{r_temp}, x{r_temp2})", f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})", False),
        ("meip", 0x800, 0x800, "RVTEST_SET_MEXT_INT", "RVTEST_CLR_MEXT_INT", False),
    ]

    # S-interrupts that can be delegated
    s_interrupts = {"ssip", "stip", "seip"}

    # Loop: MIE × mideleg × mip × mie
    for mie_val in [0, 1]:
        for mideleg_val in [0, 1]:  # 0 = none, 1 = 0x222
            for mip_name, mip_bit, mie_bit, set_fn, clr_fn, is_timer in interrupts:
                for mie_name in ["ssie", "msie", "stie", "mtie", "seie", "meie"]:
                    # Determine if delegated
                    is_delegated = (mideleg_val == 1) and (mip_name in s_interrupts)

                    # Select coverpoint
                    coverpoint = "cp_interrupts_m_deleg" if is_delegated else "cp_interrupts_m"

                    mideleg_name = ["zeros", "ones"][mideleg_val]
                    binname = f"mie{mie_val}_{mideleg_name}_{mip_name}_{mie_name}"

                    lines.extend(
                        [
                            "",
                            "# === SETUP ===",
                            f"# MIE={mie_val}, mideleg={mideleg_name}, mip={mip_name}, mie={mie_name}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8 # MIE=0",
                            "csrci mstatus, 2 # SIE=0",
                        ]
                    )

                    lines.extend(
                        [
                            "# Clear all interrupts",
                            f"LI(x{r_scratch}, 0x202)",
                            f"CSRC(mip, x{r_scratch})",
                            "RVTEST_CLR_MSW_INT",
                        ]
                    )
                    lines.extend(clr_stimer_mmode(r_scratch))
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    lines.extend(
                        [
                            "# Set mtvec.MODE = 0 (direct)",
                            f"CSRR x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"CSRW(mtvec, x{r_scratch})",
                        ]
                    )

                    lines.append("# Write mideleg value based on bins")
                    if mideleg_val == 1:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x222) # STI+SEI+SSI",
                                f"CSRW(mideleg, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.append("CSRW(mideleg, zero)")

                    # Set walking 1 in mie (convert name to bit)
                    mie_bit_map = {
                        "ssie": 0x002,
                        "msie": 0x008,
                        "stie": 0x020,
                        "mtie": 0x080,
                        "seie": 0x200,
                        "meie": 0x800,
                    }
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, {hex(mie_bit_map[mie_name])})",
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    if is_delegated:
                        lines.append("# Set SIE=1 for delegated")
                        lines.append("csrsi mstatus, 2")

                    if mie_val == 1:
                        lines.append("# Set MIE before triggering the interrupt (so trap fires immediately on set)")
                        lines.append("csrsi mstatus, 8")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
                    lines.append("# === SET INTERRUPT ===")

                    if is_timer:
                        if mip_name == "stip":
                            # Always set mip.STIP directly from M-mode.
                            # set_stimer_int's legacy path (STCE=0) calls RVTEST_GOTO_LOWER_MODE Smode,
                            # which would make the wait loop run in S-mode → coverage misses M-mode state.
                            lines.extend(set_stimer_mmode(r_scratch))
                        else:  # mtip
                            lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
                    else:
                        if mip_name == "ssip":
                            lines.extend(
                                [
                                    f"LI(x{r_scratch}, 0x2)",
                                    f"CSRS(mip, x{r_scratch})",
                                ]
                            )
                        else:
                            lines.extend([set_fn, "nop"])

                    lines.append("# === WAIT FOR INTERRUPT ===")
                    if is_delegated:
                        lines.extend(
                            [
                                "# Enter S-mode for delegated interrupts",
                                "RVTEST_GOTO_LOWER_MODE Smode",
                                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
                            ]
                        )
                    else:
                        # Stay in M-mode
                        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

                    lines.extend(
                        [
                            "# === CLEANUP ===",
                            "RVTEST_GOTO_MMODE",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            "CSRW(mideleg, zero)",
                            "CSRW(mie, zero)",
                        ]
                    )

                    if is_timer:
                        if mip_name == "stip":
                            # Reset stimecmp to max unconditionally before clearing mip.STIP.
                            # On STCE=1 systems, hardware re-asserts STIP immediately if stimecmp
                            # is not reset before the csrrc mip clear.
                            lines.extend(
                                [
                                    f"LI(x{r_temp}, -1)",
                                    f"csrw stimecmp, x{r_temp}",
                                    "#if __riscv_xlen == 32",
                                    f"csrw stimecmph, x{r_temp}",
                                    "#endif",
                                ]
                            )
                            lines.extend(clr_stimer_mmode(r_scratch))
                        else:
                            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
                    else:
                        if mip_name == "ssip":
                            lines.extend(
                                [
                                    f"LI(x{r_scratch}, 0x2)",
                                    f"CSRC(mip, x{r_scratch})",
                                ]
                            )
                        else:
                            lines.append(clr_fn)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_vectored_m_tests(test_data: TestData) -> list[str]:
    """Generate vectored interrupt tests in M-mode.
    mstatus.MIE=1, mideleg =0s, all 3 of mie.STIE/SSIE/SEIE, 3 walking 1s in mip.STIP/SSIP/SEIP (3 bins)
    Test vectored with S-interrupts, mideleg=0 (fire in M-mode).
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_vectored_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_vectored_m",
            _generate_vectored_m_tests.__doc__,
        ),
        "",
    ]

    # S-mode interrupts (fire in M-mode when not delegated)
    interrupts = [
        ("ssip", 0x002, None, None, False),
        ("stip", 0x020, None, None, True),
        ("seip", 0x200, f"SET_SEXT_INT(x{r_temp}, x{r_temp2})", f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})", False),
    ]

    for int_name, int_bit, int_set, int_clr, uses_timer in interrupts:
        binname = f"vectored_{int_name}"

        lines.extend(
            [
                "",
                f"# Test vectored M-mode: {int_name}",
                "RVTEST_GOTO_MMODE",
                "CSRW(mie, zero)",
                "csrci mstatus, 8 # MIE=0",
            ]
        )

        lines.extend(
            [
                "# Clear all interrupts",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

        lines.extend(
            [
                "# Set mtvec.MODE = 1 (vectored)",
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"ADDI x{r_scratch}, x{r_scratch}, 1 # MODE=1",
                f"CSRW(mtvec, x{r_scratch})",
            ]
        )

        lines.append("# mideleg=0 (no delegation, fire in M-mode)")
        lines.append("CSRW(mideleg, zero)")

        lines.extend(
            [
                "# Enable all S-mode interrupts",
                f"LI(x{r_scratch}, 0x222) # SSIE, STIE, SEIE",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        lines.append("# Set MIE=1")
        lines.append("csrsi mstatus, 8")

        lines.append("# Set interrupt pending")
        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

        if uses_timer:
            lines.extend(set_stimer_mmode(r_scratch))
        elif int_name == "ssip":
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRS(mip, x{r_scratch})",
                ]
            )
        else:
            lines.extend([int_set, "nop"])

        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

        lines.extend(
            [
                "# Cleanup",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
            ]
        )

        lines.append("# Clear interrupt")
        if uses_timer:
            lines.extend(clr_stimer_mmode(r_scratch))
        elif int_name == "ssip":
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )
        else:
            lines.append(int_clr)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mip_m_tests(test_data: TestData) -> list[str]:
    """Generate priority tests varying mip with MIE rising.

    Set MIE=0, configure all 64 mip patterns, mie=all 1s, mideleg=0, then set MIE=1.
    Tests which interrupt fires based on priority.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_priority_mip_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_priority_mip_m",
            _generate_priority_mip_m_tests.__doc__,
        ),
        "",
        "RVTEST_GOTO_MMODE",
    ]

    # Test all 64 mip patterns
    for mip_pattern in range(64):
        ssip = (mip_pattern >> 0) & 1
        msip = (mip_pattern >> 1) & 1
        stip = (mip_pattern >> 2) & 1
        mtip = (mip_pattern >> 3) & 1
        seip = (mip_pattern >> 4) & 1
        meip = (mip_pattern >> 5) & 1

        binname = f"priority_mip_{mip_pattern:02x}"

        lines.extend(
            [
                "",
                f"# Test priority MIE rise: mip=0x{mip_pattern:02x}",
                "CSRW(mie, zero)",
                "csrci mstatus, 8 # MIE=0",
            ]
        )

        lines.extend(
            [
                "# Clear all interrupts",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_MSW_INT",
                "RVTEST_CLR_MEXT_INT",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        lines.append("# mideleg=0 (no delegation)")
        lines.append("CSRW(mideleg, zero)")

        lines.extend(
            [
                "# Enable ALL interrupts in mie",
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        lines.append("# Set interrupt pattern (with MIE=0, won't fire yet)")
        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

        if ssip:
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRS(mip, x{r_scratch})",
                ]
            )
        if msip:
            lines.append("RVTEST_SET_MSW_INT")
        if stip:
            lines.extend(set_stimer_mmode(r_scratch))
        if mtip:
            lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        if seip:
            lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        if meip:
            lines.append("RVTEST_SET_MEXT_INT")

        lines.append("nop")

        lines.append("# Set MIE=1 (rise event - interrupt fires immediately)")
        lines.append("csrsi mstatus, 8")
        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

        lines.extend(
            [
                "# Cleanup",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
            ]
        )

        lines.append("# Clear interrupts")
        if ssip:
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )
        if msip:
            lines.append("RVTEST_CLR_MSW_INT")
        if stip:
            lines.extend(clr_stimer_mmode(r_scratch))
        if mtip:
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        if seip:
            lines.extend([f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})"])
        if meip:
            lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mie_m_tests(test_data: TestData) -> list[str]:
    """Generate priority tests varying mie with MIE rising.

    Set MIE=0, configure all 64 mie patterns, set all mip, mideleg=0, then MIE=1.
    Tests which interrupt fires based on enable priority.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_priority_mie_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_priority_mie_m",
            _generate_priority_mie_m_tests.__doc__,
        ),
        "",
        "RVTEST_GOTO_MMODE",
    ]

    # Test all 64 mie patterns
    for mie_pattern in range(64):
        ssie = (mie_pattern >> 0) & 1
        msie = (mie_pattern >> 1) & 1
        stie = (mie_pattern >> 2) & 1
        mtie = (mie_pattern >> 3) & 1
        seie = (mie_pattern >> 4) & 1
        meie = (mie_pattern >> 5) & 1

        # Build mie value
        mie_val = (ssie << 1) | (msie << 3) | (stie << 5) | (mtie << 7) | (seie << 9) | (meie << 11)

        binname = f"priority_mie_{mie_pattern:02x}"

        lines.extend(
            [
                "",
                f"# Test priority MIE rise: mie=0x{mie_pattern:02x}",
                "CSRW(mie, zero)",
                "csrci mstatus, 8 # MIE=0",
            ]
        )

        lines.extend(
            [
                "# Clear all interrupts",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_MSW_INT",
                "RVTEST_CLR_MEXT_INT",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        lines.append("# mideleg=0 (no delegation)")
        lines.append("CSRW(mideleg, zero)")

        lines.extend(
            [
                "# Set specific mie pattern",
                f"LI(x{r_scratch}, {hex(mie_val)})",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
        lines.extend(
            [
                "# Set ALL interrupts (with MIE=0, won't fire yet)",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRS(mip, x{r_scratch})",
                "RVTEST_SET_MSW_INT",
            ]
        )
        lines.extend(set_stimer_mmode(r_scratch))
        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        lines.extend(
            [
                "RVTEST_SET_MEXT_INT",
                "nop",
            ]
        )

        lines.append("# Set MIE=1 (rise event - interrupt fires immediately)")
        lines.append("csrsi mstatus, 8")
        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

        lines.extend(
            [
                "# Cleanup",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
                f"LI(x{r_scratch}, 0x202)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_MSW_INT",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        lines.extend(
            [
                "RVTEST_CLR_MEXT_INT",
            ]
        )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_wfi_m_tests(test_data: TestData) -> list[str]:
    """Generate WFI tests in M-mode.

    Test WFI with MTIP in M-mode across all MIE, SIE, TW, mideleg combinations.
    WFI should wake on timer regardless of settings.
    8 tests: 2 MIE × 2 SIE × 2 TW
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_wfi_m"

    r_mtime, r_mtimecmp, r_temp1, r_temp2, r_temp3, r_temp4 = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_wfi_m",
            _generate_wfi_m_tests.__doc__,
        ),
        "",
    ]

    # Test all 8 combinations
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for tw_val in [0, 1]:
                binname = f"wfi_m_mie{mie_val}_sie{sie_val}_tw{tw_val}"

                lines.extend(
                    [
                        "",
                        f"# Test M-mode WFI: MIE={mie_val}, SIE={sie_val}, TW={tw_val}",
                        "RVTEST_GOTO_MMODE",
                        "CSRW(mie, zero)",
                        "csrci mstatus, 8 # Clear MIE",
                        "csrci mstatus, 2 # Clear SIE",
                    ]
                )

                lines.append("# Clear timer interrupt")
                lines.extend(clr_mtimer_int(r_temp1, r_mtimecmp))

                lines.extend(
                    [
                        "# Set mideleg = 0x222 (S-interrupts delegated)",
                        f"LI(x{r_temp1}, 0x222)",
                        f"CSRW(mideleg, x{r_temp1})",
                    ]
                )

                lines.extend(
                    [
                        "# Enable MTIE",
                        f"LI(x{r_temp1}, 0x80) # MTIE bit",
                        f"CSRS(mie, x{r_temp1})",
                    ]
                )

                if mie_val:
                    lines.append("csrsi mstatus, 8 # Set MIE")

                if sie_val:
                    lines.append("csrsi mstatus, 2 # Set SIE")

                if tw_val:
                    lines.extend(
                        [
                            "# Set TW bit",
                            f"LI(x{r_temp1}, 0x200000) # TW bit (bit 21)",
                            f"CSRS(mstatus, x{r_temp1})",
                        ]
                    )

                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
                lines.append("# Set machine timer to fire soon")
                lines.extend(set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp1, r_temp2, r_temp3, r_temp4))

                lines.extend(
                    [
                        "# Execute WFI in M-mode",
                        "    nop",
                        "    wfi # Wait for timer interrupt",
                        "    nop",
                        "    nop",
                    ]
                )

                lines.extend(
                    [
                        "# Cleanup",
                        "RVTEST_GOTO_MMODE",
                        "csrci mstatus, 8 # Clear MIE",
                        "csrci mstatus, 2 # Clear SIE",
                        f"LI(x{r_temp1}, 0x200000)",
                        f"CSRC(mstatus, x{r_temp1}) # Clear TW",
                        "CSRW(mideleg, zero)",
                        "CSRW(mie, zero)",
                    ]
                )
                lines.extend(clr_mtimer_int(r_temp1, r_mtimecmp))

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp1, r_temp2, r_temp3, r_temp4])
    return lines


def _generate_trigger_mti_m_tests(test_data: TestData) -> list[str]:
    """Generate MTIP trigger test when MIE rises via CSRRS.

    Set MTIP pending with MIE=0, then use CSRRS to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_mti_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_mti_m",
            _generate_trigger_mti_m_tests.__doc__,
        ),
        "",
    ]

    binname = "trigger_mti_csrrs"

    lines.extend(
        [
            "",
            "# Test: MTIP fires when MIE rises (CSRRS)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.append("# Clear timer")
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Set mideleg=0")
    lines.append("CSRW(mideleg, zero)")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.append("# Set MTIP using the timer function")
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))

    lines.extend(
        [
            "# Wait for timer to be pending",
            "nop",
            "nop",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Use CSRRS to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"CSRRS x0, mstatus, x{r_scratch} # Set MIE=1 via CSRRS",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
        ]
    )
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_sip_m_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger test via SIP CSR write in M-mode.

    Use CSRRS to write sip.SSIP, test with MIE={0,1} and mideleg.SSI={0,1}.
    4 tests total.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_ssi_sip_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_ssi_sip_m",
            _generate_trigger_ssi_sip_m_tests.__doc__,
        ),
        "",
    ]

    # Test both MIE and mideleg.SSI values
    for mie_val in [0, 1]:
        for mideleg_ssi in [0, 1]:
            binname = f"trigger_ssi_sip_mie{mie_val}_ssi{mideleg_ssi}"

            lines.extend(
                [
                    "",
                    f"# Test: SSIP via SIP write, MIE={mie_val}, mideleg.SSI={mideleg_ssi}",
                    "RVTEST_GOTO_MMODE",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8 # MIE=0",
                ]
            )

            # Clear SSIP
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )

            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            if mideleg_ssi:
                lines.extend(
                    [
                        "# Set mideleg.SSI",
                        f"LI(x{r_scratch}, 0x2) # SSI bit",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            lines.extend(
                [
                    "# Enable all interrupts in mie",
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            # Set MIE if needed (AFTER setting up everything)
            # This prevents early firing
            if mie_val:
                lines.extend(
                    [
                        "# Set MIE",
                        "csrsi mstatus, 8",
                        "nop",
                        "nop",
                    ]
                )

            # Use CSRRS to set sip.SSI
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2) # SSIP bit (bit 1)",
                    "# interrupt fires immediately on SSIP write",
                    f"CSRRS x0, sip, x{r_scratch} # Set SSIP via SIP write",
                    "nop",
                    "nop",
                ]
            )

            lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

            lines.extend(
                [
                    "# Cleanup",
                    "RVTEST_GOTO_MMODE",
                    "csrci mstatus, 8",
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "CSRW(mideleg, zero)",
                    "CSRW(mie, zero)",
                ]
            )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_msi_m_tests(test_data: TestData) -> list[str]:
    """Generate MSIP trigger test when MIE rises via CSRRS.

    Set MSIP pending with MIE=0, then use CSRRS to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_msi_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_msi_m",
            _generate_trigger_msi_m_tests.__doc__,
        ),
        "",
    ]

    binname = "trigger_msi_csrrs"

    lines.extend(
        [
            "",
            "# Test: MSIP fires when MIE rises (CSRRS)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
        ]
    )
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Clear mideleg")
    lines.append("CSRW(mideleg, zero)")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "# Set MSIP",
            "RVTEST_SET_MSW_INT",
        ]
    )

    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use CSRRS to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"CSRRS x0, mstatus, x{r_scratch} # Set MIE=1 via CSRRS",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
            "RVTEST_CLR_MSW_INT",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_mei_m_tests(test_data: TestData) -> list[str]:
    """Generate MEIP trigger test when MIE rises via CSRRS.

    Set MEIP pending with MIE=0, then use CSRRS to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_mei_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_mei_m",
            _generate_trigger_mei_m_tests.__doc__,
        ),
        "",
    ]

    binname = "trigger_mei_csrrs"

    lines.extend(
        [
            "",
            "# Test: MEIP fires when MIE rises (CSRRS)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Clear mideleg")
    lines.append("CSRW(mideleg, zero)")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(["# Set MEIP", "RVTEST_SET_MEXT_INT"])
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use CSRRS to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"CSRRS x0, mstatus, x{r_scratch} # Set MIE=1 via CSRRS",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
            "RVTEST_CLR_MEXT_INT",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_sti_m_tests(test_data: TestData) -> list[str]:
    """Generate STIP trigger test when MIE rises via CSRRS.

    Set STIP pending with MIE=0, then use CSRRS to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sti_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_sti_m",
            _generate_trigger_sti_m_tests.__doc__,
        ),
        "",
    ]

    binname = "trigger_sti_csrrs"

    lines.extend(
        [
            "",
            "# Test: STIP fires when MIE rises (CSRRS)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Clear mideleg (STIP fires in M-mode)")
    lines.append("CSRW(mideleg, zero)")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.append("# Set STIP using M-mode direct write")
    lines.extend(set_stimer_mmode(r_scratch))
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use CSRRS to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"CSRRS x0, mstatus, x{r_scratch} # Set MIE=1 via CSRRS",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_m_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger test when MIE rises via CSRRS.

    Set SSIP pending with MIE=0, mideleg=0, then use CSRRS to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_ssi_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_ssi_m",
            _generate_trigger_ssi_m_tests.__doc__,
        ),
        "",
    ]

    binname = "trigger_ssi_csrrs"

    lines.extend(
        [
            "",
            "# Test: SSIP fires when MIE rises (CSRRS)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Set mideleg=0 (SSIP fires in M-mode)")
    lines.append("CSRW(mideleg, zero)")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "# Set SSIP",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRS(mip, x{r_scratch})",
        ]
    )
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use CSRRS to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"CSRRS x0, mstatus, x{r_scratch} # Set MIE=1 via CSRRS",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_sei_m_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger test when MIE rises via CSRRS.

    Set SEIP pending with MIE=0, mideleg=0, then use CSRRS to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_trigger_sei_m",
            _generate_trigger_sei_m_tests.__doc__,
        ),
        "",
    ]

    binname = "trigger_sei_csrrs"

    lines.extend(
        [
            "",
            "# Test: SEIP fires when MIE rises (CSRRS)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Set mideleg=0 (SEIP fires in M-mode)")
    lines.append("CSRW(mideleg, zero)")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.append("# Set SEIP")
    lines.extend([f"SET_SEXT_INT(x{r_temp}, x{r_temp2})"])
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use CSRRS to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"CSRRS x0, mstatus, x{r_scratch} # Set MIE=1 via CSRRS",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
            f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_sei_interaction_tests(test_data: TestData) -> list[str]:
    """Generate SEIP/PLIC interaction tests.

    Tests interaction between software mip.SEIP writes and PLIC hardware SEIP.
    Note: SEIP not implemented on platform - all tests expected 0%.
    """
    covergroup = "InterruptsS_S_cg"

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "SEIP Interaction Tests",
            _generate_sei_interaction_tests.__doc__,
        ),
        "",
    ]

    # === cp_sei1: csrrw to set mip.SEIP ===
    lines.extend(
        [
            "",
            "# cp_sei1: Use csrrw to set mip.SEIP (PLIC inactive)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8 # MIE=0",
            "CSRW(mideleg, zero) # mideleg=0",
            "RVTEST_CLR_SEXT_INT # Clear PLIC",
            f"LI(x{r_scratch}, 0x200) # SEIP bit",
            test_data.add_testcase("csrrw_set", "cp_sei1", covergroup),
            f"CSRRW(zero, mip, x{r_scratch}) # Write SEIP=1",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT",
            "",
        ]
    )

    # === cp_sei2: csrrs to set mip.SEIP ===
    lines.extend(
        [
            "# cp_sei2: Use csrrs to set mip.SEIP (PLIC inactive)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "RVTEST_CLR_SEXT_INT",
            f"LI(x{r_scratch}, 0x200)",
            test_data.add_testcase("csrrs_set", "cp_sei2", covergroup),
            f"CSRRS(zero, mip, x{r_scratch}) # Set SEIP=1",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT",
            "",
        ]
    )

    # === cp_sei3: PLIC sets mip.SEIP ===
    lines.extend(
        [
            "# cp_sei3: PLIC sets mip.SEIP",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mip, zero) # Clear software SEIP",
            "RVTEST_CLR_SEXT_INT",
            test_data.add_testcase("plic_set", "cp_sei3", covergroup),
            "RVTEST_SET_SEXT_INT # PLIC sets SEIP",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT",
            "",
        ]
    )

    # === cp_sei4: csrrc clears mip.SEIP (PLIC inactive, software wrote 1) ===
    lines.extend(
        [
            "# cp_sei4: Use csrrc to clear mip.SEIP (software wrote 1, PLIC inactive)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "RVTEST_CLR_SEXT_INT",
            f"LI(x{r_scratch}, 0x200)",
            f"CSRRS(zero, mip, x{r_scratch}) # First set SEIP=1 via software",
            "nop",
            test_data.add_testcase("csrrc_clr_sw", "cp_sei4", covergroup),
            f"CSRRC(zero, mip, x{r_scratch}) # Clear SEIP",
            "nop",
            "nop",
            "",
        ]
    )

    # === cp_sei5: csrrc fails to clear (PLIC active, software wrote 1) ===
    lines.extend(
        [
            "# cp_sei5: Try csrrc to clear mip.SEIP (software wrote 1, PLIC active)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "RVTEST_CLR_SEXT_INT",
            f"LI(x{r_scratch}, 0x200)",
            f"CSRRS(zero, mip, x{r_scratch}) # Software sets SEIP=1",
            "RVTEST_SET_SEXT_INT # PLIC also sets SEIP",
            "nop",
            test_data.add_testcase("csrrc_fail_plic", "cp_sei5", covergroup),
            f"CSRRC(zero, mip, x{r_scratch}) # Try to clear - should fail",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT",
            "",
        ]
    )

    # === cp_sei6: Turn off PLIC (no software write) ===
    lines.extend(
        [
            "# cp_sei6: Turn off PLIC.SEIP (software never wrote 1)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mip, zero) # No software write",
            "RVTEST_SET_SEXT_INT # PLIC sets SEIP",
            "nop",
            test_data.add_testcase("plic_off_nosw", "cp_sei6", covergroup),
            "RVTEST_CLR_SEXT_INT # Turn off PLIC",
            "nop",
            "nop",
            "",
        ]
    )

    # === cp_sei7: Turn off PLIC (software wrote 1) ===
    lines.extend(
        [
            "# cp_sei7: Turn off PLIC.SEIP (software wrote 1)",
            "RVTEST_GOTO_MMODE",
            "CSRW(mie, zero)",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            f"LI(x{r_scratch}, 0x200)",
            f"CSRRS(zero, mip, x{r_scratch}) # Software sets SEIP=1",
            "RVTEST_SET_SEXT_INT # PLIC also sets SEIP",
            "nop",
            test_data.add_testcase("plic_off_sw", "cp_sei7", covergroup),
            "RVTEST_CLR_SEXT_INT # Turn off PLIC",
            "nop",
            "nop",
            "CSRW(mip, zero) # Final cleanup",
            "",
        ]
    )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_global_ie_tests(test_data: TestData) -> list[str]:
    """Generate global interrupt enable tests.

    Test MIE and SIE interaction with M-mode interrupts.
    Cross: MIE={0,1} × SIE={0,1} × M-interrupts (MSIP, MTIP, MEIP)
    2 × 2 × 3 = 12 bins (4 achievable with only MTIP)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_global_ie"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_global_ie",
            _generate_global_ie_tests.__doc__,
        ),
        "",
    ]

    # M-mode interrupts
    m_interrupts = [
        ("msip", 0x008, 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("mtip", 0x080, 0x080, None, None, True),
        ("meip", 0x800, 0x800, "RVTEST_SET_MEXT_INT", "RVTEST_CLR_MEXT_INT", False),
    ]

    # Cross: MIE × SIE × M-interrupts
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for int_name, mip_bit, mie_bit, int_set, int_clr, is_timer in m_interrupts:
                binname = f"mie{mie_val}_sie{sie_val}_{int_name}"

                lines.extend(
                    [
                        "",
                        f"# Test: MIE={mie_val}, SIE={sie_val}, {int_name}",
                        "RVTEST_GOTO_MMODE",
                        "CSRW(mie, zero)",
                        "csrci mstatus, 8 # MIE=0",
                        "csrci mstatus, 2 # SIE=0",
                    ]
                )

                lines.extend(
                    [
                        "# Clear all interrupts",
                        f"LI(x{r_scratch}, 0x202)",
                        f"CSRC(mip, x{r_scratch})",
                        "RVTEST_CLR_MSW_INT",
                        "RVTEST_CLR_MEXT_INT",
                    ]
                )
                lines.extend(clr_stimer_mmode(r_scratch))
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                lines.append("# Set mideleg=0 (no delegation)")
                lines.append("CSRW(mideleg, zero)")

                lines.extend(
                    [
                        "# Enable matching interrupt in mie",
                        f"LI(x{r_scratch}, {hex(mie_bit)})",
                        f"CSRW(mie, x{r_scratch})",
                    ]
                )

                if mie_val:
                    lines.append("# Set MIE")
                    lines.append("csrsi mstatus, 8")

                if sie_val:
                    lines.append("# Set SIE")
                    lines.append("csrsi mstatus, 2")

                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                lines.append("# Set interrupt pending")
                if is_timer:
                    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
                else:
                    lines.extend([int_set, "nop"])

                lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

                lines.extend(
                    [
                        "# Cleanup",
                        "RVTEST_GOTO_MMODE",
                        "csrci mstatus, 8",
                        "csrci mstatus, 2",
                        "CSRW(mideleg, zero)",
                        "CSRW(mie, zero)",
                    ]
                )

                lines.append("# Clear interrupt")
                if is_timer:
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
                else:
                    lines.append(int_clr)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_user_mti_tests(test_data: TestData) -> list[str]:
    """Generate U-mode MTIP tests.

    Test MTIP from U-mode with mideleg=0 (not delegated).
    Cross: MIE={0,1} × SIE={0,1} × mtvec.MODE={0,1} × MTIP={0,1}
    2 × 2 × 2 × 2 = 16 bins
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_user_mti"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_user_mti",
            _generate_user_mti_tests.__doc__,
        ),
        "",
    ]

    # Cross: MIE × SIE × mtvec.MODE × MTIP
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mtvec_mode in [0, 1]:
                for set_timer in [False, True]:
                    timer_name = "mtip1" if set_timer else "mtip0"
                    binname = f"mie{mie_val}_sie{sie_val}_vec{mtvec_mode}_{timer_name}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, mtvec.MODE={mtvec_mode}, timer={set_timer}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8 # MIE=0",
                            "csrci mstatus, 2 # SIE=0",
                        ]
                    )

                    lines.append("# Clear timer interrupt")
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    lines.append("# Clear mideleg (not delegated)")
                    lines.append("CSRW(mideleg, zero)")

                    lines.extend(
                        [
                            "# Set both mtvec and stvec MODE",
                            f"CSRR x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {mtvec_mode}",
                            f"CSRW(mtvec, x{r_scratch})",
                            f"CSRR x{r_scratch}, stvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {mtvec_mode}",
                            f"CSRW(stvec, x{r_scratch})",
                        ]
                    )

                    lines.extend(
                        [
                            "# Enable MTIE",
                            f"LI(x{r_scratch}, 0x80) # MTIE",
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    if mie_val:
                        lines.append("# Set MIE")
                        lines.append("csrsi mstatus, 8")

                    if sie_val:
                        lines.append("# Set SIE")
                        lines.append("csrsi mstatus, 2")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    if set_timer:
                        lines.append("# Set MTIP if needed")
                        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
                        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

                    lines.extend(
                        [
                            "# Enter U-mode (interrupt fires immediately or when timer matures)",
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
                        ]
                    )

                    lines.extend(
                        [
                            "# Cleanup",
                            "RVTEST_GOTO_MMODE",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            "CSRW(mideleg, zero)",
                            "CSRW(mie, zero)",
                        ]
                    )
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_user_msi_tests(test_data: TestData) -> list[str]:
    """Generate U-mode MSIP tests.

    Test MSIP from U-mode with mideleg=0 (not delegated).
    Cross: MIE={0,1} × SIE={0,1} × stvec.MODE={0,1} × MSIP={0,1}
    2 × 2 × 2 × 2 = 16 bins
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_user_msi"

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_user_msi",
            _generate_user_msi_tests.__doc__,
        ),
        "",
    ]

    # Cross: MIE × SIE × stvec.MODE × MSIP
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for stvec_mode in [0, 1]:
                for set_msip in [False, True]:
                    msip_name = "msip1" if set_msip else "msip0"
                    binname = f"mie{mie_val}_sie{sie_val}_vec{stvec_mode}_{msip_name}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, stvec.MODE={stvec_mode}, MSIP={set_msip}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8 # MIE=0",
                            "csrci mstatus, 2 # SIE=0",
                        ]
                    )

                    lines.append("# Clear MSIP")
                    lines.append("RVTEST_CLR_MSW_INT")

                    lines.append("# Clear mideleg (not delegated)")
                    lines.append("CSRW(mideleg, zero)")

                    lines.extend(
                        [
                            "# Set both mtvec and stvec MODE",
                            f"CSRR x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                            f"CSRW(mtvec, x{r_scratch})",
                            f"CSRR x{r_scratch}, stvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                            f"CSRW(stvec, x{r_scratch})",
                        ]
                    )

                    lines.extend(
                        [
                            "# Enable MSIE",
                            f"LI(x{r_scratch}, 0x8) # MSIE",
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    if sie_val:
                        lines.append("# Set SIE")
                        lines.append("csrsi mstatus, 2")

                    if mie_val:
                        lines.append("# Set MIE")
                        lines.append("csrsi mstatus, 8")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Set MSIP BEFORE setting MIE (critical order!)
                    if set_msip:
                        lines.extend(["RVTEST_SET_MSW_INT", "nop", "nop", "nop", "nop"])

                    lines.extend(
                        [
                            "# Enter U-mode",
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    nop",
                            "    nop",
                        ]
                    )

                    # For MIE=1 + MSIP=1: Set MSIP in U-mode (wait - can't do this!)
                    # Software interrupt is immediate, not delayed like timer
                    # This case is IMPOSSIBLE to hit correctly

                    lines.extend(
                        [
                            "# Cleanup",
                            "RVTEST_GOTO_MMODE",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            "CSRW(mideleg, zero)",
                            "CSRW(mie, zero)",
                            "RVTEST_CLR_MSW_INT",
                        ]
                    )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_user_mei_tests(test_data: TestData) -> list[str]:
    """Generate U-mode MEIP tests.

    Test MEIP from U-mode with mideleg=0 (not delegated).
    Cross: MIE={0,1} × SIE={0,1} × stvec.MODE={0,1} × MEIP={0,1}
    2 × 2 × 2 × 2 = 16 bins
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_user_mei"

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_user_mei",
            _generate_user_mei_tests.__doc__,
        ),
        "",
    ]

    # Cross: MIE × SIE × stvec.MODE × MEIP
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for stvec_mode in [0, 1]:
                for set_meip in [False, True]:
                    meip_name = "meip1" if set_meip else "meip0"
                    binname = f"mie{mie_val}_sie{sie_val}_vec{stvec_mode}_{meip_name}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, stvec.MODE={stvec_mode}, MEIP={set_meip}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8 # MIE=0",
                            "csrci mstatus, 2 # SIE=0",
                        ]
                    )

                    lines.append("# Clear MEIP")
                    lines.append("RVTEST_CLR_MEXT_INT")

                    lines.append("# Clear mideleg (not delegated)")
                    lines.append("CSRW(mideleg, zero)")

                    lines.extend(
                        [
                            "# Set both mtvec and stvec MODE",
                            f"CSRR x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                            f"CSRW(mtvec, x{r_scratch})",
                            f"CSRR x{r_scratch}, stvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                            f"CSRW(stvec, x{r_scratch})",
                        ]
                    )

                    lines.extend(
                        [
                            "# Enable MEIE",
                            f"LI(x{r_scratch}, 0x800) # MEIE",
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    if sie_val:
                        lines.append("# Set SIE")
                        lines.append("csrsi mstatus, 2")

                    if mie_val:
                        lines.append("# Set MIE")
                        lines.append("csrsi mstatus, 8")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    if set_meip:
                        lines.append("# Set MEIP")
                        lines.extend(["RVTEST_SET_MEXT_INT", "nop", "nop", "nop", "nop"])

                    lines.extend(
                        [
                            "# Enter U-mode",
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    nop",
                            "    nop",
                        ]
                    )

                    lines.extend(
                        [
                            "# Cleanup",
                            "RVTEST_GOTO_MMODE",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            "CSRW(mideleg, zero)",
                            "CSRW(mie, zero)",
                            "RVTEST_CLR_MEXT_INT",
                        ]
                    )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_user_sei_tests(test_data: TestData) -> list[str]:
    """Generate SEIP tests for cp_sei_handled_m and cp_sei_handled_s.

    Cross: MIE={0,1} x SIE={0,1} x stvec.MODE={0,1} x mideleg.SEI={0,1}

    MIE=0: set SEIP in M-mode + wait, then enter U-mode → SEIP fires from U-mode (MPP=U).
    MIE=1: enter U-mode first, set SEIP from U-mode → fires from U-mode (MPP=U).
           Writing to SIG_ADDRESS in M-mode with MIE=1 traps in M-mode (MPP=M) instead.

    Part 2: S-mode entry with SIE=1 before SEIP fires covers cp_sei_handled_s
            SIE=1+SEIP=0 bins (sampled while in S-mode before the trap arrives).
    """
    covergroup = "InterruptsS_S_cg"

    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_sei_handled",
            _generate_user_sei_tests.__doc__,
        ),
        "",
    ]

    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for stvec_mode in [0, 1]:
                for mideleg_sei in [0, 1]:
                    deleg_name = "deleg" if mideleg_sei else "nodeleg"
                    coverpoint = "cp_user_sei_handled_m" if not mideleg_sei else "cp_user_sei_handled_s"
                    binname = f"mie{mie_val}_sie{sie_val}_vec{stvec_mode}_{deleg_name}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, stvec.MODE={stvec_mode}, mideleg.SEI={mideleg_sei}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            "RVTEST_CLR_SEXT_INT",
                        ]
                    )

                    if mideleg_sei:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200)",
                                f"CSRW(mideleg, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.append("CSRW(mideleg, zero)")

                    lines.extend(
                        [
                            "# Set both mtvec and stvec MODE",
                            f"CSRR x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                            f"CSRW(mtvec, x{r_scratch})",
                            f"CSRR x{r_scratch}, stvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                            f"CSRW(stvec, x{r_scratch})",
                        ]
                    )

                    lines.extend(
                        [
                            "# Enable SEIE; MPP=U here (from prior GOTO_MMODE via ecall) → fires SEIP=0 bins",
                            f"LI(x{r_scratch}, 0x200)",
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    if mie_val:
                        lines.extend(
                            [
                                "# Set MIE+MPIE so MIE=1 persists through MRET into U-mode",
                                f"LI(x{r_scratch}, 0x88)",
                                f"CSRS(mstatus, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                "# Clear MIE+MPIE",
                                f"LI(x{r_scratch}, 0x88)",
                                f"CSRC(mstatus, x{r_scratch})",
                            ]
                        )

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    if mie_val == 0:
                        # MIE=0: set SEIP in M-mode and wait; no trap since MIE=0,
                        # SEIP stays pending when we enter U-mode
                        lines.extend(["RVTEST_SET_SEXT_INT", f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})"])
                        lines.extend(["RVTEST_GOTO_LOWER_MODE Umode", f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})"])
                    else:
                        # MIE=1: enter U-mode first, then set SEIP from U-mode so
                        # the Sail latency expires in U-mode → trap fires with MPP=U
                        lines.extend(["RVTEST_GOTO_LOWER_MODE Umode"])
                        lines.extend(["    RVTEST_SET_SEXT_INT", f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})"])

                    lines.extend(
                        [
                            "RVTEST_GOTO_MMODE",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            "CSRW(mideleg, zero)",
                            "CSRW(mie, zero)",
                            "RVTEST_CLR_SEXT_INT",
                        ]
                    )

    # Part 2: S-mode entry with SIE=1 before SEIP fires covers
    # cp_sei_handled_s SIE=1+SEIP=0 bins (sampled while in S-mode before trap)
    for stvec_mode in [0, 1]:
        binname = f"smode_sie1_vec{stvec_mode}_deleg"
        lines.extend(
            [
                "",
                f"# S-mode SIE=1+SEIP=0 bins, stvec.MODE={stvec_mode}",
                "RVTEST_GOTO_MMODE",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
                "RVTEST_CLR_SEXT_INT",
                f"LI(x{r_scratch}, 0x200)",
                f"CSRW(mideleg, x{r_scratch})",
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                f"CSRW(mtvec, x{r_scratch})",
                f"CSRR x{r_scratch}, stvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                f"CSRW(stvec, x{r_scratch})",
                f"LI(x{r_scratch}, 0x200)",
                f"CSRW(mie, x{r_scratch})",
                "csrsi mstatus, 2",
                f"LI(x{r_scratch}, 0x88)",
                f"CSRC(mstatus, x{r_scratch})",
            ]
        )
        lines.append(test_data.add_testcase(binname, "cp_user_sei_handled_s", covergroup))
        lines.extend(
            [
                "RVTEST_SET_SEXT_INT",
                "RVTEST_GOTO_LOWER_MODE Smode",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "csrci mstatus, 2",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
                "RVTEST_CLR_SEXT_INT",
            ]
        )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_wfi_u_tests(test_data: TestData) -> list[str]:
    """Generate U-mode WFI tests.

    Test WFI from U-mode with MTIP.
    Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × TW=0
    TW=0 (WFI works)
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6)

    lines = [
        comment_banner(
            "cp_wfi_u",
            _generate_wfi_u_tests.__doc__,
        ),
        "",
    ]

    # Cross: MIE × SIE × mideleg × TW = 0
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mideleg_val in [0, 1]:
                mideleg_name = ["nodeleg", "deleg"][mideleg_val]
                binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}"

                coverpoint = "cp_wfi_u"

                lines.extend(
                    [
                        "",
                        f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}",
                        "RVTEST_GOTO_MMODE",
                        "CSRW(mie, zero)",
                        "csrci mstatus, 8 # MIE=0",
                        "csrci mstatus, 2 # SIE=0",
                    ]
                )

                lines.append("# Clear timer interrupt")
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                lines.append("# Write mideleg value based on bins")
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
                        "# Clear mstatus.TW",
                        f"LI(x{r_scratch}, 0x200000)",
                        f"CSRC(mstatus, x{r_scratch})",
                    ]
                )

                lines.extend(
                    [
                        "# Enable MTIE",
                        f"LI(x{r_scratch}, 0x80) # MTIE",
                        f"CSRW(mie, x{r_scratch})",
                    ]
                )

                if mie_val:
                    lines.extend(
                        [
                            "# Set MIE+MPIE so MIE=1 persists through MRET into U-mode",
                            f"LI(x{r_scratch}, 0x88)",
                            f"CSRS(mstatus, x{r_scratch})",
                        ]
                    )

                if sie_val:
                    lines.append("# Set SIE")
                    lines.append("csrsi mstatus, 2")

                lines.append("# Set timer to fire soon (delayed)")
                lines.extend(set_mtimer_int_soon(r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_stce))

                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                lines.extend(
                    [
                        "# Enter U-mode and execute WFI",
                        "RVTEST_GOTO_LOWER_MODE Umode",
                        "    wfi # TW=0: waits, TW=1: illegal instruction",
                        "    nop",
                        "    nop",
                    ]
                )

                lines.extend(
                    [
                        "# Cleanup",
                        "RVTEST_GOTO_MMODE",
                        "csrci mstatus, 8",
                        "csrci mstatus, 2",
                        f"LI(x{r_scratch}, 0x200000)",
                        f"CSRC(mstatus, x{r_scratch})",
                        "CSRW(mideleg, zero)",
                        "CSRW(mie, zero)",
                    ]
                )
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_wfi_timeout_u_tests(test_data: TestData) -> list[str]:
    """Generate U-mode WFI timeout tests.

    Test WFI timeout from U-mode with TW=1.
    Cross: MIE={0,1} × SIE={0,1}
    - mideleg = ones
    - TW = 1
    - MTIE = 1 (fixed - required for timeout mechanism)
    - MTIMECMP = max (no interrupt fires)
    - WFI times out → illegal instruction → M-mode trap
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_wfi_timeout_u"

    r_temp, r_stimecmp, r_scratch = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            "cp_wfi_timeout_u",
            _generate_wfi_timeout_u_tests.__doc__,
        ),
        "",
    ]

    # Cross: MIE × SIE (MTIE=1 fixed)
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            binname = f"mie{mie_val}_sie{sie_val}"

            lines.extend(
                [
                    "",
                    f"# Test: MIE={mie_val}, SIE={sie_val}",
                    "RVTEST_GOTO_MMODE",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8 # MIE=0",
                    "csrci mstatus, 2 # SIE=0",
                ]
            )

            lines.extend(
                [
                    "# Clear all interrupts",
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            lines.extend(
                [
                    "# Set mideleg = ones",
                    f"LI(x{r_scratch}, 0x222)",
                    f"CSRW(mideleg, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Set TW=1 (timeout enabled)",
                    f"LI(x{r_scratch}, 0x200000) # TW bit (bit 21)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Enable MTIE=1 (required for timeout to work)",
                    f"LI(x{r_scratch}, 0x80) # MTIE",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            lines.extend(
                [
                    "# Set MTIMECMP to max (no interrupt fires)",
                    f"LA(x{r_temp}, RVMODEL_MTIMECMP_ADDRESS)",
                    f"LI(x{r_scratch}, -1)",
                    f"SREG x{r_scratch}, 0(x{r_temp})",
                ]
            )

            if mie_val:
                lines.extend(
                    [
                        "# Set MIE+MPIE so MIE=1 persists through MRET into U-mode",
                        f"LI(x{r_scratch}, 0x88)",
                        f"CSRS(mstatus, x{r_scratch})",
                    ]
                )

            if sie_val:
                lines.append("# Set SIE")
                lines.append("csrsi mstatus, 2")

            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            lines.extend(
                [
                    "# Enter U-mode and execute WFI",
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    "    wfi # Times out → illegal instruction → trap to M-mode",
                    "    nop",
                ]
            )

            lines.extend(
                [
                    "# Cleanup",
                    "RVTEST_GOTO_MMODE",
                    "csrci mstatus, 8",
                    "csrci mstatus, 2",
                    f"LI(x{r_scratch}, 0x200000)",
                    f"CSRC(mstatus, x{r_scratch}) # Clear TW",
                    "CSRW(mideleg, zero)",
                    "CSRW(mie, zero)",
                ]
            )
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_temp, r_stimecmp, r_scratch])
    return lines


@add_priv_test_generator("InterruptsS", required_extensions=["Sm", "S", "I", "Zicsr"])
def make_interruptss_s(test_data: TestData) -> list[str]:
    """Generate supervisor-mode interrupt tests.

    Covers STIP, SSIP, and SEIP across S-mode, M-mode, and U-mode scenarios,
    including trigger conditions, delegation, priority, vectoring, and WFI.
    Individual test groups are enabled incrementally as they are validated.
    """
    r_temp = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "InterruptsS_S",
            "Supervisor-mode interrupt tests\nTests S-mode interrupts (STIP, SSIP, SEIP) with M→S delegation",
        ),
        "#define SET_SSW_INT(_R1, _R2)  LI(_R1, 0x2);  CSRS(mip, _R1);",
        "#define CLR_SSW_INT(_R1, _R2)  LI(_R1, 0x2);  CSRC(mip, _R1);",
        "#define SET_SEXT_INT(_R1, _R2)  LI(_R1, 0x200);  CSRS(mip, _R1);",
        "#define CLR_SEXT_INT(_R1, _R2)  LI(_R1, 0x200);  CSRC(mip, _R1);",
        "# Initial setup - clear mideleg (no U-mode delegation)",
        "CSRW(mideleg, zero)",
        f"LI(x{r_temp}, 0x200000) # Clear TW bit",
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
    lines.extend(_generate_priority_mideleg_tests(test_data))
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
