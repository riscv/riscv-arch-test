"""Supervisor-mode interrupt test generator for RISC-V privileged architecture.

This module generates tests for supervisor-mode interrupts (STIP, SSIP, SEIP)
following the exact pattern of InterruptsSm and InterruptsU.
"""

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import (
    clr_mtimer_int,
    clr_stimer_int,
    set_mtimer_int,
)
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

# def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
#     """Generate STIP trigger tests.

#     With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
#     and mie = 1s (all interrupt enables), trigger STIP and change to supervisor mode.
#     Cross: mideleg x SIE (2x2 = 4 bins)
#     """
#     covergroup = "InterruptsS_S_cg"
#     coverpoint = "cp_trigger_sti"

#     r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[0, 2])

#     lines = [
#         comment_banner(
#             "cp_trigger_sti",
#             "Trigger STIP (supervisor timer interrupt)\n"
#             "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}\n"
#             "With mstatus.MIE=0, mie=all 1s",
#         ),
#         "",
#     ]

#     # Cross: mideleg x SIE
#     for mideleg_val in [0, 1]:  # 0=no delegation, 1=delegate all S-interrupts
#         for sie_val in [0, 1]:
#             mideleg_name = ["nodeleg", "deleg"][mideleg_val]
#             sie_name = f"sie_{sie_val}"
#             binname = f"{mideleg_name}_{sie_name}"

#             lines.extend([
#                 "",
#                 "# Setup delegation and interrupt enables",
#                 "csrci mstatus, 8",  # Clear MIE (MIE=0 required by test plan)
#             ])

#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch))
#             lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

#             # Set mideleg
#             if mideleg_val:
#                 lines.extend([
#                     f"LI(x{r_scratch}, 0x222)",
#                     f"CSRW(mideleg, x{r_scratch})",
#                 ])
#             else:
#                 lines.append("CSRW(mideleg, zero)")

#             # Set SPIE (for SIE after sret)
#             lines.extend([
#                 f"LI(x{r_scratch}, 0x20)",
#                 f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
#             ])

#             # Enable ALL interrupts in mie
#             lines.extend([
#                 f"LI(x{r_scratch}, -1)",
#                 f"CSRW(mie, x{r_scratch})",
#             ])

#             # In M-mode before entering S-mode: Read STCE
#             lines.extend([
#                 "# Pre-read menvcfg.STCE in M-mode",
#                 f"CSRR x{r_stce}, menvcfg",
#                 "#if __riscv_xlen == 64",
#                 f"    srli x{r_stce}, x{r_stce}, 63",
#                 "#else",
#                 f"    srli x{r_stce}, x{r_stce}, 31",
#                 "#endif",
#                 f"andi x{r_stce}, x{r_stce}, 0x1",
#             ])

#             # Enter S-mode FIRST
#             lines.extend([
#                 test_data.add_testcase(binname, coverpoint, covergroup),
#                 "RVTEST_GOTO_LOWER_MODE Smode",
#             ])

#             # NOPs in S-mode for STIP=0 coverage
#             for _ in range(40):
#                 lines.append("    nop")

#             # NOW trigger STIP while already IN S-mode
#             # Call with pre-read STCE value
#             lines.extend(["    " + line for line in set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce)])

#             lines.extend([
#                 "RVTEST_IDLE_FOR_INTERRUPT",
#                 # "RVTEST_GOTO_MMODE",
#                 "nop",
#             ])

#             # NOPs in S-mode for STIP=0 coverage
#             for _ in range(40):
#                 lines.append("    nop")

#             lines.extend([
#                 # "RVTEST_IDLE_FOR_INTERRUPT",
#                 "RVTEST_GOTO_MMODE",
#                 "nop",
#             ])

#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch))

#     test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
#     return lines

# def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
#     """Generate STIP trigger tests.

#     With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
#     and mie = 1s (all interrupt enables), trigger STIP and change to supervisor mode.
#     Cross: mideleg x SIE (2x2 = 4 bins)
#     """
#     covergroup = "InterruptsS_S_cg"
#     coverpoint = "cp_trigger_sti"

#     r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[0, 2])

#     lines = [
#         comment_banner(
#             "cp_trigger_sti",
#             "Trigger STIP (supervisor timer interrupt)\n"
#             "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}\n"
#             "With mstatus.MIE=0, mie=all 1s",
#         ),
#         "",
#     ]

