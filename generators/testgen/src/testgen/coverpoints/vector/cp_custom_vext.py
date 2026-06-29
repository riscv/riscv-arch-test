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
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase

_VREG_COUNT = 32


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
    sew = test_data.config.sew
    assert sew is not None
    count = test_data.test_count

    vs2_label = f"vs2_vext_{count:03d}"
    vd_label = f"vd_vext_{count:03d}"
    test_data.register_vector_data(vs2_label, sew, random_elements=1)
    test_data.register_vector_data(vd_label, sew, random_elements=1)

    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    test_data.vec_regs.allocate_parameter("vd", vd, vd_emul, suppress_overlap=True)
    test_data.vec_regs.allocate_parameter("vs2", vs2, vs2_emul, suppress_overlap=True)

    params = InstructionParams(
        vd=vd,
        vd_val_pointer=vd_label,
        vs2=vs2,
        vs2_val_pointer=vs2_label,
        temp_reg=temp_reg,
        sew=sew,
        lmul=lmul,
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
    """One test per lmul: vs2 placed at top of vd's register group (legal overlap)."""
    test_chunks = []
    for lmul in lmul_list:
        vs2_emul = max(1, lmul // vext_factor)
        vd = random.choice(range(0, _VREG_COUNT, lmul))
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
