##################################
# cbp_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter(
    "CBP",
    required_params={"rs1", "rs1val", "immval"},
    reg_range=range(8, 16),
    imm_bits="xlen_log2",
    imm_signed=False,
    imm_nonzero=True,
)
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
