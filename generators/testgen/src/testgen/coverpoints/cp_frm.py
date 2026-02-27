##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_frm")
def make_frm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for frm values."""
    if coverpoint not in ["cp_frm_2", "cp_frm_3", "cp_frm_4"]:  # TODO: Why are these variants needed?
        raise ValueError(f"Unknown cp_frm coverpoint variant: {coverpoint} for {instr_name}")

    frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup")
    test_lines: list[str] = []
    for frm_mode in frm_modes:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], frm=frm_mode)
        desc = f"{coverpoint} (Test frm, mode = {frm_mode})"
        test_lines.append(
            format_single_test(instr_name, instr_type, test_data, params, desc, f"b{frm_mode}", coverpoint)
        )
        return_test_regs(test_data, params)

    return test_lines
