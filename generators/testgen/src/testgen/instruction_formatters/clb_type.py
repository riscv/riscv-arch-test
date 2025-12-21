##################################
# clb_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd


@add_instruction_formatter(
    "CLB", required_params={"rd", "rs1", "immval", "temp_val"}, reg_range=range(8, 16), imm_bits=2, imm_signed=False
)
def format_clb_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CLB-type instruction."""
    assert params.rs1 is not None
    assert params.temp_val is not None
    assert params.rd is not None and params.immval is not None

    # Add value to load data region
    test_data.add_test_data_value(params.temp_val)

    setup = [
        f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, {-params.immval} # adjust base address for load",
    ]
    test = [
        f"{instr_name} x{params.rd}, {params.immval}(x{params.rs1}) # perform operation",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
    ]
    return (setup, test, check)
