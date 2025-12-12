##################################
# cp_rbox.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_rnum coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_rnum")
def make_cp_rnum(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for rnum field of crypto instructions."""
    if coverpoint == "cp_rnum":
        rnum_vals = range(0xB)  # rnum values above 0xA are reserved
    else:
        raise ValueError(f"Unknown cp_rnum coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for rnum in rnum_vals:
        test_data.add_testcase_string(coverpoint)
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, immval=rnum)
        desc = f"{coverpoint}: rnum={rnum}"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines
