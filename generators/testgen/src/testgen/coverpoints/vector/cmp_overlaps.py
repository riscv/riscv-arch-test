##################################
# cmp_overlaps.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import itertools
import re

from testgen.asm.vector_helpers import get_egs_lmul_for_register
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews
from testgen.data.params import InstructionParams
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import get_base_lmul, parse_vector_instruction_info
from testgen.instructions.vector_params import (
    generate_random_vector_params,
    get_overlap_constraints,
    has_invalid_overlap,
)


@add_coverpoint_generator("cmp_vd_vs2")
@add_coverpoint_generator("cmp_vd_vs1")
@add_coverpoint_generator("cmp_vs1_vs2")
@add_coverpoint_generator("cmp_vs3_vs2")
def make_two_way_cmp(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Test generator for all cmp_vX_vX coverpoints.

    Generates tests where the two given registers are the same register for all valid values.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    cmp, v1, v2, *suffixes = coverpoint.split("_")
    assert cmp == "cmp"

    instr_type_config = get_instruction_type_config(instr_type)
    assert instr_type_config.vector_data is not None, "vector_data must be set for vector instruction types"
    info = parse_vector_instruction_info(instr_name, instr_type)

    lower_bound, upper_bound = 0, test_data.vec_regs.reg_count
    emul = 1
    suffix = "_".join(suffixes)

    if suffix == "nv0":
        lower_bound = 1

    emul_match = re.search(r"emul(\d)", suffix)
    if emul_match is not None:
        emul = int(emul_match.group(1))

    lte_match = re.search(r"lte(\d+)", suffix)
    if lte_match is not None:
        upper_bound = int(lte_match.group(1)) + 1

    egs_match = re.search(r"egs(\d)", suffix)
    egs = 1
    if egs_match is not None:
        egs = int(egs_match.group(1))

    test_chunks = []

    for v, sew in itertools.product(range(lower_bound, upper_bound, emul), sews):
        no_overlap = get_overlap_constraints(info, instr_type_config, False, sew)
        presets = {v1: v, v2: v}

        lmul = get_egs_lmul_for_register(v, egs) if egs != 1 else get_base_lmul(instr_name, instr_type, sew)

        # For certain overlaps with load/store instructions, the overlap can depend on SEW, so we do an overlap
        # check here to ensure we test a valid overlap
        temp_params = InstructionParams(**presets)  # pyright: ignore
        if has_invalid_overlap(
            temp_params,
            info,
            no_overlap,
            lmul,
            sew,
            instr_type_config.vector_data,
        ):
            continue

        test_data.vec_regs.allocate_operand(v1, v, int(max(lmul, 1)))
        test_data.vec_regs.allocate_operand(v2, v, int(max(lmul, 1)), suppress_overlap=True)
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul,
            sew,
            additional_no_overlap=set(),
            suite="base",
            masked=False,
            **presets,
        )

        desc = f"cmp_{v1}_{v2} (Test {v1} = {v2} = v{v}, sew={sew})"
        bin_name = f"cp_{v1}_{v2}_b{v}_sew{sew}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_vd_vs1_vs2")
def make_three_way_cmp(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates tests where all three vector source operands are the same register
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    cmp, v1, v2, v3, *suffixes = coverpoint.split("_")
    assert cmp == "cmp"

    lower_bound, upper_bound = 0, test_data.vec_regs.reg_count
    emul = 1
    suffix = "_".join(suffixes)

    if suffix == "nv0":
        lower_bound = 1

    egs_match = re.search(r"egs(\d)", suffix)
    egs = 1
    if egs_match is not None:
        egs = int(egs_match.group(1))

    test_chunks = []

    for v, sew in itertools.product(range(lower_bound, upper_bound, emul), sews):
        lmul = get_egs_lmul_for_register(v, egs) if egs != 1 else get_base_lmul(instr_name, instr_type, sew)

        presets = {v1: v, v2: v, v3: v}
        test_data.vec_regs.allocate_operand(v1, v, int(max(lmul, 1)))
        test_data.vec_regs.allocate_operand(v2, v, int(max(lmul, 1)), suppress_overlap=True)
        test_data.vec_regs.allocate_operand(v3, v, int(max(lmul, 1)), suppress_overlap=True)
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul,
            sew,
            additional_no_overlap=set(),
            suite="base",
            masked=False,
            **presets,
        )

        desc = f"cmp_{v1}_{v2}_{v3} (Test {v1} = {v2} = {v3} = v{v}, sew={sew})"
        bin_name = f"cp_{v1}_{v2}_{v3}_b{v}_sew{sew}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
