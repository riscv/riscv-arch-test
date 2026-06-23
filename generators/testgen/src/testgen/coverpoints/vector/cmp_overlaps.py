##################################
# cmp_overlaps.py
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


@add_coverpoint_generator("cmp_vd_vs2")
def make_vd_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        try:
            params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vd=v, vs2=v)
        except ValueError:
            continue

        desc = f"cmp_vd_vs2 (Test vd = vs2 = v{v})"
        bin_name = f"cp_vd_vs2_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_vd_vs1")
def make_vd_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vd=v, vs1=v)

        desc = f"cmp_vd_vs1 (Test vd = vs1 = v{v})"
        bin_name = f"cp_vd_vs1_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_vs1_vs2")
def make_vs1_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vs1=v, vs2=v)

        desc = f"cmp_vs1_vs2 (Test vs1 = vs2 = v{v})"
        bin_name = f"cp_vs1_vs2_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_vd_vs1_vs2")
def make_vd_vs1_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, vd=v, vs1=v, vs2=v)

        desc = f"cmp_vd_vs1_vs2 (Test vd = vs1 = vs2 = v{v})"
        bin_name = f"cp_vd_vs1_vs2_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
