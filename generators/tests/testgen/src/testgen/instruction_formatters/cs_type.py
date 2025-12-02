##################################
# cs_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter


@add_instruction_formatter(
    "CS", required_params={"rs1", "rs1val", "rs2", "rs2val", "immval"}, imm_bits=5, imm_signed=False
)
def format_cs_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CS-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.immval is not None
    # scaled_imm = modify_imm(params.immval, 5, signed=False) * 4
    # TODO: Implement CS-type instruction formatting
    # setup = [
    #     load_int_reg("rs1", params.rs1, params.rs1val, test_data),
    #     load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    # ]
    # test = [
    #     f"{instr_name} x{params.rs2}, {scaled_imm}(x{params.rs1}) # perform operation imm = {params.immval} scaled_imm = {scaled_imm}",
    # ]
    # check = []
    return ([], [], [])  # Placeholder return until implemented
