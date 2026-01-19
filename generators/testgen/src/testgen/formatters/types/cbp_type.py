##################################
# cbp_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cbp_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "immval"},
    reg_range=range(8, 16),
    imm_bits="xlen_log2",
    imm_signed=True,
    imm_nonzero=True,
)


@add_instruction_formatter("CBP", cbp_config)
def format_cbp_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CBP-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.immval is not None
    setup = [
        load_int_reg("rd/rs1", params.rs1, params.rs1val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rs1}, {params.immval} # perform operation",
    ]
    check = [write_sigupd(params.rs1, test_data, "int")]
    return (setup, test, check)
