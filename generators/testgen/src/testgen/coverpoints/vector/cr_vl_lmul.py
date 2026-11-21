##################################
# cr_vl_lmul.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import re

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import PresetMask
from testgen.data.random import random_range
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import get_legal_lmuls
from testgen.instructions.vector_params import generate_random_vector_params

_NO_OVERLAP_MASKED = {("vs1", "v0"), ("vs2", "v0"), ("vd", "v0"), ("vs3", "v0")}


@add_coverpoint_generator("cr_vl_lmul")
def make_vl_lmul(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests crossing all valid lmuls with vls chosen from VLMAX, 1 (or EGS), and a random vl.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew

    egs = 1
    config = get_instruction_type_config(instr_type)
    assert config.vector_data is not None
    can_mask = config.vector_data.maskable
    suffix = coverpoint.removeprefix("cr_vl_lmul_")
    if egs_match := re.search(r"egs(\d)", suffix):
        egs = int(egs_match.group(1))
    max_lmul = vl_lmul_max(suffix, sew)

    max_lmul = int(math.log2(max_lmul))
    min_lmul = min(get_legal_lmuls(sew))

    lmul_exponents = list(range(min_lmul, max_lmul + 1))
    vl_options = ["vlmax", egs, "random"]

    test_chunks = []
    for l in lmul_exponents:
        lmul = 2.0**l
        for vl in vl_options:
            vta = random_range(0, 1)
            vma = random_range(0, 1)
            masked = random_range(0, 1) == 1 if can_mask else False
            maskval = PresetMask.VLMAX_M1_ONES if masked else None
            no_overlap = _NO_OVERLAP_MASKED if masked else None

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul,
                suite="length",
                masked=masked,
                additional_no_overlap=no_overlap,
                maskval=maskval,
                vl=vl,
                ta=vta,
                ma=vma,
            )

            desc = f"cr_vl_lmul (Test lmul = {lmul}, vl = {vl})"
            bin_name = f"cp_vl_lmul_vl_{vl}_lmul_{lmul}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks


def vl_lmul_max(suffix: str, sew: int) -> float:
    """Return the largest LMUL that the cr_vl_lmul_<suffix> coverpoint covers at an SEW.

    e<EEW>[_emul<N>max]: unit-stride or strided data of EEW, so EMUL = EEW / SEW * LMUL <= N (default 8).
    ei<EEW>_lmul<N>max: indexed segments, so data EMUL = LMUL <= N and index EMUL = EEW / SEW * LMUL <= 8.
    lmul<N>max: LMUL <= N. Anything else: LMUL <= 8.
    """
    cap = int(m.group(1)) if (m := re.search(r"[el]mul(\d)max", suffix)) else 8
    if m := re.match(r"ei(\d+)", suffix):
        return min(cap, 8 * sew / int(m.group(1)))
    if m := re.match(r"e(\d+)", suffix):
        return min(8, cap * sew / int(m.group(1)))
    return cap
