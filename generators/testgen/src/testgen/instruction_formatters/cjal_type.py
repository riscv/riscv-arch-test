##################################
# cjal_type.py
#
# jcarlin@hmc.edu December 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter


@add_instruction_formatter("CJAL", required_params={"temp_reg", "immval"}, imm_bits=11)
def format_cjal_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CJAL-type instruction (c.jal)."""
    raise NotImplementedError(
        "CJAL-type instruction formatter is not implemented. All coverpoints for CJAL-type "
        "instructions are special coverpoints and do not use the instruction formatter."
    )
