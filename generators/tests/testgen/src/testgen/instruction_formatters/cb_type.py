##################################
# cb_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter("CB")
def format_cb_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CB-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rd is not None
    assert params.immval is not None
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        f"LI(x{params.rd}, 1) # initialize rd to 1 (branch taken value)",
    ]
    test = [
        f"{instr_name} x{params.rs1}, 1f # perform operation",
    ]
    check = [
        f"LI(x{params.rd}, 0) # branch not taken, set rd to 0",
        "1:",
        write_sigupd(params.rd, test_data, "int"),
    ]
    return (setup, test, check)
