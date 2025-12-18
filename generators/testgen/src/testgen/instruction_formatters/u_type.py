##################################
# u_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd


@add_instruction_formatter("U", required_params={"rd", "immval"}, imm_bits=20, imm_signed=False)
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
