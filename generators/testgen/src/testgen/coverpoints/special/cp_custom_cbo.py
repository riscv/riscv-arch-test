##################################
# cp_custom_cbo.py
#
# David_Harris@hmc.edu 22 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_cbo coverpoint generator."""

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk


@add_coverpoint_generator("cp_custom_cbo")
def make_custom_cbo(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cbo coverpoints."""
    if (
        instr_name != "cbo.inval"
        and instr_name != "cbo.clean"
        and instr_name != "cbo.flush"
        and instr_name != "cbo.zero"
    ):
        raise ValueError(f"cp_custom_cbo generator only supports cbo instructions, got {instr_name}")

    tc = test_data.begin_test_chunk()
    test_lines: list[str] = []

    reg1, reg2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    test_lines.extend(
        [
            "# cp_custom_cbo: Write 65 words to scratch, issue cbo instruction, read them back and record signature",
            f"LA(x{reg2}, scratch)",
        ]
    )

    for offset in [0, 255]:
        test_lines.extend(
            [
                f"# Testing offset {offset} to check behavior across cache line boundaries",
                f"addi x{reg2}, x{reg2}, {offset} # offset within the scratch region, potentially hitting different lines and checking alignment doesn't matter",
            ]
        )

        for word in range(65):
            test_lines.extend(
                [
                    f"LI(x{reg1}, {word * 0x00FEDCBA + 0xD00F})",
                    f"sw x{reg1}, {word * 4}(x{reg2})",
                ]
            )

        test_lines.extend(
            [
                f"{instr_name} (x{reg2}) # Issue cbo instruction on first line of scratch",
            ]
        )

        for word in range(65):
            test_lines.extend(
                [
                    test_data.add_testcase(f"word {word} offset {offset}", "cp_custom_cbo"),
                    f"lw x{reg1}, {word * 4}(x{reg2})",
                    write_sigupd(reg1, test_data),
                    "",
                ]
            )

    # Return registers
    test_data.int_regs.return_registers([reg1, reg2])

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
