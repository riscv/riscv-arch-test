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

FpSource = Literal["fs1", "fs2", "fs3"]

# Positive infinity and the canonical NaN of each narrow format that can be NaN-boxed, by width
_INFINITY = {32: 0x7F800000, 16: 0x7C00}
_CANONICAL_NAN = {32: 0x7FC00000, 16: 0x7E00}


def _is_nan(narrow: int, narrow_bits: int) -> bool:
    """Return True if narrow is a NaN encoding of the narrow_bits-wide format."""
    return narrow & ((1 << (narrow_bits - 1)) - 1) > _INFINITY[narrow_bits]


def _other_operand(
    instr_name: str, instr_type: str, operand: FpSource, rand_val: int, low_bits: int, narrow_bits: int
) -> int:
    """Choose a narrow value for an FP source that is not under test.

    The value is chosen so that a DUT that ignores the upper bits of the operand under test
    (using its low bits) gets a different result or flags than one that treats it as a
    canonical NaN:
    - fltq: +infinity when fs1 is under test and -infinity when fs2 is, so the comparison is
      true for the low bits but false for the canonical NaN. fltq(+inf, y) and fltq(y, -inf)
      are false for every y, so those two edges cannot tell the cases apart;
    - other comparisons: the operand under test's own (non-NaN) low bits, so feq/fle/fleq
      return 1 and flt raises no NV only when the upper bits are ignored;
    - fmin/fmax: the canonical NaN, so the result is the low bits instead of the canonical NaN;
    - everything else, including fminm/fmaxm, which return the canonical NaN for any NaN input:
      the random value, with any NaN turned into an infinity.
    """
    infinity = _INFINITY[narrow_bits]
    sign = 1 << (narrow_bits - 1)
    mnemonic = instr_name.split(".")[0]
    if instr_type == "FC" and not _is_nan(low_bits, narrow_bits):
        if mnemonic == "fltq":
            return infinity if operand == "fs1" else sign | infinity
        return low_bits
    if mnemonic in ("fmin", "fmax"):
        return _CANONICAL_NAN[narrow_bits]
    narrow = rand_val & ((1 << narrow_bits) - 1)
    if _is_nan(narrow, narrow_bits):
        narrow &= sign | infinity  # clear the fraction so the value is not a NaN
    return narrow


def _make_badNB(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData, operand: FpSource
) -> list[TestChunk]:
    """Generate bad NaN-Box tests for one FP source operand (fs1, fs2 or fs3).

    Only the operand under test is improperly boxed. Every other FP source is properly boxed,
    with a value chosen by _other_operand.
    """
    if coverpoint.endswith("_D_S"):
        edges, load_type, reg_bits, narrow_bits = FLOAT_EDGES.bad_NaN_double_single, "double", 64, 32
    elif coverpoint.endswith("D_H"):
        edges, load_type, reg_bits, narrow_bits = FLOAT_EDGES.bad_NaN_double_half, "double", 64, 16
    elif coverpoint.endswith("S_H"):
        edges, load_type, reg_bits, narrow_bits = FLOAT_EDGES.bad_NaN_single_half, "single", 32, 16
    else:
        raise ValueError(f"Unsupported coverpoint for bad NaN-Box tests: {coverpoint} for instr {instr_name}.")
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
            other = _other_operand(instr_name, instr_type, operand, getattr(params, name), low_bits, narrow_bits)
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
