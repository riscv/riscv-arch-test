##################################
# instructions/scalar_data.py
#
# Per-instruction random source values for scalar tests, for instructions where uniformly random bits make the
# result uninformative (FP adds that absorb the smaller operand, converts that overflow or round to zero, divides
# that return 0 or 1, permutations with out-of-range indices, condition tests that never see zero).
#
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import random
import re
import struct
from collections.abc import Callable

from testgen.data.params import InstructionParams
from testgen.data.random import random_int
from testgen.data.state import TestData

# FP formats: (exponent bits, stored significand bits)
FP_FORMATS = {"h": (5, 10), "bf16": (8, 7), "s": (8, 23), "d": (11, 52), "q": (15, 112)}

# Fraction of random FP tests that start with random nonzero fflags, so a DUT that clears or overwrites fflags fails
PRESET_FFLAGS_FRACTION = 0.5

# FP-to-int converts (as in the vector tests): a quarter of sources are uniform over 1.5x the integer range, to
# cover the saturation boundary; the rest have a log-uniform magnitude from 2^-2 up, with fractional bits
CONVERT_UNIFORM_FRACTION = 0.25
CONVERT_RANGE_SCALE = 1.5
CONVERT_MIN_EXPONENT = -2
CONVERT_UNSIGNED_NEGATIVE_FRACTION = 0.125

# Fraction of narrowing converts and fround sources left uniformly random
UNBIASED_FRACTION = 0.25

# Fraction of fsqrt sources that are negative
SQRT_NEGATIVE_FRACTION = 0.1

# Fraction of xperm index elements that are in range
XPERM_IN_RANGE_FRACTION = 0.85

FP_ADDS = re.compile(r"f(add|sub)\.(h|s|d|q)$")
FP_FMAS = re.compile(r"fn?m(add|sub)\.(h|s|d|q)$")
FP_SQRT = re.compile(r"fsqrt\.(h|s|d|q)$")
FP_ROUND = re.compile(r"froundn?x?\.(h|s|d|q)$")
FP_TO_INT = re.compile(r"fcvt\.(w|wu|l|lu)\.(h|s|d|q)$|fcvtmod\.w\.d$")
INT_TO_FP = re.compile(r"fcvt\.(h|s|d|q)\.(w|wu|l|lu)$")
FP_TO_FP = re.compile(r"fcvt\.(h|bf16|s|d|q)\.(h|bf16|s|d|q)$")
DIVIDES = re.compile(r"(div|rem)(u?)(w?)$")
XPERM = re.compile(r"xperm(4|8)$")
CZERO = re.compile(r"czero\.(eqz|nez)$")
COUNT_ZEROS = re.compile(r"(clz|ctz)(w?)$")


def _mask(bits: int) -> int:
    return (1 << bits) - 1


def _value_of_width(width: int) -> int:
    """A random nonnegative integer whose highest set bit is bit width-1 (0 for width 0)."""
    return 0 if width == 0 else random.randint(1 << (width - 1), (1 << width) - 1)


def _log_distance(limit: int) -> int:
    """A distance from 0 to about limit with a logarithmic distribution: a random bit width, then a random value."""
    return _value_of_width(random.randint(0, max(1, limit).bit_length()))


##################################
# FP encoding
##################################


def fp_bits(fmt: str, sign: int, exponent: int, significand: int) -> int:
    """Encode an FP value from a sign, an unbiased exponent, and stored significand bits, with no rounding.

    Exponents below the normal range give a subnormal (or zero), and above it infinity."""
    ebits, mbits = FP_FORMATS[fmt]
    bias = (1 << (ebits - 1)) - 1
    biased = exponent + bias
    significand &= _mask(mbits)
    if biased >= (1 << ebits) - 1:
        biased, significand = (1 << ebits) - 1, 0
    elif biased <= 0:
        shift = 1 - biased
        significand = ((1 << mbits) | significand) >> shift if shift <= mbits else 0
        biased = 0
    return (sign << (ebits + mbits)) | (biased << mbits) | significand


