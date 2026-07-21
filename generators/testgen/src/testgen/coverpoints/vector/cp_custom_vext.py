##################################
# cp_custom_vext.py
#
# Tests for vzext/vsext register overlaps.  The VEXT instructions produce vd
# with EMUL=lmul and take vs2 with EMUL=lmul/N.  Placing vs2 at the top of
# vd's register group tests the legal-but-tricky overlap case.
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import random

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


def _make_vext_overlap_test(
    test_data: TestData,
    instr_name: str,
    instr_type: str,
    vd: int,
    vd_emul: int,
    vs2: int,
    vs2_emul: int,
    lmul: int,
    desc: str,
    bin_name: str,
    coverpoint: str,
) -> TestChunk:
    """
    Generate a test with vd and vs2 having the given preset values and random val_pointers.
    """

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    test_data.vec_regs.allocate_operand("vd", vd, vd_emul, suppress_overlap=True)
    test_data.vec_regs.allocate_operand("vs2", vs2, vs2_emul, suppress_overlap=True)

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul,
        vd=vd,
        vs2=vs2,
        sew=sew,
        vector_suite="base",
    )

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return tc


def _make_vext_overlaps(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    vext_factor: int,
    lmul_list: list,
) -> list[TestChunk]:
    """
    Generate tests where the vext instruction has a valid overlap: vs2 is placed on top of vd's register group.
    """
    test_chunks = []
    for lmul in lmul_list:
        vs2_emul = max(1, lmul // vext_factor)
        vd = random.choice(range(0, test_data.vec_regs.reg_count, lmul))
        vs2 = vd + (lmul - vs2_emul)

        desc = f"cp_custom_vext{vext_factor}_overlapping_vd_vs2 (lmul={lmul}, vd=v{vd}, vs2=v{vs2})"
        bin_name = f"cp_custom_vext{vext_factor}_overlapping_vd_vs2_lmul{lmul}"

        test_chunks.append(
            _make_vext_overlap_test(
                test_data, instr_name, instr_type, vd, lmul, vs2, vs2_emul, lmul, desc, bin_name, coverpoint
            )
        )
    return test_chunks


@add_coverpoint_generator("cp_custom_vext2_overlapping_vd_vs2")
def make_vext2_overlapping(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    return _make_vext_overlaps(instr_name, instr_type, coverpoint, test_data, vext_factor=2, lmul_list=[2, 4, 8])


@add_coverpoint_generator("cp_custom_vext4_overlapping_vd_vs2")
def make_vext4_overlapping(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    return _make_vext_overlaps(instr_name, instr_type, coverpoint, test_data, vext_factor=4, lmul_list=[4, 8])


@add_coverpoint_generator("cp_custom_vext8_overlapping_vd_vs2")
def make_vext8_overlapping(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    return _make_vext_overlaps(instr_name, instr_type, coverpoint, test_data, vext_factor=8, lmul_list=[8])
