##################################
# cr_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.data.instruction_params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter("CR")
def format_cr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CR-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None
    # x0 is not allowed as rs2 for c.add and c.mv
    if instr_name in ["c.add", "c.mv"] and params.rs2 == 0:
            test_data.int_regs.return_register(params.rs2)
            params.rs2=test_data.int_regs.get_register(exclude_reg=[0])
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rd}, x{params.rs2} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
