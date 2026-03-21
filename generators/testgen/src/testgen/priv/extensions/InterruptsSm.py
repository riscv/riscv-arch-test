##################################
# priv/extensions/interruptsSm.py
#
# InterruptsSm privileged extension test generator.
# sanarayanan@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""InterruptsSm privileged extension test generator for machine-mode interrupts."""

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, set_mtimer_int, set_mtimer_int_soon
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_trigger_mti_tests(test_data: TestData) -> list[str]:
    """Generate timer interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_mti"
    ######################################

    # Exclude: x0 (zero), x2 (sp), x5 (t0-used by macros),
    # x7 (t2-consumed by interrupt macros), x30 (t5-consumed by interrupt macros)
    r1, r_mtime, r_mtimecmp, r_temp, r_temp2 = test_data.int_regs.get_registers(5, exclude_regs=[0, 2, 7, 30])

    lines = [
        comment_banner(
            "cp_trigger_mti",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use MTIMECMP to cause mip.MTIP",
        ),
        "",
    ]

    # Setup: Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r1}, -1)                 # Enable all interrupts",
            f"CSRW mie, x{r1}               # Enable all interrupts in mie",
            "",
        ]
    )

    # Test 1: mstatus.MIE = 0 should NOT take interrupt
    lines.extend(
        [
            test_data.add_testcase("mie_0", coverpoint, covergroup),
            "CSRRCI zero, mstatus, 8    # mstatus.MIE = 0",
        ]
    )
    lines.extend(set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2))
    lines.append("RVTEST_IDLE_FOR_INTERRUPT")
    lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))
    lines.append("")

    # Test 2: mstatus.MIE = 1 should take interrupt
    lines.extend(
        [
            test_data.add_testcase("mie_1", coverpoint, covergroup),
            "CSRRSI zero, mstatus, 8    # mstatus.MIE = 1",
        ]
    )
    lines.extend(set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2))
    lines.append("RVTEST_IDLE_FOR_INTERRUPT")
    lines.append("")

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2])
    return lines


def _generate_trigger_msi_tests(test_data: TestData) -> list[str]:
    """Generate software interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_msi"
    ######################################

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_cleanup = test_data.int_regs.get_registers(
        6, exclude_regs=[0, 2, 7, 30]
    )

    lines = [
        comment_banner(
            "cp_trigger_msi",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use CLINT.MSIP to cause mip.MSIP",
        ),
        "",
    ]

    # Setup: Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r1}, -1)                 # Enable all interrupts",
            f"CSRW mie, x{r1}               # Enable all interrupts in mie",
            "",
        ]
    )

    # Test 1: mstatus.MIE = 0 should NOT take interrupt
    lines.extend(
        [
            test_data.add_testcase("mie_0", coverpoint, covergroup),
            "CSRRCI zero, mstatus, 8    # mstatus.MIE = 0",
            "RVTEST_SET_MSW_INT     # Trigger software interrupt",
            "RVTEST_IDLE_FOR_INTERRUPT",
            "RVTEST_CLR_MSW_INT     # Clear interrupt",
            "",
        ]
    )

    # Test 2: mstatus.MIE = 1 should take interrupt
    lines.extend(
        [
            test_data.add_testcase("mie_1", coverpoint, covergroup),
            "CSRRSI zero, mstatus, 8    # mstatus.MIE = 1",
            "RVTEST_SET_MSW_INT     # Interrupt fires",
            "RVTEST_IDLE_FOR_INTERRUPT",
            "",
        ]
    )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_cleanup])
    return lines


