##################################
# cp_bs.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_bs coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_bs")
def make_cp_bs(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for bs field of crypto instructions."""
    if coverpoint == "cp_bs":
        bs_vals = range(4)
    else:
        raise ValueError(f"Unknown cp_bs coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for bs in bs_vals:
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, immval=bs)
        desc = f"{coverpoint}: bs={bs}"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines
