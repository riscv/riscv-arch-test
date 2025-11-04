##################################
# jr_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.instruction_params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("JR", required_params={"rd", "rs1", "rs2", "immval"})
def format_jr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format JR-type instruction."""
    assert params.rs1 is not None and params.rs2 is not None and params.rd is not None
    assert params.immval is not None
    scaled_imm = modify_imm(params.immval, 12)

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_reg=[0])

    setup = [
        f"LA(x{params.rs1}, 1f) # load jump target address",
        f"LI(x{params.rs2}, 1) # initialize indicator to 1 (jump taken)",
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

    test = [
        f"{instr_name} x{params.rd}, x{params.rs1}, {scaled_imm} # perform jump with offset",
    ]
    temp_reg = test_data.int_regs.get_register(exclude_reg=[0])
    check = [
        f"LI(x{params.rs2}, 0) # should not execute (jump not taken)",
        "1:",
        f"auipc x{temp_reg}, 0 # get current PC",
        f"sub x{params.rd}, x{params.rd}, x{temp_reg} # subtract current PC to make position-independent",
        write_sigupd(params.rd, test_data, "int"),
        write_sigupd(params.rs2, test_data, "int"),
    ]
    test_data.int_regs.return_register(temp_reg)
    test_data.int_regs.return_registers(params.used_int_regs)
    return (setup, test, check)
