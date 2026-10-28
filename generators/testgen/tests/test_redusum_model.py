##################################
# test_redusum_model.py
#
# Check the vfredusum/vfwredusum legal-outcome model against brute force over every reduction tree.
# SPDX-License-Identifier: Apache-2.0
# Run: python -m unittest discover generators/testgen/tests
##################################

"""
Brute-force soundness check of testgen.coverpoints.vector._redusum_model.

For a few leaves (vs1[0] and up to three active elements) every binary reduction tree is enumerated, with every
node rounding its exact sum to the accumulator format, a wider format or not at all, and the root rounded once more
to the accumulator. Each outcome (value, infinity or NaN, and NV/OF/NX) must be inside the model's legal set.
Signed zeros compare equal here, and UF is not checked, to keep the reference rounding simple.
"""

import random
import struct
import sys
import unittest
from fractions import Fraction
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from testgen.coverpoints.vector import _redusum_model as model

INF = "inf"
NAN = "nan"
# A value: an exact finite Fraction, (INF, sign) or (NAN, 0). Formats are (precision, emin, emax); None means exact.
Val = Fraction | tuple[str, int]
F16, F32, F64 = (11, -14, 15), (24, -126, 127), (53, -1022, 1023)


def decode16(bits: int) -> Val:
    """fp16 bits to an exact Fraction, or (INF, sign)."""
    sign = -1 if bits >> 15 else 1
    exp, frac = (bits >> 10) & 0x1F, bits & 0x3FF
    if exp == 0x1F:
        return (INF, sign)
    if exp == 0:
        return sign * Fraction(frac, 1 << 24)
    return sign * Fraction(frac | 0x400, 1 << 25) * 2**exp


def decode_acc(bits: int, width: int) -> Fraction:
    """Finite accumulator bits (fp16 or fp32) to an exact Fraction."""
    fmt = model.FORMATS[width]
    leaf = model.decode(bits, fmt, fmt)
    return Fraction(leaf.x, 1 << fmt.q)


def round_to(x: Fraction, fmt: tuple[int, int, int], mode: int) -> tuple[Val, int]:
    """Round x to fmt in mode; return the value (or (INF, sign)) and the NX/OF flags."""
    prec, emin, emax = fmt
    if x == 0:
        return x, 0
    sign = -1 if x < 0 else 1
    mag = abs(x)
    e = mag.numerator.bit_length() - mag.denominator.bit_length()
    while Fraction(2) ** e > mag:
        e -= 1
    while Fraction(2) ** (e + 1) <= mag:
        e += 1
    quantum = Fraction(2) ** (max(e, emin) - prec + 1)
    n, rem = divmod(mag, quantum)
    n = int(n)
    if rem:
        half = quantum / 2
        up = {
            model.RNE: rem > half or (rem == half and n % 2 == 1),
            model.RMM: rem >= half,
            model.RTZ: False,
            model.RDN: sign < 0,
            model.RUP: sign > 0,
        }[mode]
        n += up
    r = n * quantum
    flags = model.NX if rem else 0
    max_fin = (2 - Fraction(2) ** (1 - prec)) * Fraction(2) ** emax
    if r > max_fin:
        to_inf = mode in (model.RNE, model.RMM) or (mode == model.RUP and sign > 0) or (mode == model.RDN and sign < 0)
        return ((INF, sign) if to_inf else sign * max_fin), model.OF | model.NX
    return sign * r, flags


def add(a: Val, b: Val) -> Val:
    """Exact sum of two values, propagating infinities; opposite infinities give NaN with NV."""
    if isinstance(a, tuple) or isinstance(b, tuple):
        if isinstance(a, tuple) and isinstance(b, tuple):
            return (NAN, 0) if a[1] != b[1] else a
        return a if isinstance(a, tuple) else b
    return a + b


def outcomes(
    leaves: list[Val], node_fmts: list[tuple[int, int, int] | None], acc: tuple[int, int, int], mode: int
) -> set[tuple[Val, int]]:
    """Every (value, flags) a reduction tree over leaves can produce."""

    @cache
    def sub(idx: frozenset) -> frozenset:
        if len(idx) == 1:
            return frozenset({(leaves[next(iter(idx))], 0)})
        items = sorted(idx)
        first, rest = items[0], items[1:]
        res = set()
        for mask in range(1 << len(rest)):  # left subtree always holds `first`, so each split is seen once
            left = frozenset([first] + [r for i, r in enumerate(rest) if mask >> i & 1])
            right = idx - left
            if not right:
                continue
            for lv, lf in sub(left):
                for rv, rf in sub(right):
                    s = add(lv, rv)
                    if isinstance(s, tuple):
                        res.add((s, lf | rf | (model.NV if s[0] == NAN else 0)))
                        continue
                    for fmt in node_fmts:
                        v, f = (s, 0) if fmt is None else round_to(s, fmt, mode)
                        res.add((v, lf | rf | f))
        return frozenset(res)

    final = set()
    for v, f in sub(frozenset(range(len(leaves)))):
        if isinstance(v, tuple):
            final.add((v, f))
        else:
            rv, rf = round_to(v, acc, mode)
            final.add((rv, f | rf))
    return final


