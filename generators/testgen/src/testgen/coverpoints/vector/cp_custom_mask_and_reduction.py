##################################
# cp_custom_mask_and_reduction.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import itertools

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews
from testgen.data.params import PresetMask
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_vmask_write_lmulge1")
def make_vmask_write_lmulge1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test ensuring that only the first register in the group is modified.
    TODO: Generate a better SIGUPD for this test, as a mask producing SIGUPD only checks one register. This case is not being
        properly exercised.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks = []
    for lmul, sew in itertools.product([1, 2, 4, 8], sews):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, sew, suite="length", vl="vlmax")
        desc = f"cp_custom_vmask_write_lmulge1 (lmul={lmul}, sew={sew})"
        bin_name = f"cp_custom_vmask_write_lmulge1_lmul_{lmul}_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_custom_vmask_write_v0_masked")
def make_vmask_write_v0_masked(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate a test where vd = v0 for mask producing operation.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks = []
    for sew in sews:
        test_data.vec_regs.allocate_operand("vd", 0, 1)
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            1,
            sew,
            suite="length",
            vl="vlmax",
            vd=0,
            maskval=PresetMask.ONES,
            additional_no_overlap={("vs1", "v0"), ("vs2", "v0")},
        )
        desc = f"cp_custom_vmask_write_v0_masked (vd=v0, mask=ones, sew={sew})"
        bin_name = f"cp_custom_vmask_write_v0_masked_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_custom_element0Masked")
def make_element0Masked(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test confirming that the scalar element is not impacted by the mask.

    TODO: Verify correctness here: Coverage says we need ones, but this test seems like it would make more sense with
        zeros in the mask.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks = []
    for sew in sews:
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            1,
            sew,
            suite="length",
            vl="vlmax",
            maskval=PresetMask.ONES,
            additional_no_overlap={("vd", "v0"), ("vs1", "v0"), ("vs2", "v0")},
        )
        desc = f"cp_custom_element0Masked (maskval=ones, vl=vlmax, sew={sew})"
        bin_name = f"cp_custom_element0Masked_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_custom_vreductionw_vd_vs1_emul16")
def make_vreductionw_vd_vs1_emul_16(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generates a test performing a widening reduction at lmul = 8. Normal widening instructions would imply
    an emul of 16, but because this is a test for reductions, which use scalar registers, the instruction
    is valid.
    """

    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks: list[TestChunk] = []
    for sew in sews:
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=8, sew=sew, suite="length")
        desc = f"cp_custom_vreductionw_vd_vs1_emul_16 (lmul=8, sew={sew})"
        bin_name = f"cp_custom_vreductionw_vd_vs1_emul_16_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_custom_voffgroup_vd_lmul")
def make_voffgroup_vd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test that ensures that scalar destination registers can be accessed off group, with lmul > 1 because
    they have an emul of 1 for reductions.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v, sew in itertools.product(range(test_data.vec_regs.reg_count), sews):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_operand("vd", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, sew, suite="length", vl="vlmax", vd=v
        )
        desc = f"cp_custom_voffgroup_vd_lmul{lmul} (lmul={lmul}, vd=v{v}, sew={sew})"
        bin_name = f"cp_custom_voffgroup_vd_lmul{lmul}_b{v}_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_custom_voffgroup_vs1_lmul")
def make_voffgroup_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test that ensures that scalar vs1 registers can be accessed off group, with lmul > 1 because
    they have an emul of 1 for reductions.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v, sew in itertools.product(range(test_data.vec_regs.reg_count), sews):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_operand("vs1", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, sew, suite="length", vl="vlmax", vs1=v
        )
        desc = f"cp_custom_voffgroup_vs1_lmul{lmul} (lmul={lmul}, vs1=v{v}, sew={sew})"
        bin_name = f"cp_custom_voffgroup_vs1_lmul{lmul}_b{v}_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_custom_voffgroup_vs2_lmul")
def make_voffgroup_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test that ensures that scalar vs2 registers can be accessed off group, with lmul > 1 because
    they have an emul of 1 for reductions.
    """
    sews, coverpoint = extract_coverpoint_sews(coverpoint)
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v, sew in itertools.product(range(test_data.vec_regs.reg_count), sews):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_operand("vs2", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul, sew, suite="length", vl="vlmax", vs2=v
        )
        desc = f"cp_custom_voffgroup_vs2_lmul{lmul} (lmul={lmul}, vs2=v{v}, sew={sew})"
        bin_name = f"cp_custom_voffgroup_vs2_lmul{lmul}_b{v}_sew{sew}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)
    return test_chunks
