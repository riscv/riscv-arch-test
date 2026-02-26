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


@add_coverpoint_generator("cp_csr_frm")
def make_frm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for frm values."""
    if coverpoint != "cp_csr_frm":
        raise ValueError(f"Unknown cp_csr_frm coverpoint variant: {coverpoint} for {instr_name}")

    # csr frm modes 0-4, end at 0 so the rest of the test continues in rne
    frm_modes = (("rmm", 4), ("rup", 3), ("rdn", 2), ("rtz", 1), ("rne", 0))
    test_lines: list[str] = []
    for frm_name, frm_mode in frm_modes:
        test_lines.append(test_data.add_testcase(f"{frm_name}", coverpoint))
        test_lines.append(f"\nfsrmi 0x{frm_mode:x} # set fcsr.frm to mode {frm_mode}\n")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
        desc = f"{coverpoint} (Test dynamic frm, fcsr.frm = {frm_mode})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines
