##################################
# ciw_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

ciw_config = InstructionTypeConfig(
    required_params={"rs1val", "rd", "immval"},
    reg_range=range(8, 16),
    imm_bits=10,
    imm_signed=False,
    imm_nonzero=True,
)


@add_instruction_formatter("CIW", ciw_config)
def format_ciw_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CIW-type instruction."""
    assert params.rs1val is not None
    assert params.rd is not None
    assert params.immval is not None
    # CIW immediates must be multiples of 4 (bottom 2 bits are zero)
    params.immval = params.immval & ~0b11
    if instr_name != "c.addi4spn":
        raise ValueError(f"Unexpected CIW-type instruction: {instr_name}. CIW is currently only used for c.addi4spn.")
    setup: list[str] = []
    if params.rd != 2:
        # For c.addi4spn, rs1 must be x2 (sp)
        asm = test_data.int_regs.consume_registers([2])  # ensure sp is reserved
        if asm:
            setup.append(asm)
    setup.append(load_int_reg("sp", 2, params.rs1val, test_data))
    test = [
        f"{instr_name} x{params.rd}, sp, {params.immval} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    if params.rd != 2:
        test_data.int_regs.return_register(2)  # release sp
    return (setup, test, check)