#     # Cross: mideleg x SIE
#     for mideleg_val in [0, 1]:  # 0=no delegation, 1=delegate all S-interrupts
#         for sie_val in [0, 1]:
#             mideleg_name = ["nodeleg", "deleg"][mideleg_val]
#             sie_name = f"sie_{sie_val}"
#             binname = f"{mideleg_name}_{sie_name}"

#             # === M-MODE SETUP ===
#             lines.extend([
#                 "",
#                 "# M-mode setup",
#                 "csrci mstatus, 8",  # MIE=0
#             ])

#             # Clear all timers first
#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch))
#             lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

#             # Set mideleg
#             if mideleg_val:
#                 lines.extend([
#                     f"LI(x{r_scratch}, 0x222)",  # Delegate STI+SEI+SSI
#                     f"CSRW(mideleg, x{r_scratch})",
#                 ])
#             else:
#                 lines.append("CSRW(mideleg, zero)")

#             # Set SPIE (controls SIE after sret)
#             lines.extend([
#                 f"LI(x{r_scratch}, 0x20)",  # SPIE bit
#                 f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
#             ])

#             # Enable all interrupts in mie
#             lines.extend([
#                 f"LI(x{r_scratch}, -1)",  # All interrupts
#                 f"CSRW(mie, x{r_scratch})",
#             ])

#             # Read menvcfg.STCE (needed for timer operations in S-mode)
#             lines.extend([
#                 "# Read menvcfg.STCE",
#                 f"CSRR x{r_stce}, menvcfg",
#                 "#if __riscv_xlen == 64",
#                 f"    srli x{r_stce}, x{r_stce}, 63",
#                 "#else",
#                 f"    srli x{r_stce}, x{r_stce}, 31",
#                 "#endif",
#                 f"andi x{r_stce}, x{r_stce}, 0x1",
#             ])

#             # === ENTER S-MODE ===
#             lines.extend([
#                 test_data.add_testcase(binname, coverpoint, covergroup),
#                 "RVTEST_GOTO_LOWER_MODE Smode",
#             ])

#             # NOPs in S-mode for STIP=0 coverage
#             for _ in range(40):
#                 lines.append("    nop")

#             # Set timer WHILE IN S-mode (uses pre-read STCE)
#             lines.extend(["    " + line for line in set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce)])

#             # Wait for interrupt (or not)
#             lines.append("RVTEST_IDLE_FOR_INTERRUPT")

#             # Clear timer BEFORE returning to M-mode (prevents spurious interrupt)
#             lines.extend([
#                 "",
#                 "# Clear timer before M-mode return",
#                 f"beqz x{r_stce}, 3f",  # Skip if STCE=0 (legacy needs M-mode)
#                 "# Sstc: Clear stimecmp from S-mode",
#                 f"    LI(x{r_temp}, -1)",
#                 f"    csrw stimecmp, x{r_temp}",
#                 "#if __riscv_xlen == 32",
#                 f"    csrw stimecmph, x{r_temp}",
#                 "#endif",
#                 "3:",
#             ])

#             # Return to M-mode
#             lines.extend([
#                 "RVTEST_GOTO_MMODE",
#                 "csrci mstatus, 8",  # Immediately disable MIE
#             ])

#             # Final cleanup in M-mode
#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch))
#             lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

#     test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
#     return lines


# def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
#     """Generate STIP trigger tests.

#     With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
#     and mie = 1s (all interrupt enables), trigger STIP and change to supervisor mode.
#     Cross: mideleg x SIE (2x2 = 4 bins)
#     """
#     covergroup = "InterruptsS_S_cg"
#     coverpoint = "cp_trigger_sti"

#     r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[0, 2])

#     lines = [
#         comment_banner(
#             "cp_trigger_sti",
#             "Trigger STIP (supervisor timer interrupt)\n"
#             "Cross: mideleg={0/STI+SEI+SSI}ma x mstatus.SIE={0/1}\n"
#             "With mstatus.MIE=0, mie=all 1s",
#         ),
#         "",
#     ]

