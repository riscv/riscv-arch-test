##################################
# css_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("CSS")
def format_css_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSS-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None
    assert params.immval is not None
    scaled_imm = modify_imm(params.immval, 8)
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rs2}, {scaled_imm}(sp) # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
