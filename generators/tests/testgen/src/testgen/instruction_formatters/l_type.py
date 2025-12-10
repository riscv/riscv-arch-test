##################################
# l_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import to_hex, write_sigupd


@add_instruction_formatter(
    "L", required_params={"rd", "rs1", "temp_val", "immval", "temp_reg"}, imm_bits=12, imm_signed=True
)
def format_l_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format L-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for L-type instruction"
    assert params.rd is not None, "rd must be provided for L-type instruction"
    assert params.immval is not None and params.temp_val is not None, (
        "immval and temp_val must be provided for L-type instruction"
    )

    # Add value to load data region
    test_data.add_test_data_value(params.temp_val)

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    setup = [f"mv x{params.rs1}, x{test_data.int_regs.link_reg} # move data_ptr to rs1"]

    # Handle special case where offset is -2048 (can't represent +2048 in 12 bits)
    if params.immval == -2048:
        setup.extend(
            [
                f"addi x{params.rs1}, x{params.rs1}, 2047 # increment by 2047",
                f"addi x{params.rs1}, x{params.rs1}, 1    # increment by 1 more for total +2048 offset",
            ]
        )
    else:
        setup.append(f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset")

    test = [
        f"{instr_name} x{params.rd}, {params.immval}(x{params.rs1}) # perform load ({to_hex(params.temp_val, test_data.xlen)})",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        f"addi x{test_data.int_regs.link_reg}, x{test_data.int_regs.link_reg}, REGWIDTH # increment data_ptr",
    ]
    return (setup, test, check)
