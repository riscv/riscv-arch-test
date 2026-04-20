##################################
# cl_type.py
#
# jcarlin@hmc.edu Nov 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cl_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "immval", "temp_val"},
    reg_range=range(8, 16),
    imm_bits=8,
    imm_signed=False,
)


@add_instruction_formatter("CL", cl_config)
def format_cl_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CL-type instruction."""
    assert params.rs1 is not None
    assert params.temp_val is not None
    assert params.rd is not None and params.immval is not None

    # Determine alignment requirement and max value: c.ld needs 8-byte, c.lw needs 4-byte
    if instr_name == "c.ld":
        alignment = 8
        max_val = 248
    elif instr_name == "c.lw":
        alignment = 4
        max_val = 124
    else:
        raise ValueError(f"Unknown CL instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

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
