##################################
# cj_type.py
#
# jcarlin@hmc.edu November 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter


@add_instruction_formatter("CJ", required_params={"temp_reg", "immval"})
def format_cj_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CJ-type instruction."""
    # TODO
    setup = []
    test = []
    check = []
    return (setup, test, check)
