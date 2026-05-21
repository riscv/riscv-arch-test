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


@add_coverpoint_generator("cp_frm")
def make_frm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for frm values."""
    if coverpoint not in ["cp_frm_2", "cp_frm_3", "cp_frm_4"]:  # TODO: Why are these variants needed?
        raise ValueError(f"Unknown cp_frm coverpoint variant: {coverpoint} for {instr_name}")

    # Static modes encode rm in the instruction. For dyn, rm=111 in the encoding and the
    # actual rounding comes from fcsr.frm, so we sweep all 5 legal frm values explicitly
    # rather than relying on a random pick that lands on rne (the power-on default) 20% of
    # the time and silently agrees with a DUT that ignores fcsr.frm.
    frm_variants: list[tuple[str, int | None]] = [("dyn", v) for v in range(5)]
    frm_variants += [(m, None) for m in ("rdn", "rmm", "rne", "rtz", "rup")]

    test_chunks: list[TestChunk] = []
    for frm_mode, csr_val in frm_variants:
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], frm=frm_mode, csr_frm_val=csr_val
        )
        bin_name = f"b{frm_mode}{csr_val}" if csr_val is not None else f"b{frm_mode}"
        desc_suffix = f", fcsr.frm = {csr_val}" if csr_val is not None else ""
        desc = f"{coverpoint} (Test frm, mode = {frm_mode}{desc_suffix})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
