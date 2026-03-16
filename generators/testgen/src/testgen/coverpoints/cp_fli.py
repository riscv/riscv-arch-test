##################################
# cp_fli.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""FLI coverpoint handler (cp_rs1_fli)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.testcase import TestCase
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_rs1_fli")
def make_fs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestCase]:
    """Generate tests for source floating-point register 1 coverpoints."""
    # Determine which fs1 registers to test based on coverpoint variant
    if coverpoint != "cp_rs1_fli":
        raise ValueError(f"Unknown cp_rs1_fli coverpoint variant: {coverpoint} for {instr_name}")

    test_cases: list[TestCase] = []

    # Generate tests
    for val in range(32):
        params = generate_random_params(test_data, instr_type, rs1=val)
        desc = f"{coverpoint} (val 'rs1' = {val})"
        tc = format_single_test(instr_name, instr_type, test_data, params, desc, f"b{val}", coverpoint)
        test_cases.append(tc)
        return_test_regs(test_data, params)

    return test_cases
