##################################
# cp_asm_count.py
#
# jcarlin@hmc.edu 21 Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk


@add_coverpoint_generator("cp_asm_count")
def make_asm_count(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a simple testcase that just executes the instruction once.
    Used for counting instruction execution in simulation.
    """
    tc = test_data.begin_test_chunk()
    tc.code = [
        "# Testcase cp_asm_count",
        test_data.add_testcase("count", coverpoint),
        f"{instr_name}",
    ]
    return [test_data.end_test_chunk()]
