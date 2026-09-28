##################################
# cbo_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cbo_config = InstructionTypeConfig(required_params={"rs1", "rs1val", "immval"}, imm_bits=12, imm_signed=True)


@add_instruction_formatter("CBO", cbo_config)
def format_cbo_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CBO-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None and params.immval is not None
    setup = [
        f"LA(x{params.rs1}, scratch) # load address of scratch into rs1",
        f"addi x{params.rs1}, x{params.rs1}, {abs(params.immval % 256)} # offset within the scratch region, potentially hitting different lines and checking alignment doesn't matter",
    ]
    test = [
        f"{instr_name} (x{params.rs1}) # perform operation",
    ]
    # cbo.zero must zero the block holding rs1; the other CBOs may legally be no-ops, so they have no check.
    # Dirtying the byte first keeps the check meaningful when an earlier testcase already zeroed the block.
    check = [""]
    if instr_name == "cbo.zero":
        setup.append(f"sb x{params.rs1}, 0(x{params.rs1}) # dirty a byte inside the block so zeroing it is observable")
        check = [
            f"lbu x{params.rs1}, 0(x{params.rs1}) # read back a byte inside the zeroed block; must be 0",
            write_sigupd(params.rs1, test_data, "int"),
        ]
    return (setup, test, check)
