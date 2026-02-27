##################################
# cp_fp_NaNBox.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point NaN-Box value coverpoint generator (cp_NaNBox)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_NaNBox")
def make_NaNBox(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate test for NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        load_size = "single"
    elif coverpoint.endswith("D_H") or coverpoint.endswith("S_H"):
        load_size = "half"
    else:
        raise ValueError(f"Unsupported coverpoint for NaN-Box test: {coverpoint} for instr {instr_name}.")

    test_lines: list[str] = []
    params = generate_random_params(test_data, instr_type, exclude_regs=[0], fp_load_type=load_size)
    desc = f"{coverpoint} (Test NaN-Boxed inputs)"
    test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc, "NaNBox", coverpoint))
    return_test_regs(test_data, params)

    return test_lines
