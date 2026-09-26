##################################
# cr_vtype_agnostic.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import random
import re

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import PresetMask
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import get_element_group_lmul, get_legal_lmuls
from testgen.instructions.vector_params import generate_random_vector_params

_NO_OVERLAP_MASKED = {("vs1", "v0"), ("vs2", "v0"), ("vd", "v0"), ("vs3", "v0")}


@add_coverpoint_generator("cr_vtype_agnostic")
def make_vtype_agnostic(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate length-suite tests crossing all tail and mask agnostic/undisturbed policies.
    """
    sew = test_data.config.sew
    assert sew is not None

    eew = None
    max_emul = 8
    egs = 1
    config = get_instruction_type_config(instr_type)
    assert config.vector_data is not None
    masked = config.vector_data.maskable
    if coverpoint.startswith("cr_vtype_agnostic_"):
        suffix = coverpoint[len("cr_vtype_agnostic_") :]

        # Capture _e8
        eew_match = re.match(r"^e(\d+)", suffix)
        if eew_match is not None:
            eew = int(eew_match.group(1))

        # Capture _lmulXmax or _emulXmax
        emul_match = re.search(r"[el]mul(\d)max", suffix)
        if emul_match is not None:
            max_emul = int(emul_match.group(1))

        # Capture _egsX
        egs_match = re.search(r"egs(\d)", suffix)
        if egs_match:
            egs = int(egs_match.group(1))

        if "nomask" in suffix:
            masked = False

    # Determine maximum supported lmul
    if eew is None:
        max_lmul = max_emul
    elif eew / sew > 1:
        max_lmul = max_emul / (eew / sew)
    else:
        max_lmul = max_emul

    max_lmul = int(math.log2(max_lmul))
    min_lmul = min(get_legal_lmuls(sew))

    if egs != 1:
        min_lmul = max(min_lmul, int(math.log2(get_element_group_lmul(egs))))

    lmul_exponents = list(range(min_lmul, max_lmul + 1))

    test_chunks = []
    for vta in [0, 1]:
        for vma in [0, 1]:
            lmul = 2.0 ** random.choice(lmul_exponents)

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul,
                suite="length",
                masked=masked,
                additional_no_overlap=_NO_OVERLAP_MASKED,
                maskval=PresetMask.VLMAX_M1_ONES if masked else None,
                vl="random",
                ta=vta,
                ma=vma,
                egs=egs,
            )

            desc = f"cr_vtype_agnostic (Test vta = {vta}, vma = {vma})"
            bin_name = f"cp_vtype_agnostic_vta_{vta}_vma_{vma}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks
