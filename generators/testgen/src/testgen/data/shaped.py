##################################
# data/shaped.py
#
# Random source values shaped so that test results are informative, shared by the scalar and vector generators
#
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import random
import struct

# FP formats: (exponent bits, stored significand bits)
FP_FORMATS = {"h": (5, 10), "bf16": (8, 7), "s": (8, 23), "d": (11, 52), "q": (15, 112)}

# FP-to-int converts: a quarter of sources are uniform over 1.5x the integer range, to cover the saturation boundary
# (about 1/3 of them saturate); the rest have a log-uniform magnitude from 2^-2 up, with fractional bits that make the
# rounding mode matter
CONVERT_UNIFORM_FRACTION = 0.25
CONVERT_RANGE_SCALE = 1.5
CONVERT_MIN_EXPONENT = -2
CONVERT_UNSIGNED_NEGATIVE_FRACTION = 0.125


def mask(bits: int) -> int:
    return (1 << bits) - 1


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
    sign, biased, frac = double >> 63, (double >> 52) & 0x7FF, double & mask(52)
    if biased == 0:
        return sign << 127  # Only zero reaches here (magnitudes are >= 2^-2)
    return (sign << 127) | ((biased - 1023 + 16383) << 112) | (frac << 60)


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
