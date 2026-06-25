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
from testgen.coverpoints.vector.vector_helpers import extract_instruction_info
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase


def _parse_lmul(coverpoint: str) -> int:
    """Extract the integer LMUL suffix from a coverpoint name like *_lmul2."""
    return int(coverpoint.rsplit("_lmul", 1)[1])


def _make_overlap_test(
    test_data: TestData,
    instr_name: str,
    instr_type: str,
    vd: int,
    vd_width: int,
    vs2: int,
    vs2_width: int,
    vs1: int,
    vs1_width: int,
    lmul: int,
    desc: str,
    bin_name: str,
    coverpoint: str,
) -> TestChunk:
    """Build a single test case with explicitly overlapping vector registers.

    allocate_parameter(suppress_overlap=True) is used so the register file
    does not reject the intentional overlap; the formatter enforces correct
    assembly order.
    """
    sew = test_data.config.sew
    assert sew is not None
    count = test_data.test_count

    vs1_label = f"vs1_overlap_{count:03d}"
    vs2_label = f"vs2_overlap_{count:03d}"
    vd_label = f"vd_overlap_{count:03d}"
    test_data.register_vector_data(vs1_label, sew, random_elements=1)
    test_data.register_vector_data(vs2_label, sew, random_elements=1)
    test_data.register_vector_data(vd_label, sew, random_elements=1)

    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    # Allocate in order: vd first (consuming its range), then the overlapping
    # register (suppress_overlap skips already-consumed slots), then the
    # non-overlapping register.
    test_data.vec_regs.allocate_parameter("vd", vd, vd_width, suppress_overlap=True)
    test_data.vec_regs.allocate_parameter("vs2", vs2, vs2_width, suppress_overlap=True)
    test_data.vec_regs.allocate_parameter("vs1", vs1, vs1_width, suppress_overlap=True)

    params = InstructionParams(
        vd=vd,
        vd_val_pointer=vd_label,
        vs2=vs2,
        vs2_val_pointer=vs2_label,
        vs1=vs1,
        vs1_val_pointer=vs1_label,
        temp_reg=temp_reg,
        sew=sew,
        lmul=lmul,
        vector_suite="base",
    )

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return tc


def _probe_free_registers(test_data: TestData, vd: int, emul: int, alignment: int) -> list[int]:
    """Temporarily allocate vd to find registers that do not overlap with it."""
    test_data.vec_regs.allocate_parameter("_vd_probe", vd, emul, suppress_overlap=True)
    candidates = list(test_data.vec_regs.free_registers(alignment, 1))
    test_data.vec_regs.deallocate_parameter("_vd_probe")
    return candidates


# ---------------------------------------------------------------------------
# Top-of-vd overlap with vs2 (WVV widening: vd is wider than vs2/vs1)
# ---------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vdOverlapTopVs2_vd_vs2")
def make_vd_overlap_top_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    vd = random.choice(range(0, 32, emul))
    vs2 = vd + lmul
    vs1 = random.choice(_probe_free_registers(test_data, vd, emul, lmul))

    desc = f"cp_custom_vdOverlapTopVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
    bin_name = f"cp_custom_vdOverlapTopVs2_vd_vs2_lmul{lmul}"
    return [
        _make_overlap_test(
            test_data, instr_name, instr_type, vd, emul, vs2, lmul, vs1, lmul, lmul, desc, bin_name, coverpoint
        )
    ]


@add_coverpoint_generator("cp_custom_allVdOverlapTopVs2_vd_vs2")
def make_all_vd_overlap_top_vs2(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    chunks = []
    for vd in range(0, 32, emul):
        vs2 = vd + lmul
        vs1 = random.choice(_probe_free_registers(test_data, vd, emul, lmul))

        desc = f"cp_custom_allVdOverlapTopVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
        bin_name = f"cp_custom_allVdOverlapTopVs2_vd_vs2_lmul{lmul}_vd_v{vd}_vs2_v{vs2}"
        chunks.append(
            _make_overlap_test(
                test_data, instr_name, instr_type, vd, emul, vs2, lmul, vs1, lmul, lmul, desc, bin_name, coverpoint
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Top-of-vd overlap with vs1 (WVV and WWV: vs1 or vs2 may also be widened)
# ---------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vdOverlapTopVs1_vd_vs1")
def make_vd_overlap_top_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    # For WWV, vs2 is also widened and must be aligned to emul.
    info = extract_instruction_info(instr_name, instr_type)
    vs2_width = emul if info.widen_vs2 else lmul
    vs2_alignment = vs2_width

    vd = random.choice(range(0, 32, emul))
    vs1 = vd + lmul
    vs2 = random.choice(_probe_free_registers(test_data, vd, emul, vs2_alignment))

    desc = f"cp_custom_vdOverlapTopVs1_vd_vs1_lmul{lmul} (vd=v{vd}, vs1=v{vs1})"
    bin_name = f"cp_custom_vdOverlapTopVs1_vd_vs1_lmul{lmul}"
    return [
        _make_overlap_test(
            test_data, instr_name, instr_type, vd, emul, vs2, vs2_width, vs1, lmul, lmul, desc, bin_name, coverpoint
        )
    ]


@add_coverpoint_generator("cp_custom_allVdOverlapTopVs1_vd_vs1")
def make_all_vd_overlap_top_vs1(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    info = extract_instruction_info(instr_name, instr_type)
    vs2_width = emul if info.widen_vs2 else lmul
    vs2_alignment = vs2_width

    chunks = []
    for vd in range(0, 32, emul):
        vs1 = vd + lmul
        vs2 = random.choice(_probe_free_registers(test_data, vd, emul, vs2_alignment))

        desc = f"cp_custom_allVdOverlapTopVs1_vd_vs1_lmul{lmul} (vd=v{vd}, vs1=v{vs1})"
        bin_name = f"cp_custom_allVdOverlapTopVs1_vd_vs1_lmul{lmul}_vd_v{vd}_vs1_v{vs1}"
        chunks.append(
            _make_overlap_test(
                test_data, instr_name, instr_type, vd, emul, vs2, vs2_width, vs1, lmul, lmul, desc, bin_name, coverpoint
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Bottom-of-vs2 overlap with vd (VWV narrowing: vd is narrower than vs2)
# ---------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vdOverlapBtmVs2_vd_vs2")
def make_vd_overlap_btm_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    lmul = _parse_lmul(coverpoint)
    emul = 2 * lmul

    # vd must be aligned to emul because vs2 = vd and vs2 needs emul alignment.
    vd = random.choice(range(0, 32, emul))
    vs2 = vd  # bottom overlap: vs2 starts at the same register as vd

    # Consume the full vs2 range during probing so vs1 candidates exclude it.
    test_data.vec_regs.allocate_parameter("_vd_probe", vd, lmul, suppress_overlap=True)
    test_data.vec_regs.allocate_parameter("_vs2_probe", vs2, emul, suppress_overlap=True)
    vs1_candidates = list(test_data.vec_regs.free_registers(lmul, 1))
    test_data.vec_regs.deallocate_parameter("_vd_probe")
    test_data.vec_regs.deallocate_parameter("_vs2_probe")
    vs1 = random.choice(vs1_candidates)

    desc = f"cp_custom_vdOverlapBtmVs2_vd_vs2_lmul{lmul} (vd=v{vd}, vs2=v{vs2})"
    bin_name = f"cp_custom_vdOverlapBtmVs2_vd_vs2_lmul{lmul}"
    return [
        _make_overlap_test(
            test_data, instr_name, instr_type, vd, lmul, vs2, emul, vs1, lmul, lmul, desc, bin_name, coverpoint
        )
    ]
