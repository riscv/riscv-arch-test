##################################
# cp_fp_badNB.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point bad NaN-Box value coverpoint generators (cp_fs1_badNB, cp_fs2_badNB, cp_fs3_badNB)."""

from typing import Literal

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.params import generate_random_params

# Exponent and fraction widths of the narrow formats that can be NaN-boxed
_NARROW_FORMATS = {32: (8, 23), 16: (5, 10)}


def _badNB_variant(coverpoint: str, instr_name: str) -> tuple[tuple[int, ...], Literal["single", "double"], int, int]:
    """Return (edges, load type, register width, narrow width) for a badNB coverpoint variant."""
    if coverpoint.endswith("_D_S"):
        return FLOAT_EDGES.bad_NaN_double_single, "double", 64, 32
    if coverpoint.endswith("D_H"):
        return FLOAT_EDGES.bad_NaN_double_half, "double", 64, 16
    if coverpoint.endswith("S_H"):
        return FLOAT_EDGES.bad_NaN_single_half, "single", 32, 16
    raise ValueError(f"Unsupported coverpoint for bad NaN-Box tests: {coverpoint} for instr {instr_name}.")


def _is_nan(narrow: int, narrow_bits: int) -> bool:
    """Return True if narrow is a NaN encoding of the narrow_bits-wide format."""
    exp_bits, frac_bits = _NARROW_FORMATS[narrow_bits]
    exp_mask = (1 << exp_bits) - 1
    return (narrow >> frac_bits) & exp_mask == exp_mask and narrow & ((1 << frac_bits) - 1) != 0


def _other_operand(instr_name: str, instr_type: str, rand_val: int, low_bits: int, narrow_bits: int) -> int:
    """Choose a narrow value for an FP source that is not under test.

    The value is chosen so that a DUT that ignores the upper bits of the operand under test
    (using its low bits) gets a different result or flags than one that treats it as a
    canonical NaN:
    - comparisons: the operand under test's own (non-NaN) low bits, so feq returns 1 and
      flt/fle raise no NV only when the upper bits are ignored;
    - fmin/fmax: the canonical NaN, so the result is the low bits instead of the canonical NaN;
    - everything else: the random value, with any NaN turned into an infinity.
    """
    frac_bits = _NARROW_FORMATS[narrow_bits][1]
    exp_bits = _NARROW_FORMATS[narrow_bits][0]
    if instr_type == "FC" and not _is_nan(low_bits, narrow_bits):
        return low_bits
    if instr_name.split(".")[0] in ("fmin", "fmax"):
        return ((1 << (exp_bits + 1)) - 1) << (frac_bits - 1)  # canonical NaN
    narrow = rand_val & ((1 << narrow_bits) - 1)
    if _is_nan(narrow, narrow_bits):
        narrow &= ~((1 << frac_bits) - 1)  # clear the fraction so the value is not a NaN
    return narrow


def _make_badNB(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData, operand: str
) -> list[TestChunk]:
    """Generate bad NaN-Box tests for one FP source operand (fs1, fs2 or fs3).

    Only the operand under test is improperly boxed. Every other FP source is properly boxed,
    with a value chosen by _other_operand.
    """
    edges, load_type, reg_bits, narrow_bits = _badNB_variant(coverpoint, instr_name)
    required_params = get_instruction_type_config(instr_type).required_params or set()
    other_vals = [f"{fs}val" for fs in ("fs1", "fs2", "fs3") if fs != operand and f"{fs}val" in required_params]

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fp_load_type=load_type, **{f"{operand}val": edge_val}
        )
        low_bits = edge_val & ((1 << narrow_bits) - 1)
        box = ((1 << reg_bits) - 1) ^ ((1 << narrow_bits) - 1)
        for name in other_vals:
            other = _other_operand(instr_name, instr_type, getattr(params, name), low_bits, narrow_bits)
            setattr(params, name, box | other)
        desc = f"{coverpoint} (Test source {operand} value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_fs1_badNB")
def make_fs1_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs1 bad NaN-Box values."""
    return _make_badNB(instr_name, instr_type, coverpoint, test_data, "fs1")


@add_coverpoint_generator("cp_fs2_badNB")
def make_fs2_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs2 bad NaN-Box values."""
    return _make_badNB(instr_name, instr_type, coverpoint, test_data, "fs2")


@add_coverpoint_generator("cp_fs3_badNB")
def make_fs3_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs3 bad NaN-Box values."""
    return _make_badNB(instr_name, instr_type, coverpoint, test_data, "fs3")
