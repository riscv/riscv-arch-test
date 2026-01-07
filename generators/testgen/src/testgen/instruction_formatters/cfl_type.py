##################################
# cfl_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import write_sigupd

cfl_config = InstructionTypeConfig(
    required_params={"fd", "rs1", "immval", "temp_val"},
    reg_range=range(8, 16),
    imm_bits=8,
    imm_signed=False,
)


@add_instruction_formatter("CFL", cfl_config)
def format_cfl_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CFL-type instruction."""
    assert params.rs1 is not None
    assert params.temp_val is not None
    assert params.fd is not None and params.immval is not None

    # Determine alignment requirement and max value: c.fld needs 8-byte, c.flw needs 4-byte
    if instr_name == "c.fld":
        alignment = 8
        max_val = 248
    elif instr_name == "c.flw":
        alignment = 4
        max_val = 124
    else:
        raise ValueError(f"Unknown CFL instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    # Add value to load data region
    test_data.add_test_data_value(params.temp_val)

    setup = [
        f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, {-params.immval} # adjust base address for load",
    ]
    test = [
        f"{instr_name} f{params.fd}, {params.immval}(x{params.rs1}) # perform operation",
    ]
    check = [
        write_sigupd(params.fd, test_data, "float"),
        f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
    ]
    return (setup, test, check)
