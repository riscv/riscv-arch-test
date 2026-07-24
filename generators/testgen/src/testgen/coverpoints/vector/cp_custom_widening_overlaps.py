##################################
# cp_custom_widening_overlaps.py
#
# Tests for intentional legal register overlaps in widening/narrowing
# instructions, mirroring the make_custom_vdOverlap* family from the
# reference generator.
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


def _parse_lmul(coverpoint: str) -> int:
    """Extract the integer LMUL suffix from a coverpoint name like *_lmul2."""
    return int(coverpoint.rsplit("_lmul", 1)[1])


# ---------------------------------------------------------------------------
# Top-of-vd overlap with vs2 (WVV/WVX widening: vd is wider than vs2)
# ---------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vdOverlapTopVs2_vd_vs2")
def make_vd_overlap_top_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a test where vs2 overlaps the top of vd
    """
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    vd = random.choice(range(0, 32, emul))
    vs2 = vd + lmul

    desc = f"cp_custom_vdOverlapTopVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
    bin_name = f"cp_custom_vdOverlapTopVs2_vd_vs2_lmul{lmul}"

    params = generate_random_vector_params(
        test_data, instr_name, instr_type, lmul, vd=vd, vs2=vs2, additional_no_overlap={("vd", "vs1")}
    )

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_allVdOverlapTopVs2_vd_vs2")
def make_all_vd_overlap_top_vs2(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate tests for all possible vs2 overlaps on top of vd
    """
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    chunks = []
    for vd in range(0, 32, emul):
        vs2 = vd + lmul
        desc = f"cp_custom_allVdOverlapTopVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
        bin_name = f"cp_custom_allVdOverlapTopVs2_vd_vs2_lmul{lmul}_vd_v{vd}_vs2_v{vs2}"

        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, vd=vd, vs2=vs2, additional_no_overlap={("vd", "vs1")}
        )

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_test_regs(test_data, params)

        chunks.append(tc)

    return chunks


# ---------------------------------------------------------------------------
# Top-of-vd overlap with vs1 (WVV and WWV: vs1 overlaps upper half of vd)
# ---------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vdOverlapTopVs1_vd_vs1")
def make_vd_overlap_top_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a test where vs1 overlaps the top of vd
    """
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    vd = random.choice(range(0, 32, emul))
    vs1 = vd + lmul

    desc = f"cp_custom_vdOverlapTopVs1_vd_vs1_lmul{lmul} (vd=v{vd}, vs1=v{vs1})"
    bin_name = f"cp_custom_vdOverlapTopVs1_vd_vs1_lmul{lmul}"

    params = generate_random_vector_params(
        test_data, instr_name, instr_type, lmul, vd=vd, vs1=vs1, additional_no_overlap={("vd", "vs2")}
    )

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_allVdOverlapTopVs1_vd_vs1")
def make_all_vd_overlap_top_vs1(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate tests where all possible vs1 overlaps on top of vd are exercised
    """
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    chunks = []
    for vd in range(0, 32, emul):
        vs1 = vd + lmul

        desc = f"cp_custom_allVdOverlapTopVs1_vd_vs1_lmul{lmul} (vd=v{vd}, vs1=v{vs1})"
        bin_name = f"cp_custom_allVdOverlapTopVs1_vd_vs1_lmul{lmul}_vd_v{vd}_vs1_v{vs1}"

        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, vd=vd, vs1=vs1, additional_no_overlap={("vd", "vs2")}
        )

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_test_regs(test_data, params)

        chunks.append(tc)

    return chunks


# ---------------------------------------------------------------------------
# Bottom-of-vs2 overlap with vd (VWV/VWX/VWI narrowing: vd is narrower than vs2)
# ---------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vdOverlapBtmVs2_vd_vs2")
def make_vd_overlap_btm_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a test where vd overlaps the bottom of vs2
    """
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    # vd must be aligned to emul because vs2 = vd and vs2 needs emul alignment.
    vd = random.choice(range(0, 32, emul))
    vs2 = vd  # bottom overlap: vs2 starts at the same register as vd

    desc = f"cp_custom_vdOverlapBtmVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
    bin_name = f"cp_custom_vdOverlapBtmVs2_vd_vs2_lmul{lmul}"

    params = generate_random_vector_params(
        test_data, instr_name, instr_type, lmul, vd=vd, vs2=vs2, additional_no_overlap={("vs1", "vs2")}
    )

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_allVdOverlapBtmVs2_vd_vs2")
def make_all_vd_overlap_btm_vs2(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate tests where all possible combinations of vd and vs2, where vd overlaps the bottom of vs2 are exercised
    """
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    chunks = []
    for vd in range(0, 32, emul):
        vs2 = vd  # bottom overlap
        desc = f"cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
        bin_name = f"cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul{lmul}_vd_v{vd}_vs2_v{vs2}"

        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, vd=vd, vs2=vs2, additional_no_overlap={("vs1", "vs2")}
        )

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_test_regs(test_data, params)

        chunks.append(tc)

    return chunks
