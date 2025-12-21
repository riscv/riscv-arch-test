##################################
# cp_asm_count.py
#
# jcarlin@hmc.edu 21 Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData


@add_coverpoint_generator("cp_asm_count")
def make_asm_count(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """
    Generate a simple testcase that just executes the instruction once.
    Used for counting instruction execution in simulation.
    """
    test_data.add_testcase_string(coverpoint)
    test_lines = [
        "",
        "# Testcase cp_asm_count",
        f"{instr_name}",
    ]
    return test_lines
