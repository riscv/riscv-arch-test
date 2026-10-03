##################################
# clh_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

clh_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "immval", "temp_val"},
    reg_range=range(8, 16),
    imm_bits=2,
    imm_signed=False,
)


@add_instruction_formatter("CLH", clh_config)
def format_clh_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CLH-type instruction."""
    assert params.rs1 is not None
    assert params.temp_val is not None
    assert params.rd is not None and params.immval is not None

    # Mask off bottom bit to ensure alignment
    params.immval &= ~1

    # Add value to load data region
    assert test_data.test_chunk is not None
    test_data.test_chunk.data_values.append(params.temp_val)

    # rs1 points at the data slot, so uimm selects the byte within the slot. The slot holds a value
    # with distinct bytes for cp_uimm tests, so a misdecoded offset loads a different value.
    setup = [
        f"mv x{params.rs1}, x{test_data.int_regs.data_reg} # base address is the data slot",
    ]
    test = [
        f"{instr_name} x{params.rd}, {params.immval}(x{params.rs1}) # perform operation",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
    ]
    return (setup, test, check)
