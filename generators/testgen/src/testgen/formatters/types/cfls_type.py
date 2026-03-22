##################################
# cfls_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import to_hex, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cfls_config = InstructionTypeConfig(
    required_params={"fd", "immval", "temp_reg", "temp_val"},
    reg_range=range(1, 31),  # fd cannot be x0
    imm_bits=9,  # c.ldsp: [0, 504] in multiples of 8, c.lwsp: [0, 252] in multiples of 4
    imm_signed=False,
)


@add_instruction_formatter("CFLS", cfls_config)
def format_cfls_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CFLS-type stack-pointer-based loads instruction."""
    assert params.temp_reg is not None and params.temp_val is not None
    assert params.fd is not None and params.immval is not None

    # Determine alignment requirement and max value: c.ldsp needs 8-byte, c.lwsp needs 4-byte
    if instr_name == "c.fldsp":
        alignment = 8
        max_val = 504
    elif instr_name == "c.flwsp":
        alignment = 4
        max_val = 252
    else:
        raise ValueError(f"Unknown CFLS instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    # Add value to load data region
    assert test_data.test_chunk is not None
    test_data.test_chunk.data_values.append(params.temp_val)

    setup: list[str] = []
    # sp (x2) is used as the base pointer for CFLS instructions
    # Ensure sp is allocated
    asm = test_data.int_regs.consume_registers([2])
    if asm:
        setup.append(asm)

    setup.extend(
        [
            f"mv sp, x{test_data.int_regs.data_reg} # move data_ptr to sp",
            f"addi sp, sp, {-params.immval} # adjust base address for load",
        ]
    )
    test = [
        f"{instr_name} f{params.fd}, {params.immval}(sp) # perform load ({to_hex(params.temp_val, test_data.xlen)})",
    ]
    check = [
        write_sigupd(params.fd, test_data, "float"),
        f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
    ]
    # Return sp
    test_data.int_regs.return_register(2)
    return (setup, test, check)
