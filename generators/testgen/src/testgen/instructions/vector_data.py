##################################
# instructions/vector_data.py
#
# Per-instruction random source data for vector tests, for instructions where uniformly random
# bits make the result uninformative (always "not equal", always saturated, always zero).
#
# SPDX-License-Identifier: Apache-2.0
##################################

import random
import re

from testgen.data.edges import VECTOR_EDGES
from testgen.data.params import InstructionParams
from testgen.data.random import random_int
from testgen.data.shaped import fp_to_int_source, mask
from testgen.data.state import TestData

# Fraction of compare elements whose vs2 equals the other operand
EQUAL_FRACTION = 0.4

# Fraction of narrowing-clip elements whose shifted value is outside the destination range
CLIP_SATURATE_FRACTION = 0.25

EQUALITY_COMPARES = re.compile(r"vm(f?eq|f?ne|seq|sne)\.v[vxif]$")
NARROWING_CLIPS = re.compile(r"vnclipu?\.w[vxi]$")
FP_TO_INT_CONVERTS = re.compile(r"v(f|fw|fn)cvt\.(rtz\.)?(xu?)\.f\.[vw]$")
# Compares and clips whose vs2 elements are fitted to vs1's
VS1_FITTED = re.compile(r"vm(f?eq|f?ne|seq|sne)\.vv$|vnclipu?\.wv$")

# FP format of each SEW
FP_FORMAT_OF_SEW = {16: "h", 32: "s", 64: "d"}


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
        return params.rs1val & mask(sew)
    if instruction.endswith(".vi"):
        assert params.immval is not None
        return params.immval & mask(sew)
    assert params.fs1val is not None
    return params.fs1val & mask(sew)


def compare_elements(
    instruction: str, count: int, eew: int, params: InstructionParams, test_data: TestData
) -> list[int]:
    """Random vs2 elements, each equal to the other operand with probability EQUAL_FRACTION."""
    other = _equal_operand(instruction, params, test_data, eew)
    elements = []
    for i in range(count):
        value = other if isinstance(other, int) else (other[i] if i < len(other) else None)
        if value is not None and random.random() < EQUAL_FRACTION:
            elements.append(value & mask(eew))
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
    return q & mask(2 * sew)


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


def fp_to_int_sources(instruction: str, count: int, eew: int) -> list[int]:
    """vs2 elements for an FP-to-int convert, with magnitudes up to a little past the destination integer range."""
    match = FP_TO_INT_CONVERTS.match(instruction)
    assert match is not None
    int_width = {"f": eew, "fw": 2 * eew, "fn": eew // 2}[match.group(1)]
    signed = match.group(3) == "x"
    return [fp_to_int_source(FP_FORMAT_OF_SEW[eew], int_width, signed=signed) for _ in range(count)]


def instruction_random_elements(
    instruction: str, register: str, count: int, eew: int, sew: int, params: InstructionParams, test_data: TestData
) -> list[int] | None:
    """
    Random elements for a source register whose uniformly random bits would make the result uninformative,
    or None to use uniformly random data.
    """
    if register == "vs1" and VS1_FITTED.match(instruction):
        # Give vs1 an element list, never a label into shared data, so vs2 can be fitted to its elements
        return [random_int(eew) for _ in range(count)]
    if register != "vs2":
        return None
    if EQUALITY_COMPARES.match(instruction):
        return compare_elements(instruction, count, eew, params, test_data)
    if NARROWING_CLIPS.match(instruction):
        return clip_elements(instruction, count, sew, params, test_data)
    if FP_TO_INT_CONVERTS.match(instruction):
        return fp_to_int_sources(instruction, count, eew)
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