#     # Cross: mideleg x SIE
#     for mideleg_val in [0, 1]:  # 0=no delegation, 1=delegate all S-interrupts
#         for sie_val in [0, 1]:
#             mideleg_name = ["nodeleg", "deleg"][mideleg_val]
#             sie_name = f"sie_{sie_val}"
#             binname = f"{mideleg_name}_{sie_name}"

#             # === M-MODE SETUP ===
#             lines.extend(
#                 [
#                     "",
#                     "# M-mode setup",
#                     "csrci mstatus, 8",  # MIE=0
#                 ]
#             )

#             # Clear all timers first
#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
#             lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

#             # Set mideleg
#             if mideleg_val:
#                 lines.extend(
#                     [
#                         f"LI(x{r_scratch}, 0x222)",  # Delegate STI+SEI+SSI
#                         f"CSRW(mideleg, x{r_scratch})",
#                     ]
#                 )
#             else:
#                 lines.append("CSRW(mideleg, zero)")

#             # Set SPIE (controls SIE after sret)
#             # lines.extend([
#             #     f"LI(x{r_scratch}, 0x20)",  # SPIE bit
#             #     f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
#             # ])
#             lines.extend(
#                 [
#                     f"LI(x{r_scratch}, 0x02)",  # SIE bit 1, not SPIE!
#                     f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
#                 ]
#             )

#             # Enable all interrupts in mie
#             lines.extend(
#                 [
#                     f"LI(x{r_scratch}, -1)",  # All interrupts
#                     f"CSRW(mie, x{r_scratch})",
#                 ]
#             )

#             # Read menvcfg.STCE (needed for timer operations in S-mode)
#             lines.extend(
#                 [
#                     "# Read menvcfg.STCE",
#                     f"CSRR x{r_stce}, menvcfg",
#                     "#if __riscv_xlen == 64",
#                     f"    srli x{r_stce}, x{r_stce}, 63",
#                     "#else",
#                     f"    srli x{r_stce}, x{r_stce}, 31",
#                     "#endif",
#                     f"andi x{r_stce}, x{r_stce}, 0x1",
#                 ]
#             )

#             # === ENTER S-MODE ===
#             lines.extend(
#                 [
#                     test_data.add_testcase(binname, coverpoint, covergroup),
#                     "RVTEST_GOTO_LOWER_MODE Smode",
#                 ]
#             )

#             # TODO: adding this for now to get sie in s-mode:
#             # NOW set SIE in S-mode based on sie_val
#             # if sie_val:
#             #     lines.append("    csrsi sstatus, 2")  # Set SIE (bit 1 of sstatus)
#             # else:
#             #     lines.append("    csrci sstatus, 2")  # Clear SIE (bit 1 of sstatus)

#             # NOPs in S-mode for STIP=0 coverage
#             lines.extend(
#                 [
#                     f"    LI(x{r_scratch}, 20)",  # 2500 iterations × 2 instructions = 5000 cycles
#                     f"1:  addi x{r_scratch}, x{r_scratch}, -1",
#                     f"    bnez x{r_scratch}, 1b",
#                 ]
#             )

#             # Set timer WHILE IN S-mode (pass r_stce explicitly)
#             lines.extend(["    " + line for line in set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce)])

#             # More NOPs for STIP=1 coverage before interrupt fires
#             lines.extend(
#                 [
#                     f"    LI(x{r_scratch}, 2500)",  # 2500 iterations × 2 instructions = 5000 cycles
#                     f"1:  addi x{r_scratch}, x{r_scratch}, -1",
#                     f"    bnez x{r_scratch}, 1b",
#                 ]
#             )

#             # Wait for interrupt (or not)
#             lines.append("RVTEST_IDLE_FOR_INTERRUPT")

#             # Clear timer BEFORE returning to M-mode (prevents spurious interrupt)
#             lines.extend(
#                 [
#                     "",
#                     "# Clear timer before M-mode return",
#                     f"beqz x{r_stce}, 3f",  # Skip if STCE=0 (legacy needs M-mode)
#                     "# Sstc: Clear stimecmp from S-mode",
#                     f"    LI(x{r_temp}, -1)",
#                     f"    csrw stimecmp, x{r_temp}",
#                     "#if __riscv_xlen == 32",
#                     f"    csrw stimecmph, x{r_temp}",
#                     "#endif",
#                     "3:",
#                 ]
#             )

