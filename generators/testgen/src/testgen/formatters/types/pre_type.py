##################################
# pre_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

pre_config = InstructionTypeConfig(required_params={"rs1", "rs1val", "immval"}, imm_bits=7, imm_signed=True)


@add_instruction_formatter("PRE", pre_config)
def format_pre_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format PRE-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None and params.immval is not None
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
    ]
    test = [
        # f"{instr_name} {(((params.immval + 64) % 128) - 64)*32}(x{params.rs1}) # perform operation",
        f"{instr_name} {(int(params.immval / 32)) * 32}(x{params.rs1}) # perform operation",
    ]
    return (setup, test, [""])