def random_fp(fmt: str, exponent: int, sign: int | None = None) -> int:
    """A random FP value with the given unbiased exponent (random sign unless given)."""
    mbits = FP_FORMATS[fmt][1]
    return fp_bits(fmt, random.randint(0, 1) if sign is None else sign, exponent, random_int(mbits, signed=False))


def exponent_range(fmt: str) -> tuple[int, int]:
    """Smallest and largest unbiased exponents of normal numbers."""
    ebits = FP_FORMATS[fmt][0]
    bias = (1 << (ebits - 1)) - 1
    return 1 - bias, bias


def float_to_fp(value: float, fmt: str) -> int:
    """Encode a Python float in the given FP format (round to nearest for h/s; truncated for bf16)."""
    if fmt == "h":
        return struct.unpack("<H", struct.pack("<e", value))[0]
    single = struct.unpack("<I", struct.pack("<f", value))[0]
    if fmt == "s":
        return single
    if fmt == "bf16":
        return single >> 16
    double = struct.unpack("<Q", struct.pack("<d", value))[0]
    if fmt == "d":
        return double
    # Quad: widen the double's exponent and significand
    sign, biased, frac = double >> 63, (double >> 52) & 0x7FF, double & _mask(52)
    if biased == 0:
        return sign << 127  # Only zero reaches here (magnitudes are >= 2^-2)
    return (sign << 127) | ((biased - 1023 + 16383) << 112) | (frac << 60)


##################################
# FP generators
##################################


def fp_add_sources(fmt: str) -> tuple[int, int]:
    """Two operands whose exponents differ by a log-distributed distance, so most additions overlap."""
    emin, emax = exponent_range(fmt)
    precision = FP_FORMATS[fmt][1] + 1
    e1 = random.randint(emin, emax)
    distance = _log_distance(precision + 3)
    e2 = e1 + distance if random.random() < 0.5 else e1 - distance
    if not emin <= e2 <= emax:
        e2 = 2 * e1 - e2  # Reflect back into range
    return random_fp(fmt, e1), random_fp(fmt, max(emin, min(emax, e2)))


def fp_fma_sources(fmt: str) -> tuple[int, int, int]:
    """Multiplicands whose product is in range, and an addend whose exponent is a log-distributed distance away."""
    emin, emax = exponent_range(fmt)
    precision = FP_FORMATS[fmt][1] + 1
    product = random.randint(emin, emax)
    e1 = random.randint(max(emin, product - emax), min(emax, product - emin))
    distance = _log_distance(2 * precision + 3)
    e3 = product + distance if random.random() < 0.5 else product - distance
    if not emin <= e3 <= emax:
        e3 = 2 * product - e3
    return random_fp(fmt, e1), random_fp(fmt, product - e1), random_fp(fmt, max(emin, min(emax, e3)))


def fp_to_int_source(fmt: str, int_width: int, *, signed: bool) -> int:
    """An FP source whose magnitude reaches CONVERT_RANGE_SCALE times the destination integer range."""
    fp_max = 2.0 ** min(exponent_range(fmt)[1] + 1, 1023)
    int_range = 2.0 ** (int_width - 1 if signed else int_width)
    limit = min(CONVERT_RANGE_SCALE * int_range, fp_max * 0.99)
    if random.random() < CONVERT_UNIFORM_FRACTION:
        magnitude = random.uniform(0, limit)
    else:
        magnitude = 2.0 ** random.uniform(CONVERT_MIN_EXPONENT, math.log2(limit))
    negative_fraction = 0.5 if signed else CONVERT_UNSIGNED_NEGATIVE_FRACTION
    value = -magnitude if random.random() < negative_fraction else magnitude
    return float_to_fp(value, fmt)


