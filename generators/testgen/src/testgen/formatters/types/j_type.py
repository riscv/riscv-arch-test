##################################
# j_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

j_config = InstructionTypeConfig(required_params={"rd", "temp_reg"})


@add_instruction_formatter("J", j_config)
def format_j_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format J-type instruction."""
    assert params.rd is not None and params.temp_reg is not None
    setup = [
        f"LI(x{params.temp_reg}, 1) # initialize indicator to 1 (jump taken)",
    ]
    test = [
        f"{instr_name} x{params.rd}, 1f # perform jump",
    ]
    check = [
        f"LI(x{params.temp_reg}, -1) # should not execute (jump not taken)",
        "1:",
        write_sigupd(params.rd, test_data, "int"),
        write_sigupd(params.temp_reg, test_data, "int"),
    ]
    return (setup, test, check)
