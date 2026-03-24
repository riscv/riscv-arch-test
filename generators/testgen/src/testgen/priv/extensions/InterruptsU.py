##################################
# priv/extensions/interruptsU.py
#
# InterruptsU privileged extension test generator.
# sanarayanan@hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""InterruptsU privileged extension test generator for user-mode interrupts."""

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, set_mtimer_int, set_mtimer_int_soon
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_user_mti_tests(test_data: TestData) -> list[str]:
    """Generate undelegated MTI interrupt tests from U-mode."""
    covergroup = "InterruptsU_cg"
    coverpoint = "cp_user_mti"

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_user_mti",
            "Undelegated MTI interrupt from U-mode\n"
            "Cross: mtvec.MODE={00/01} x mstatus.MIE={0/1}\n"
            "Should always trap to M-mode",
        ),
        "",
    ]

    # Cross: mtvec.MODE x mstatus.MIE (2x2 = 4 bins)
    for mtvec_mode in [0, 1]:
        for mstatus_mie in [0, 1]:
            mode_name = ["direct", "vectored"][mtvec_mode]
            mie_name = f"mie_{mstatus_mie}"
            binname = f"{mode_name}_{mie_name}"

            if mtvec_mode:
                lines.append("csrsi mtvec, 1")

            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",
                    f"{'CSRS' if mstatus_mie else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x80)",
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    *set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2),
                ]
            )

            for _ in range(5000):
                lines.append("    nop")

            lines.extend(
                [
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    *clr_mtimer_int(r_temp, r_mtimecmp),
                ]
            )

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch])
    return lines


def _generate_user_msi_tests(test_data: TestData) -> list[str]:
    """Generate undelegated MSI interrupt tests from U-mode."""
    covergroup = "InterruptsU_cg"
    coverpoint = "cp_user_msi"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_user_msi",
            "Undelegated MSI interrupt from U-mode\n"
            "Cross: mtvec.MODE={00/01} x mstatus.MIE={0/1}\n"
            "Should always trap to M-mode",
        ),
        "",
    ]

    for mtvec_mode in [0, 1]:
        for mstatus_mie in [0, 1]:
            mode_name = ["direct", "vectored"][mtvec_mode]
            mie_name = f"mie_{mstatus_mie}"
            binname = f"{mode_name}_{mie_name}"

            lines.extend(
                [
                    "",
                    "csrci mstatus, 8",  # Clear mstatus.MIE (bit 3)
                    "csrci mtvec, 3",  # Clear mtvec.MODE (bits 1:0)
                ]
            )

            if mtvec_mode:
                lines.append("csrsi mtvec, 1")  # Set mtvec.MODE to vectored (01)

            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",  # mstatus.MPIE bit mask (bit 7)
                    f"{'CSRS' if mstatus_mie else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x08)",  # Enable MSIE
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "RVTEST_SET_MSW_INT",
                ]
            )

            for _ in range(5000):
                lines.append("    nop")

            lines.extend(
                [
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    "RVTEST_CLR_MSW_INT",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_user_mei_tests(test_data: TestData) -> list[str]:
    """Generate undelegated MEI interrupt tests from U-mode."""
    covergroup = "InterruptsU_cg"
    coverpoint = "cp_user_mei"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_user_mei",
            "Undelegated MEI interrupt from U-mode\n"
            "Cross: mtvec.MODE={00/01} x mstatus.MIE={0/1}\n"
            "Should always trap to M-mode",
        ),
        "",
    ]

    for mtvec_mode in [0, 1]:
        for mstatus_mie in [0, 1]:
            mode_name = ["direct", "vectored"][mtvec_mode]
            mie_name = f"mie_{mstatus_mie}"
            binname = f"{mode_name}_{mie_name}"

            lines.extend(
                [
                    "",
                    "csrci mstatus, 8",  # Clear mstatus.MIE (bit 3)
                    "csrci mtvec, 3",  # Clear mtvec.MODE (bits 1:0)
                ]
            )

            if mtvec_mode:
                lines.append("csrsi mtvec, 1")  # Set mtvec.MODE to vectored (01)

            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",  # mstatus.MPIE bit mask (bit 7)
                    f"{'CSRS' if mstatus_mie else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x800)",  # Enable MEIE
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "RVTEST_SET_MEXT_INT",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_user_wfi_tests(test_data: TestData) -> list[str]:
    """Generate WFI tests from U-mode."""
    covergroup = "InterruptsU_cg"
    coverpoint = "cp_wfi"

    r_mtime, r_mtimecmp, r_temp, r_temp2, r_t1, r_t2, r_scratch = test_data.int_regs.get_registers(7, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_wfi",
            "WFI in U-mode waits for interrupt\n"
            "Cross: mstatus.MIE={0/1} x mstatus.TW={0/1}\n"
            "mie.MTIE=1, timer fires soon",
        ),
        "",
    ]

    # Cross: MIE x TW (2x2 = 4 bins)
    for mie_val in [0, 1]:
        for tw_val in [0, 1]:
            binname = f"mie_{mie_val}_tw_{tw_val}"

            lines.extend(
                [
                    "",
                    f"LI(x{r_scratch}, 0x200008)",
                    f"CSRC(mstatus, x{r_scratch})",
                ]
            )

            # Set MIE if needed
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",  # mstatus.MPIE bit mask (bit 7)
                    f"{'CSRS' if mie_val else 'CSRC'}(mstatus, x{r_scratch})",
                ]
            )

            # Set TW if needed
            if tw_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x200000)",
                        f"CSRS(mstatus, x{r_scratch})",
                    ]
                )

            # Enable MTIE
            lines.extend([f"LI(x{r_scratch}, 0x80)", f"CSRW(mie, x{r_scratch})", "RVTEST_GOTO_LOWER_MODE Umode"])

            # WFI - label right before
            lines.extend(
                [
                    *set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp, r_t1, r_t2, r_temp2),  # Set timer to fire soon
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "    wfi",
                    "    nop",
                    "    RVTEST_GOTO_MMODE",
                    *clr_mtimer_int(r_temp, r_mtimecmp),
                ]
            )

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_temp, r_temp2, r_t1, r_t2, r_scratch])
    return lines


