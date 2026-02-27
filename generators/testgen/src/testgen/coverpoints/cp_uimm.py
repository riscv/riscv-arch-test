##################################
# cp_uimm.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_uimm coverpoint generator."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_uimm")
def make_cp_uimm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for unsigned immediate values."""
    if coverpoint == "cp_uimm":
        uimm_vals = range(0, test_data.xlen)
    elif coverpoint.endswith("_5"):
        uimm_vals = range(0, 32)
    elif coverpoint.endswith("_n0"):
        uimm_vals = range(1, test_data.xlen)
    else:
        raise ValueError(f"Unknown cp_uimm coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for uimm in uimm_vals:
        params = generate_random_params(test_data, instr_type, immval=uimm)
        desc = f"{coverpoint}: imm={uimm}"
        test_lines.append(
            format_single_test(instr_name, instr_type, test_data, params, desc, f"uimm{uimm}", coverpoint)
        )
        return_test_regs(test_data, params)

    return test_lines
