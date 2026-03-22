##################################
# cp_custom_prefetch.py
#
# David_Harris@hmc.edu 22 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_prefetch coverpoint generator."""

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk


@add_coverpoint_generator("cp_custom_prefetch")
def make_custom_prefetch(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for prefetch coverpoints."""
    if instr_name != "prefetch.i" and instr_name != "prefetch.r" and instr_name != "prefetch.w":
        raise ValueError(f"cp_custom_prefetch generator only supports prefetch instructions, got {instr_name}")

    tc = test_data.begin_test_chunk()
    test_lines: list[str] = []

    reg1, reg2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    test_lines.extend(
        [
            "# cp_custom_prefetch: Write 65 words to scratch, issue prefetch instruction, read them back and record signature",
            f"LA(x{reg2}, scratch)",
        ]
    )

    for i in range(65):
        test_lines.extend(
            [
                f"LI(x{reg1}, {i * 0x00FEDCBA})",
                f"sw x{reg1}, {i * 4}(x{reg2})",
            ]
        )

    test_lines.extend(
        [
            f"{instr_name} 0(x{reg2}) # Issue prefetch instruction on first line of scratch",
        ]
    )

    for i in range(65):
        test_lines.extend(
            [
                test_data.add_testcase(f"word {i}", "cp_custom_prefetch"),
                f"lw x{reg1}, {i * 4}(x{reg2})",
                write_sigupd(reg1, test_data),
                "",
            ]
        )

    # Return registers
    test_data.int_regs.return_registers([reg1, reg2])

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