def fp_narrowing_source(source: str, dest: str) -> int:
    """A source mostly in the destination's range, with log-distributed magnitude: its exponent is uniform from
    below the destination's subnormals to just past its overflow threshold."""
    if random.random() < UNBIASED_FRACTION:
        return random_int(sum(FP_FORMATS[source]) + 1, signed=False)
    emin, emax = exponent_range(dest)
    smin, smax = exponent_range(source)
    dest_precision = FP_FORMATS[dest][1] + 1
    exponent = random.randint(max(smin, emin - dest_precision - 1), min(smax, emax + 1))
    return random_fp(source, exponent)


def fp_round_source(fmt: str) -> int:
    """A source that usually has both integer and fraction bits: exponent from -2 to the precision."""
    if random.random() < UNBIASED_FRACTION:
        return random_int(sum(FP_FORMATS[fmt]) + 1, signed=False)
    return random_fp(fmt, random.randint(-2, FP_FORMATS[fmt][1] + 1))


def fp_sqrt_source(fmt: str) -> int:
    """A random source that is negative only SQRT_NEGATIVE_FRACTION of the time."""
    bits = random_int(sum(FP_FORMATS[fmt]) + 1, signed=False)
    sign_bit = 1 << sum(FP_FORMATS[fmt])
    return bits | sign_bit if random.random() < SQRT_NEGATIVE_FRACTION else bits & ~sign_bit


##################################
# Integer generators
##################################


def _random_upper(value: int, width: int, xlen: int) -> int:
    """Fill the bits above width with random bits (ignored by word instructions)."""
    if width >= xlen:
        return value & _mask(xlen)
    return (random_int(xlen - width, signed=False) << width) | (value & _mask(width))


def int_to_fp_source(dest: str, width: int, *, signed: bool) -> int:
    """A width-bit integer with a log-distributed magnitude (random sign if signed). Most magnitudes stay within
    a bit or two of the destination's largest finite value, so converts to a narrow format mostly don't overflow."""
    magnitude_bits = width - 1 if signed else width
    if random.random() >= UNBIASED_FRACTION:
        magnitude_bits = min(magnitude_bits, exponent_range(dest)[1] + 2)
    value = _value_of_width(random.randint(0, magnitude_bits))
    if signed and random.random() < 0.5:
        value = -value
    return value & _mask(width)


def divide_sources(width: int, *, signed: bool) -> tuple[int, int]:
    """A dividend and nonzero divisor with log-distributed magnitudes, the divisor at most one bit wider than the
    dividend, so quotients of every length occur."""
    magnitude_bits = width - 1 if signed else width
    dividend_width = random.randint(1, magnitude_bits)
    dividend = _value_of_width(dividend_width)
    # Allowing the divisor one bit wider than the dividend gives some zero quotients
    divisor = _value_of_width(random.randint(1, min(magnitude_bits, dividend_width + 1)))
    if signed:
        dividend = -dividend if random.random() < 0.5 else dividend
        divisor = -divisor if random.random() < 0.5 else divisor
    return dividend & _mask(width), divisor & _mask(width)


def xperm_indices(element_bits: int, xlen: int) -> int:
    """xperm index elements, most of them in range (less than the number of elements in a register)."""
    elements = xlen // element_bits
    value = 0
    for i in range(elements):
        if random.random() < XPERM_IN_RANGE_FRACTION:
            index = random.randrange(elements)
        else:
            index = random.randrange(1 << element_bits)
        value |= index << (i * element_bits)
    return value