def _generate_trigger_mei_tests(test_data: TestData) -> list[str]:
    """Generate machine-mode external interrupt trigger tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_trigger_mei"
    ######################################

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2 = test_data.int_regs.get_registers(5, exclude_regs=[0, 2, 7, 30])

    lines = [
        comment_banner(
            "cp_trigger_mei",
            "With mstatus.MIE = {0/1}, and mie = all 1s, use PLIC to cause mip.MEIP",
        ),
        "",
    ]

    # Setup: Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r1}, -1)                 # Enable all interrupts",
            f"CSRW mie, x{r1}               # Enable all interrupts in mie",
            "",
        ]
    )

    # Test 1: mstatus.MIE = 0 should NOT take interrupt
    lines.extend(
        [
            test_data.add_testcase("mie_0", coverpoint, covergroup),
            "CSRRCI zero, mstatus, 8",
            "RVTEST_SET_MEXT_INT",
            "RVTEST_IDLE_FOR_INTERRUPT",
            "RVTEST_CLR_MEXT_INT",
            "",
        ]
    )

    # Test 2: mstatus.MIE = 1 should take interrupt
    lines.extend(
        [
            test_data.add_testcase("mie_1", coverpoint, covergroup),
            "CSRRSI zero, mstatus, 8",
            "RVTEST_SET_MEXT_INT",
            "RVTEST_IDLE_FOR_INTERRUPT",
            "",
        ]
    )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2])
    return lines


def _generate_interrupt_cross_tests(test_data: TestData) -> list[str]:
    """Generate interrupt cross-product tests (mstatus.MIE x mtvec.MODE x mip x mie)."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_interrupts"
    ######################################

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_mie_val, r_mie_save, r_csr_tmp = test_data.int_regs.get_registers(
        8, exclude_regs=[0, 2, 7, 30]
    )

    lines = [
        comment_banner(
            "cp_interrupts",
            "Cross of mstatus.MIE = {0/1}, mtvec.MODE = 00, 3 walking 1s in mip.MTIP/MSIP/MEIP,\n"
            "3 walking 1s in mie.MTIE/MSIE/MEIE (2 x 3 x 3 bins)",
        ),
        "",
        "csrci mtvec, 3     # Clear MODE bits (set to 00=direct)",
    ]

    # Unroll: mstatus.MIE x mie enables x mip pending
    for mstatus_mie in [1, 0]:
        if mstatus_mie == 0:
            lines.append(f"CSRRCI x{r_csr_tmp}, mstatus, 8   # mstatus.MIE = 0")
        else:
            lines.append(f"CSRRSI x{r_csr_tmp}, mstatus, 8   # mstatus.MIE = 1")

        # 3 interrupt enables: s1 = 2 (MEIE), 1 (MTIE), 0 (MSIE)
        for s1 in [2, 1, 0]:
            mie_bit = 3 + s1 * 4
            mie_val = 1 << mie_bit
            enable_name = ["msie", "mtie", "meie"][s1]

            lines.extend(
                [
                    f"LI(x{r_mie_val}, {mie_val})",
                    f"CSRW(mie, x{r_mie_val})",
                ]
            )

            # 3 interrupt pending: s2 = 2 (MEIP), 1 (MTIP), 0 (MSIP)
            for s2 in [2, 1, 0]:
                int_name = ["msip", "mtip", "meip"][s2]
                binname = f"mie_{mstatus_mie}_{int_name}_{enable_name}"

                lines.extend(
                    [
                        test_data.add_testcase(binname, coverpoint, covergroup),
                    ]
                )

                # Trigger interrupt
                if s2 == 2:  # MEIP
                    lines.append("RVTEST_SET_MEXT_INT")
                elif s2 == 1:  # MTIP
                    lines.extend(set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2))
                else:  # MSIP
                    lines.append("RVTEST_SET_MSW_INT")

                # More settling
                lines.append("RVTEST_IDLE_FOR_INTERRUPT")

                # Clear to prevent leakage
                if s2 == 2:
                    lines.append("RVTEST_CLR_MEXT_INT")
                elif s2 == 1:
                    lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))
                else:
                    lines.append("RVTEST_CLR_MSW_INT")

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_mie_val, r_mie_save, r_csr_tmp])
    return lines


