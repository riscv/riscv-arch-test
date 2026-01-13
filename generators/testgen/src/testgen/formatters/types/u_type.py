##################################
# u_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

u_config = InstructionTypeConfig(required_params={"rd", "immval"}, imm_bits=20, imm_signed=False)


@add_instruction_formatter("U", u_config)
def format_u_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format U-type instruction."""
    assert params.rd is not None and params.immval is not None
    setup = []
    test = [
        f"{instr_name} x{params.rd}, {params.immval} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
