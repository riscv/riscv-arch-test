##################################
# i_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("I", required_params={"rd", "rs1", "rs1val", "immval"})
def format_i_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format I-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rd is not None
    assert params.immval is not None
    scaled_imm = modify_imm(params.immval, 12)
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rd}, x{params.rs1}, {scaled_imm} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