def _generate_vectored_tests(test_data: TestData) -> list[str]:
    """Generate vectored interrupt mode tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_vectored"
    ######################################

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_mie_all, r_mie_save, r_csr_tmp = test_data.int_regs.get_registers(
        8, exclude_regs=[0, 2, 7, 30]
    )

    lines = [
        comment_banner(
            "cp_vectored",
            "Cross of mtvec.MODE = {00, 01}, mstatus.MIE=1, all 3 of mie.MTIE/MSIE/MEIE,\n"
            "3 walking 1s in mip.MTIP/MSIP/MEIP (2 modes x 3 interrupts = 6 bins)",
        )
    ]

    # Test BOTH modes
    for mode in [0, 1]:  # 0=direct, 1=vectored
        mode_name = ["direct", "vectored"][mode]

        lines.extend(
            [
                f"# Set mtvec.MODE = {mode:02b} ({mode_name})",
                f"CSRRCI x{r_csr_tmp}, mtvec, 3",
                f"CSRRSI x{r_csr_tmp}, mtvec, {mode}",
                f"CSRRSI x{r_csr_tmp}, mstatus, 8",
                f"LI(x{r_mie_all}, 0x888)",
                f"CSRW mie, x{r_mie_all}",
                "",
            ]
        )

        # Raise each interrupt type: s2 = 2 (MEIP), 1 (MTIP), 0 (MSIP)
        for s2 in [2, 1, 0]:
            int_name = ["msip", "mtip", "meip"][s2]

            lines.extend(
                [
                    f"CSRR x{r_mie_save}, mie",
                    test_data.add_testcase(f"{mode_name}_{int_name}", coverpoint, covergroup),
                ]
            )

            # Trigger interrupt
            if s2 == 2:  # MEIP
                lines.append("RVTEST_SET_MEXT_INT")
            elif s2 == 1:  # MTIP
                lines.extend(set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2))
            else:  # MSIP
                lines.append("RVTEST_SET_MSW_INT")

            # Settling time
            lines.extend(
                [
                    f"CSRW mie, x{r_mie_save}",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                ]
            )

            # Always clear for safety
            if s2 == 2:
                lines.append("RVTEST_CLR_MEXT_INT")
            elif s2 == 1:
                lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))
            else:
                lines.append("RVTEST_CLR_MSW_INT")

    lines.append(f"CSRRCI x{r_csr_tmp}, mtvec, 1     # restore mtvec.MODE = 00 (direct)")

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_mie_all, r_mie_save, r_csr_tmp])
    return lines


def _generate_priority_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests."""
    ######################################
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_priority"
    ######################################

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_mie_mask, r_scratch, r_csr_tmp = test_data.int_regs.get_registers(
        8, exclude_regs=[0, 2, 7, 30]
    )

    lines = [
        comment_banner(
            "cp_priority",
            "With mstatus.MIE = 1, write cross product of 8 values of mie.{MSIE/MTIE/MEIE}\n"
            "with hardware events giving the 8 values of mip.{MSIP/MTIP/MEIP} (8 x 8 bins)",
        ),
        "",
        f"CSRRSI x{r_csr_tmp}, mstatus, 8   # mstatus.MIE = 1",
    ]

    # Unroll s1 loop: 7 down to 0 (mie values)
    for s1 in range(7, -1, -1):
        # Build mie value from s1 in python
        mie_value = ((s1 & 4) << 9) | ((s1 & 2) << 6) | ((s1 & 1) << 3)

        lines.extend(
            [
                f"CSRRW x{r_csr_tmp}, mie, zero",
                f"LI(x{r_mie_mask}, {mie_value})",
            ]
        )

        # Unroll s2 loop: 7 down to 0 (mip values)
        for s2 in range(7, -1, -1):
            binname = f"mie_{s1:03b}_mip_{s2:03b}"

            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            # Conditionally trigger interrupts based on s2 bits
            if s2 & 4:  # bit 2: MEIP
                lines.append("RVTEST_SET_MEXT_INT")
            if s2 & 2:  # bit 1: MTIP
                lines.extend(set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2))
            if s2 & 1:  # bit 0: MSIP
                lines.append("RVTEST_SET_MSW_INT")

            # Just write mie directly - no mstatus manipulation!
            lines.extend(
                [
                    f"CSRW mie, x{r_mie_mask}    # Set mie atomically (interrupts enabled)",
                    "RVTEST_IDLE_FOR_INTERRUPT",  # Then interrupt fires
                ]
            )

            # Now clear all interrupts (after disabling)
            lines.append("RVTEST_CLR_MEXT_INT")
            lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))
            lines.append("RVTEST_CLR_MSW_INT")

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_mie_mask, r_scratch, r_csr_tmp])
    return lines


