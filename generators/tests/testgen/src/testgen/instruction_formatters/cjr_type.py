##################################
# cjr_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd


@add_instruction_formatter("CJR", required_params={"rs1", "temp_reg", "temp_val"}, reg_range=range(1, 32))
def format_cjalr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CJR-type instruction."""
    assert params.rs1 is not None and params.temp_reg is not None and params.temp_val is not None
    setup = [
        f"LA(x{params.rs1}, 1f) # set up jump target",
        f"LI(x{params.temp_reg}, {params.temp_val}) # value to check if jump is taken",
    ]
    test = [
        f"{instr_name} x{params.rs1} # perform operation",
    ]
    check = [
        f"LI(x{params.temp_reg}, 0) # jump is not taken",
        "1: # jump target",
        write_sigupd(params.temp_reg, test_data),
    ]
    return (setup, test, check)
