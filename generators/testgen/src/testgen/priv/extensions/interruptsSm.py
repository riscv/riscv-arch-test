##################################
# priv/extensions/interruptsSm.py
#
# InterruptsSm privileged extension test generator.
# sanarayanan@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""InterruptsSm privileged extension test generator for machine-mode interrupts."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_trigger_mti_tests(test_data: TestData) -> list[str]:
    """Generate timer interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_mti"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_mti",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use MTIMECMP to cause mip.MTIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0 should NOT take interrupt
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            "    RVMODEL_SET_MTIMER_INT     # trigger timer interrupt",
            "    RVMODEL_CLR_MTIMER_INT     # reset mtimecmp (no interrupt fired)",
            f"    # x{r1} should still be 1 since no interrupt",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1 should take interrupt
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            "    RVMODEL_SET_MTIMER_INT     # interrupt fires, handler runs",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_trigger_msi_tests(test_data: TestData) -> list[str]:
    """Generate software interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_msi"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_msi",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use CLINT.MSIP to cause mip.MSIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0 should NOT take interrupt
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            "    RVMODEL_SET_MSW_INT        # trigger software interrupt",
            "    RVMODEL_CLR_MSW_INT        # clear it (no interrupt fired)",
            f"    # x{r1} should still be 1 since no interrupt",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1 should take interrupt
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            "    RVMODEL_SET_MSW_INT        # interrupt fires, handler runs",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_trigger_mei_tests(test_data: TestData) -> list[str]:
    """Generate machine-mode external interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_mei"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_mei",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use PLIC to cause mip.MEIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0 should NOT take interrupt
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            "    RVMODEL_SET_MEXT_INT",
            "    RVMODEL_CLR_MEXT_INT",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1 should take interrupt
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            "    RVMODEL_SET_MEXT_INT",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
    """Generate supervisor timer interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_sti"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_sti",
            "With mstatus.MIE = {0/1}, and mie = all 1s, write mip.STIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            f"    LI x{r2}, 32               # 1 in bit 5",
            f"    CSRRS x{r2}, mip, x{r2}    # set mip.STIP",
            f"    CSRRC x{r2}, mip, x{r2}    # reset mip.STIP",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            f"    LI x{r2}, 32               # 1 in bit 5",
            f"    CSRRS x{r2}, mip, x{r2}    # set mip.STIP, expect interrupt",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_trigger_ssi_mip_tests(test_data: TestData) -> list[str]:
    """Generate supervisor software interrupt trigger tests via MIP."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_ssi_mip"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_ssi_mip",
            "With mstatus.MIE = {0/1}, and mie = all 1s, write mip.SSIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            f"    CSRRSI x{r2}, mip, 2       # set mip.SSIP",
            f"    CSRRCI x{r2}, mip, 2       # reset mip.SSIP",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            f"    CSRRSI x{r2}, mip, 2       # set mip.SSIP, expect interrupt",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_trigger_sei_plic_tests(test_data: TestData) -> list[str]:
    """Generate supervisor external interrupt trigger tests via PLIC."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_sei_plic"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_sei_plic",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use PLIC to cause mip.SEIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            "    RVMODEL_SET_SEXT_INT",
            "    RVMODEL_CLR_SEXT_INT",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            "    RVMODEL_SET_SEXT_INT",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_trigger_sei_sie_tests(test_data: TestData) -> list[str]:
    """Generate supervisor external interrupt trigger tests via SIE."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_sei_sie"
    ######################################

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_trigger_sei_sie",
            "With mstatus.MIE = {0/1}, and mie = all 1s, write mip.SEIP",
        ),
        "",
        f"LI x{r1}, -1               # all 1s",
        f"CSRRW x{r2}, mie, x{r1}    # enable all interrupts",
        "",
    ]

    # Test 1: mstatus.MIE = 0
    lines.extend(
        [
            test_data.add_testcase(coverpoint, "mie_0", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRCI x{r2}, mstatus, 8   # mstatus.MIE = 0",
            f"    LI x{r2}, 512              # 1 in bit 9",
            f"    CSRRS x{r2}, mip, x{r2}    # set mip.SEIP",
            f"    CSRRC x{r2}, mip, x{r2}    # reset mip.SEIP",
            write_sigupd(r1, test_data),
        ]
    )

    # Test 2: mstatus.MIE = 1
    lines.extend(
        [
            "",
            test_data.add_testcase(coverpoint, "mie_1", covergroup),
            f"    LI x{r1}, 1                # success code",
            f"    CSRRSI x{r2}, mstatus, 8   # mstatus.MIE = 1",
            f"    LI x{r2}, 512              # 1 in bit 9",
            f"    CSRRS x{r2}, mip, x{r2}    # set mip.SEIP, expect interrupt",
            f"    LI x{r1}, -1               # trap handler skips this",
            write_sigupd(r1, test_data),
        ]
    )

    test_data.int_regs.return_registers([r1, r2])
    return lines


def _generate_interrupt_cross_tests(test_data: TestData) -> list[str]:
    """Generate interrupt cross-product tests (mstatus.MIE x mtvec.MODE x mip x mie)."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_interrupts"
    ######################################

    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_interrupts",
            "Cross of mstatus.MIE = {0/1}, mtvec.MODE = 00, 3 walking 1s in mip.MTIP/MSIP/MEIP,\n"
            "3 walking 1s in mie.MTIE/MSIE/MEIE (2 x 3 x 3 bins)",
        ),
        "",
        "CSRRCI t6, mtvec, 3     # mtvec.MODE = 00",
    ]

    # Unroll: mstatus.MIE x mie enables x mip pending
    for mstatus_mie in [1, 0]:
        if mstatus_mie == 0:
            lines.append("CSRRCI t6, mstatus, 8   # mstatus.MIE = 0")
        else:
            lines.append("CSRRSI t6, mstatus, 8   # mstatus.MIE = 1")

        # 3 interrupt enables: s1 = 2 (MEIE), 1 (MTIE), 0 (MSIE)
        for s1 in [2, 1, 0]:
            mie_bit = 3 + s1 * 4
            mie_val = 1 << mie_bit
            enable_name = ["msie", "mtie", "meie"][s1]

            lines.extend(
                [
                    f"LI t4, {mie_val}            # enable {enable_name.upper()}",
                    "CSRRW t6, mie, t4       # set enable, clear others",
                ]
            )

            # 3 interrupt pending: s2 = 2 (MEIP), 1 (MTIP), 0 (MSIP)
            for s2 in [2, 1, 0]:
                int_name = ["msip", "mtip", "meip"][s2]
                binname = f"mie_{mstatus_mie}_{int_name}_{enable_name}"

                lines.extend(
                    [
                        test_data.add_testcase(coverpoint, binname, covergroup),
                        f"    LI x{r1}, 1             # success flag",
                        "    CSRR t6, mie            # save mie (trap clears it)",
                    ]
                )

                if s2 == 2:  # MEIP
                    lines.extend(["    RVMODEL_SET_MEXT_INT", "    RVMODEL_CLR_MEXT_INT"])
                elif s2 == 1:  # MTIP
                    lines.extend(["    RVMODEL_SET_MTIMER_INT", "    RVMODEL_CLR_MTIMER_INT"])
                else:  # MSIP
                    lines.extend(["    RVMODEL_SET_MSW_INT", "    RVMODEL_CLR_MSW_INT"])

                if mstatus_mie == 1 and s1 == s2:  # Interrupt should fire
                    lines.append(f"    LI x{r1}, -1            # trap handler skips this")

                lines.extend(
                    [
                        "    CSRW mie, t6            # restore mie",
                        write_sigupd(r1, test_data),
                        "",
                    ]
                )

    test_data.int_regs.return_registers([r1])
    return lines


