##################################
# cp_vector_regs.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vd")
def make_vd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    TODO:
    elif coverpoint == "cp_vd_lte30"                  : make_vd(test, sew, range(vreg_count-1), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte29"                  : make_vd(test, sew, range(vreg_count-2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte28"                  : make_vd(test, sew, range(vreg_count-3), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte27"                  : make_vd(test, sew, range(vreg_count-4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte26"                  : make_vd(test, sew, range(vreg_count-5), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte25"                  : make_vd(test, sew, range(vreg_count-6), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte24"                  : make_vd(test, sew, range(vreg_count-7), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_nv0"                    : make_vd(test, sew, range(1,vreg_count))
    elif coverpoint == "cp_vd_emul2"                  : make_vd(test, sew, range(0,vreg_count,2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_emul4"                  : make_vd(test, sew, range(0,vreg_count,4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_emul8"                  : make_vd(test, sew, range(0,vreg_count,8), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_egs4"                   : make_vd(test, sew, range(0,vreg_count), egs=4)
    elif coverpoint == "cp_vd_egs8"                   : make_vd(test, sew, range(0,vreg_count), egs=8)
    """

    test_chunks = []
    for v in range(32):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vd=v)

        desc = "cp_vd (Test destination vd = v" + str(v) + ")"
        bin_name = f"cp_vd_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
