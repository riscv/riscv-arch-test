##################################
# b_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd

b_config = InstructionTypeConfig(required_params={"rs1", "rs1val", "rs2", "rs2val", "temp_reg", "temp_val"})


@add_instruction_formatter("B", b_config)
def format_b_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format B-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.temp_reg is not None and params.temp_val is not None
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        load_int_reg("branch taken value", params.temp_reg, params.temp_val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rs1}, x{params.rs2}, 1f # perform operation",
    ]
    check = [
        f"LI(x{params.temp_reg}, -1) # branch not taken, set temp_reg to 0",
        "1:",
        write_sigupd(params.temp_reg, test_data),
    ]
    return (setup, test, check)
