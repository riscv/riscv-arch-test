##################################
# ci_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.instruction_params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("CI")
def format_ci_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CI-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.immval is not None
    setup: list[str] = []
    if instr_name == "c.addi16sp":
        # For c.addi16sp, the immediate is scaled by 16 and rs1 must be x2 (sp)
        scaled_imm = modify_imm(params.immval, 10)
        test_data.int_regs.return_registers(params.used_int_regs)
        params.rs2 = None
        params.rd = None
        params.rs1 = 2
        setup.append(test_data.int_regs.consume_registers([2]))
    else:
        scaled_imm = modify_imm(params.immval, 6)
    setup.append(
        load_int_reg("rs1", params.rs1, params.rs1val, test_data)
    )
    test = [
        f"{instr_name} x{params.rs1}, {scaled_imm} # perform operation",
    ]
    check = [write_sigupd(params.rs1, test_data, "int")]
    return (setup, test, check)