#             # Return to M-mode
#             lines.extend(
#                 [
#                     "RVTEST_GOTO_MMODE",
#                     "csrci mstatus, 8",  # Immediately disable MIE
#                 ]
#             )

#             # Final cleanup in M-mode
#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
#             lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

#     test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
#     return lines

# worshsipping this, one above is more og
# def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
#     """Generate STIP trigger tests.

#     With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
#     and mie = 1s (all interrupt enables), mip.STIP=1, change to supervisor mode.
#     Cross: mideleg x SIE (2x2 = 4 bins)
#     """
#     covergroup = "InterruptsS_S_cg"
#     coverpoint = "cp_trigger_sti"

#     r_scratch = test_data.int_regs.get_registers(1, exclude_regs=[0, 2])[0]

#     lines = [
#         comment_banner(
#             "cp_trigger_sti",
#             "Trigger STIP (supervisor timer interrupt)\n"
#             "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}\n"
#             "With mstatus.MIE=0, mie=all 1s, mip.STIP=1",
#         ),
#         "",
#     ]

#     # Cross: mideleg x SIE
#     for mideleg_val in [0, 1]:
#         for sie_val in [0, 1]:
#             mideleg_name = ["nodeleg", "deleg"][mideleg_val]
#             sie_name = f"sie_{sie_val}"
#             binname = f"{mideleg_name}_{sie_name}"

#             # === M-MODE SETUP (safe order) ===
#             lines.extend([
#                 "",
#                 "# M-mode setup",
#                 "CSRW(mie, zero)",  # 1. Disable ALL interrupts first
#                 "csrci mstatus, 8",  # 2. MIE=0
#                 f"LI(x{r_scratch}, 0x20)",  # 3. Clear any pending STIP
#                 f"CSRC(mip, x{r_scratch})",
#                 "csrci mstatus, 2",  # 3. SIE=0 (clear first)
#             ])

#             lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch))
#             lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

#             # 4. Set mideleg
#             if mideleg_val:
#                 lines.extend([
#                     f"LI(x{r_scratch}, 0x222)",  # Delegate STI+SEI+SSI
#                     f"CSRW(mideleg, x{r_scratch})",
#                 ])
#             else:
#                 lines.append("CSRW(mideleg, zero)")

#             # 5. Enable all interrupts in mie (but MIE still 0)
#             lines.extend([
#                 f"LI(x{r_scratch}, -1)",
#                 f"CSRW(mie, x{r_scratch})",
#             ])

#             # 6. Set SIE in mstatus (last step before STIP)
#             lines.extend([
#                 f"LI(x{r_scratch}, 0x02)",  # SIE bit
#                 f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
#             ])

#             # 7. Set STIP (test plan: "mip.STIP=1")
#             # lines.extend([
#             #     test_data.add_testcase(binname, coverpoint, covergroup),
#             #     f"LI(x{r_scratch}, 0x20)",  # STIP bit
#             #     f"CSRS(mip, x{r_scratch})",
#             #     "nop",
#             # ])

#             # 8. Enter S-mode (test plan: "change to supervisor mode")
#             lines.extend([
#                 "RVTEST_GOTO_LOWER_MODE Smode",
#                 "nop",
#                 "nop",
#                 "nop",
#             ])

#             # 9. Return and cleanup
#             lines.extend([
#                 "RVTEST_GOTO_MMODE",
#                 "csrci mstatus, 8",  # Disable MIE
#                 f"LI(x{r_scratch}, 0x20)",
#                 f"CSRC(mip, x{r_scratch})",  # Clear STIP
#             ])

#     test_data.int_regs.return_registers([r_scratch])
#     return lines


