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
    """
    Helper function to get a mask for the bits above the bottom log2(SEW) bits
    """
    bottom = int(math.log2(sew))
    width = xlen - bottom
    return ((1 << width) - 1) << bottom


def _make_shift_upperbits_test(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    *,
    narrow: bool,
) -> list[TestChunk]:
    """
    Generate a test ensuring that only the bottom log2(SEW) bits are used to control the shift amount
    """

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    xlen = test_data.config.xlen

    # For a narrow shift (VWV), the valid shift-amount bits are log2(2*SEW).
    # Upper bits above that boundary should be ignored; set them to 1 to verify.
    effective_sew = 2 * sew if narrow else sew
    element_val = _shift_upper_bits_mask(xlen, effective_sew) & ((1 << sew) - 1)

    label = f"vs1_shift_upperbits{'n' if narrow else ''}_sew{sew}"
    test_data.register_vector_data(label, sew, elements=[element_val])

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        vs1_val_pointer=label,
    )

    suffix = "n" if narrow else ""
    desc = f"cp_custom_vshift{suffix}_upperbits_vs1_ones (upper shift bits in vs1 = ones)"
    bin_name = f"cp_custom_vshift{suffix}_upperbits_vs1_ones"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_vshift_upperbits_vs1_ones")
def make_shift_upperbits_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a test ensuring that only the bottom (log2(SEW)) bits are used to control the shift amount (not narrowing variant)
    """
    return _make_shift_upperbits_test(instr_name, instr_type, coverpoint, test_data, narrow=False)


@add_coverpoint_generator("cp_custom_vshiftn_upperbits_vs1_ones")
def make_shiftn_upperbits_vs1(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate a test ensuring that only the bottom (log2(SEW)) bits are used to control the shift amount (narrowing variant)
    """
    return _make_shift_upperbits_test(instr_name, instr_type, coverpoint, test_data, narrow=True)


def _make_shift_upperbits_rs1_test(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
    *,
    narrow: bool,
) -> list[TestChunk]:
    """
    Generate a test ensuring that only the bottom log2(SEW) bits control the shift amount.
    """
    sew = test_data.config.sew
    assert sew is not None, "SEW must be provided for vector tests"

    xlen = test_data.config.xlen

    effective_sew = 2 * sew if narrow else sew
    rs1val = _shift_upper_bits_mask(xlen, effective_sew)

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        lmul=1,
        rs1val=rs1val,
    )

    suffix = "n" if narrow else ""
    desc = f"cp_custom_vshift{suffix}_upperbits_rs1_ones (upper shift bits in rs1 = ones)"
    bin_name = f"cp_custom_vshift{suffix}_upperbits_rs1_ones"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]


@add_coverpoint_generator("cp_custom_vshift_upperbits_rs1_ones")
def make_shift_upperbits_rs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate a test ensuring that only the bottom log2(SEW) bits control the shift amount. (not narrowing variant)
    """
    return _make_shift_upperbits_rs1_test(instr_name, instr_type, coverpoint, test_data, narrow=False)


@add_coverpoint_generator("cp_custom_vshiftn_upperbits_rs1_ones")
def make_shiftn_upperbits_rs1(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generate a test ensuring that only the bottom log2(SEW) bits control the shift amount. (narrowing variant)
    """
    return _make_shift_upperbits_rs1_test(instr_name, instr_type, coverpoint, test_data, narrow=True)
