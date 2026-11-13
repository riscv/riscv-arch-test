##################################
# asm/wait.py
#
# Race-free wait for an interrupt with WFI or WRS.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Race-free wait for an interrupt with WFI or WRS.

A wait instruction may complete before the interrupt arrives, so a test waits in a loop that checks
whether the interrupt has been taken before each wait. That check races with the interrupt: if the
interrupt is taken after the check but before the wait instruction, the trap handler clears its source
and the wait instruction then waits for an interrupt that never comes. The trap handler closes the race
using rvtest_wait_loop:

- wait_loop_arm() records the loop's bounds in rvtest_wait_loop before the test arms the interrupt.
- The trap handler clears the loop's exit on every interrupt. If the interrupt was taken inside the loop,
  it also resumes at the exit instead of returning to the interrupted instruction.
- wait_loop() leaves when the exit has been cleared, so an interrupt taken before the loop ends the
  wait as well.

Both use the label of the current testcase, so call them after add_testcase(), once per testcase.
"""

from testgen.data.state import TestData


def wait_loop_arm(test_data: TestData, addr_reg: int, tmp_reg: int) -> list[str]:
    """Arm the wait loop that wait_loop() emits later. Run it in the mode that waits, before arming the interrupt."""
    label = test_data.current_testcase_label
    return [
        "# Arm the wait loop: from here on, an interrupt releases it (see testgen/asm/wait.py)",
        f"LA(x{addr_reg}, rvtest_wait_loop)",
        f"LA(x{tmp_reg}, {label}_wait)",
        f"SREG x{tmp_reg}, 0(x{addr_reg}) # first instruction of the loop",
        f"LA(x{tmp_reg}, {label}_waited)",
        f"SREG x{tmp_reg}, REGWIDTH(x{addr_reg}) # loop exit",
    ]


def wait_loop(test_data: TestData, reg: int, wait: list[str], pending: tuple[str, int] | None = None) -> list[str]:
    """Repeat the wait instruction(s) until an interrupt releases the loop armed by wait_loop_arm().

    `wait` ends with the WFI or WRS instruction. `pending` = (CSR, mask) also leaves when an interrupt is
    pending in CSR, for interrupts that are masked and so are never taken. Clobbers `reg`.
    """
    label = test_data.current_testcase_label
    return [
        f"{label}_wait:",
        f"LA(x{reg}, rvtest_wait_loop)",
        f"LREG x{reg}, REGWIDTH(x{reg})",
        f"beqz x{reg}, {label}_waited # released: the interrupt has been taken",
        *(
            [
                f"csrr x{reg}, {pending[0]}",
                f"andi x{reg}, x{reg}, {pending[1]:#x}",
                f"bnez x{reg}, {label}_waited # interrupt pending but masked",
            ]
            if pending
            else []
        ),
        *wait,
        f"j {label}_wait",
        f"{label}_waited:",
        f"LA(x{reg}, rvtest_wait_loop)",
        f"SREG zero, REGWIDTH(x{reg}) # disarm, in case the loop left on a pending, masked interrupt",
    ]
