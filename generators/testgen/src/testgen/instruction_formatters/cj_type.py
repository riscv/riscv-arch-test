##################################
# cj_type.py
#
# jcarlin@hmc.edu November 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter


@add_instruction_formatter("CJ", required_params={"temp_reg", "immval"}, imm_bits=11)
def format_cj_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CJ-type instruction."""
    # TODO: Implement CJ-type instruction formatting
    setup: list[str] = []
    if instr_name == "c.jal":
        # Ensure ra (x1) is allocated
        setup.append(test_data.int_regs.consume_registers([1]))
    test = []
    check = []
    if instr_name == "c.jal":
        test_data.int_regs.return_register(1)
    return (setup, test, check)
