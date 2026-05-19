##################################
# cn_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""CN-type (c.nop) instruction formatter."""

from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cn_config = InstructionTypeConfig(required_params=set(), imm_bits=6, imm_signed=True)


@add_instruction_formatter("CN", cn_config)
def format_cn_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CN-type instruction (c.nop, optionally with hint immediate)."""
    setup: list[str] = []
    operand = f" {params.immval}" if params.immval is not None else ""
    test = [f"{instr_name}{operand} # perform operation"]
    return (setup, test, [])