def _generate_wfi_tests(test_data: TestData) -> list[str]:
    """Generate WFI instruction tests."""
    covergroup = "InterruptsSm_cg"
    coverpoint = "cp_wfi"

    r_mtime, r_mtimecmp, r_t0, r_t1, r_t2, r_t3, r_scratch, r_csr_tmp = test_data.int_regs.get_registers(
        8, exclude_regs=[0, 2, 7, 30]
    )

    lines = [
        comment_banner(
            "cp_wfi",
            "Cross Product of mstatus.MIE = {0/1}, mstatus.TW = {0/1}, mie.MTIE = 1\nWFI instruction",
        ),
        "",
    ]

    for mie_val in [1, 0]:
        for tw_val in [1, 0]:
            binname = f"mie_{mie_val}_tw_{tw_val}"

            lines.extend(
                [
                    "",
                    "CSRW mie, zero",
                    "CSRW mstatus, zero",
                ]
            )
            lines.extend(clr_mtimer_int(r_t0, r_mtimecmp))

            # Set TW if needed
            mstatus_val = tw_val << 21  # TW bit, MIE=0
            lines.extend(
                [
                    f"LI(x{r_scratch}, {mstatus_val})",
                    f"csrw mstatus, x{r_scratch}",
                ]
            )

            # Enable MTIE
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",
                    f"CSRW mie, x{r_scratch}",
                ]
            )

            # Enable MIE if needed, this is set here to avoid a premature interrupt before we go into wfi
            if mie_val:
                lines.append("csrsi mstatus, 8")

            # Set timer
            lines.extend(set_mtimer_int_soon(r_mtime, r_mtimecmp, r_t0, r_t1, r_t2, r_t3))

            lines.extend(
                [
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "wfi",
                    "nop",
                ]
            )

            # Clear timer after test
            lines.extend(clr_mtimer_int(r_t0, r_mtimecmp))
            lines.append("")

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_t0, r_t1, r_t2, r_t3, r_scratch, r_csr_tmp])
    return lines


@add_priv_test_generator("InterruptsSm", required_extensions=["Sm", "I", "Zicsr"])
def make_interruptssm(test_data: TestData) -> list[str]:
    """Generate tests for InterruptsSm machine-mode interrupts."""

    # consumer t2 and t5 for interrupt subroutines, but mark as consumed for whole test since they're used throughout
    test_data.int_regs.consume_registers([7, 30])

    lines: list[str] = []

    lines.extend(_generate_trigger_mti_tests(test_data))
    lines.extend(_generate_trigger_msi_tests(test_data))
    lines.extend(_generate_trigger_mei_tests(test_data))
    lines.extend(_generate_interrupt_cross_tests(test_data))
    lines.extend(_generate_vectored_tests(test_data))
    lines.extend(_generate_priority_tests(test_data))
    lines.extend(_generate_wfi_tests(test_data))

    # Return the consumed registers before test ends
    test_data.int_regs.return_registers([7, 30])

    return lines
