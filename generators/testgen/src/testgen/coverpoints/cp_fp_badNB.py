##################################
# cp_fp_badNB.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point bad NaN-Box value coverpoint generators (cp_fs1_badNB, cp_fs2_badNB, cp_fs3_badNB)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES
from testgen.data.params import InstructionParams
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params

_INFINITY = {32: 0x7F800000, 16: 0x7C00}
_CANONICAL_NAN = {32: 0x7FC00000, 16: 0x7E00}
# Use a non-NaN operand for arithmetic instructions so a broken box check produces a non-NaN result.
_ONE = {32: 0x3F800000, 16: 0x3C00}


def _is_nan(value: int, bits: int) -> bool:
    """Return whether value is a NaN encoding of the given width."""
    return value & ((1 << (bits - 1)) - 1) > _INFINITY[bits]


def _other_value(instr_name: str, instr_type: str, operand: str, edge_val: int, narrow_bits: int) -> int:
    """Choose an operand value that distinguishes an improperly boxed source."""
    mask = (1 << narrow_bits) - 1
    low_bits = edge_val & mask
    infinity = _INFINITY[narrow_bits]
    sign = 1 << (narrow_bits - 1)
    mnemonic = instr_name.split(".")[0]

    if instr_type == "FC" and not _is_nan(low_bits, narrow_bits):
        if mnemonic == "fltq":
            return infinity if operand == "fs1" else sign | infinity
        return low_bits
    if mnemonic in ("fmin", "fmax"):
        return _CANONICAL_NAN[narrow_bits]
    return _ONE[narrow_bits]


def _box_other_operands(
    params: InstructionParams, instr_name: str, instr_type: str, coverpoint: str, operand: str, edge_val: int
) -> None:
    """Properly NaN-box every floating-point source other than operand."""
    if coverpoint.endswith("_D_S"):
        reg_bits, narrow_bits = 64, 32
    elif coverpoint.endswith("D_H"):
        reg_bits, narrow_bits = 64, 16
    elif coverpoint.endswith("S_H"):
        reg_bits, narrow_bits = 32, 16
    else:
        raise ValueError(f"Unsupported coverpoint for bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    box = ((1 << reg_bits) - 1) ^ ((1 << narrow_bits) - 1)
    for source in ("fs1", "fs2", "fs3"):
        if source == operand or getattr(params, source) is None:
            continue
        value_name = f"{source}val"
        value = _other_value(instr_name, instr_type, operand, edge_val, narrow_bits)
        setattr(params, value_name, box | value)


@add_coverpoint_generator("cp_fs1_badNB")
def make_fs1_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs1 bad NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        edges = FLOAT_EDGES.bad_NaN_double_single
        load_size = "double"
    elif coverpoint.endswith("D_H"):
        edges = FLOAT_EDGES.bad_NaN_double_half
        load_size = "double"
    elif coverpoint.endswith("S_H"):
        edges = FLOAT_EDGES.bad_NaN_single_half
        load_size = "single"
    else:
        raise ValueError(f"Unsupported coverpoint for fs1 bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fs1val=edge_val, fp_load_type=load_size
        )
        _box_other_operands(params, instr_name, instr_type, coverpoint, "fs1", edge_val)
        desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_fs2_badNB")
def make_fs2_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs2 bad NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        edges = FLOAT_EDGES.bad_NaN_double_single
        load_size = "double"
    elif coverpoint.endswith("D_H"):
        edges = FLOAT_EDGES.bad_NaN_double_half
        load_size = "double"
    elif coverpoint.endswith("S_H"):
        edges = FLOAT_EDGES.bad_NaN_single_half
        load_size = "single"
    else:
        raise ValueError(f"Unsupported coverpoint for fs2 bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fs2val=edge_val, fp_load_type=load_size
        )
        _box_other_operands(params, instr_name, instr_type, coverpoint, "fs2", edge_val)
        desc = f"{coverpoint} (Test source fs2 value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_fs3_badNB")
def make_fs3_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fs3 bad NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        edges = FLOAT_EDGES.bad_NaN_double_single
        load_size = "double"
    elif coverpoint.endswith("D_H"):
        edges = FLOAT_EDGES.bad_NaN_double_half
        load_size = "double"
    elif coverpoint.endswith("S_H"):
        edges = FLOAT_EDGES.bad_NaN_single_half
        load_size = "single"
    else:
        raise ValueError(f"Unsupported coverpoint for fs3 bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    test_chunks: list[TestChunk] = []
    for edge_val in edges:
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fs3val=edge_val, fp_load_type=load_size
        )
        _box_other_operands(params, instr_name, instr_type, coverpoint, "fs3", edge_val)
        desc = f"{coverpoint} (Test source fs3 value = {test_data.flen_format_str.format(edge_val)})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{edge_val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
