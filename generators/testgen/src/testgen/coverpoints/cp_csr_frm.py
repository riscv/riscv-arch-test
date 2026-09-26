##################################
# cp_fp_reg_edges.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point register edge value coverpoint generators (cp_fs1_edges, cp_fs2_edges, cp_fs3_edges)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_csr_frm")
def make_frm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for frm values."""
    if coverpoint not in ["cp_csr_frm", "cp_csr_frm_v"]:
        raise ValueError(f"Unknown cp_csr_frm coverpoint variant: {coverpoint} for {instr_name}")

    is_vector = coverpoint.endswith("_v")

    # Test each valid fcsr.frm value (0-4) via dynamic rounding mode (rm=111 in the encoding).
    frm_modes = (("rne", 0), ("rtz", 1), ("rdn", 2), ("rup", 3), ("rmm", 4))
    test_chunks: list[TestChunk] = []
    for frm_name, frm_val in frm_modes:
        if is_vector:
            assert test_data.config.sew is not None, "SEW must be provided for vector tests"
            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                get_base_lmul(instr_name, instr_type, test_data.config.sew),
                frm="dyn",
                csr_frm_val=frm_val,
            )
        else:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], frm="dyn", csr_frm_val=frm_val)
        desc = f"{coverpoint} (Test dynamic frm, fcsr.frm = {frm_val})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, frm_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
