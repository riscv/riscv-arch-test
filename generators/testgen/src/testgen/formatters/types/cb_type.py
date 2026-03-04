##################################
# cb_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cb_config = InstructionTypeConfig(required_params={"rs1", "rs1val", "temp_reg", "temp_val"}, reg_range=range(8, 16))


@add_instruction_formatter("CB", cb_config)
def format_cb_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CB-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.temp_reg is not None and params.temp_val is not None
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("branch taken value", params.temp_reg, params.temp_val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rs1}, 1f # perform operation",
    ]
    check = [
        f"LI(x{params.temp_reg}, 0) # branch not taken, set temp_reg to 0",
        "1:",
        write_sigupd(params.temp_reg, test_data),
    ]
    return (setup, test, check)
