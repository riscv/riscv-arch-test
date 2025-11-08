##################################
# css_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter


@add_instruction_formatter("CSS", required_params={"rs2", "immval"})
def format_css_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSS-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.immval is not None
    # TODO: Implement CSS-type instruction formatting
    # scaled_imm = modify_imm(params.immval, 8)
    # setup = [
    #     load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    # ]
    # test = [
    #     f"{instr_name} x{params.rs2}, {scaled_imm}(sp) # perform operation",
    # ]
    # check = []
    return ([], [], [])  # Placeholder return until implemented
