##################################
# l_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("L", required_params={"rd", "rs1", "rs2", "rs2val", "immval"})
def format_l_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format L-type instruction."""
    assert params.rs1 is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None
    assert params.immval is not None
    scaled_imm = modify_imm(params.immval, 12)

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_reg=[0])

    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        f"LA(x{params.rs1}, scratch) # load base address",
    ]

    # Handle special case where offset is -2048 (can't represent +2048 in 12 bits)
    if scaled_imm == -2048:
        setup.extend(
            [
                f"addi x{params.rs1}, x{params.rs1}, 2047 # increment by 2047",
                f"addi x{params.rs1}, x{params.rs1}, 1 # increment by 1 more for total +2048",
            ]
        )
    else:
        neg_scaled_imm = -scaled_imm
        setup.append(f"addi x{params.rs1}, x{params.rs1}, {neg_scaled_imm} # adjust base address for offset")

    setup.append(f"SREG x{params.rs2}, {scaled_imm}(x{params.rs1}) # store test value to memory")
    test = [
        f"{instr_name} x{params.rd}, {scaled_imm}(x{params.rs1}) # perform load",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
