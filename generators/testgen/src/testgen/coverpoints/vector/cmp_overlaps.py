##################################
# cmp_overlaps.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import re

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import extract_instruction_info, get_base_lmul
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instr_type_config
from testgen.formatters.vector_params import generate_random_vector_params, get_overlap_constraints, has_invalid_overlap


@add_coverpoint_generator("cmp_vd_vs2")
@add_coverpoint_generator("cmp_vd_vs1")
@add_coverpoint_generator("cmp_vs1_vs2")
@add_coverpoint_generator("cmp_vs3_vs2")
def make_two_way_cmp(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Test generator for all cmp_vX_vX coverpoints.

    Generates tests where the two given registers are the same register for all valid values.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    cmp, v1, v2, *suffixes = coverpoint.split("_")
    assert cmp == "cmp"

    info = extract_instruction_info(instr_name, instr_type)
    instr_type_config = get_instr_type_config(instr_type)
    assert instr_type_config.vector_data is not None, "vector_data must be set for vector instruction types"

    lower_bound, upper_bound = 0, test_data.vec_regs.reg_count
    emul = 1
    suffix = "_".join(suffixes)

    if suffix == "nv0":
        lower_bound = 1

    emul_match = re.search(r"emul(\d)", suffix)
    if emul_match is not None:
        emul = int(emul_match.group(1))

    sew_match = re.search(r"sew(\d+)", suffix)
    if sew_match is not None:
        sew = int(sew_match.group(1))
        # This suffix means to only test one specific sew
        if sew != test_data.config.sew:
            return []
    sew_lte_match = re.search(r"sew_lte_(\d+)", suffix)
    if sew_lte_match is not None:
        max_sew = int(sew_lte_match.group(1))
        if test_data.config.sew > max_sew:
            return []

    if "eew_eq_sew" in suffix:
        if info.index_eew is not None:
            eew = info.index_eew
        elif info.load_store_eew is not None:
            eew = info.load_store_eew
        else:
            raise ValueError(f"Unable to Extract EEW from {instr_name}")

        if eew != test_data.config.sew:
            return []

    # Notice the slight difference from the sew_let_(\d+) format
    lte_match = re.search(r"lte(\d+)", suffix)
    if lte_match is not None:
        upper_bound = int(lte_match.group(1)) + 1

    egs_match = re.search(r"egs(\d)", suffix)
    if egs_match is not None:
        raise NotImplementedError("Handle EGS")

    test_chunks = []
    lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)

    no_overlap = get_overlap_constraints(info, instr_type_config, False, test_data.config.sew)
    for v in range(lower_bound, upper_bound, emul):
        presets = {v1: v, v2: v}

        # For certain overlaps with load/store instructions, the overlap can depend on SEW, so we do an overlap
        # check here to ensure we test a valid overlap
        temp_params = InstructionParams(**presets)  # pyright: ignore
        if has_invalid_overlap(
            temp_params,
            info,
            no_overlap,
            1,  # lmul
            test_data.config.sew,
            instr_type_config.vector_data.scalar_regs,
            instr_type_config.vector_data.mask_regs,
        ):
            continue

        test_data.vec_regs.allocate_operand(v1, v, int(max(lmul, 1)))
        test_data.vec_regs.allocate_operand(v2, v, int(max(lmul, 1)), suppress_overlap=True)
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=1,
            additional_no_overlap=set(),
            suite="base",
            masked=False,
            **presets,
        )

        desc = f"cmp_{v1}_{v2} (Test {v1} = {v2} = v{v})"
        bin_name = f"cp_{v1}_{v2}_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_vd_vs1_vs2")
def make_three_way_cmp(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates tests where all three vector source operands are the same register
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    cmp, v1, v2, v3, *suffixes = coverpoint.split("_")
    assert cmp == "cmp"

    lower_bound, upper_bound = 0, test_data.vec_regs.reg_count
    emul = 1
    suffix = "_".join(suffixes)

    if suffix == "nv0":
        lower_bound = 1

    egs_match = re.search(r"egs(\d)", suffix)
    if egs_match is not None:
        raise NotImplementedError("Handle EGS")

    test_chunks = []
    lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)

    for v in range(lower_bound, upper_bound, emul):
        presets = {v1: v, v2: v, v3: v}
        test_data.vec_regs.allocate_operand(v1, v, int(max(lmul, 1)))
        test_data.vec_regs.allocate_operand(v2, v, int(max(lmul, 1)), suppress_overlap=True)
        test_data.vec_regs.allocate_operand(v3, v, int(max(lmul, 1)), suppress_overlap=True)
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=1,
            additional_no_overlap=set(),
            suite="base",
            masked=False,
            **presets,
        )

        desc = f"cmp_{v1}_{v2}_{v3} (Test {v1} = {v2} = {v3} = v{v})"
        bin_name = f"cp_{v1}_{v2}_{v3}_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
