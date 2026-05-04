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
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_csr_frm")
def make_frm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for frm values."""
    if coverpoint != "cp_csr_frm":
        raise ValueError(f"Unknown cp_csr_frm coverpoint variant: {coverpoint} for {instr_name}")

    # Test each valid fcsr.frm value (0-4) via the dynamic rounding mode path (rm=111).
    # Passing frm="dyn" encodes rm=111 in the instruction; csr_frm_val tells the formatter
    # which exact value to write into fcsr.frm before the instruction executes, and the
    # formatter restores fcsr.frm=0 in check — no ordering dependency needed.
    frm_modes = (("rne", 0), ("rtz", 1), ("rdn", 2), ("rup", 3), ("rmm", 4))
    test_chunks: list[TestChunk] = []
    for frm_name, frm_val in frm_modes:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], frm="dyn", csr_frm_val=frm_val)
        desc = f"{coverpoint} (Test dynamic frm, fcsr.frm = {frm_val})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, frm_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
