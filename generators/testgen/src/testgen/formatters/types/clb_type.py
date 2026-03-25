##################################
# clb_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

clb_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "immval", "temp_val"},
    reg_range=range(8, 16),
    imm_bits=2,
    imm_signed=False,
)


@add_instruction_formatter("CLB", clb_config)
def format_clb_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CLB-type instruction."""
    assert params.rs1 is not None
    assert params.temp_val is not None
    assert params.rd is not None and params.immval is not None

    # Add value to load data region
    assert test_data.test_chunk is not None
    test_data.test_chunk.data_values.append(params.temp_val)

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
