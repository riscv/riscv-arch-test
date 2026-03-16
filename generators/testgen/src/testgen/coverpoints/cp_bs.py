##################################
# cp_bs.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_bs coverpoint generator."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.testcase import TestCase
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_bs")
def make_cp_bs(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestCase]:
    """Generate tests for bs field of crypto instructions."""
    if coverpoint == "cp_bs":
        bs_vals = range(4)
    else:
        raise ValueError(f"Unknown cp_bs coverpoint variant: {coverpoint} for {instr_name}")

    test_cases: list[TestCase] = []
    for bs in bs_vals:
        params = generate_random_params(test_data, instr_type, immval=bs)
        desc = f"{coverpoint}: bs={bs}"
        tc = format_single_test(instr_name, instr_type, test_data, params, desc, f"b{bs}", coverpoint)
        test_cases.append(tc)
        return_test_regs(test_data, params)

    return test_cases
