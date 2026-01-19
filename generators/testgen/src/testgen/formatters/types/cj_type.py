##################################
# cj_type.py
#
# jcarlin@hmc.edu November 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cj_config = InstructionTypeConfig(required_params={"temp_reg", "temp_val", "immval"}, imm_bits=11)


@add_instruction_formatter("CJ", cj_config)
def format_cj_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CJ-type instruction."""
    raise NotImplementedError(
        "CJ-type instruction formatter is not implemented. All coverpoints for CJ-type instructions are special coverpoints and do not use the instruction formatter."
    )
