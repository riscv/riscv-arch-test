##################################
# lf_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import to_hex, write_sigupd

lr_config = InstructionTypeConfig(required_params={"rd", "rs1", "temp_val", "temp_reg"})


@add_instruction_formatter("LR", lr_config)
def format_lr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format LR-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for LR-type instruction"
    assert params.rd is not None, "rd must be provided for LR-type instruction"
    assert params.temp_val is not None, "temp_val must be provided for LR-type instruction"

    # Add value to load data region
    test_data.add_test_data_value(params.temp_val)

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    setup = [f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, 0 # copy data_ptr to rs1"]

    test = [
        f"{instr_name} x{params.rd}, (x{params.rs1}) # perform load ({to_hex(params.temp_val, test_data.xlen)})",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
    ]
    return (setup, test, check)