class RedusumModelTest(unittest.TestCase):
    def check(self, scalar: int, elems: list[int], widening: bool) -> None:
        acc_w = 32 if widening else 16
        acc = F32 if widening else F16
        node_fmts = [F32, F64, None] if widening else [F16, F32, F64, None]
        leaves = [decode16(b) for b in [scalar, *elems]]
        scalar_arg = scalar
        if widening:  # vs1[0] is an fp32 value: pass the fp16 scalar converted exactly
            v = leaves[0]
            f = (v[1] * float("inf")) if isinstance(v, tuple) else float(v)
            scalar_arg = struct.unpack(">I", struct.pack(">f", f))[0] | ((scalar >> 15) << 31)
        for mode in model.MODES:
            res = model.reduce_bits(scalar_arg, elems, mode, 16, widening)
            lo = None if res.lo_bits is None else decode_acc(res.lo_bits, acc_w)
            hi = None if res.hi_bits is None else decode_acc(res.hi_bits, acc_w)
            must = res.must & (model.NV | model.OF | model.NX)
            for v, f in outcomes(leaves, node_fmts, acc, mode):
                ctx = f"scalar={scalar:#06x} elems={[hex(e) for e in elems]} mode={model.MODE_NAMES[mode]} widening={widening} -> {v}"
                if isinstance(v, tuple) and v[0] == NAN:
                    self.assertTrue(res.nan, ctx)
                elif isinstance(v, tuple):
                    self.assertTrue(res.pos_inf if v[1] > 0 else res.neg_inf, ctx)
                else:
                    assert lo is not None and hi is not None, ctx
                    self.assertTrue(lo <= v <= hi, f"{ctx} outside [{lo}, {hi}]")
                checked = f & (model.NV | model.OF | model.NX)
                self.assertEqual(checked & ~res.may, 0, f"{ctx}: flags {f:#x} not allowed (may {res.may:#x})")
                self.assertEqual(must & ~checked, 0, f"{ctx}: flags {f:#x} lack required {must:#x}")

    def test_overflow_flag(self) -> None:
        """OF is required when every tree overflows, optional when only some do, and forbidden when none can."""
        cases = [
            (0x7BFF, [0x7BFF], model.OF),  # max + max overflows in every tree
            (0x7BFF, [0x7BFF, 0x7BFF], model.OF),
            (0xFBFF, [0xFBFF, 0xFBFF], model.OF),
            (0x7BFF, [0x7BFF, 0xFBFF], 0),  # overflows only if max + max is rounded to fp16 first
            (0x3C00, [0x3C00, 0x3C00], 0),  # cannot overflow
        ]
        for scalar, elems, must_of in cases:
            self.check(scalar, elems, False)
            for mode in model.MODES:
                res = model.reduce_bits(scalar, elems, mode, 16, False)
                ctx = f"scalar={scalar:#06x} elems={[hex(e) for e in elems]} mode={model.MODE_NAMES[mode]}"
                self.assertEqual(res.must & model.OF, must_of, ctx)
        self.assertTrue(model.reduce_bits(0x7BFF, [0x7BFF, 0xFBFF], model.RNE, 16, False).may & model.OF)
        self.assertFalse(model.reduce_bits(0x3C00, [0x3C00, 0x3C00], model.RNE, 16, False).may & model.OF)

    def test_random_small_reductions(self) -> None:
        rng = random.Random(2897)
        pool = [
            0x3C00, 0x3C01, 0xBC00, 0x0001, 0x8001, 0x03FF, 0x0400, 0x7BFF, 0xFBFF, 0x7BFE,
            0x6400, 0xE400, 0x1400, 0x9400, 0x3555, 0xB555, 0x0000, 0x8000, 0x7C00, 0xFC00,
        ]  # fmt: skip
        for _ in range(60):
            n = rng.randint(1, 3)
            vals = [rng.choice(pool) for _ in range(n + 1)]
            for widening in (False, True):
                self.check(vals[0], vals[1:], widening)


if __name__ == "__main__":
    unittest.main()
