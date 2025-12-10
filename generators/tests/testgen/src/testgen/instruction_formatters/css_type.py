##################################
# css_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg


@add_instruction_formatter("CSS", required_params={"rs2", "rs2val", "immval"}, imm_bits=6)
def format_css_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSS-type instruction."""
    assert params.rs2 is not None and params.rs2val is not None
    assert params.immval is not None
    setup: list[str] = []
    # sp (x2) is used as the base pointer for CSS instructions
    # Ensure sp is allocated
    if params.rd != 2:
        setup.append(test_data.int_regs.consume_registers([2]))
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rs2}, {params.immval}(sp) # perform operation",
    ]
    check = ["# TODO: Add check code for CSS instruction"]
    return (setup, test, check)
