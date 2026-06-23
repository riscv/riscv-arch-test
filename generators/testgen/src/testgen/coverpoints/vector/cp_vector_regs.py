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


@add_coverpoint_generator("cp_vs2")
def make_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        test_data.vec_regs.allocate_parameter("vs2", v, 1)
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vs2=v)

        desc = f"cp_vs2 (Test source vs2 = v{v})"
        bin_name = f"cp_vs2_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vs1")
def make_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        test_data.vec_regs.allocate_parameter("vs1", v, 1)
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vs1=v)

        desc = f"cp_vs1 (Test source vs1 = v{v})"
        bin_name = f"cp_vs1_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vd")
def make_vd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    TODO: EGS4 Handling
    """

    lower_limit, upper_limit = 0, test_data.vec_regs.reg_count
    emul = 1
    if coverpoint.startswith("cp_vd_"):
        suffix = coverpoint[len("cp_vd_") :]

        if suffix.startswith("lte"):
            upper_limit = int(suffix[len("lte") :])
        elif suffix == "nv0":
            lower_limit = 1
        elif suffix.startswith("emul"):
            emul = int(suffix[len("emul") :])

    test_chunks = []
    for v in range(lower_limit, upper_limit, emul):
        test_data.vec_regs.allocate_parameter("vd", v, 1)
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vd=v)

        desc = "cp_vd (Test destination vd = v" + str(v) + ")"
        bin_name = f"cp_vd_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
