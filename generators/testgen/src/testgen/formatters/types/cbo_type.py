##################################
# cbo_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cbo_config = InstructionTypeConfig(required_params={"rs1", "rs1val", "immval"}, imm_bits=12, imm_signed=True)


@add_instruction_formatter("CBO", cbo_config)
def format_cbo_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CBO-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None and params.immval is not None
    setup = [
        f"LA(x{params.rs1}, scratch) # load address of scratch into rs1",
        f"addi x{params.rs1}, x{params.rs1}, {abs(params.immval % 256)} # offset within the scratch region, potentially hitting different lines and checking alignment doesn't matter",
    ]
    test = [
        f"{instr_name} (x{params.rs1}) # perform operation",
    ]
    return (setup, test, [""])
