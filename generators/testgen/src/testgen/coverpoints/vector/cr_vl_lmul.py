##################################
# cr_vl_lmul.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import re

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import get_legal_lmuls
from testgen.data.params import PresetMask
from testgen.data.random import random_range
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params

_NO_OVERLAP_MASKED = {("vs1", "v0"), ("vs2", "v0"), ("vd", "v0"), ("vs3", "v0")}


@add_coverpoint_generator("cr_vl_lmul")
def make_vl_lmul(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests crossing all valid lmuls with vls chosen from VLMAX, 1 (or EGS), and a random vl.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew

    eew = None
    max_emul = 8
    egs = 1
    can_mask = True
    if coverpoint.startswith("cr_vl_lmul_"):
        suffix = coverpoint[len("cr_vl_lmul_") :]

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
            can_mask = False

    # Determine maximum supported lmul
    if eew is None:
        max_lmul = max_emul
    elif eew / sew > 1:
        max_lmul = max_emul / (eew / sew)
    else:
        max_lmul = max_emul

    max_lmul = int(math.log2(max_lmul))
    min_lmul = min(get_legal_lmuls(sew))

    lmul_exponents = list(range(min_lmul, max_lmul + 1))
    vl_options = ["vlmax", egs, "random"]

    if egs != 1:
        raise NotImplementedError("EGS If Defs are Not in cr_vl_lmul.py")

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
            return_test_regs(test_data, params)

    return test_chunks