def _generate_vectored_tests(test_data: TestData) -> list[str]:
    """Generate vectored interrupt mode tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_vectored"
    ######################################

    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_vectored",
            "Cross of mtvec.MODE = 01, mstatus.MIE=1, all 3 of mie.MTIE/MSIE/MEIE,\n"
            "3 walking 1s in mip.MTIP/MSIP/MEIP (3 bins)",
        ),
        "",
        "CSRRCI t6, mtvec, 3",
        "CSRRSI t6, mtvec, 1     # mtvec.MODE = 01",
        "CSRRSI t6, mstatus, 8   # mstatus.MIE = 1",
        "CSRRW t6, mie, zero     # clear all enables",
        "LI s1, 0x888            # MEIE/MTIE/MSIE",
        "CSRRS t6, mie, s1       # enable all three",
    ]

    # Raise each interrupt type: s2 = 2 (MEIP), 1 (MTIP), 0 (MSIP)
    for s2 in [2, 1, 0]:
        int_name = ["msip", "mtip", "meip"][s2]

        lines.extend(
            [
                test_data.add_testcase(coverpoint, int_name, covergroup),
                f"    LI x{r1}, 1             # success flag",
                "    CSRR t6, mie            # save mie",
            ]
        )

        if s2 == 2:  # MEIP
            lines.extend(["    RVMODEL_SET_MEXT_INT", "    RVMODEL_CLR_MEXT_INT"])
        elif s2 == 1:  # MTIP
            lines.extend(["    RVMODEL_SET_MTIMER_INT", "    RVMODEL_CLR_MTIMER_INT"])
        else:  # MSIP
            lines.extend(["    RVMODEL_SET_MSW_INT", "    RVMODEL_CLR_MSW_INT"])

        lines.extend(
            [
                f"    LI x{r1}, -1            # trap handler skips this",
                "    CSRW mie, t6            # restore mie",
                write_sigupd(r1, test_data),
            ]
        )

    test_data.int_regs.return_registers([r1])
    return lines


def _generate_priority_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_priority"
    ######################################

    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_priority",
            "With mstatus.MIE = 1, write cross product of 8 values of mie.{MSIE/MTIE/MEIE}\n"
            "with hardware events giving the 8 values of mip.{MSIP/MTIP/MEIP} (8 x 8 bins)",
        ),
        "",
        "CSRRSI t6, mstatus, 8   # mstatus.MIE = 1",
    ]

    # Unroll s1 loop: 7 down to 0 (mie values)
    for s1 in range(7, -1, -1):
        # Build mie value from s1
        lines.extend(
            [
                "CSRRW t6, mie, zero     # clear all enables",
                f"LI t0, {s1 & 4}         # check bit 2",
                "slli t0, t0, 9          # mie.MEIE position",
                "mv s3, t0",
                f"LI t0, {s1 & 2}         # check bit 1",
                "slli t0, t0, 6          # mie.MTIE position",
                "or s3, s3, t0",
                f"LI t0, {s1 & 1}         # check bit 0",
                "slli t0, t0, 3          # mie.MSIE position",
                "or s3, s3, t0",
            ]
        )

        # Unroll s2 loop: 7 down to 0 (mip values)
        for s2 in range(7, -1, -1):
            binname = f"mie_{s1:03b}_mip_{s2:03b}"

            lines.extend(
                [
                    test_data.add_testcase(coverpoint, binname, covergroup),
                    f"    LI x{r1}, 1             # success flag",
                ]
            )

            # Trigger interrupts based on s2
            if s2 & 4:  # bit 2: MEIP
                lines.append("    RVMODEL_SET_MEXT_INT")
            if s2 & 2:  # bit 1: MTIP
                lines.append("    RVMODEL_SET_MTIMER_INT")
            if s2 & 1:  # bit 0: MSIP
                lines.append("    RVMODEL_SET_MSW_INT")

            lines.append("    CSRRS t6, mie, s3       # enable interrupts")

            # Check if any interrupt should fire
            if (s1 & s2) != 0:  # If any enabled interrupt is pending
                lines.append(f"    LI x{r1}, -1            # trap handler skips this")

            lines.extend(
                [
                    "    CSRRC t6, mie, s3       # disable for next test",
                    "    RVMODEL_CLR_MEXT_INT",
                    "    RVMODEL_CLR_MTIMER_INT",
                    "    RVMODEL_CLR_MSW_INT",
                    write_sigupd(r1, test_data),
                ]
            )

    test_data.int_regs.return_registers([r1])
    return lines


def _generate_wfi_tests(test_data: TestData) -> list[str]:
    """Generate WFI instruction tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_wfi"
    ######################################

    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_wfi",
            "Cross Product of mstatus.MIE = {0/1}, mstatus.TW = {0/1}, mie.MTIE = 1\n"
            "Set MTIMECMP = TIME + 0x100 to interrupt in the future\n"
            "WFI instruction",
        ),
    ]

    # Unroll s2 loop: 3 down to 0
    for s2 in range(3, -1, -1):
        mie_val = (s2 >> 1) & 1  # bit 1
        tw_val = s2 & 1  # bit 0
        binname = f"mie_{mie_val}_tw_{tw_val}"

        lines.extend(
            [
                test_data.add_testcase(coverpoint, binname, covergroup),
                f"    LI x{r1}, 1             # success flag",
                "    LI t0, 0x20000A",
                "    CSRRC t6, mstatus, t0   # clear TW, MIE, SIE",
            ]
        )

        # Set MIE if bit 1 is set
        if s2 & 2:
            lines.append("    CSRRSI t6, mstatus, 8   # set mstatus.MIE")

        # Set TW if bit 0 is set
        if s2 & 1:
            lines.extend(
                [
                    "    LA t0, 0x200000",
                    "    CSRRS t6, mstatus, t0   # set mstatus.TW",
                ]
            )

        lines.extend(
            [
                "    LI t0, 0x80",
                "    CSRRW t6, mie, t0       # set mie.MTIE = 1",
                "    RVMODEL_SET_MTIMER_INT_SOON",
                "    nop",
                "    wfi",
                "    nop",
            ]
        )

        # If MIE=1, interrupt will fire
        if mie_val == 1:
            lines.append(f"    LI x{r1}, -1            # trap handler skips this")

        lines.append(write_sigupd(r1, test_data))

    test_data.int_regs.return_registers([r1])
    return lines


@add_priv_test_generator("InterruptsSm", extensions=["Sm", "I", "Zicsr"])
def make_interruptssm(test_data: TestData) -> list[str]:
    """Generate tests for InterruptsSm machine-mode interrupts."""
    lines: list[str] = [
        "",
        "RVMODEL_CLR_MTIMER_INT",
        "",
    ]

    lines.extend(_generate_trigger_mti_tests(test_data))
    lines.extend(_generate_trigger_msi_tests(test_data))
    lines.extend(_generate_trigger_mei_tests(test_data))

    lines.extend(_generate_trigger_sti_tests(test_data))
    lines.extend(_generate_trigger_ssi_mip_tests(test_data))
    lines.extend(_generate_trigger_sei_plic_tests(test_data))
    lines.extend(_generate_trigger_sei_sie_tests(test_data))

    lines.extend(_generate_interrupt_cross_tests(test_data))
    lines.extend(_generate_vectored_tests(test_data))
    lines.extend(_generate_priority_tests(test_data))
    lines.extend(_generate_wfi_tests(test_data))

    return lines
