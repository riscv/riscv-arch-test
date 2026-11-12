##################################
# instructions/vector_data.py
#
# Per-instruction random source data for vector tests, for instructions where uniformly random
# bits make the result uninformative (always "not equal", always saturated, always zero).
#
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import random
import re
import struct

from testgen.data.edges import VECTOR_EDGES
from testgen.data.params import InstructionParams
from testgen.data.random import random_int
from testgen.data.state import TestData

# Fraction of compare elements whose vs2 equals the other operand
EQUAL_FRACTION = 0.4

# Fraction of narrowing-clip elements whose shifted value is outside the destination range
CLIP_SATURATE_FRACTION = 0.25

# FP-to-int converts: fraction of sources drawn uniformly over the range (the rest have log-uniform magnitude)
CONVERT_UNIFORM_FRACTION = 0.25
CONVERT_RANGE_SCALE = 1.5  # Sources reach 1.5x the destination integer range, so about 1/3 of uniform ones saturate
CONVERT_MIN_EXPONENT = -2  # Smallest log-uniform magnitude is 2^-2, so rounding to zero is exercised
CONVERT_UNSIGNED_NEGATIVE_FRACTION = 0.125

EQUALITY_COMPARES = re.compile(r"vm(f?eq|f?ne|seq|sne)\.v[vxif]$")
NARROWING_CLIPS = re.compile(r"vnclipu?\.w[vxi]$")
FP_TO_INT_CONVERTS = re.compile(r"v(f|fw|fn)cvt\.(rtz\.)?(xu?)\.f\.[vw]$")

FP_FORMATS = {
    16: ("<e", "<H", 65504.0),
    32: ("<f", "<I", 3.4028234663852886e38),
    64: ("<d", "<Q", 1.7976931348623157e308),
}


def _mask(bits: int) -> int:
    return (1 << bits) - 1


def _vs1_elements(params: InstructionParams, test_data: TestData) -> list[int]:
    """Elements of the vs1 data label, if vs1 has one."""
    if params.vs1_val_pointer is None or params.vs1_val_pointer not in test_data.vector_labels:
        return []
    return list(test_data.vector_labels[params.vs1_val_pointer][0])


def _equal_operand(instruction: str, params: InstructionParams, test_data: TestData, sew: int) -> list[int] | int:
    """The value vs2 is compared against: vs1's elements, or the scalar/immediate truncated to SEW."""
    if instruction.endswith(".vv"):
        return _vs1_elements(params, test_data)
    if instruction.endswith(".vx"):
        assert params.rs1val is not None
        return params.rs1val & _mask(sew)
    if instruction.endswith(".vi"):
        assert params.immval is not None
        return params.immval & _mask(sew)
    assert params.fs1val is not None
    return params.fs1val & _mask(sew)


def compare_elements(
    instruction: str, count: int, eew: int, params: InstructionParams, test_data: TestData
) -> list[int]:
    """Random vs2 elements, each equal to the other operand with probability EQUAL_FRACTION."""
    other = _equal_operand(instruction, params, test_data, eew)
    elements = []
    for i in range(count):
        value = other if isinstance(other, int) else (other[i] if i < len(other) else None)
        if value is not None and random.random() < EQUAL_FRACTION:
            elements.append(value & _mask(eew))
        else:
            elements.append(random_int(eew, signed=False))
    return elements


def clip_source(sew: int, shift: int, *, signed: bool) -> int:
    """
    A 2*SEW-bit narrowing-clip source that shifts right by `shift` to a value in the SEW-bit destination range
    (or, with probability CLIP_SATURATE_FRACTION, 1-2 bits outside it), with random bits shifted out for rounding.
    """
    if random.random() < CLIP_SATURATE_FRACTION:
        extra = random.randint(1, 2)
        if signed:
            magnitude = random.randint(1 << (sew - 1), (1 << (sew - 1 + extra)) - 1)
            q = -magnitude - 1 if random.random() < 0.5 else magnitude
        else:
            q = random.randint(1 << sew, (1 << (sew + extra)) - 1)
    else:
        q = random_int(sew, signed=signed)
    if shift:
        q = (q << shift) | random_int(shift, signed=False)
    return q & _mask(2 * sew)


