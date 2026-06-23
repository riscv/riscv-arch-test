##################################
# cp_custom_vshift.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


def _shift_upper_bits_mask(xlen: int, sew: int) -> int:
    bottom = int(math.log2(sew))
    width = xlen - bottom
    return ((1 << width) - 1) << bottom


@add_coverpoint_generator("cp_custom_shift_vv")
def make_shift_vv(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    xlen = test_data.config.xlen
    assert sew is not None and xlen is not None

    element_val = _shift_upper_bits_mask(xlen, sew) & ((1 << sew) - 1)
    label = "vs_corner_shift_upperbits_vs1_ones"
    test_data.register_vector_data(label, sew, elements=[element_val])

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        vs1_val_pointer=label,
    )

    desc = "cp_custom_shift_vv (Test vs1 upper shift bits = ones)"
    bin_name = "cp_custom_shift_vv_upperbits_vs1_ones"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

    return_test_regs(test_data, params)
    return [tc]
