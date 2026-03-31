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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

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
                ]
            )

            # 6. Set SIE (delegated) or MIE (not delegated)
            if mideleg_val == 1:
                # Delegated: set SIE
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x02)",  # SIE bit
                        f"{'CSRS' if int_enable_val else 'CSRC'}(mstatus, x{r_scratch})",
                    ]
                )
            else:
                # Not delegated: set MIE
                if int_enable_val:
                    lines.append("csrsi mstatus, 8")

            # 7. Set SSIP
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",  # SSIP bit
                    f"CSRS(mip, x{r_scratch})",  # Set via CSR write
                    "nop",
                    "nop",
                ]
            )

            # 8. Enter S-mode
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    "    nop",
                    "    nop",
                ]
            )

            # 9. Return and cleanup
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "# Complete state cleanup",
                    "csrci mstatus, 8",  # Clear MIE
                    "csrci mstatus, 2",  # Clear SIE
                    "CSRW(mideleg, zero)",  # Clear delegation
                    "CSRW(mie, zero)",  # Clear all interrupt enables
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

    r_scratch = test_data.int_regs.get_registers(1, exclude_regs=[])[0]

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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

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

    r_scratch = test_data.int_regs.get_registers(1, exclude_regs=[])[0]

    lines = [
        comment_banner(
            "cp_trigger_changingtos_ssi",
            "Trigger SSIP when enabling SIE in S-mode\n"
            "Set SSIP in M-mode, enter S-mode with SIE=0, then set sstatus.SIE=1",
        ),
        "",
        "# M-mode setup",
        "CSRW(mie, zero)",
        "csrci mstatus, 8",  # MIE=0
        "csrci mstatus, 2",  # SIE=0 (critical!)
    ]

    # Clear SSIP
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
        ]
    )

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

    # Set SSIP in M-mode
    lines.extend(
        [
            test_data.add_testcase("changingtos_ssi", coverpoint, covergroup),
            f"LI(x{r_scratch}, 0x2)",  # SSIP bit
            f"CSRS(mip, x{r_scratch})",  # Set via CSR write
            "nop",
        ]
    )

    # Enter S-mode (SIE=0, so no trap yet despite SSIP=1)
    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    # In S-mode: set sstatus.SIE=1 (interrupt should fire)
    lines.extend(
        [
            f"    LI(x{r_scratch}, 0x02)",  # SIE bit
            f"    csrrs x0, sstatus, x{r_scratch}",  # Set SIE=1
            "RVTEST_IDLE_FOR_INTERRUPT",
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
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
        ]
    )

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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_interrupts_s",
            "Test interrupts with walking 1s in mip and mie\nmideleg={0, 0x222} × 6 mip × 6 mie = 72 tests",
        ),
        "",
    ]

    # ALL 6 interrupts
    mip_interrupts = [
        ("ssip", 0x002, None, None, False),
        ("msip", 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("stip", 0x020, None, None, True),
        ("mtip", 0x080, None, None, True),
        ("seip", 0x200, "RVTEST_SET_SEXT_INT", "RVTEST_CLR_SEXT_INT", False),
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

    # Test BOTH mideleg values
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

                # Clear all interrupts
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRC(mip, x{r_scratch})",
                        "RVTEST_CLR_MSW_INT",
                        "RVTEST_CLR_SEXT_INT",
                        "RVTEST_CLR_MEXT_INT",
                    ]
                )
                lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                # Set mtvec.MODE = 0 (direct)
                lines.extend(
                    [
                        f"CSRR x{r_scratch}, mtvec",
                        f"SRLI x{r_scratch}, x{r_scratch}, 2",
                        f"SLLI x{r_scratch}, x{r_scratch}, 2",
                        f"CSRW(mtvec, x{r_scratch})",
                    ]
                )

                # Set mideleg
                if mideleg_val:
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x222)",
                            f"CSRW(mideleg, x{r_scratch})",
                        ]
                    )
                else:
                    lines.append("CSRW(mideleg, zero)")

                # Set walking 1 in mie
                lines.extend(
                    [
                        f"LI(x{r_scratch}, {hex(mie_bit)})",
                        f"CSRW(mie, x{r_scratch})",
                    ]
                )

                # Set SIE=1 (will take effect when entering S-mode)
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x02)",
                        f"CSRS(mstatus, x{r_scratch})",
                    ]
                )

                # Ensure MIE is 0
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x80)",  # MPIE bit
                        f"CSRC(mstatus, x{r_scratch})",  # MPIE=0
                    ]
                )

                # Set interrupt pending
                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                if mip_timer:
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
                elif mip_name == "ssip":
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x2)",
                            f"CSRS(mip, x{r_scratch})",
                        ]
                    )
                else:
                    lines.extend([mip_set, "nop"])

                # Wait in M-mode
                lines.extend(
                    [
                        f"    LI(x{r_scratch}, 2500)",
                        f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                        f"    bnez x{r_scratch}, 1b",
                    ]
                )

                # Enter S-mode
                lines.append("RVTEST_GOTO_LOWER_MODE Smode")

                # Wait in S-mode
                lines.extend(
                    [
                        f"    LI(x{r_scratch}, 2500)",
                        f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                        f"    bnez x{r_scratch}, 1b",
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

                # Clear interrupt
                if mip_timer:
                    if mip_name == "stip":
                        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                    else:
                        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
                elif mip_name == "ssip":
                    # Clear both ways for SSIP
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x2)",
                            f"CSRC(mip, x{r_scratch})",
                        ]
                    )
                else:
                    lines.append(mip_clr)

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_vectored_s_tests(test_data: TestData) -> list[str]:
    """Generate vectored interrupt tests for S-mode.

    In M-mode with MIE=0, set interrupt pending but no trap fires.
    Enter S-mode with SIE=1 - now interrupts can fire (delegated to S, or trap to M).
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_vectored_s"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_vectored_s",
            "Test vectored vs direct interrupt handling\nSet interrupt in M-mode (MIE=0), then enter S-mode (SIE=1)",
        ),
        "",
    ]

    # ALL 6 interrupts (including M-mode ones!)
    interrupts = [
        ("ssip", 0x002, None, None, False),
        ("msip", 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("stip", 0x020, None, None, True),
        ("mtip", 0x080, None, None, True),
        ("seip", 0x200, "RVTEST_SET_SEXT_INT", "RVTEST_CLR_SEXT_INT", False),
        ("meip", 0x800, "RVTEST_SET_MEXT_INT", "RVTEST_CLR_MEXT_INT", False),
    ]

    for stvec_mode in [0, 1]:  # direct, vectored
        stvec_mode_name = ["direct", "vectored"][stvec_mode]

        for int_name, int_bit, int_set, int_clr, uses_timer in interrupts:
            binname = f"{stvec_mode_name}_{int_name}"

            # === M-MODE SETUP ===
            lines.extend(
                [
                    "",
                    f"# Test: stvec.MODE={stvec_mode_name}, interrupt={int_name}",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",  # MIE=0 (blocks interrupts in M-mode)
                    "csrci mstatus, 2",  # SIE=0 initially
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                    "RVTEST_CLR_SEXT_INT",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Set stvec.MODE
            lines.extend(
                [
                    f"CSRR x{r_scratch}, stvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"ADDI x{r_scratch}, x{r_scratch}, {stvec_mode}",
                    f"CSRW(stvec, x{r_scratch})",
                ]
            )

            # Set mideleg (delegate S-interrupts)
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x222)",
                    f"CSRW(mideleg, x{r_scratch})",
                ]
            )

            # Enable ALL interrupts in mie
            lines.extend(
                [
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set SIE=1 (will take effect when entering S-mode)
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Ensure MIE = 0
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",  # MPIE bit
                    f"CSRC(mstatus, x{r_scratch})",  # MPIE=0
                ]
            )

            # Set interrupt in M-mode (MIE=0, so no trap yet)
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
                else:  # mtip
                    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
            elif int_name == "ssip":
                # Override macro with CSR for SSIP
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRS(mip, x{r_scratch})",
                    ]
                )
            else:
                lines.extend([int_set, "nop"])

            lines.extend(
                [
                    f"    LI(x{r_scratch}, 2500)",  # Short - trap fires quickly
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
                ]
            )

            # Enter S-mode (interrupt pending, SIE=1, trap will fire)
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")

            # NOPs to allow coverage sampling before trap
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 2500)",  # Short - trap fires quickly
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
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

            # Clear interrupt
            if uses_timer:
                if int_name == "stip":
                    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                else:
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
            elif int_name == "ssip":
                # Clear both ways for SSIP
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


# ======================================================================
# NEXT SET OF TESTS
# ======================================================================


def _generate_priority_mip_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests.

    Test all 2^6 = 64 combinations of mip with mie=all 1s.
    Cross: mideleg={0, 0x222} × 64 mip patterns = 128 tests
    Highest priority interrupt should fire.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_priority_mip_s"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_priority_mip_s",
            "Test interrupt priority with all mip combinations\n2^6 mip patterns × 2 mideleg values = 128 tests",
        ),
        "",
    ]

    # Test both mideleg values
    for mideleg_val in [0, 1]:
        mideleg_name = ["nodeleg", "deleg"][mideleg_val]

        # Test all 64 combinations of 6 interrupt bits
        for mip_pattern in range(64):
            # Extract which interrupts are set in this pattern
            ssip_set = (mip_pattern >> 0) & 1
            msip_set = (mip_pattern >> 1) & 1
            stip_set = (mip_pattern >> 2) & 1
            mtip_set = (mip_pattern >> 3) & 1
            seip_set = (mip_pattern >> 4) & 1
            meip_set = (mip_pattern >> 5) & 1

            binname = f"{mideleg_name}_mip_{mip_pattern:02x}"

            # === M-MODE SETUP ===
            lines.extend(
                [
                    "",
                    f"# Test: mideleg={mideleg_name}, mip_pattern=0x{mip_pattern:02x}",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",  # MIE=0
                    "csrci mstatus, 2",  # SIE=0 initially
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                    "RVTEST_CLR_SEXT_INT",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Set mtvec.MODE = 0 (direct)
            lines.extend(
                [
                    f"CSRR x{r_scratch}, mtvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"CSRW(mtvec, x{r_scratch})",
                ]
            )

            # Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # Enable ALL interrupts in mie
            lines.extend(
                [
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set SIE=1
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Set the interrupt pattern
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            # Set each interrupt according to the pattern
            if ssip_set:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRS(mip, x{r_scratch})",
                    ]
                )
            if msip_set:
                lines.append("RVTEST_SET_MSW_INT")
            if stip_set:
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
            if mtip_set:
                lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
            if seip_set:
                lines.append("RVTEST_SET_SEXT_INT")
            if meip_set:
                lines.append("RVTEST_SET_MEXT_INT")

            lines.append("nop")

            # Enter S-mode (highest priority interrupt will fire)
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")

            # Wait for coverage
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 100)",
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
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

            # Clear all interrupts that were set
            if ssip_set:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRC(mip, x{r_scratch})",
                    ]
                )
            if msip_set:
                lines.append("RVTEST_CLR_MSW_INT")
            if stip_set:
                lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            if mtip_set:
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
            if seip_set:
                lines.append("RVTEST_CLR_SEXT_INT")
            if meip_set:
                lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mie_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests varying mie.

    Set ALL mip bits, vary mie through all combinations.
    Test both S-mode (8 combinations) and M-mode (7 combinations, excluding 000).
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint_s = "cp_priority_mie_s"
    coverpoint_m = "cp_priority_mie_s_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_priority_mie_s",
            "Test interrupt priority with all mie combinations\nAll mip bits set, vary mie",
        ),
        "",
    ]

    # Test both mideleg values
    for mideleg_val in [0, 1]:
        mideleg_name = ["nodeleg", "deleg"][mideleg_val]

        # S-mode combinations: 8 patterns (including 000)
        for mie_pattern_s in range(8):
            ssie = (mie_pattern_s >> 0) & 1
            stie = (mie_pattern_s >> 1) & 1
            seie = (mie_pattern_s >> 2) & 1

            # Build mie value with S-mode bits
            mie_val = (ssie << 1) | (stie << 5) | (seie << 9)

            binname = f"{mideleg_name}_s_mie_{mie_pattern_s:03b}"

            lines.extend(
                [
                    "",
                    f"# Test: mideleg={mideleg_name}, S-mode mie pattern={mie_pattern_s:03b}",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",  # MIE=0
                    "csrci mstatus, 2",  # SIE=0
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                    "RVTEST_CLR_SEXT_INT",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Set mtvec.MODE = 0
            lines.extend(
                [
                    f"CSRR x{r_scratch}, mtvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"CSRW(mtvec, x{r_scratch})",
                ]
            )

            # Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # Set specific mie pattern
            lines.extend(
                [
                    f"LI(x{r_scratch}, {hex(mie_val)})",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set SIE=1
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Set ALL S-mode interrupts
            lines.append(test_data.add_testcase(binname, coverpoint_s, covergroup))
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRS(mip, x{r_scratch})",
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
            lines.extend(
                [
                    "RVTEST_SET_SEXT_INT",
                    "nop",
                ]
            )

            # Enter S-mode
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")

            # Wait for coverage
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 100)",
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
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
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.append("RVTEST_CLR_SEXT_INT")

        # M-mode combinations: 7 patterns (excluding 000)
        for mie_pattern_m in range(1, 8):  # Skip 0 (combo_000)
            msie = (mie_pattern_m >> 0) & 1
            mtie = (mie_pattern_m >> 1) & 1
            meie = (mie_pattern_m >> 2) & 1

            # Build mie value with M-mode bits
            mie_val = (msie << 3) | (mtie << 7) | (meie << 11)

            binname = f"{mideleg_name}_m_mie_{mie_pattern_m:03b}"

            lines.extend(
                [
                    "",
                    f"# Test: mideleg={mideleg_name}, M-mode mie pattern={mie_pattern_m:03b}",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",
                    "csrci mstatus, 2",
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                    "RVTEST_CLR_SEXT_INT",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Set mtvec.MODE = 0
            lines.extend(
                [
                    f"CSRR x{r_scratch}, mtvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"CSRW(mtvec, x{r_scratch})",
                ]
            )

            # Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # Set specific mie pattern
            lines.extend(
                [
                    f"LI(x{r_scratch}, {hex(mie_val)})",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set SIE=1
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Set ALL M-mode interrupts
            lines.append(test_data.add_testcase(binname, coverpoint_m, covergroup))
            lines.extend(
                [
                    "RVTEST_SET_MSW_INT",
                ]
            )
            lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
            lines.extend(
                [
                    "RVTEST_SET_MEXT_INT",
                    "nop",
                ]
            )

            # Enter S-mode (M-interrupt will fire immediately)
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")

            # Wait
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 100)",
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
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
                    "RVTEST_CLR_MSW_INT",
                ]
            )
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
            lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_both_s_tests(test_data: TestData) -> list[str]:
    """Generate interrupt priority tests with mip == mie.

    For each pattern, set the same bits in both mip and mie.
    Tests priority when multiple interrupts are both pending and enabled.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint_s = "cp_priority_both_s"
    coverpoint_m = "cp_priority_both_s_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

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
                    f"# Test: mideleg={mideleg_name}, S-mode pattern={pattern:03b} (mip==mie)",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",
                    "csrci mstatus, 2",
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_SEXT_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

            # Set mtvec.MODE = 0
            lines.extend(
                [
                    f"CSRR x{r_scratch}, mtvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"CSRW(mtvec, x{r_scratch})",
                ]
            )

            # Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # Set mie pattern
            lines.extend(
                [
                    f"LI(x{r_scratch}, {hex(mie_val)})",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set SIE=1
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Set matching mip pattern
            lines.append(test_data.add_testcase(binname, coverpoint_s, covergroup))

            if ssip:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRS(mip, x{r_scratch})",
                    ]
                )
            if stip:
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
            if seip:
                lines.append("RVTEST_SET_SEXT_INT")

            lines.append("nop")

            # Enter S-mode
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")

            # Wait
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 100)",
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
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

            if ssip:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRC(mip, x{r_scratch})",
                    ]
                )
            if stip:
                lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            if seip:
                lines.append("RVTEST_CLR_SEXT_INT")

        # M-mode: patterns 1-7 (skip 0, no interrupt = no MRET)
        for pattern in range(1, 8):
            msip = (pattern >> 0) & 1
            mtip = (pattern >> 1) & 1
            meip = (pattern >> 2) & 1

            # Set same pattern in both mip and mie
            mie_val = (msip << 3) | (mtip << 7) | (meip << 11)

            binname = f"{mideleg_name}_m_both_{pattern:03b}"

            lines.extend(
                [
                    "",
                    f"# Test: mideleg={mideleg_name}, M-mode pattern={pattern:03b} (mip==mie)",
                    "CSRW(mie, zero)",
                    "csrci mstatus, 8",
                    "csrci mstatus, 2",
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    "RVTEST_CLR_MSW_INT",
                    "RVTEST_CLR_MEXT_INT",
                ]
            )
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Set mtvec.MODE = 0
            lines.extend(
                [
                    f"CSRR x{r_scratch}, mtvec",
                    f"SRLI x{r_scratch}, x{r_scratch}, 2",
                    f"SLLI x{r_scratch}, x{r_scratch}, 2",
                    f"CSRW(mtvec, x{r_scratch})",
                ]
            )

            # Set mideleg
            if mideleg_val:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x222)",
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # Set mie pattern
            lines.extend(
                [
                    f"LI(x{r_scratch}, {hex(mie_val)})",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set SIE=1
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x02)",
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Set matching mip pattern
            lines.append(test_data.add_testcase(binname, coverpoint_m, covergroup))

            if msip:
                lines.append("RVTEST_SET_MSW_INT")
            if mtip:
                lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
            if meip:
                lines.append("RVTEST_SET_MEXT_INT")

            lines.append("nop")

            # Enter S-mode
            lines.append("RVTEST_GOTO_LOWER_MODE Smode")

            # Wait
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 100)",
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
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

            if msip:
                lines.append("RVTEST_CLR_MSW_INT")
            if mtip:
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
            if meip:
                lines.append("RVTEST_CLR_MEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mideleg_m_tests(test_data: TestData) -> list[str]:
    """Generate mideleg priority tests.

    Test all 8 mideleg patterns (2^3) with all S-interrupts set.
    mip = SSIP+STIP+SEIP, mie = all 1s, MIE=0, SIE=1.
    Verifies undelegated interrupts take priority over delegated.
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_priority_mideleg_m",
            "Test interrupt priority with varying mideleg patterns\n"
            "All S-interrupts set, vary delegation to test priority",
        ),
        "",
    ]

    # Test all 8 mideleg patterns
    for mideleg_pattern in range(8):
        ssie = (mideleg_pattern >> 0) & 1
        stie = (mideleg_pattern >> 1) & 1
        seie = (mideleg_pattern >> 2) & 1

        mideleg_val = (ssie << 1) | (stie << 5) | (seie << 9)

        # S-mode coverage: only combo_111 (all delegated)
        # M-mode coverage: all combos with at least one undelegated
        coverpoint = "cp_priority_mideleg_s/cp_priority_mideleg_m" if mideleg_pattern == 7 else "cp_priority_mideleg_m"

        binname = f"mideleg_{mideleg_pattern:03b}"

        lines.extend(
            [
                "",
                f"# Test: mideleg pattern={mideleg_pattern:03b}",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",  # MIE=0
                "csrci mstatus, 2",  # SIE=0
            ]
        )

        # Clear all interrupts
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_SEXT_INT",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

        # Set mtvec.MODE = 0
        lines.extend(
            [
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"CSRW(mtvec, x{r_scratch})",
            ]
        )

        # Set mideleg pattern
        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(mideleg_val)})",
                f"CSRW(mideleg, x{r_scratch})",
            ]
        )

        # Enable ALL interrupts in mie (mie = 1s)
        lines.extend(
            [
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Set SIE=1
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x02)",
                f"CSRS(mstatus, x{r_scratch})",
            ]
        )

        # Set ALL S-mode interrupts (mip = SSIP+STIP+SEIP)
        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRS(mip, x{r_scratch})",
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
        lines.extend(
            [
                "RVTEST_SET_SEXT_INT",
                "nop",
            ]
        )

        # Enter S-mode
        lines.append("RVTEST_GOTO_LOWER_MODE Smode")

        # Wait for highest priority interrupt to fire
        lines.extend(
            [
                f"    LI(x{r_scratch}, 100)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
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
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
        lines.append("RVTEST_CLR_SEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_priority_mideleg_s_tests(test_data: TestData) -> list[str]:
    """Generate priority among delegated interrupts test.

    Set all S-interrupts (mip=all), but mie=mideleg (matching).
    Only delegated+enabled interrupts fire, testing priority within delegated interrupts.
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_priority_mideleg_s"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_priority_mideleg_s",
            "Test priority among delegated interrupts\nmip=all S-interrupts, mie=mideleg (matching)",
        ),
        "",
    ]

    # Test patterns 1-7 (skip 0 = nothing enabled)
    for mideleg_pattern in range(1, 8):
        ssie = (mideleg_pattern >> 0) & 1
        stie = (mideleg_pattern >> 1) & 1
        seie = (mideleg_pattern >> 2) & 1

        # mie = mideleg (same pattern)
        mideleg_val = (ssie << 1) | (stie << 5) | (seie << 9)
        mie_val = mideleg_val  # MATCHING

        binname = f"delegated_priority_{mideleg_pattern:03b}"

        lines.extend(
            [
                "",
                f"# Test: mideleg=mie pattern={mideleg_pattern:03b}",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",  # MIE=0
                "csrci mstatus, 2",  # SIE=0
            ]
        )

        # Clear all interrupts
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_SEXT_INT",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

        # Set mtvec.MODE = 0
        lines.extend(
            [
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"CSRW(mtvec, x{r_scratch})",
            ]
        )

        # Set mideleg
        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(mideleg_val)})",
                f"CSRW(mideleg, x{r_scratch})",
            ]
        )

        # Set mie = mideleg (MATCHING)
        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(mie_val)})",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Set SIE=1
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x02)",
                f"CSRS(mstatus, x{r_scratch})",
            ]
        )

        # Set ALL S-mode interrupts (mip = all)
        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRS(mip, x{r_scratch})",
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
        lines.extend(
            [
                "RVTEST_SET_SEXT_INT",
                "nop",
            ]
        )

        # Enter S-mode (only delegated+enabled interrupts fire)
        lines.append("RVTEST_GOTO_LOWER_MODE Smode")

        # Wait for highest priority delegated interrupt
        lines.extend(
            [
                f"    LI(x{r_scratch}, 100)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
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
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
        lines.append("RVTEST_CLR_SEXT_INT")

    test_data.int_regs.return_registers([r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce])
    return lines


def _generate_wfi_s_tests(test_data: TestData) -> list[str]:
    """Generate S-mode WFI tests.

    Test WFI from S-mode with MTIP.
    Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × TW={0,1}

    Split:
    - cp_wfi_s: TW=0, WFI executes in S-mode
    - cp_wfi_s_tw: TW=1, WFI timeout → illegal instruction → M-mode trap
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_wfi_s",
            "Test WFI from S-mode with MTIP\nCross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × TW={0,1}",
        ),
        "",
    ]

    # Cross: MIE × SIE × mideleg × TW
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mideleg_val in [0, 1]:
                for tw_val in [0, 1]:
                    mideleg_name = ["zeros", "ones"][mideleg_val]

                    # Select coverpoint based on TW
                    coverpoint = "cp_wfi_s" if tw_val == 0 else "cp_wfi_s_tw"

                    binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}_tw{tw_val}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}, TW={tw_val}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                        ]
                    )

                    # Clear timer
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    # Set mideleg
                    if mideleg_val == 1:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x222)",
                                f"CSRW(mideleg, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.append("CSRW(mideleg, zero)")

                    # Set TW bit
                    if tw_val:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200000)",  # TW bit (bit 21)
                                f"CSRS(mstatus, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200000)",
                                f"CSRC(mstatus, x{r_scratch})",
                            ]
                        )

                    # Enable MTIE
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x80)",  # MTIE
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    # Set MIE
                    if mie_val:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x80)",  # MPIE bit
                                f"CSRS(mstatus, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x80)",
                                f"CSRC(mstatus, x{r_scratch})",
                            ]
                        )

                    # Set SIE
                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    # Set timer to fire soon (delayed)
                    lines.extend(set_mtimer_int_soon(r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_stce))

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Enter S-mode and execute WFI
                    lines.extend(
                        [
                            "RVTEST_GOTO_LOWER_MODE Smode",
                        ]
                    )

                    lines.extend(
                        [
                            "    wfi",  # TW=0: waits, TW=1: timeout → illegal instruction
                            "    nop",
                            "    nop",
                        ]
                    )

                    # Cleanup
                    lines.extend(
                        [
                            "RVTEST_GOTO_MMODE",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                            f"LI(x{r_scratch}, 0x200000)",
                            f"CSRC(mstatus, x{r_scratch})",  # Clear TW
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

    r_temp, r_stimecmp, r_scratch = test_data.int_regs.get_registers(3, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_wfi_timeout_s",
            "Test WFI timeout from S-mode and U-mode\n"
            "Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × MTIE={0,1} × mode={S,U}",
        ),
        "",
    ]

    # Cross: MIE × SIE × mideleg × MTIE × mode
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mideleg_val in [0, 1]:
                for mtie_val in [0, 1]:
                    for mode in ["Smode", "Umode"]:
                        mideleg_name = ["zeros", "ones"][mideleg_val]
                        mode_short = mode[0].lower()  # 's' or 'u'

                        # Select coverpoint based on mode
                        coverpoint = "cp_wfi_timeout_s" if mode == "Smode" else "cp_wfi_timeout_u_tw"

                        binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}_mtie{mtie_val}_{mode_short}"

                        lines.extend(
                            [
                                "",
                                f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}, MTIE={mtie_val}, mode={mode}",
                                "RVTEST_GOTO_MMODE",
                                "CSRW(mie, zero)",
                                "csrci mstatus, 8",  # MIE=0
                                "csrci mstatus, 2",  # SIE=0
                            ]
                        )

                        # Clear all interrupts
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x2)",
                                f"CSRC(mip, x{r_scratch})",
                                "RVTEST_CLR_MSW_INT",
                            ]
                        )
                        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
                        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                        # Set mideleg
                        if mideleg_val == 1:
                            lines.extend(
                                [
                                    f"LI(x{r_scratch}, 0x222)",
                                    f"CSRW(mideleg, x{r_scratch})",
                                ]
                            )
                        else:
                            lines.append("CSRW(mideleg, zero)")

                        # Set TW=1 (timeout enabled)
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200000)",  # TW bit (bit 21)
                                f"CSRS(mstatus, x{r_scratch})",
                            ]
                        )

                        # Set MTIE
                        if mtie_val:
                            lines.extend(
                                [
                                    f"LI(x{r_scratch}, 0x80)",  # MTIE
                                    f"CSRW(mie, x{r_scratch})",
                                ]
                            )
                        else:
                            lines.append("CSRW(mie, zero)")

                        # Set MTIMECMP to max (no interrupt)
                        lines.extend(
                            [
                                f"LA(x{r_temp}, RVMODEL_MTIMECMP_ADDRESS)",
                                f"LI(x{r_scratch}, -1)",
                                f"SREG x{r_scratch}, 0(x{r_temp})",
                            ]
                        )

                        # Set MIE
                        if mie_val:
                            lines.append("csrsi mstatus, 8")

                        # Set SIE
                        if sie_val:
                            lines.append("csrsi mstatus, 2")

                        # Sample in M-mode (before entering target mode)
                        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                        # Enter target mode and execute WFI
                        lines.extend(
                            [
                                f"RVTEST_GOTO_LOWER_MODE {mode}",
                                "    wfi",  # TW=1 → illegal instruction
                                "    nop",
                            ]
                        )

                        # Cleanup
                        lines.extend(
                            [
                                "RVTEST_GOTO_MMODE",
                                "csrci mstatus, 8",
                                "csrci mstatus, 2",
                                f"LI(x{r_scratch}, 0x200000)",
                                f"CSRC(mstatus, x{r_scratch})",  # Clear TW
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_interrupts_m",
            "Test interrupts with walking 1s\n2 MIE × 2 mideleg × 6 mip × 6 mie = 144 bins",
        ),
        "",
    ]

    # 6 interrupts (walking 1s)
    interrupts = [
        ("ssip", 0x002, 0x002, None, None, False),
        ("msip", 0x008, 0x008, "RVTEST_SET_MSW_INT", "RVTEST_CLR_MSW_INT", False),
        ("stip", 0x020, 0x020, None, None, True),
        ("mtip", 0x080, 0x080, None, None, True),
        ("seip", 0x200, 0x200, "RVTEST_SET_SEXT_INT", "RVTEST_CLR_SEXT_INT", False),
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

                    # === SETUP ===
                    lines.extend(
                        [
                            "",
                            f"# MIE={mie_val}, mideleg={mideleg_name}, mip={mip_name}, mie={mie_name}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                        ]
                    )

                    # Clear all interrupts
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x2)",
                            f"CSRC(mip, x{r_scratch})",
                            "RVTEST_CLR_MSW_INT",
                            # Reset stimecmp to max unconditionally before clearing mip.STIP.
                            # clr_stimer_int(r_stce=0) always uses legacy csrrc path which does NOT
                            # reset stimecmp; on STCE=1 systems hardware immediately re-asserts STIP.
                            f"LI(x{r_temp}, -1)",
                            f"csrw stimecmp, x{r_temp}",
                            "#if __riscv_xlen == 32",
                            f"csrw stimecmph, x{r_temp}",
                            "#endif",
                        ]
                    )
                    lines.extend(clr_stimer_mmode(r_scratch))
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    # Set mtvec.MODE = 0 (direct)
                    lines.extend(
                        [
                            f"CSRR x{r_scratch}, mtvec",
                            f"SRLI x{r_scratch}, x{r_scratch}, 2",
                            f"SLLI x{r_scratch}, x{r_scratch}, 2",
                            f"CSRW(mtvec, x{r_scratch})",
                        ]
                    )

                    # Set mideleg
                    if mideleg_val == 1:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x222)",  # STI+SEI+SSI
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

                    # Set SIE=1 for delegated
                    if is_delegated:
                        lines.append("csrsi mstatus, 2")

                    # Set MIE before triggering the interrupt (so trap fires immediately on set)
                    if mie_val == 1:
                        lines.append("csrsi mstatus, 8")

                    # === SET INTERRUPT ===
                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    if is_timer:
                        if mip_name == "stip":
                            # Always set mip.STIP directly from M-mode.
                            # set_stimer_int's legacy path (STCE=0) calls RVTEST_GOTO_LOWER_MODE Smode,
                            # which would make the wait loop run in S-mode → coverage misses M-mode state.
                            lines.extend(set_stimer_mmode(r_scratch))
                        else:  # mtip
                            if mie_val == 1:
                                lines.extend(
                                    set_mtimer_int_soon(r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_stce)
                                )
                            else:
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

                    # === WAIT FOR INTERRUPT ===
                    if is_delegated:
                        # Enter S-mode for delegated interrupts
                        lines.extend(
                            [
                                "RVTEST_GOTO_LOWER_MODE Smode",
                                f"    LI(x{r_scratch}, 5000)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]
                        )
                    else:
                        # Stay in M-mode
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 5000)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]
                        )

                    # === CLEANUP ===
                    lines.extend(
                        [
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

    Test vectored vs direct with S-interrupts, mideleg=0 (fire in M-mode).
    3 interrupts: SSIP, STIP, SEIP
    """
    covergroup = "InterruptsS_S_cg"
    coverpoint = "cp_vectored_m"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_vectored_m",
            "Test vectored interrupts in M-mode\nS-interrupts with mideleg=0 fire in M-mode",
        ),
        "",
    ]

    # S-mode interrupts (fire in M-mode when not delegated)
    interrupts = [
        ("ssip", 0x002, None, None, False),
        ("stip", 0x020, None, None, True),
        ("seip", 0x200, "RVTEST_SET_SEXT_INT", "RVTEST_CLR_SEXT_INT", False),
    ]

    for int_name, int_bit, int_set, int_clr, uses_timer in interrupts:
        binname = f"vectored_{int_name}"

        lines.extend(
            [
                "",
                f"# Test vectored M-mode: {int_name}",
                "RVTEST_GOTO_MMODE",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",  # MIE=0
            ]
        )

        # Clear all interrupts
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_SEXT_INT",
            ]
        )
        lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))

        # Set mtvec.MODE = 1 (vectored)
        lines.extend(
            [
                f"CSRR x{r_scratch}, mtvec",
                f"SRLI x{r_scratch}, x{r_scratch}, 2",
                f"SLLI x{r_scratch}, x{r_scratch}, 2",
                f"ADDI x{r_scratch}, x{r_scratch}, 1",  # MODE=1
                f"CSRW(mtvec, x{r_scratch})",
            ]
        )

        # mideleg=0 (no delegation, fire in M-mode)
        lines.append("CSRW(mideleg, zero)")

        # Enable all S-mode interrupts
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x222)",  # SSIE, STIE, SEIE
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Set MIE=1
        lines.append("csrsi mstatus, 8")

        # Set interrupt pending
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

        # Wait for interrupt
        lines.extend(
            [
                f"    LI(x{r_scratch}, 2500)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
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

        # Clear interrupt
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_priority_mip_m",
            "Test interrupt priority with MIE rising\nAll 64 mip patterns, mie=all 1s, mideleg=0, MIE 0→1",
        ),
        "",
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
                "RVTEST_GOTO_MMODE",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",  # MIE=0
            ]
        )

        # Clear all interrupts
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_MSW_INT",
                "RVTEST_CLR_SEXT_INT",
                "RVTEST_CLR_MEXT_INT",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        # mideleg=0 (no delegation)
        lines.append("CSRW(mideleg, zero)")

        # Enable ALL interrupts in mie
        lines.extend(
            [
                f"LI(x{r_scratch}, -1)",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Set interrupt pattern (with MIE=0, won't fire yet)
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
            lines.append("RVTEST_SET_SEXT_INT")
        if meip:
            lines.append("RVTEST_SET_MEXT_INT")

        lines.append("nop")

        # Set MIE=1 (rise event - interrupt fires)
        lines.append("csrsi mstatus, 8")

        # Wait for highest priority interrupt to fire
        lines.extend(
            [
                f"    LI(x{r_scratch}, 2500)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
            ]
        )

        # Cleanup
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
            ]
        )

        # Clear interrupts
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
            lines.append("RVTEST_CLR_SEXT_INT")
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_priority_mie_m",
            "Test interrupt priority with MIE rising\nAll 64 mie patterns, mip=all 1s, mideleg=0, MIE 0→1",
        ),
        "",
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
                "RVTEST_GOTO_MMODE",
                "CSRW(mie, zero)",
                "csrci mstatus, 8",  # MIE=0
            ]
        )

        # Clear all interrupts
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_MSW_INT",
                "RVTEST_CLR_SEXT_INT",
                "RVTEST_CLR_MEXT_INT",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

        # mideleg=0 (no delegation)
        lines.append("CSRW(mideleg, zero)")

        # Set specific mie pattern
        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(mie_val)})",
                f"CSRW(mie, x{r_scratch})",
            ]
        )

        # Set ALL interrupts (with MIE=0, won't fire yet)
        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
        lines.extend(
            [
                f"LI(x{r_scratch}, 0x2)",
                f"CSRS(mip, x{r_scratch})",
                "RVTEST_SET_MSW_INT",
            ]
        )
        lines.extend(set_stimer_mmode(r_scratch))
        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
        lines.extend(
            [
                "RVTEST_SET_SEXT_INT",
                "RVTEST_SET_MEXT_INT",
                "nop",
            ]
        )

        # Set MIE=1 (rise event - interrupt fires)
        lines.append("csrsi mstatus, 8")

        # Wait for highest priority enabled interrupt
        lines.extend(
            [
                f"    LI(x{r_scratch}, 100)",
                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                f"    bnez x{r_scratch}, 1b",
            ]
        )

        # Cleanup
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                "csrci mstatus, 8",
                "CSRW(mideleg, zero)",
                "CSRW(mie, zero)",
                f"LI(x{r_scratch}, 0x2)",
                f"CSRC(mip, x{r_scratch})",
                "RVTEST_CLR_MSW_INT",
            ]
        )
        lines.extend(clr_stimer_mmode(r_scratch))
        lines.extend(clr_mtimer_int(r_temp, r_stimecmp))
        lines.extend(
            [
                "RVTEST_CLR_SEXT_INT",
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

    r_mtime, r_mtimecmp, r_temp1, r_temp2, r_temp3, r_temp4 = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_wfi_m",
            "Test WFI in M-mode with MTIP\n8 tests: MIE × SIE × TW combinations",
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
                        "csrci mstatus, 8",  # Clear MIE
                        "csrci mstatus, 2",  # Clear SIE
                    ]
                )

                # Clear timer
                lines.extend(clr_mtimer_int(r_temp1, r_mtimecmp))

                # Set mideleg = 0x222 (S-interrupts delegated)
                lines.extend(
                    [
                        f"LI(x{r_temp1}, 0x222)",
                        f"CSRW(mideleg, x{r_temp1})",
                    ]
                )

                # Enable MTIE
                lines.extend(
                    [
                        f"LI(x{r_temp1}, 0x80)",  # MTIE bit
                        f"CSRS(mie, x{r_temp1})",
                    ]
                )

                # Set MIE
                if mie_val:
                    lines.append("csrsi mstatus, 8")

                # Set SIE
                if sie_val:
                    lines.append("csrsi mstatus, 2")

                # Set TW bit
                if tw_val:
                    lines.extend(
                        [
                            f"LI(x{r_temp1}, 0x200000)",  # TW bit (bit 21)
                            f"CSRS(mstatus, x{r_temp1})",
                        ]
                    )

                # Set machine timer to fire soon
                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
                lines.extend(set_mtimer_int_soon(r_mtime, r_mtimecmp, r_temp1, r_temp2, r_temp3, r_temp4))

                # Execute WFI in M-mode
                lines.extend(
                    [
                        "    nop",
                        "    wfi",  # Wait for timer interrupt
                        "    nop",
                        "    nop",
                    ]
                )

                # Cleanup
                lines.extend(
                    [
                        "RVTEST_GOTO_MMODE",
                        "csrci mstatus, 8",  # Clear MIE
                        "csrci mstatus, 2",  # Clear SIE
                        f"LI(x{r_temp1}, 0x200000)",
                        f"CSRC(mstatus, x{r_temp1})",  # Clear TW
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_mti_m",
            "Test MTIP trigger when MIE rises via CSRRS instruction",
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
            "csrci mstatus, 8",  # MIE=0
        ]
    )

    # Clear timer
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg=0
    lines.append("CSRW(mideleg, zero)")

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Set MTIP using the timer function
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))

    # Wait for timer to be pending
    lines.extend(
        [
            "nop",
            "nop",
            "nop",
            "nop",
        ]
    )

    # Use CSRRS to set MIE=1 (interrupt fires)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x8)",  # MIE bit (bit 3)
            f"CSRRS x0, mstatus, x{r_scratch}",  # Set MIE=1 via CSRRS
            "nop",
            "nop",
        ]
    )

    # Cleanup
    lines.extend(
        [
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_ssi_sip_m",
            "Test SSIP trigger via SIP write (CSRRS) in M-mode\n4 tests: MIE={0,1} × mideleg.SSI={0,1}",
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
                    "csrci mstatus, 8",  # MIE=0
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

            # Set mideleg.SSI
            if mideleg_ssi:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",  # SSI bit
                        f"CSRW(mideleg, x{r_scratch})",
                    ]
                )
            else:
                lines.append("CSRW(mideleg, zero)")

            # Enable all interrupts in mie
            lines.extend(
                [
                    f"LI(x{r_scratch}, -1)",
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set MIE if needed (AFTER setting up everything)
            # This prevents early firing
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            # Set MIE
            if mie_val:
                lines.extend(
                    [
                        "csrsi mstatus, 8",
                        "nop",
                        "nop",
                    ]
                )

            # Use CSRRS to set sip.SSIP (with MIE still 0)
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",  # SSIP bit (bit 1)
                    f"CSRRS x0, sip, x{r_scratch}",  # Set SSIP via SIP write
                    "nop",
                    "nop",
                ]
            )

            # Wait for highest priority enabled interrupt
            lines.extend(
                [
                    f"    LI(x{r_scratch}, 2500)",
                    f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                    f"    bnez x{r_scratch}, 1b",
                ]
            )

            # Cleanup
            lines.extend(
                [
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_msi_m",
            "Test MSIP trigger when MIE rises via CSRRS instruction",
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
            "csrci mstatus, 8",  # MIE=0
        ]
    )

    # Clear all interrupts
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
        ]
    )
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg=0
    lines.append("CSRW(mideleg, zero)")

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Set MSIP
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "RVTEST_SET_MSW_INT",
        ]
    )

    lines.extend(
        [
            f"    LI(x{r_scratch}, 2500)",
            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
            f"    bnez x{r_scratch}, 1b",
        ]
    )

    # Use CSRRS to set MIE=1 (interrupt fires)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x8)",  # MIE bit (bit 3)
            f"CSRRS x0, mstatus, x{r_scratch}",  # Set MIE=1 via CSRRS
            "nop",
            "nop",
        ]
    )

    # Cleanup
    lines.extend(
        [
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_mei_m",
            "Test MEIP trigger when MIE rises via CSRRS instruction",
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
            "csrci mstatus, 8",  # MIE=0
        ]
    )

    # Clear all interrupts
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_SEXT_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg=0
    lines.append("CSRW(mideleg, zero)")

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Set MEIP
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "RVTEST_SET_MEXT_INT",
        ]
    )

    lines.extend(
        [
            f"    LI(x{r_scratch}, 2500)",
            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
            f"    bnez x{r_scratch}, 1b",
        ]
    )

    # Use CSRRS to set MIE=1 (interrupt fires)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x8)",  # MIE bit (bit 3)
            f"CSRRS x0, mstatus, x{r_scratch}",  # Set MIE=1 via CSRRS
        ]
    )

    # Cleanup
    lines.extend(
        [
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_sti_m",
            "Test STIP trigger when MIE rises via CSRRS instruction",
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
            "csrci mstatus, 8",  # MIE=0
        ]
    )

    # Clear all interrupts
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_SEXT_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg=0 (STIP fires in M-mode)
    lines.append("CSRW(mideleg, zero)")

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Set STIP using M-mode direct write
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(set_stimer_mmode(r_scratch))

    lines.extend(
        [
            f"    LI(x{r_scratch}, 2500)",
            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
            f"    bnez x{r_scratch}, 1b",
        ]
    )

    # Use CSRRS to set MIE=1 (interrupt fires)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x8)",  # MIE bit (bit 3)
            f"CSRRS x0, mstatus, x{r_scratch}",  # Set MIE=1 via CSRRS
            "nop",
            "nop",
        ]
    )

    # Cleanup
    lines.extend(
        [
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_ssi_m",
            "Test SSIP trigger when MIE rises via CSRRS instruction",
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
            "csrci mstatus, 8",  # MIE=0
        ]
    )

    # Clear all interrupts
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_SEXT_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg=0 (SSIP fires in M-mode)
    lines.append("CSRW(mideleg, zero)")

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Set SSIP
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRS(mip, x{r_scratch})",
        ]
    )

    lines.extend(
        [
            f"    LI(x{r_scratch}, 2500)",
            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
            f"    bnez x{r_scratch}, 1b",
        ]
    )

    # Use CSRRS to set MIE=1 (interrupt fires)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x8)",  # MIE bit (bit 3)
            f"CSRRS x0, mstatus, x{r_scratch}",  # Set MIE=1 via CSRRS
            "nop",
            "nop",
        ]
    )

    # Cleanup
    lines.extend(
        [
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_trigger_sei_m",
            "Test SEIP trigger when MIE rises via CSRRS instruction",
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
            "csrci mstatus, 8",  # MIE=0
        ]
    )

    # Clear all interrupts
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x2)",
            f"CSRC(mip, x{r_scratch})",
            "RVTEST_CLR_MSW_INT",
            "RVTEST_CLR_SEXT_INT",
            "RVTEST_CLR_MEXT_INT",
        ]
    )
    lines.extend(clr_stimer_mmode(r_scratch))
    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

    # Set mideleg=0 (SEIP fires in M-mode)
    lines.append("CSRW(mideleg, zero)")

    # Enable all interrupts in mie
    lines.extend(
        [
            f"LI(x{r_scratch}, -1)",
            f"CSRW(mie, x{r_scratch})",
        ]
    )

    # Set SEIP
    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
    lines.extend(
        [
            "RVTEST_SET_SEXT_INT",
        ]
    )

    lines.extend(
        [
            f"    LI(x{r_scratch}, 2500)",
            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
            f"    bnez x{r_scratch}, 1b",
        ]
    )

    # Use CSRRS to set MIE=1 (interrupt fires)
    lines.extend(
        [
            f"LI(x{r_scratch}, 0x8)",  # MIE bit (bit 3)
            f"CSRRS x0, mstatus, x{r_scratch}",  # Set MIE=1 via CSRRS
            "nop",
            "nop",
        ]
    )

    # Cleanup
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "csrci mstatus, 8",
            "CSRW(mideleg, zero)",
            "CSRW(mie, zero)",
            "RVTEST_CLR_SEXT_INT",
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

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "SEIP Interaction Tests",
            "Test SEIP interaction between CSR writes and PLIC\nExpected 0% - SEIP not implemented on platform",
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
            "csrci mstatus, 8",  # MIE=0
            "CSRW(mideleg, zero)",  # mideleg=0
            "RVTEST_CLR_SEXT_INT",  # Clear PLIC
            f"LI(x{r_scratch}, 0x200)",  # SEIP bit
            test_data.add_testcase("csrrw_set", "cp_sei1", covergroup),
            f"CSRRW(zero, mip, x{r_scratch})",  # Write SEIP=1
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
            f"CSRRS(zero, mip, x{r_scratch})",  # Set SEIP=1
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
            "CSRW(mip, zero)",  # Clear software SEIP
            test_data.add_testcase("plic_set", "cp_sei3", covergroup),
            "RVTEST_SET_SEXT_INT",  # PLIC sets SEIP
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
            f"CSRRS(zero, mip, x{r_scratch})",  # First set SEIP=1 via software
            "nop",
            test_data.add_testcase("csrrc_clr_sw", "cp_sei4", covergroup),
            f"CSRRC(zero, mip, x{r_scratch})",  # Clear SEIP
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
            f"CSRRS(zero, mip, x{r_scratch})",  # Software sets SEIP=1
            "RVTEST_SET_SEXT_INT",  # PLIC also sets SEIP
            "nop",
            test_data.add_testcase("csrrc_fail_plic", "cp_sei5", covergroup),
            f"CSRRC(zero, mip, x{r_scratch})",  # Try to clear - should fail
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
            "CSRW(mip, zero)",  # No software write
            "RVTEST_SET_SEXT_INT",  # PLIC sets SEIP
            "nop",
            test_data.add_testcase("plic_off_nosw", "cp_sei6", covergroup),
            "RVTEST_CLR_SEXT_INT",  # Turn off PLIC
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
            f"CSRRS(zero, mip, x{r_scratch})",  # Software sets SEIP=1
            "RVTEST_SET_SEXT_INT",  # PLIC also sets SEIP
            "nop",
            test_data.add_testcase("plic_off_sw", "cp_sei7", covergroup),
            "RVTEST_CLR_SEXT_INT",  # Turn off PLIC
            "nop",
            "nop",
            "CSRW(mip, zero)",  # Final cleanup
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_global_ie",
            "Test global interrupt enables in M-mode\nCross: MIE={0,1} × SIE={0,1} × M-interrupts",
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
                        "csrci mstatus, 8",  # MIE=0
                        "csrci mstatus, 2",  # SIE=0
                    ]
                )

                # Clear all interrupts
                lines.extend(
                    [
                        f"LI(x{r_scratch}, 0x2)",
                        f"CSRC(mip, x{r_scratch})",
                        "RVTEST_CLR_MSW_INT",
                        "RVTEST_CLR_SEXT_INT",
                        "RVTEST_CLR_MEXT_INT",
                    ]
                )
                lines.extend(clr_stimer_mmode(r_scratch))
                lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                # Set mideleg=0 (no delegation)
                lines.append("CSRW(mideleg, zero)")

                # Enable matching interrupt in mie
                lines.extend(
                    [
                        f"LI(x{r_scratch}, {hex(mie_bit)})",
                        f"CSRW(mie, x{r_scratch})",
                    ]
                )

                # Set MIE
                if mie_val:
                    lines.append("csrsi mstatus, 8")

                # Set SIE
                if sie_val:
                    lines.append("csrsi mstatus, 2")

                # Set interrupt pending
                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                if is_timer:
                    lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
                else:
                    lines.extend([int_set, "nop"])

                # Wait for interrupt (if MIE=1, fires; if MIE=0, doesn't)
                lines.extend(
                    [
                        f"    LI(x{r_scratch}, 2500)",
                        f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                        f"    bnez x{r_scratch}, 1b",
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

                # Clear interrupt
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

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_user_mti",
            "Test MTIP from U-mode (not delegated)\nCross: MIE={0,1} × SIE={0,1} × mtvec.MODE={0,1} × MTIP={0,1}",
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
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                        ]
                    )

                    # Clear timer
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    # Set mideleg.MTI=0 (not delegated)
                    lines.append("CSRW(mideleg, zero)")

                    # Set both mtvec and stvec MODE
                    lines.extend(
                        [
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

                    # Enable MTIE
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x80)",  # MTIE
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    # Set MIE
                    if mie_val:
                        lines.append("csrsi mstatus, 8")

                    # Set SIE
                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Set MTIP if needed
                    if set_timer:
                        lines.extend(set_mtimer_int(r_mtime, r_stimecmp, r_temp, r_temp2))
                        lines.extend(
                            [
                                f"    LI(x{r_scratch}, 2500)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]
                        )

                    # Enter U-mode
                    lines.extend(
                        [
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    nop",
                            "    nop",
                            "    nop",
                            "    nop",
                        ]
                    )

                    lines.extend(
                        [
                            f"    LI(x{r_scratch}, 2500)",
                            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                            f"    bnez x{r_scratch}, 1b",
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

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "cp_user_msi",
            "Test MSIP from U-mode (not delegated)\nCross: MIE={0,1} × SIE={0,1} × stvec.MODE={0,1} × MSIP={0,1}",
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
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                        ]
                    )

                    # Clear MSIP
                    lines.append("RVTEST_CLR_MSW_INT")

                    # Set mideleg.MSI=0 (not delegated)
                    lines.append("CSRW(mideleg, zero)")

                    # Set both mtvec and stvec MODE
                    lines.extend(
                        [
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

                    # Enable MSIE
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x8)",  # MSIE
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    # Set SIE first
                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    # NOW set MIE
                    if mie_val:
                        lines.append("csrsi mstatus, 8")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Set MSIP BEFORE setting MIE (critical order!)
                    if set_msip:
                        lines.extend(
                            [
                                "RVTEST_SET_MSW_INT",
                                "nop",
                                "nop",
                            ]
                        )
                        lines.extend(
                            [
                                f"    LI(x{r_scratch}, 2500)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]
                        )

                    # Enter U-mode
                    lines.extend(
                        [
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    nop",
                            "    nop",
                        ]
                    )

                    # For MIE=1 + MSIP=1: Set MSIP in U-mode (wait - can't do this!)
                    # Software interrupt is immediate, not delayed like timer
                    # This case is IMPOSSIBLE to hit correctly

                    # Cleanup
                    lines.extend(
                        [
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

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "cp_user_mei",
            "Test MEIP from U-mode (not delegated)\nCross: MIE={0,1} × SIE={0,1} × stvec.MODE={0,1} × MEIP={0,1}",
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
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                        ]
                    )

                    # Clear MEIP
                    lines.append("RVTEST_CLR_MEXT_INT")

                    # Set mideleg.MEI=0 (not delegated)
                    lines.append("CSRW(mideleg, zero)")

                    # Set both mtvec and stvec MODE
                    lines.extend(
                        [
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

                    # Enable MEIE
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x800)",  # MEIE
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    # Set SIE
                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    # Set MIE
                    if mie_val:
                        lines.append("csrsi mstatus, 8")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Set MEIP
                    if set_meip:
                        lines.extend(
                            [
                                "RVTEST_SET_MEXT_INT",
                            ]
                        )
                        lines.extend(
                            [
                                f"    LI(x{r_scratch}, 2500)",
                                f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                                f"    bnez x{r_scratch}, 1b",
                            ]
                        )

                    # Enter U-mode (always)
                    lines.extend(
                        [
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    nop",
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
                            "RVTEST_CLR_MEXT_INT",
                        ]
                    )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_user_sei_tests(test_data: TestData) -> list[str]:
    """Generate U-mode SEIP tests.

    cp_user_sei: MIE=0, enters U-mode
    cp_user_sei_m: MIE=1, stays in M-mode
    """
    covergroup = "InterruptsS_S_cg"

    r_scratch = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(
            "cp_user_sei",
            "Test SEIP from U-mode with delegation",
        ),
        "",
    ]

    # Cross: MIE × SIE × stvec.MODE × mideleg.SEI
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for stvec_mode in [0, 1]:
                for mideleg_sei in [0, 1]:
                    deleg_name = "deleg" if mideleg_sei else "nodeleg"

                    # Select coverpoint based on MIE
                    coverpoint = "cp_user_sei" if mie_val == 0 else "cp_user_sei_m"

                    binname = f"mie{mie_val}_sie{sie_val}_vec{stvec_mode}_{deleg_name}"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, stvec.MODE={stvec_mode}, mideleg.SEI={mideleg_sei}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",
                            "csrci mstatus, 2",
                        ]
                    )

                    # Clear SEIP
                    lines.append("RVTEST_CLR_SEXT_INT")

                    # Set mideleg
                    if mideleg_sei:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200)",
                                f"CSRW(mideleg, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.append("CSRW(mideleg, zero)")

                    # Set both mtvec and stvec MODE
                    lines.extend(
                        [
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

                    # Enable SEIE
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x200)",
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    # Set SIE
                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    # Set MIE
                    if mie_val:
                        lines.append("csrsi mstatus, 8")

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Try to set SEIP (not implemented)
                    lines.extend(
                        [
                            "RVTEST_SET_SEXT_INT",
                        ]
                    )
                    lines.extend(
                        [
                            f"    LI(x{r_scratch}, 2500)",
                            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                            f"    bnez x{r_scratch}, 1b",
                        ]
                    )

                    # Enter U-mode (for both MIE=0 and MIE=1)
                    lines.extend(
                        [
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    nop",
                            "    nop",
                        ]
                    )
                    lines.extend(
                        [
                            f"    LI(x{r_scratch}, 2500)",
                            f"1:  addi x{r_scratch}, x{r_scratch}, -1",
                            f"    bnez x{r_scratch}, 1b",
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
                            "RVTEST_CLR_SEXT_INT",
                        ]
                    )

    test_data.int_regs.return_registers([r_scratch])
    return lines


def _generate_wfi_u_tests(test_data: TestData) -> list[str]:
    """Generate U-mode WFI tests.

    Test WFI from U-mode with MTIP.
    Cross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × TW={0,1}
    Split: TW=0 (WFI works) and TW=1 (illegal instruction)
    """
    covergroup = "InterruptsS_S_cg"

    r_mtime, r_temp, r_temp2, r_stimecmp, r_scratch, r_stce = test_data.int_regs.get_registers(6, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_wfi_u",
            "Test WFI from U-mode\nCross: MIE={0,1} × SIE={0,1} × mideleg={0,0x222} × TW={0,1}",
        ),
        "",
    ]

    # Cross: MIE × SIE × mideleg × TW
    for mie_val in [0, 1]:
        for sie_val in [0, 1]:
            for mideleg_val in [0, 1]:
                for tw_val in [0, 1]:
                    mideleg_name = ["nodeleg", "deleg"][mideleg_val]
                    tw_name = f"tw{tw_val}"
                    binname = f"mie{mie_val}_sie{sie_val}_{mideleg_name}_{tw_name}"

                    coverpoint = "cp_wfi_u" if tw_val == 0 else "cp_wfi_u_tw"

                    lines.extend(
                        [
                            "",
                            f"# Test: MIE={mie_val}, SIE={sie_val}, mideleg={mideleg_name}, TW={tw_val}",
                            "RVTEST_GOTO_MMODE",
                            "CSRW(mie, zero)",
                            "csrci mstatus, 8",  # MIE=0
                            "csrci mstatus, 2",  # SIE=0
                        ]
                    )

                    # Clear timer
                    lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

                    # Set mideleg
                    if mideleg_val:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x222)",
                                f"CSRW(mideleg, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.append("CSRW(mideleg, zero)")

                    # Set TW bit
                    if tw_val:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200000)",  # TW bit (bit 21)
                                f"CSRS(mstatus, x{r_scratch})",
                            ]
                        )
                    else:
                        lines.extend(
                            [
                                f"LI(x{r_scratch}, 0x200000)",
                                f"CSRC(mstatus, x{r_scratch})",
                            ]
                        )

                    # Enable MTIE
                    lines.extend(
                        [
                            f"LI(x{r_scratch}, 0x80)",  # MTIE
                            f"CSRW(mie, x{r_scratch})",
                        ]
                    )

                    # Set MIE
                    if mie_val:
                        lines.append("csrsi mstatus, 8")

                    # Set SIE
                    if sie_val:
                        lines.append("csrsi mstatus, 2")

                    # Set timer to fire soon (delayed)
                    lines.extend(set_mtimer_int_soon(r_mtime, r_stimecmp, r_temp, r_temp2, r_scratch, r_stce))

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

                    # Enter U-mode and execute WFI
                    lines.extend(
                        [
                            "RVTEST_GOTO_LOWER_MODE Umode",
                            "    wfi",  # TW=0: waits, TW=1: illegal instruction
                            "    nop",
                            "    nop",
                        ]
                    )

                    # Cleanup
                    lines.extend(
                        [
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

    r_temp, r_stimecmp, r_scratch = test_data.int_regs.get_registers(3, exclude_regs=[])

    lines = [
        comment_banner(
            "cp_wfi_timeout_u",
            "Test WFI timeout from U-mode\nCross: MIE={0,1} × SIE={0,1}",
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
                    "csrci mstatus, 8",  # MIE=0
                    "csrci mstatus, 2",  # SIE=0
                ]
            )

            # Clear all interrupts
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x2)",
                    f"CSRC(mip, x{r_scratch})",
                    "RVTEST_CLR_MSW_INT",
                ]
            )
            lines.extend(clr_stimer_int(r_temp, r_stimecmp, r_scratch, 0))
            lines.extend(clr_mtimer_int(r_temp, r_stimecmp))

            # Set mideleg = ones
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x222)",
                    f"CSRW(mideleg, x{r_scratch})",
                ]
            )

            # Set TW=1 (timeout enabled)
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x200000)",  # TW bit (bit 21)
                    f"CSRS(mstatus, x{r_scratch})",
                ]
            )

            # Enable MTIE=1 (required for timeout to work)
            lines.extend(
                [
                    f"LI(x{r_scratch}, 0x80)",  # MTIE
                    f"CSRW(mie, x{r_scratch})",
                ]
            )

            # Set MTIMECMP to max (no interrupt fires)
            lines.extend(
                [
                    f"LA(x{r_temp}, RVMODEL_MTIMECMP_ADDRESS)",
                    f"LI(x{r_scratch}, -1)",
                    f"SREG x{r_scratch}, 0(x{r_temp})",
                ]
            )

            # Set MIE
            if mie_val:
                lines.append("csrsi mstatus, 8")

            # Set SIE
            if sie_val:
                lines.append("csrsi mstatus, 2")

            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            # Enter U-mode and execute WFI
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    "    wfi",  # Times out → illegal instruction → trap to M-mode
                    "    nop",
                ]
            )

            # Cleanup
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "csrci mstatus, 8",
                    "csrci mstatus, 2",
                    f"LI(x{r_scratch}, 0x200000)",
                    f"CSRC(mstatus, x{r_scratch})",  # Clear TW
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