def _clip_shifts(instruction: str, count: int, sew: int, params: InstructionParams, test_data: TestData) -> list[int]:
    """Shift amount for each element: the low log2(2*SEW) bits of vs1's element, rs1, or the immediate."""
    shift_mask = 2 * sew - 1
    if instruction.endswith(".wv"):
        shifts = _vs1_elements(params, test_data)
        return [shifts[i] & shift_mask if i < len(shifts) else random.randint(0, shift_mask) for i in range(count)]
    scalar = params.rs1val if instruction.endswith(".wx") else params.immval
    assert scalar is not None
    return [scalar & shift_mask] * count


def clip_elements(instruction: str, count: int, sew: int, params: InstructionParams, test_data: TestData) -> list[int]:
    """vs2 elements for vnclip/vnclipu fitted to each element's shift amount."""
    signed = not instruction.startswith("vnclipu")
    return [
        clip_source(sew, shift, signed=signed) for shift in _clip_shifts(instruction, count, sew, params, test_data)
    ]


def fp_to_int_source(instruction: str, eew: int) -> int:
    """
    Bits of an FP source of width eew for an FP-to-int convert, with magnitude up to CONVERT_RANGE_SCALE times the
    destination integer range: some uniform over the range (saturation boundary), most log-uniform (fractional bits
    that make rounding modes matter).
    """
    match = FP_TO_INT_CONVERTS.match(instruction)
    assert match is not None
    int_width = {"f": eew, "fw": 2 * eew, "fn": eew // 2}[match.group(1)]
    signed = match.group(3) == "x"
    pack_fmt, unpack_fmt, fp_max = FP_FORMATS[eew]
    int_range = 1 << (int_width - 1 if signed else int_width)
    limit = min(CONVERT_RANGE_SCALE * int_range, fp_max)

    if random.random() < CONVERT_UNIFORM_FRACTION:
        magnitude = random.uniform(0, limit)
    else:
        magnitude = 2.0 ** random.uniform(CONVERT_MIN_EXPONENT, math.log2(limit))
    negative_fraction = 0.5 if signed else CONVERT_UNSIGNED_NEGATIVE_FRACTION
    value = -magnitude if random.random() < negative_fraction else magnitude
    value = max(-fp_max, min(fp_max, value))
    return struct.unpack(unpack_fmt, struct.pack(pack_fmt, value))[0]


def instruction_random_elements(
    instruction: str, register: str, count: int, eew: int, sew: int, params: InstructionParams, test_data: TestData
) -> list[int] | None:
    """
    Random elements for a source register whose uniformly random bits would make the result uninformative,
    or None to use uniformly random data.
    """
    if register != "vs2":
        return None
    if EQUALITY_COMPARES.match(instruction):
        return compare_elements(instruction, count, eew, params, test_data)
    if NARROWING_CLIPS.match(instruction):
        return clip_elements(instruction, count, sew, params, test_data)
    if FP_TO_INT_CONVERTS.match(instruction):
        return [fp_to_int_source(instruction, eew) for _ in range(count)]
    return None


def clip_random_edge_label(instruction: str, shift: int, test_data: TestData) -> str | None:
    """
    For a narrowing clip, register a per-test 'random' vs2 edge fitted to the shift amount (avoiding every other
    edge value, so it still lands in the random bin) and return its label; None for other instructions.
    """
    if not NARROWING_CLIPS.match(instruction):
        return None
    sew = test_data.config.sew
    assert sew is not None
    eew = 2 * sew
    other_edges = {VECTOR_EDGES.edge_value(edge, eew) for edge in VECTOR_EDGES.vx_edges if "random" not in edge}
    value = clip_source(sew, shift & (eew - 1), signed=not instruction.startswith("vnclipu"))
    while value in other_edges or value == 0x81:
        value = clip_source(sew, shift & (eew - 1), signed=not instruction.startswith("vnclipu"))
    label = f"vs2_edge_random_clip_{test_data.test_count:03d}"
    test_data.register_vector_data(label, eew, elements=[value])
    return label
