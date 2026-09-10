##################################
# priv/extensions/InterruptsSSm.py
#
# InterruptsS privileged extension test generator.
# ellyu@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_int,
    clr_stimer_mmode,
    set_menvcfg_stce,
    set_mtimer_int,
    set_mtimer_int_soon,
    set_stimecmp_max,
    set_stimecmp_zero,
    set_stimer_mmode,
)
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_interrupts_m_tests(test_data: TestData) -> list[str]:
    """Generate interrupt tests in M-mode.

    Cross: MIE={0,1} × mideleg={0,0x222} × 6 mip walking × 6 mie walking
    Total: 2 × 2 × 6 × 6 = 144 bins

    Routes to:
    - cp_interrupts_m: Non-delegated (mideleg=0) OR M-interrupts (always M-mode)
    - cp_interrupts_m_deleg: Delegated interrupts (mideleg=0xAAA + MSIP/MTIP/MEIP/SSIP/STIP/SEIP)
    """
    covergroup = "InterruptsSSm_cg"

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
        ("msip", 0x008, 0x008, "RVTEST_SET_MSW_INT_M", "RVTEST_CLR_MSW_INT_M", False),
        ("stip", 0x020, 0x020, None, None, True),
        ("mtip", 0x080, 0x080, None, None, True),
        ("seip", 0x200, 0x200, f"SET_SEXT_INT(x{r_temp}, x{r_temp2})", f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})", False),
        ("meip", 0x800, 0x800, "RVTEST_SET_MEXT_INT_M", "RVTEST_CLR_MEXT_INT_M", False),
    ]

    # S-interrupts that can be delegated
    # deleg_interrupts = {"ssip", "stip", "seip", "msip", "mtip", "meip"}

    # Loop: MIE × mideleg × mip × mie
    for mie_val in [0, 1]:
        for mideleg_val in [0, 1]:  # 0 = none, 1 = 0xAAA
            for mip_name, mip_bit, mie_bit, set_fn, clr_fn, is_timer in interrupts:
                for mie_name in ["ssie", "msie", "stie", "mtie", "seie", "meie"]:
                    # Select coverpoint
                    coverpoint = "cp_interrupts_m_deleg" if mideleg_val else "cp_interrupts_m"

                    mideleg_name = ["zeros", "ones"][mideleg_val]
                    binname = f"mie{mie_val}_{mideleg_name}_{mip_name}_{mie_name}"

                    lines.extend(
                        [
                            "",
                            "# === SETUP ===",
                            f"# MIE={mie_val}, mideleg={mideleg_name}, mip={mip_name}, mie={mie_name}",
                            "RVTEST_GOTO_MMODE",
                            "csrw mie, zero",
                            "csrci mstatus, 8 # MIE=0",
                            "csrci mstatus, 2 # SIE=0",
                        ]
                    )

                    lines.extend(
                        [
                            "# Clear all interrupts",
                            f"LI(x{r_scratch}, 0x202)",
                            f"csrc mip, x{r_scratch}",
                            "RVTEST_CLR_MSW_INT_M",
                        ]
                    )
                    lines.extend(clr_stimer_mmode(r_scratch))
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    lines.extend(
                        [
                            "# Set mtvec.MODE = 0 (direct)",
                            f"csrr x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"csrw mtvec, x{r_scratch}",
                        ]
                    )

                    lines.append("# Write mideleg value based on bins")
                    if mideleg_val == 1:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0xAAA) # MTI+MEI+MSI+STI+SEI+SSI",
                                f"csrw mideleg, x{r_scratch}",
                            ]
                        )
                    else:
                        lines.append("csrw mideleg, zero")

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
                            f"csrw mie, x{r_scratch}",
                        ]
                    )

                    if mideleg_val:
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
                                    f"csrs mip, x{r_scratch}",
                                ]
                            )
                        else:
                            lines.extend([set_fn, "nop"])

                    lines.append("# === WAIT FOR INTERRUPT ===")
                    if mideleg_val:
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
                            "csrw mideleg, zero",
                            "csrw mie, zero",
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
                                    f"csrc mip, x{r_scratch}",
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
    covergroup = "InterruptsSSm_cg"
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
                "csrw mie, zero",
                "csrci mstatus, 8 # MIE=0",
            ]
        )

        lines.extend(
            [
                "# Clear all interrupts",
                f"LI(x{r_scratch}, 0x202)",
                f"csrc mip, x{r_scratch}",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

        lines.extend(
            [
                "# Set mtvec.MODE = 1 (vectored)",
                f"csrr x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"ADDI x{r_scratch}, x{r_scratch}, 1 # MODE=1",
                f"csrw mtvec, x{r_scratch}",
            ]
        )

        lines.append("# mideleg=0 (no delegation, fire in M-mode)")
        lines.append("csrw mideleg, zero")

        lines.extend(
            [
                "# Enable all S-mode interrupts",
                f"LI(x{r_scratch}, 0x222) # SSIE, STIE, SEIE",
                f"csrw mie, x{r_scratch}",
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
                    f"csrs mip, x{r_scratch}",
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
                "csrw mideleg, zero",
                "csrw mie, zero",
            ]
        )

        lines.append("# Clear interrupt")
        if uses_timer:
            lines.extend(clr_stimer_mmode(r_scratch))
        elif int_name == "ssip":
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"csrc mip, x{r_scratch}",
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
    covergroup = "InterruptsSSm_cg"
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
                "csrw mie, zero",
                "csrci mstatus, 8 # MIE=0",
            ]
        )

        lines.extend(
            [
                "# Clear all interrupts",
                f"LI(x{r_scratch}, 0x202)",
                f"csrc mip, x{r_scratch}",
                "RVTEST_CLR_MSW_INT_M",
                "RVTEST_CLR_MEXT_INT_M",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        lines.append("# mideleg=0 (no delegation)")
        lines.append("csrw mideleg, zero")

        lines.extend(
            [
                "# Enable ALL interrupts in mie",
                f"LI(x{r_scratch}, -1)",
                f"csrw mie, x{r_scratch}",
            ]
        )

        lines.append("# Set interrupt pattern (with MIE=0, won't fire yet)")
        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

        if ssip:
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"csrs mip, x{r_scratch}",
                ]
            )
        if msip:
            lines.append("RVTEST_SET_MSW_INT_M")
        if stip:
            lines.extend(set_stimer_mmode(r_scratch))
        if mtip:
            lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        if seip:
            lines.append(f"SET_SEXT_INT(x{r_temp}, x{r_temp2})")
        if meip:
            lines.append("RVTEST_SET_MEXT_INT_M")

        lines.append("nop")

        lines.append("# Set MIE=1 (rise event - interrupt fires immediately)")
        lines.append("csrsi mstatus, 8")
        lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

        lines.extend(
            [
                "# Cleanup",
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "csrw mideleg, zero",
                "csrw mie, zero",
            ]
        )

        lines.append("# Clear interrupts")
        if ssip:
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"csrc mip, x{r_scratch}",
                ]
            )
        if msip:
            lines.append("RVTEST_CLR_MSW_INT_M")
        if stip:
            lines.extend(clr_stimer_mmode(r_scratch))
        if mtip:
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        if seip:
            lines.extend([f"CLR_SEXT_INT(x{r_temp}, x{r_temp2})"])
        if meip:
            lines.append("RVTEST_CLR_MEXT_INT_M")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mie_m_tests(test_data: TestData) -> list[str]:
    """Generate priority tests varying mie with MIE rising.

    Set MIE=0, configure all 64 mie patterns, set all mip, mideleg=0, then MIE=1.
    Tests which interrupt fires based on enable priority.
    """
    covergroup = "InterruptsSSm_cg"
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
                "csrw mie, zero",
                "csrci mstatus, 8 # MIE=0",
            ]
        )

        lines.extend(
            [
                "# Clear all interrupts",
                f"LI(x{r_scratch}, 0x202)",
                f"csrc mip, x{r_scratch}",
                "RVTEST_CLR_MSW_INT_M",
                "RVTEST_CLR_MEXT_INT_M",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        lines.append("# mideleg=0 (no delegation)")
        lines.append("csrw mideleg, zero")

        lines.extend(
            [
                "# Set specific mie pattern",
                f"LI(x{r_scratch}, {hex(mie_val)})",
                f"csrw mie, x{r_scratch}",
            ]
        )

        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
        lines.extend(
            [
                "# Set ALL interrupts (with MIE=0, won't fire yet)",
                f"LI(x{r_scratch}, 0x202)",
                f"csrs mip, x{r_scratch}",
                "RVTEST_SET_MSW_INT_M",
            ]
        )
        lines.extend(set_stimer_mmode(r_scratch))
        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        lines.extend(
            [
                "RVTEST_SET_MEXT_INT_M",
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
                "csrw mideleg, zero",
                "csrw mie, zero",
                f"LI(x{r_scratch}, 0x202)",
                f"csrc mip, x{r_scratch}",
                "RVTEST_CLR_MSW_INT_M",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        lines.extend(
            [
                "RVTEST_CLR_MEXT_INT_M",
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
    covergroup = "InterruptsSSm_cg"
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
                        "csrw mie, zero",
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
                        f"csrw mideleg, x{r_temp1}",
                    ]
                )

                lines.extend(
                    [
                        "# Enable MTIE",
                        f"LI(x{r_temp1}, 0x80) # MTIE bit",
                        f"csrs mie, x{r_temp1}",
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
                            f"csrs mstatus, x{r_temp1}",
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
                        f"csrc mstatus, x{r_temp1} # Clear TW",
                        "csrw mideleg, zero",
                        "csrw mie, zero",
                    ]
                )
                lines.extend(clr_mtimer_int(r_temp1, r_mtimecmp))

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp1, r_temp2, r_temp3, r_temp4])
    return lines


def _generate_trigger_mti_m_tests(test_data: TestData) -> list[str]:
    """Generate MTIP trigger test when MIE rises.

    Set MTIP pending with MIE=0, then set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsSSm_cg"
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
            "# Test: MTIP fires when MIE rises",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.append("# Clear timer")
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Set mideleg=0")
    lines.append("csrw mideleg, zero")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"csrw mie, x{r_scratch}",
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
            "# Set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"csrs mstatus, x{r_scratch} # MIE=1",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mie, zero",
        ]
    )
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_sip_m_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger test via SIP CSR write in M-mode.

    Write sip.SSIP, test with MIE={0,1} and mideleg.SSI={0,1}.
    4 tests total.
    """
    covergroup = "InterruptsSSm_cg"
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
                    "csrw mie, zero",
                    "csrci mstatus, 8 # MIE=0",
                ]
            )

            # Clear SSIP
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"csrc mip, x{r_scratch}",
                ]
            )

            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            if mideleg_ssi:
                lines.extend(
                    [
                        "# Set mideleg.SSI",
                        f"LI(x{r_scratch}, 0x2) # SSI bit",
                        f"csrw mideleg, x{r_scratch}",
                    ]
                )
            else:
                lines.append("csrw mideleg, zero")

            lines.extend(
                [
                    "# Enable all interrupts in mie",
                    f"LI(x{r_scratch}, -1)",
                    f"csrw mie, x{r_scratch}",
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

            # set sip.SSI
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2) # SSIP bit (bit 1)",
                    "# interrupt fires immediately on SSIP write",
                    f"csrs sip, x{r_scratch} # Set sip.SSIP",
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
                    f"csrc mip, x{r_scratch}",
                    "csrw mideleg, zero",
                    "csrw mie, zero",
                ]
            )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_msi_m_tests(test_data: TestData) -> list[str]:
    """Generate MSIP trigger test when MIE.

    Set MSIP pending with MIE=0, set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsSSm_cg"
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
            "# Test: MSIP fires when MIE rises (csrrs)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x2)",
            f"csrc mip, x{r_scratch}",
            "RVTEST_CLR_MSW_INT_M",
        ]
    )
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Clear mideleg")
    lines.append("csrw mideleg, zero")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"csrw mie, x{r_scratch}",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "# Set MSIP",
            "RVTEST_SET_MSW_INT_M",
        ]
    )

    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use csrrs to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"csrs mstatus, x{r_scratch} # Set MIE=1 via csrrs",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mie, zero",
            "RVTEST_CLR_MSW_INT_M",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_mei_m_tests(test_data: TestData) -> list[str]:
    """Generate MEIP trigger test when MIE rises via csrrs.

    Set MEIP pending with MIE=0, then use csrrs to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsSSm_cg"
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
            "# Test: MEIP fires when MIE rises (csrrs)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"csrc mip, x{r_scratch}",
            "RVTEST_CLR_MSW_INT_M",
            "RVTEST_CLR_MEXT_INT_M",
        ]
    )
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Clear mideleg")
    lines.append("csrw mideleg, zero")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"csrw mie, x{r_scratch}",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(["# Set MEIP", "RVTEST_SET_MEXT_INT_M"])
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use csrrs to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"csrrs x0, mstatus, x{r_scratch} # Set MIE=1 via csrrs",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mie, zero",
            "RVTEST_CLR_MEXT_INT_M",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_sti_m_tests(test_data: TestData) -> list[str]:
    """Generate STIP trigger test when MIE rises via csrrs.

    Set STIP pending with MIE=0, then use csrrs to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsSSm_cg"
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
            "# Test: STIP fires when MIE rises (csrrs)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"csrc mip, x{r_scratch}",
            "RVTEST_CLR_MSW_INT_M",
            "RVTEST_CLR_MEXT_INT_M",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Clear mideleg (STIP fires in M-mode)")
    lines.append("csrw mideleg, zero")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"csrw mie, x{r_scratch}",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.append("# Set STIP using M-mode direct write")
    lines.extend(set_stimer_mmode(r_scratch))
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use csrrs to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"csrrs x0, mstatus, x{r_scratch} # Set MIE=1 via csrrs",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mie, zero",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_m_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger test when MIE rises via csrrs.

    Set SSIP pending with MIE=0, mideleg=0, then use csrrs to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsSSm_cg"
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
            "# Test: SSIP fires when MIE rises (csrrs)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"csrc mip, x{r_scratch}",
            "RVTEST_CLR_MSW_INT_M",
            "RVTEST_CLR_MEXT_INT_M",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Set mideleg=0 (SSIP fires in M-mode)")
    lines.append("csrw mideleg, zero")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"csrw mie, x{r_scratch}",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "# Set SSIP",
            f"LI(x{r_scratch}, 0x2)",
            f"csrs mip, x{r_scratch}",
        ]
    )
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use csrrs to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"csrrs x0, mstatus, x{r_scratch} # Set MIE=1 via csrrs",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mie, zero",
            f"LI(x{r_scratch}, 0x2)",
            f"csrc mip, x{r_scratch}",
        ]
    )

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_sei_m_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger test when MIE rises via csrrs.

    Set SEIP pending with MIE=0, mideleg=0, then use csrrs to set MIE=1.
    Interrupt fires when MIE rises.
    """
    covergroup = "InterruptsSSm_cg"
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
            "# Test: SEIP fires when MIE rises (csrrs)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
        ]
    )

    lines.extend(
        [
            "# Clear all interrupts",
            f"LI(x{r_scratch}, 0x202)",
            f"csrc mip, x{r_scratch}",
            "RVTEST_CLR_MSW_INT_M",
            "RVTEST_CLR_MEXT_INT_M",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    lines.append("# Set mideleg=0 (SEIP fires in M-mode)")
    lines.append("csrw mideleg, zero")

    lines.extend(
        [
            "# Enable all interrupts in mie",
            f"LI(x{r_scratch}, -1)",
            f"csrw mie, x{r_scratch}",
        ]
    )

    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.append("# Set SEIP")
    lines.extend([f"SET_SEXT_INT(x{r_temp}, x{r_temp2})"])
    lines.append(f"RVTEST_IDLE_FOR_INTERRUPT(x{r_scratch})")

    lines.extend(
        [
            "# Use csrrs to set MIE=1 (interrupt fires)",
            f"LI(x{r_scratch}, 0x8) # MIE bit (bit 3)",
            f"csrrs x0, mstatus, x{r_scratch} # Set MIE=1 via csrrs",
            "nop",
            "nop",
        ]
    )

    lines.extend(
        [
            "# Cleanup",
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mie, zero",
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
    covergroup = "InterruptsSSm_cg"

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
            "csrw mie, zero",
            "csrci mstatus, 8 # MIE=0",
            "csrw mideleg, zero # mideleg=0",
            "RVTEST_CLR_SEXT_INT_M # Clear PLIC",
            f"LI(x{r_scratch}, 0x200) # SEIP bit",
            test_data.add_testcase("csrrw_set", "cp_sei1", covergroup),
            f"csrrw zero, mip, x{r_scratch} # Write SEIP=1",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT_M",
            "",
        ]
    )

    # === cp_sei2: csrrs to set mip.SEIP ===
    lines.extend(
        [
            "# cp_sei2: Use csrrs to set mip.SEIP (PLIC inactive)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "RVTEST_CLR_SEXT_INT_M",
            f"LI(x{r_scratch}, 0x200)",
            test_data.add_testcase("csrrs_set", "cp_sei2", covergroup),
            f"csrrs zero, mip, x{r_scratch} # Set SEIP=1",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT_M",
            "",
        ]
    )

    # === cp_sei3: PLIC sets mip.SEIP ===
    lines.extend(
        [
            "# cp_sei3: PLIC sets mip.SEIP",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mip, zero # Clear software SEIP",
            "RVTEST_CLR_SEXT_INT_M",
            test_data.add_testcase("plic_set", "cp_sei3", covergroup),
            "RVTEST_SET_SEXT_INT_M # PLIC sets SEIP",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT_M",
            "",
        ]
    )

    # === cp_sei4: csrrc clears mip.SEIP (PLIC inactive, software wrote 1) ===
    lines.extend(
        [
            "# cp_sei4: Use csrrc to clear mip.SEIP (software wrote 1, PLIC inactive)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "RVTEST_CLR_SEXT_INT_M",
            f"LI(x{r_scratch}, 0x200)",
            f"csrs mip, x{r_scratch} # First set SEIP=1 via software",
            "nop",
            test_data.add_testcase("csrrc_clr_sw", "cp_sei4", covergroup),
            f"csrc mip, x{r_scratch} # Clear SEIP",
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
            "csrw mie, zero",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "RVTEST_CLR_SEXT_INT_M",
            f"LI(x{r_scratch}, 0x200)",
            f"csrs mip, x{r_scratch} # Software sets SEIP=1",
            "RVTEST_SET_SEXT_INT_M # PLIC also sets SEIP",
            "nop",
            test_data.add_testcase("csrrc_fail_plic", "cp_sei5", covergroup),
            f"csrc mip, x{r_scratch} # Try to clear - should fail",
            "nop",
            "nop",
            "RVTEST_CLR_SEXT_INT_M",
            "",
        ]
    )

    # === cp_sei6: Turn off PLIC (no software write) ===
    lines.extend(
        [
            "# cp_sei6: Turn off PLIC.SEIP (software never wrote 1)",
            "RVTEST_GOTO_MMODE",
            "csrw mie, zero",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            "csrw mip, zero # No software write",
            "RVTEST_SET_SEXT_INT_M # PLIC sets SEIP",
            "nop",
            test_data.add_testcase("plic_off_nosw", "cp_sei6", covergroup),
            "RVTEST_CLR_SEXT_INT_M # Turn off PLIC",
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
            "csrw mie, zero",
            "csrci mstatus, 8",
            "csrw mideleg, zero",
            f"LI(x{r_scratch}, 0x200)",
            f"csrs mip, x{r_scratch} # Software sets SEIP=1",
            "RVTEST_SET_SEXT_INT_M # PLIC also sets SEIP",
            "nop",
            test_data.add_testcase("plic_off_sw", "cp_sei7", covergroup),
            "RVTEST_CLR_SEXT_INT_M # Turn off PLIC",
            "nop",
            "nop",
            "csrw mip, zero # Final cleanup",
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
    covergroup = "InterruptsSSm_cg"
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
        ("msip", 0x008, 0x008, "RVTEST_SET_MSW_INT_M", "RVTEST_CLR_MSW_INT_M", False),
        ("mtip", 0x080, 0x080, None, None, True),
        ("meip", 0x800, 0x800, "RVTEST_SET_MEXT_INT_M", "RVTEST_CLR_MEXT_INT_M", False),
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
                        "csrw mie, zero",
                        "csrci mstatus, 8 # MIE=0",
                        "csrci mstatus, 2 # SIE=0",
                    ]
                )

                lines.extend(
                    [
                        "# Clear all interrupts",
                        f"LI(x{r_scratch}, 0x202)",
                        f"csrc mip, x{r_scratch}",
                        "RVTEST_CLR_MSW_INT_M",
                        "RVTEST_CLR_MEXT_INT_M",
                    ]
                )
                lines.extend(clr_stimer_mmode(r_scratch))
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                lines.append("# Set mideleg=0 (no delegation)")
                lines.append("csrw mideleg, zero")

                lines.extend(
                    [
                        "# Enable matching interrupt in mie",
                        f"LI(x{r_scratch}, {hex(mie_bit)})",
                        f"csrw mie, x{r_scratch}",
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
                        "csrw mideleg, zero",
                        "csrw mie, zero",
                    ]
                )

                lines.append("# Clear interrupt")
                if is_timer:
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
                else:
                    lines.append(int_clr)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_stip_write_stimecmp_tests(test_data: TestData) -> list[str]:
    """Generate stip write test with STIMECMP implemented

    Attempt to write to mip.STIP with STIMECMP implemented
    1 bin
    """
    covergroup = "InterruptsSSm_cg"
    coverpoint = "cp_stip_write_stimecmp"

    r_temp = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            coverpoint,
            _generate_stip_write_stimecmp_tests.__doc__,
        ),
        "",
    ]
    lines.extend(
        [
            "#ifdef SSTC_SUPPORTED",
            "# set menvcfg.STCE",
            *set_menvcfg_stce(r_temp, True),
            "# clear mstatus.MIE",
            f"LI(x{r_temp}, 0x8)",
            f"csrs mstatus, x{r_temp}",
            "# clear STIP through STIMECMP",
            *set_stimecmp_max(r_temp),
            "",
            test_data.add_testcase("Write_1", coverpoint, covergroup),
            "# attempt to write mip.STIP",
            f"LI(x{r_temp}, 0x20)",
            f"csrs mip, x{r_temp}",
            f"csrr x{r_temp}, mip",
            write_sigupd(r_temp, test_data),
            "",
            "# set STIP through STIMECMP",
            *set_stimecmp_zero(),
            test_data.add_testcase("Write_0", coverpoint, covergroup),
            "# attempt to write 0 to mip.STIP",
            f"LI(x{r_temp}, 0x20)",
            f"csrc mip, x{r_temp}",
            f"csrr x{r_temp}, mip",
            write_sigupd(r_temp, test_data),
            "",
            "# Clean up: clear Supervisor timer interrupt",
            *set_stimecmp_max(r_temp),
            "#endif",
        ]
    )
    test_data.int_regs.return_registers([r_temp])
    return lines


