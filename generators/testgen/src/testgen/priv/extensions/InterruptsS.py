##################################
# priv/extensions/InterruptsS.py
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
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
    """Generate STIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    and mie = 1s (all interrupt enables), trigger STIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"

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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"

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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"

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
    covergroup = "InterruptsS_cg"

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
    """Generate S-mode WFI timeout tests.

    Test WFI timeout with TW=1, MTIMECMP=max.
    Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × MTIE={0,1}
    Total: 2×2×2×2 = 16 bins
    """
    covergroup = "InterruptsS_cg"

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
                    mideleg_name = ["zeros", "ones"][mideleg_val]

                    coverpoint = "cp_wfi_timeout_s"

                    binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}_mtie{mtie_val}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}, MTIE={mtie_val}",
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
                                "# Set MIE+MPIE so MIE=1 persists through MRET into lower-mode",
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
                            "RVTEST_GOTO_LOWER_MODE Smode",
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


def _generate_user_mti_tests(test_data: TestData) -> list[str]:
    """Generate U-mode MTIP tests.

    Test MTIP from U-mode with mideleg=0 (not delegated).
    Cross: MIE={0,1} × SIE={0,1} × mtvec.MODE={0,1} × MTIP={0,1}
    2 × 2 × 2 × 2 = 16 bins
    """
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"
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
    covergroup = "InterruptsS_cg"

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
    covergroup = "InterruptsS_cg"

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

    Test WFI timeout from U-mode with TW={0/1}.
    Cross: MIE={0,1} × SIE={0,1}
    - mideleg = ones
    - MTIE = 1 (fixed - required for timeout mechanism)
    - MTIMECMP = max (no interrupt fires)
    - WFI times out → illegal instruction → M-mode trap
    """
    covergroup = "InterruptsS_cg"
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
    for tw_val in [0, 1]:
        for mie_val in [0, 1]:
            for sie_val in [0, 1]:
                binname = f"mie{mie_val}_sie{sie_val}_tw{tw_val}"

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
                        f"# Write TW={tw_val}",
                        f"LI(x{r_scratch}, 0x200000) # TW bit (bit 21)",
                        f"{'CSRS' if tw_val else 'CSRC'}(mstatus, x{r_scratch})",
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


@add_priv_test_generator("InterruptsS", required_extensions=["S", "Zicsr"])
def make_interruptss_s(test_data: TestData) -> list[TestChunk]:
    """Generate supervisor-mode interrupt tests.

    Covers STIP, SSIP, and SEIP across S-mode, M-mode, and U-mode scenarios,
    including trigger conditions, delegation, priority, vectoring, and WFI.
    Individual test groups are enabled incrementally as they are validated.
    """
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    r_temp = test_data.int_regs.get_register()

    tc.code = [
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
    tc.code.extend(_generate_trigger_sti_tests(test_data))
    tc.code.extend(_generate_trigger_ssi_mip_tests(test_data))
    tc.code.extend(_generate_trigger_ssi_sip_tests(test_data))
    tc.code.extend(_generate_trigger_sei_tests(test_data))
    tc.code.extend(_generate_trigger_sei_seip_tests(test_data))
    tc.code.extend(_generate_changingtos_sti_tests(test_data))
    tc.code.extend(_generate_changingtos_ssi_tests(test_data))
    tc.code.extend(_generate_changingtos_sei_tests(test_data))
    tc.code.extend(_generate_interrupts_s_tests(test_data))
    tc.code.extend(_generate_vectored_s_tests(test_data))
    tc.code.extend(_generate_priority_mip_s_tests(test_data))
    tc.code.extend(_generate_priority_mie_s_tests(test_data))
    tc.code.extend(_generate_priority_both_s_tests(test_data))
    tc.code.extend(_generate_priority_mideleg_tests(test_data))
    tc.code.extend(_generate_wfi_s_tests(test_data))
    tc.code.extend(_generate_wfi_timeout_s_tests(test_data))

    # -----------------------------------------------------------------------
    # U-mode interrupt tests
    # -----------------------------------------------------------------------
    tc.code.extend(_generate_user_mti_tests(test_data))
    tc.code.extend(_generate_user_msi_tests(test_data))
    tc.code.extend(_generate_user_mei_tests(test_data))
    tc.code.extend(_generate_user_sei_tests(test_data))
    tc.code.extend(_generate_wfi_u_tests(test_data))
    tc.code.extend(_generate_wfi_timeout_u_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
