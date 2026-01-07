##################################
# is_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd

is_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "rs1val", "immval"}, imm_bits="xlen_log2", imm_signed=False
)


@add_instruction_formatter("IS", is_config)
def format_is_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format IS-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rd is not None
    assert params.immval is not None
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
    ]
    test = [
        f"{instr_name} x{params.rd}, x{params.rs1}, {params.immval} # perform operation",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
    ]
    return (setup, test, check)