@add_priv_test_generator(
    "InterruptsSSm",
    required_extensions=["Sm", "S"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_interruptsssm(test_data: TestData) -> list[TestChunk]:
    """Generate supervisor-mode interrupt tests running in M mode.

    The test runs in M mode, checking features that only exist if S is supported
    """
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    r_temp = test_data.int_regs.get_register()

    tc.code = [
        comment_banner(
            "InterruptsSSm",
            "Runs in M mode, testing features that only exist when S supported",
        ),
        "#define SET_SSW_INT(_R1, _R2)  LI(_R1, 0x2);  csrs mip, _R1;",
        "#define CLR_SSW_INT(_R1, _R2)  LI(_R1, 0x2);  csrc mip, _R1;",
        "#define SET_SEXT_INT(_R1, _R2)  LI(_R1, 0x200);  csrs mip, _R1;",
        "#define CLR_SEXT_INT(_R1, _R2)  LI(_R1, 0x200);  csrc mip, _R1;",
        "# Initial setup - clear mideleg (no delegation)",
        "csrw mideleg, zero",
        f"LI(x{r_temp}, 0x200000) # Clear TW bit",
        f"csrc mstatus, x{r_temp}",
        "",
    ]

    test_data.int_regs.return_registers([r_temp])

    # -----------------------------------------------------------------------
    # M-mode interrupt tests (non-delegated and delegated S-interrupts)
    # -----------------------------------------------------------------------
    tc.code.extend(_generate_interrupts_m_tests(test_data))
    tc.code.extend(_generate_vectored_m_tests(test_data))
    tc.code.extend(_generate_priority_mip_m_tests(test_data))
    tc.code.extend(_generate_priority_mie_m_tests(test_data))
    tc.code.extend(_generate_wfi_m_tests(test_data))
    tc.code.extend(_generate_trigger_mti_m_tests(test_data))
    tc.code.extend(_generate_trigger_ssi_sip_m_tests(test_data))
    tc.code.extend(_generate_trigger_msi_m_tests(test_data))
    tc.code.extend(_generate_trigger_mei_m_tests(test_data))
    tc.code.extend(_generate_trigger_sti_m_tests(test_data))
    tc.code.extend(_generate_trigger_ssi_m_tests(test_data))
    tc.code.extend(_generate_trigger_sei_m_tests(test_data))
    tc.code.extend(_generate_sei_interaction_tests(test_data))
    tc.code.extend(_generate_global_ie_tests(test_data))
    tc.code.extend(_generate_stip_write_stimecmp_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
