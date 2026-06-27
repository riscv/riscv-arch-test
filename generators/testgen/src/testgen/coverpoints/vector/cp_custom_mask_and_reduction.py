##################################
# cp_custom_mask_and_reduction.py
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

_VREG_COUNT = 32


@add_coverpoint_generator("cp_custom_vmask_write_lmulge1")
def make_vmask_write_lmulge1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
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
    # Force vd=0: exercises the case where the mask-producing result is written to v0.
    # maskval="ones" causes mask-capable types (VVSR, WVWSR) to emit v0.t.
    # For MVVM/MVXM the formatter skips mask setup when vd==0 (carry-in is the mask, not a gate).
    test_data.vec_regs.allocate_parameter("vd", 0, 1)
    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        suite="length",
        vl="vlmax",
        vd=0,
        maskval="ones",
        additional_no_overlap={("vs1", "v0"), ("vs2", "v0")},
    )
    desc = "cp_custom_vmask_write_v0_masked (vd=v0, mask=ones)"
    bin_name = "cp_custom_vmask_write_v0_masked"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_element0Masked")
def make_element0Masked(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    # Reduction instructions write their result to vd[0]. Test with mask=ones (all elements
    # active) at vlmax. Prevent vd/vs1/vs2 from aliasing v0 so the mask and operands are distinct.
    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        suite="length",
        vl="vlmax",
        maskval="ones",
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
    # Widening reduction at lmul=8: vs2 occupies 8 registers (maximum emul for the source vector).
    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=8, suite="length")
    desc = "cp_custom_vreductionw_vd_vs1_emul_16 (lmul=8)"
    bin_name = "cp_custom_vreductionw_vd_vs1_emul_16"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_voffgroup_vd_lmul")
def make_voffgroup_vd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    # coverpoint ends with "lmul{N}", e.g. "cp_custom_voffgroup_vd_lmul4"
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v in range(_VREG_COUNT):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_parameter("vd", v, 1)
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
    # coverpoint ends with "lmul{N}", e.g. "cp_custom_voffgroup_vs1_lmul4"
    lmul = int(coverpoint.split("lmul")[1])
    test_chunks = []
    for v in range(_VREG_COUNT):
        if v % lmul == 0:
            continue
        test_data.vec_regs.allocate_parameter("vs1", v, 1)
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, suite="length", vl="vlmax", vs1=v
        )
        desc = f"cp_custom_voffgroup_vs1_lmul{lmul} (lmul={lmul}, vs1=v{v})"
        bin_name = f"cp_custom_voffgroup_vs1_lmul{lmul}_b{v}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)
    return test_chunks
