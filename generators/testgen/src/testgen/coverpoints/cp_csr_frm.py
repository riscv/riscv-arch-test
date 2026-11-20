##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

import itertools

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_csr_frm")
def make_frm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for frm values."""
    is_vector = "v" in coverpoint.split("_")
    if is_vector:
        sews, coverpoint = extract_coverpoint_sews(coverpoint)
    else:
        sews = [None]

    if coverpoint not in ["cp_csr_frm", "cp_csr_frm_v"]:
        raise ValueError(f"Unknown cp_csr_frm coverpoint variant: {coverpoint} for {instr_name}")

    # Test each valid fcsr.frm value (0-4) via dynamic rounding mode (rm=111 in the encoding).
    frm_modes = (("rne", 0), ("rtz", 1), ("rdn", 2), ("rup", 3), ("rmm", 4))
    test_chunks: list[TestChunk] = []
    for (frm_name, frm_val), sew in itertools.product(frm_modes, sews):
        if is_vector:
            assert sew is not None
            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                get_base_lmul(instr_name, instr_type, sew),
                sew,
                frm="dyn",
                csr_frm_val=frm_val,
            )
        else:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], frm="dyn", csr_frm_val=frm_val)
        sew_desc = f", sew={sew}" if sew is not None else ""
        sew_bin = f"_sew{sew}" if sew is not None else ""
        desc = f"{coverpoint} (Test dynamic frm, fcsr.frm = {frm_val}{sew_desc})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{frm_name}{sew_bin}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