def _generate_trigger_sti_tests(test_data: TestData) -> list[str]:
    """Generate STIP trigger tests.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    and mie = 1s (all interrupt enables), trigger STIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sti"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_sti",
            "Trigger STIP (supervisor timer interrupt)\n"
            "Cross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}\n"
            "With mstatus.MIE=0, mie=all 1s",
        ),
        "",
    ]

    # Cross: mideleg x SIE
    for mideleg_val in [0, 1]:
        for sie_val in [0, 1]:
            mideleg_name = ["nodeleg", "deleg"][mideleg_val]
            sie_name = f"sie_{sie_val}"
            binname = f"{mideleg_name}_{sie_name}"

            # === M-MODE SETUP (safe order) ===
            lines.extend(
                [
                    "",
                    "# M-mode setup",
                    "CSRW(mie, zero)",  # 1. Disable ALL interrupts first
                    "csrci mstatus, 8",  # 2. MIE=0
                    "csrci mstatus, 2",  # 3. SIE=0 (clear first)
                ]
            )

            # Clear timers
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

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
                ]
            )

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
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",  # SIE bit
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                ]
            )

            # 8. Set STIP directly (we're in M-mode, can write mip directly)
            lines.extend(
                [
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    f"LI(x{r_scratch}, 0x20)",  # STIP bit
                    f"CSRS(mip, x{r_scratch})",  # Set mip.STIP=1
                    "nop",
                ]
            )

            # 8. Set STIP using timer functions
            # lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
            # lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))
            lines.append("nop")

            # 9. Enter S-mode
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "nop",
                    "nop",
                    "nop",
                ]
            )

            # lines.extend(set_stimer_int(r_mtime, r_temp, r_temp2, r_scratch, r_stce))

            lines.extend(
                [
                    f"    LI(x{r_scratch}, 2500)",  # 2500 iterations × 2 instructions = 5000 cycles
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
                ]
            )

            # 10. Return and cleanup
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "# Complete state cleanup",
                    "csrci mstatus, 8",  # Clear MIE
                    "csrci mstatus, 2",  # Clear SIE
                    "CSRW(mideleg, zero)",  # Clear delegation
                    "CSRW(mie, zero)",  # Clear all interrupt enables
                    f"LI(x{r_scratch}, 0x20)",  # Clear STIP
                    f"CSRC(mip, x{r_scratch})",
                ]
            )

            # Clear timer
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_trigger_ssi_mip_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger tests via mip.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    set mip.SSIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_ssi_mip"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_ssi_mip",
            "Trigger SSIP via mip.SSIP\nCross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}",
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
                    f"LI(x{r_scratch}, 0x20)",  # SPIE
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x02)",  # SSIE bit (bit 1)
                    f"CSRW(mie, x{r_scratch})",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Set mip.SSIP",
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mip, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    "# Clear mip.SSIP",
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_trigger_ssi_sip_tests(test_data: TestData) -> list[str]:
    """Generate SSIP trigger tests via sip.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    write sip.SSIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_ssi_sip"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

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
                    f"LI(x{r_scratch}, 0x20)",
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRW(mie, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Write sip.SSIP from S-mode",
                    f"LI(x{r_scratch}, 0x02)",
                    f"csrs sip, x{r_scratch})",
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
    """Generate SEIP trigger tests via external interrupt controller.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    use PLIC/EIC to trigger SEIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_sei",
            "Trigger SEIP via external interrupt controller\nCross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}",
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
                    f"LI(x{r_scratch}, 0x20)",
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x200)",  # SEIE bit (bit 9)
                    f"CSRW(mie, x{r_scratch})",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "RVTEST_SET_SEXT_INT",  # Platform-specific macro
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    "RVTEST_CLR_SEXT_INT",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_trigger_sei_seip_tests(test_data: TestData) -> list[str]:
    """Generate SEIP trigger tests via mip.SEIP.

    With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/STI+SEI+SSI},
    write mip.SEIP and change to supervisor mode.
    Cross: mideleg x SIE (2x2 = 4 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_sei_seip"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_sei_seip",
            "Set SEIP via mip.SEIP\nCross: mideleg={0/STI+SEI+SSI} x mstatus.SIE={0/1}",
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
                    f"LI(x{r_scratch}, 0x20)",
                    f"{'CSRS' if sie_val else 'CSRC'}(mstatus, x{r_scratch})",
                    f"LI(x{r_scratch}, 0x200)",
                    f"CSRW(mie, x{r_scratch})",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Set mip.SEIP",
                    f"LI(x{r_scratch}, 0x200)",
                    f"CSRS(mip, x{r_scratch})",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "RVTEST_IDLE_FOR_INTERRUPT",
                    "RVTEST_GOTO_MMODE",
                    "nop",
                    "# Clear mip.SEIP",
                    f"LI(x{r_scratch}, 0x200)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_changingtos_sti_tests(test_data: TestData) -> list[str]:
    """Generate STI interrupt trigger when changing to S-mode.

    With mstatus.MIE=0, mstatus.SIE=0, mideleg={STI+SEI+SSI}, mie=1s,
    set mip.STIP, change to supervisor mode, then enable sstatus.SIE.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_changingtos_sti"

    r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_changingtos_sti",
            "Trigger STIP when changing to S-mode\nSet STIP, enter S-mode with SIE=0, then enable SIE",
        ),
        "",
        "# Setup: mideleg=all, mie=all, MIE=0, SIE=0",
        f"LI(x{r_scratch}, 0x222)",
        f"CSRW(mideleg, x{r_scratch})",
        f"LI(x{r_scratch}, -1)",
        f"CSRW(mie, x{r_scratch})",
        "csrci mstatus, 8",  # MIE=0
        f"LI(x{r_scratch}, 0x20)",  # SPIE
        f"CSRC(mstatus, x{r_scratch})",  # SIE will be 0 after sret
        test_data.add_testcase("sti_changingtos", coverpoint, covergroup),
        "# Set STIP",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        f"LA(x{r_stimecmp}, RVMODEL_STIMECMP_ADDRESS)",
    ]

    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))

    lines.extend(
        [
            "# Enter S-mode with SIE=0",
            "RVTEST_GOTO_LOWER_MODE Smode",
            "# Now in S-mode, enable SIE",
            "csrsi sstatus, 2",  # sstatus.SIE bit 1
            "RVTEST_IDLE_FOR_INTERRUPT",
            "RVTEST_GOTO_MMODE",
            "nop",
        ]
    )

    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    test_data.int_regs.return_registers([r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch])
    return lines


def _generate_changingtos_ssi_tests(test_data: TestData) -> list[str]:
    """Generate SSI interrupt trigger when changing to S-mode."""
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_trigger_changingtos_ssi"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

    lines = [
        comment_banner(
            "cp_trigger_changingtos_ssi",
            "Trigger SSIP when changing to S-mode",
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

    r_scratch = test_data.int_regs.get_register(exclude_regs=[0, 2])

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
    """Generate interrupt cross-product tests.

    Cross of mstatus.MIE = 0, mtvec.MODE = 00, mideleg={0/STI+SEI+SSI},
    6 walking 1s in mie, 6 walking 1s in mip, change to supervisor mode.
    (2 x 6 x 6 = 72 bins)
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_interrupts_s"

    r_mtime, r_stimecmp, r_temp, r_temp2, r_mie_val, r_scratch = test_data.int_regs.get_registers(
        6, exclude_regs=[0, 2]
    )

    lines = [
        comment_banner(
            "cp_interrupts_s",
            "Cross product: mideleg x mie x mip\n2 x 6 x 6 = 72 bins",
        ),
        "",
    ]

    # mideleg: 0 (no delegation) or 1 (delegate all S-interrupts)
    for mideleg_val in [0, 1]:
        mideleg_name = ["nodeleg", "deleg"][mideleg_val]

        lines.extend(
            [
                "",
                f"# mideleg = {mideleg_name}",
                "csrci mstatus, 8",  # MIE=0
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
            "cp_vectored_s",
            "Vectored interrupt mode tests\nCross: stvec.MODE x interrupt type (2 x 6 = 12 bins)",
        ),
        "",
    ]

    # Test both direct (00) and vectored (01) modes
    for mode in [0, 1]:
        mode_name = ["direct", "vectored"][mode]

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

    Test supervisor-mode interrupts with delegation from M-mode.
    All tests execute in S-mode after proper mideleg setup.
    """
    r_temp = test_data.int_regs.get_register(exclude_regs=[0, 2])

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

    # Generate all test functions
    lines.extend(_generate_trigger_sti_tests(test_data))
    # lines.extend(_generate_trigger_ssi_mip_tests(test_data))
    # lines.extend(_generate_trigger_ssi_sip_tests(test_data))
    # lines.extend(_generate_trigger_sei_tests(test_data))
    # lines.extend(_generate_trigger_sei_seip_tests(test_data))
    # lines.extend(_generate_changingtos_sti_tests(test_data))
    # lines.extend(_generate_changingtos_ssi_tests(test_data))
    # lines.extend(_generate_changingtos_sei_tests(test_data))
    # lines.extend(_generate_interrupts_s_tests(test_data))
    # lines.extend(_generate_vectored_s_tests(test_data))

    return lines
