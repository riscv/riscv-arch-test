##################################
# cis_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd

cis_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "immval"},
    imm_bits="xlen_log2",
    imm_signed=False,
    imm_nonzero=True,
)


@add_instruction_formatter("CIS", cis_config)
def format_ci_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CIS-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.immval is not None
    setup: list[str] = [load_int_reg("rd/rs1", params.rs1, params.rs1val, test_data)]
    test = [
        f"{instr_name} x{params.rs1}, {params.immval} # perform operation",
    ]
    check = [write_sigupd(params.rs1, test_data, "int")]
    return (setup, test, check)
