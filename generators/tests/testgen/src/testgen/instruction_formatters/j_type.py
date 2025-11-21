##################################
# j_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd


@add_instruction_formatter("J", required_params={"rd", "rs2"})
def format_j_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format J-type instruction."""
    assert params.rd is not None and params.rs2 is not None
    setup = [
        f"LI(x{params.rs2}, 1) # initialize indicator to 1 (jump taken)",
    ]
    test = [
        f"{instr_name} x{params.rd}, 1f # perform jump",
    ]
    check = [
        f"LI(x{params.rs2}, 0) # should not execute (jump not taken)",
        "1:",
        write_sigupd(params.rd, test_data, "int"),
        write_sigupd(params.rs2, test_data, "int"),
    ]
    return (setup, test, check)
