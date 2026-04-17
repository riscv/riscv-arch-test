##################################
# cp_custom_cbo.py
#
# David_Harris@hmc.edu 22 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_cbo coverpoint generator."""

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk


@add_coverpoint_generator("cp_custom_cbo")
def make_custom_cbo(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for cbo coverpoints."""
    if instr_name not in ["cbo.inval", "cbo.clean", "cbo.flush", "cbo.zero"]:
        raise ValueError(f"cp_custom_cbo generator only supports cbo instructions, got {instr_name}")

    tc = test_data.begin_test_chunk()
    test_lines: list[str] = []

    reg1, reg2, reg3 = test_data.int_regs.get_registers(3, exclude_regs=[0])

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
                f"addi x{reg3}, x{reg2}, {offset} # offset within the scratch region, potentially hitting different lines and checking alignment doesn't matter",
            ]
        )

        # for cbo.inval, start by putting some known data in memory and cleaning it to ensure it is in memory and not just in the cache.
        # this data will then be overwritten with new data before cbo.inval, and readback should show either the original data or the new data
        mask_cmd = ""
        if instr_name == "cbo.inval":
            for word in range(65):
                test_lines.extend(
                    [
                        f"# Write initial data to memory for word {word}",
                        load_int_reg("rs1", reg1, word + 0x101, test_data),  # write data with a 1 in bit 8
                        f"sw x{reg1}, {word * 4}(x{reg2})",
                    ]
                )
            test_lines.append(f"cbo.clean (x{reg3}) # Clean the cache to ensure data is in memory, then write new data")
            mask_cmd = f"andi x{reg1}, x{reg1}, ~0x100 # Mask to the bits that should be preserved by cbo.inval"

        for word in range(65):
            test_lines.extend(
                [
                    load_int_reg("rs1", reg1, word + 0x001, test_data),
                    f"sw x{reg1}, {word * 4}(x{reg2})",
                ]
            )

        test_lines.extend(
            [
                f"{instr_name} (x{reg3}) # Issue cbo instruction on first line of scratch or at an offset",
            ]
        )
        for word in range(65):
            test_lines.extend(
                [
                    test_data.add_testcase(f"word {word} offset {offset}", "cp_custom_cbo"),
                    f"lw x{reg1}, {word * 4}(x{reg2}) # Read back data",
                    mask_cmd,
                    write_sigupd(reg1, test_data),
                    "",
                ]
            )

    # Return registers
    test_data.int_regs.return_registers([reg1, reg2, reg3])

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
