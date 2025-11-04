##################################
# u_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.instruction_params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("U", required_params={"rd", "immval"})
def format_u_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format U-type instruction."""
    assert params.rd is not None and params.immval is not None
    scaled_imm = modify_imm(params.immval, 20, signed=False)
    setup = []
    test = [
        f"{instr_name} x{params.rd}, {scaled_imm} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
