##################################
# ci_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd

ci_config = InstructionTypeConfig(required_params={"rs1", "rs1val", "immval"}, imm_bits=6, imm_signed=True)


@add_instruction_formatter("CI", ci_config)
def format_ci_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CI-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.immval is not None
    setup: list[str] = []
    if instr_name == "c.addi16sp":
        # For c.addi16sp, the immediate is scaled by 16 (left shift by 4) and rs1 must be x2 (sp)
        # params.immval <<= 4
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = 2
        setup.append(test_data.int_regs.consume_registers([params.rs1]))
    setup.append(load_int_reg("rd/rs1", params.rs1, params.rs1val, test_data))
    test = [
        f"{instr_name} x{params.rs1}, {params.immval} # perform operation",
    ]
    check = [write_sigupd(params.rs1, test_data, "int")]
    return (setup, test, check)