def _generate_user_wfi_timeout_tests(test_data: TestData) -> list[str]:
    """Generate WFI timeout tests (illegal instruction) from U-mode."""
    covergroup = "InterruptsU_cg"
    coverpoint = "cp_wfi_timeout"

    r_temp, r_mtimecmp, r_scratch = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_wfi_timeout",
            "WFI in U-mode with TW=1 causes illegal instruction\n"
            "Cross: mstatus.MIE={0/1} x mie.MTIE={0/1}\n"
            "mstatus.TW=1 (fixed), timer cleared (no interrupt)",
        ),
        "",
        "# Set TW=1 for entire test block",
        f"LI(x{r_scratch}, 0x200000)",
        f"CSRS(mstatus, x{r_scratch})",
        "",
    ]

    # Cross: MIE x MTIE (2x2 = 4 bins), TW=1 fixed
    for mie_val in [0, 1]:
        for mtie_val in [0, 1]:
            binname = f"mie_{mie_val}_mtie_{mtie_val}"

            lines.extend(
                [
                    "",
                    "csrci mstatus, 8",  # Clear mstatus.MIE (bit 3)
                    f"LI(x{r_scratch}, 0x80)",
                    f"CSRC(mie, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x80)",  # mstatus.MPIE bit mask (bit 7)
                    f"{'CSRS' if mie_val else 'CSRC'}(mstatus, x{r_scratch})",
                ]
            )

            # Set MTIE if needed
            if mtie_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x80)",
                        f"CSRS(mie, x{r_scratch})",
                    ]
                )

            # Clear timer (ensure no interrupt)
            lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))

            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "wfi",
                    "nop",
                    "RVTEST_GOTO_MMODE",
                ]
            )

    test_data.int_regs.return_registers([r_temp, r_mtimecmp, r_scratch])
    return lines


@add_priv_test_generator("InterruptsU", required_extensions=["Sm", "U", "I", "Zicsr"])
def make_interruptsu(test_data: TestData) -> list[str]:
    """Generate tests for InterruptsU user-mode interrupt behavior."""

    lines: list[str] = []

    r_temp, r_mtimecmp = test_data.int_regs.get_registers(2, exclude_regs=[0])

    # Initial setup - clear any pending timer
    lines.extend(
        [
            "CSRW(mideleg, zero)",
        ]
    )
    lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))
    lines.append("")

    # Return the temporary registers
    test_data.int_regs.return_registers([r_temp, r_mtimecmp])

    # Generate all test sections
    lines.extend(_generate_user_mti_tests(test_data))
    lines.extend(_generate_user_msi_tests(test_data))
    lines.extend(_generate_user_mei_tests(test_data))
    lines.extend(_generate_user_wfi_tests(test_data))
    lines.extend(_generate_user_wfi_timeout_tests(test_data))

    return lines