def orcb_source(xlen: int) -> int:
    """Bytes that are zero half the time and random nonzero otherwise."""
    value = 0
    for i in range(xlen // 8):
        if random.random() < 0.5:
            value |= random.randint(1, 255) << (8 * i)
    return value


def count_zeros_source(width: int, *, leading: bool) -> int:
    """A width-bit value whose leading (or trailing) zero count is uniform from 0 to width."""
    zeros = random.randint(0, width)
    if zeros == width:
        return 0
    if leading:
        top = width - 1 - zeros
        return (1 << top) | random_int(top, signed=False) if top else 1
    return ((random_int(width - zeros - 1, signed=False) << 1 | 1) << zeros) & _mask(width)


##################################
# Dispatch
##################################


def _source_fmt(instruction: str) -> str:
    return instruction.rsplit(".", 1)[1]


SourceGenerator = Callable[[], dict[str, int]]


def _fp_sources(instruction: str) -> SourceGenerator | None:
    """Generators for an FP instruction's sources, or None for uniformly random bits."""
    if m := FP_ADDS.match(instruction):
        return lambda: dict(zip(("fs1val", "fs2val"), fp_add_sources(m.group(2)), strict=True))
    if m := FP_FMAS.match(instruction):
        return lambda: dict(zip(("fs1val", "fs2val", "fs3val"), fp_fma_sources(m.group(2)), strict=True))
    if m := FP_SQRT.match(instruction):
        return lambda: {"fs1val": fp_sqrt_source(m.group(1))}
    if m := FP_ROUND.match(instruction):
        return lambda: {"fs1val": fp_round_source(m.group(1))}
    if m := FP_TO_INT.match(instruction):
        dest = m.group(1) or "w"
        width = 32 if dest.startswith("w") else 64
        return lambda: {"fs1val": fp_to_int_source(_source_fmt(instruction), width, signed=not dest.endswith("u"))}
    if m := FP_TO_FP.match(instruction):
        dest, source = m.groups()
        if FP_FORMATS[dest][1] < FP_FORMATS[source][1] or FP_FORMATS[dest][0] < FP_FORMATS[source][0]:
            return lambda: {"fs1val": fp_narrowing_source(source, dest)}
    return None


def _int_sources(instruction: str, xlen: int) -> SourceGenerator | None:
    """Generators for an integer-source instruction's register values, or None for uniformly random bits."""
    if m := INT_TO_FP.match(instruction):
        dest, source = m.groups()
        width = 32 if source.startswith("w") else 64
        signed = not source.endswith("u")
        return lambda: {"rs1val": _random_upper(int_to_fp_source(dest, width, signed=signed), width, xlen)}
    if m := DIVIDES.fullmatch(instruction):
        width = 32 if m.group(3) else xlen

        def divide() -> dict[str, int]:
            dividend, divisor = divide_sources(width, signed=not m.group(2))
            return {"rs1val": _random_upper(dividend, width, xlen), "rs2val": _random_upper(divisor, width, xlen)}

        return divide
    if m := XPERM.fullmatch(instruction):
        return lambda: {"rs1val": random_int(xlen, signed=False), "rs2val": xperm_indices(int(m.group(1)), xlen)}
    if CZERO.fullmatch(instruction):
        return lambda: {
            "rs1val": random_int(xlen, signed=False),
            "rs2val": 0 if random.random() < 0.5 else random_int(xlen, signed=False, nonzero=True),
        }
    if instruction == "orc.b":
        return lambda: {"rs1val": orcb_source(xlen)}
    if m := COUNT_ZEROS.fullmatch(instruction):
        width = 32 if m.group(2) else xlen
        leading = m.group(1) == "clz"
        return lambda: {"rs1val": _random_upper(count_zeros_source(width, leading=leading), width, xlen)}
    return None


def bias_random_sources(instruction: str, params: InstructionParams, filled: set[str], test_data: TestData) -> None:
    """
    Replace uniformly random source values with ones from the instruction's generator, when every source the
    generator sets was randomly filled (so edge and other fixed values are never changed).
    """
    generator = _fp_sources(instruction) or _int_sources(instruction, test_data.xlen)
    if generator is None:
        return
    values = generator()
    if all(name in filled for name in values):
        for name, value in values.items():
            setattr(params, name, value)


def is_fp_instruction(instruction: str) -> bool:
    """True for scalar FP instructions, whose tests set fflags before the instruction."""
    return instruction.startswith(("f", "c.f")) and not instruction.startswith("fence")


def random_fflags_preset() -> int:
    """Nonzero fflags to set before a random FP test (PRESET_FFLAGS_FRACTION of the time), else 0."""
    return random.randint(1, 31) if random.random() < PRESET_FFLAGS_FRACTION else 0
