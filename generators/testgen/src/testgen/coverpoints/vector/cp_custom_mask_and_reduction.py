##################################
# cp_custom_mask_and_reduction.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.params import PresetMask
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_vmask_write_lmulge1")
def make_vmask_write_lmulge1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test ensuring that only the first register in the group is modified.
    TODO: Generate a better SIGUPD for this test, as a mask producing SIGUPD only checks one register. This case is not being
        properly exercised.
    """
    test_chunks = []
    for lmul in [1, 2, 4, 8]:
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, suite="length", vl="vlmax")
        desc = f"cp_custom_vmask_write_lmulge1 (lmul={lmul})"
        bin_name = f"cp_custom_vmask_write_lmulge1_lmul_{lmul}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_custom_vmask_write_v0_masked")
def make_vmask_write_v0_masked(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate a test where vd = v0 for mask producing operation.
    """
    test_data.vec_regs.allocate_operand("vd", 0, 1)
    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        suite="length",
        vl="vlmax",
        vd=0,
        maskval=PresetMask.ONES,
        additional_no_overlap={("vs1", "v0"), ("vs2", "v0")},
    )
    desc = "cp_custom_vmask_write_v0_masked (vd=v0, mask=ones)"
    bin_name = "cp_custom_vmask_write_v0_masked"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_element0Masked")
def make_element0Masked(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test confirming that the scalar element is not impacted by the mask.

    TODO: Verify correctness here: Coverage says we need ones, but this test seems like it would make more sense with
        zeros in the mask.
    """
    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        suite="length",
        vl="vlmax",
        maskval=PresetMask.ONES,
        additional_no_overlap={("vd", "v0"), ("vs1", "v0"), ("vs2", "v0")},
    )
    desc = "cp_custom_element0Masked (maskval=ones, vl=vlmax)"
    bin_name = "cp_custom_element0Masked"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_vreductionw_vd_vs1_emul_16")
def make_vreductionw_vd_vs1_emul_16(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generates a test performing a widening reduction at lmul = 8. Normal widening instructions would imply
    an emul of 16, but because this is a test for reductions, which use scalar registers, the instruction
    is valid.
    """
    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=8, suite="length")
    desc = "cp_custom_vreductionw_vd_vs1_emul_16 (lmul=8)"
    bin_name = "cp_custom_vreductionw_vd_vs1_emul_16"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_voffgroup_vd_lmul")
def make_voffgroup_vd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test that ensures that scalar destination registers can be accessed off group, with lmul > 1 because
    they have an emul of 1 for reductions.
    """
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_operand("vd", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, suite="length", vl="vlmax", vd=v
        )
        desc = f"cp_custom_voffgroup_vd_lmul{lmul} (lmul={lmul}, vd=v{v})"
        bin_name = f"cp_custom_voffgroup_vd_lmul{lmul}_b{v}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_custom_voffgroup_vs1_lmul")
def make_voffgroup_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test that ensures that scalar vs1 registers can be accessed off group, with lmul > 1 because
    they have an emul of 1 for reductions.
    """
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_operand("vs1", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, suite="length", vl="vlmax", vs1=v
        )
        desc = f"cp_custom_voffgroup_vs1_lmul{lmul} (lmul={lmul}, vs1=v{v})"
        bin_name = f"cp_custom_voffgroup_vs1_lmul{lmul}_b{v}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)
    return test_chunks


@add_coverpoint_generator("cp_custom_voffgroup_vs2_lmul")
def make_voffgroup_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a test that ensures that scalar vs2 registers can be accessed off group, with lmul > 1 because
    they have an emul of 1 for reductions.
    """
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v in range(test_data.vec_regs.reg_count):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_operand("vs2", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, suite="length", vl="vlmax", vs2=v
        )
        desc = f"cp_custom_voffgroup_vs2_lmul{lmul} (lmul={lmul}, vs2=v{v})"
        bin_name = f"cp_custom_voffgroup_vs2_lmul{lmul}_b{v}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)
    return test_chunks
