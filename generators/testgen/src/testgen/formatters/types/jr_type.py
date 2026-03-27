##################################
# jr_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, return_test_regs, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

jr_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "rs2", "immval", "temp_reg", "temp_val"},
    imm_bits=12,
    imm_signed=True,
)


@add_instruction_formatter("JR", jr_config)
def format_jr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format JR-type instruction."""
    assert params.rs1 is not None and params.temp_reg is not None and params.rd is not None
    assert params.immval is not None and params.temp_val is not None

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    setup = [
        f"LA(x{params.rs1}, 1f) # load jump target address",
        load_int_reg("jump check value", params.temp_reg, params.temp_val, test_data),
    ]

    # Handle special case where offset is -2048 (can't represent +2048 in 12 bits)
    if params.immval == -2048:
        setup.extend(
            [
                f"addi x{params.rs1}, x{params.rs1}, 2047 # increment by 2047",
                f"addi x{params.rs1}, x{params.rs1}, 1 # increment by 1 more for total +2048",
            ]
        )
    else:
        setup.append(f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset")

    test = [
        f"{instr_name} x{params.rd}, x{params.rs1}, {params.immval} # perform jump with offset",
    ]
    check = [
        f"addi x{params.temp_reg}, x{params.temp_reg}, -4 # should not execute",
        "1:",
        f"addi x{params.temp_reg}, x{params.temp_reg}, 2 # should execute",
        write_sigupd(params.temp_reg, test_data, "int"),
        f"auipc x{params.temp_reg}, 0 # get current PC",
        f"sub x{params.rd}, x{params.rd}, x{params.temp_reg} # subtract current PC to make position-independent",
        write_sigupd(params.rd, test_data, "int"),
    ]
    return_test_regs(test_data, params)
    return (setup, test, check)
