##################################
# _redusum_model.py
#
# Legal-outcome model for the unordered floating-point sum reductions (vfredusum.vs, vfwredusum.vs).
# david_harris@hmc.edu Oct 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Compute every result and exception flag that vfredusum.vs or vfwredusum.vs may legally produce.

The ISA manual (norm:vfredusum_op) lets an implementation use any binary reduction tree over vs1[0] and the
active elements of vs2. Each node rounds its exact sum to any format whose precision and exponent range are at
least those of the accumulator format A (SEW, or 2*SEW for vfwredusum), so the formats can differ per node. A
node fed only by masked-off or tail elements either adds the additive identity or copies its other input, and
an extra additive identity may be added to the final result. The root is rounded once more to A.

The model is an abstract interpretation of that freedom. Each multiset of leaves maps to an over-approximation of
its outcome set: a closed interval of finite values (with signed zeros), the possible infinities and NaN, and the
flags that may or must be raised. Each node is monotone in its inputs, so interval endpoints combine endpoint to
endpoint. Finite values are integers scaled by 2^Q, where 2^-Q is A's smallest subnormal, so every leaf, sum and
rounding is exact.

Simplifications that keep the model sound:
  * Every node may also round its result again any number of times (masked-off and tail leaves can insert
    identity nodes anywhere), so each node result is closed under repeated rounding.
  * Zero leaves are dropped when any nonzero leaf is present. Adding a zero is a rounding of the other input,
    which the closure already covers, and an exact zero sum gets its sign from the rounding mode alone.
  * Addition never underflows: sums of A values are exact multiples of A's smallest subnormal.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

# Rounding modes in frm encoding
RNE, RTZ, RDN, RUP, RMM = 0, 1, 2, 3, 4
MODES = (RNE, RTZ, RDN, RUP, RMM)
MODE_NAMES = {RNE: "rne", RTZ: "rtz", RDN: "rdn", RUP: "rup", RMM: "rmm"}

# fflags bits
NV, DZ, OF, UF, NX = 0x10, 0x08, 0x04, 0x02, 0x01


@dataclass(frozen=True)
class Fmt:
    """IEEE 754 binary format: total width, precision in bits (with the hidden bit) and exponent range."""

    width: int
    prec: int
    emin: int
    emax: int

    @property
    def q(self) -> int:
        """Values are integers scaled by 2^q: 2^-q is the smallest subnormal."""
        return self.prec - 1 - self.emin

    @property
    def frac_bits(self) -> int:
        return self.prec - 1

    @property
    def exp_bits(self) -> int:
        return self.width - self.prec

    @property
    def max_norm(self) -> int:
        """Largest finite magnitude, scaled."""
        return ((1 << self.prec) - 1) << (self.emax - self.prec + 1 + self.q)

    @property
    def overflow_mag(self) -> int:
        """2^(emax+1), scaled: a rounded magnitude this large overflows every format with this exponent range."""
        return 1 << (self.emax + 1 + self.q)

    @property
    def sign_bit(self) -> int:
        return 1 << (self.width - 1)

    @property
    def pos_inf(self) -> int:
        return ((1 << self.exp_bits) - 1) << self.frac_bits

    @property
    def canonical_nan(self) -> int:
        return self.pos_inf | (1 << (self.frac_bits - 1))


FORMATS = {16: Fmt(16, 11, -14, 15), 32: Fmt(32, 24, -126, 127), 64: Fmt(64, 53, -1022, 1023)}


# ---------------------------------------------------------------------------------------------------------------
# Encoding and decoding
# ---------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Leaf:
    """A decoded input: kind is 'fin', 'inf', 'qnan' or 'snan'. Finite values are scaled to the accumulator."""

    kind: str
    x: int = 0  # scaled value (finite)
    neg: bool = False  # sign (finite zero sign or infinity sign)


def decode(bits: int, fmt: Fmt, acc: Fmt) -> Leaf:
    """Decode fmt bits into a Leaf whose finite value is scaled for the accumulator format acc."""
    neg = bool(bits >> (fmt.width - 1) & 1)
    exp = (bits >> fmt.frac_bits) & ((1 << fmt.exp_bits) - 1)
    frac = bits & ((1 << fmt.frac_bits) - 1)
    if exp == (1 << fmt.exp_bits) - 1:
        if frac == 0:
            return Leaf("inf", neg=neg)
        return Leaf("qnan" if frac >> (fmt.frac_bits - 1) else "snan", neg=neg)
    # Scaled to fmt: subnormal spacing 1
    mag = frac if exp == 0 else (frac | (1 << fmt.frac_bits)) << (exp - 1)
    mag <<= acc.q - fmt.q
    return Leaf("fin", -mag if neg else mag, neg)


def encode(x: int, neg_zero: bool, fmt: Fmt) -> int:
    """Encode a scaled value that is exactly representable in fmt (and in range) as fmt bits."""
    if x == 0:
        return fmt.sign_bit if neg_zero else 0
    sign = fmt.sign_bit if x < 0 else 0
    mag = abs(x)
    e = mag.bit_length() - 1  # scaled exponent
    if e < fmt.prec - 1:  # subnormal
        return sign | mag
    shift = e - (fmt.prec - 1)
    assert mag & ((1 << shift) - 1) == 0, "value not representable"
    exp_field = shift + 1
    assert exp_field < (1 << fmt.exp_bits) - 1, "value out of range"
    return sign | (exp_field << fmt.frac_bits) | ((mag >> shift) & ((1 << fmt.frac_bits) - 1))


def representable(x: int, fmt: Fmt) -> bool:
    """True if scaled value x is a finite value of fmt (with fmt's exponent range)."""
    mag = abs(x)
    if mag > fmt.max_norm:
        return False
    shift = mag.bit_length() - fmt.prec
    return shift <= 0 or mag & ((1 << shift) - 1) == 0


def key_of_bits(bits: int, width: int) -> int:
    """Map an encoding to an unsigned key that orders values: -inf < ... < -0 < +0 < ... < +inf."""
    sign = 1 << (width - 1)
    return (~bits & ((1 << width) - 1)) if bits & sign else bits | sign


# ---------------------------------------------------------------------------------------------------------------
# Rounding
# ---------------------------------------------------------------------------------------------------------------


def _round_mag(mag: int, k: int, mode: int, neg: bool) -> int:
    """Round a nonnegative magnitude to a multiple of 2^k for a value of the given sign."""
    if k <= 0:
        return mag
    unit = 1 << k
    low = mag & (unit - 1)
    base = mag - low
    if low == 0:
        return mag
    half = unit >> 1
    if mode == RTZ or (mode == RDN and not neg) or (mode == RUP and neg):
        up = False
    elif mode in (RUP, RDN):
        up = True
    elif low != half:
        up = low > half
    else:
        up = mode == RMM or bool((base >> k) & 1)
    return base + unit if up else base


def grid_exp(mag: int, prec: int) -> int:
    """Exponent k of the precision-prec grid at magnitude mag (spacing 2^k, at least 1 = smallest subnormal)."""
    return max(mag.bit_length() - prec, 0)


@dataclass
class Cands:
    """Results of rounding one exact value in every legal format."""

    lo: int  # smallest finite result (scaled)
    hi: int  # largest finite result (scaled)
    clean_lo: int = 0  # smallest finite result of a format that does not overflow
    clean_hi: int = 0  # largest finite result of a format that does not overflow
    pos_inf: bool = False
    neg_inf: bool = False
    inexact: bool = False
    overflow: bool = False


@lru_cache(maxsize=1 << 18)
def round_any(x: int, mode: int, acc: Fmt) -> Cands:
    """
    Round x (nonzero, scaled) to every format with precision >= acc.prec and exponent range containing acc's.

    A precision of acc.prec + j rounds to multiples of 2^(k0 - j), where 2^k0 is acc's grid at |x|; a large
    enough precision is exact. Directed rounding of the magnitude is extreme at j = 0. For round-to-nearest,
    every j before the highest set bit b of the remainder below 2^k0 rounds down to the same truncation a0, and
    the first j that rounds up (at bit b, unless that is a tie that rounds to even) gives the largest result.
    Formats with acc's exponent range overflow when the rounded magnitude reaches 2^(emax+1); formats with a
    wider exponent range keep the finite value.
    """
    neg = x < 0
    mag = -x if neg else x
    k0 = grid_exp(mag, acc.prec)
    rem = mag & ((1 << k0) - 1)
    a0 = mag - rem
    if rem == 0:
        min_mag = max_mag = mag
    elif mode == RTZ or (mode == RDN and not neg) or (mode == RUP and neg):
        min_mag, max_mag = a0, mag
    elif mode in (RUP, RDN):
        min_mag, max_mag = mag, a0 + (1 << k0)
    else:
        b = rem.bit_length() - 1
        tie = rem == 1 << b
        up = not tie or mode == RMM or bool((mag >> (b + 1)) & 1)
        max_mag = a0 + (1 << (b + 1)) if up else mag
        if b < k0 - 1 or not up:
            min_mag = a0
        else:
            # j = 0 rounds up: find the first coarser-than-exact grid that rounds down
            min_mag = mag
            for j in range(1, k0 + 1):
                r = _round_mag(mag, k0 - j, mode, neg)
                if r == mag:
                    break
                if r < mag:
                    min_mag = r
                    break
    lo, hi = (-max_mag, -min_mag) if neg else (min_mag, max_mag)
    c = Cands(lo=lo, hi=hi, clean_lo=lo, clean_hi=hi, inexact=min_mag != max_mag)
    if max_mag >= acc.overflow_mag:
        c.overflow = c.inexact = True
        if mode in (RNE, RMM) or (mode == RUP and not neg) or (mode == RDN and neg):
            if neg:
                c.neg_inf = True
            else:
                c.pos_inf = True
        elif neg:
            # A format with acc's range overflows to its largest finite value; acc's own is the smallest such
            c.hi = max(c.hi, -acc.max_norm)
        else:
            c.lo = min(c.lo, acc.max_norm)
    return c


def round_final(x: int, mode: int, acc: Fmt) -> tuple[str, int, bool, bool]:
    """Round scaled x (nonzero) to acc: return (kind, value, inexact, overflow) with kind 'fin' or 'inf'."""
    neg = x < 0
    mag = -x if neg else x
    r = _round_mag(mag, grid_exp(mag, acc.prec), mode, neg)
    inexact = r != mag
    if r > acc.max_norm:
        to_inf = mode in (RNE, RMM) or (mode == RUP and not neg) or (mode == RDN and neg)
        if to_inf:
            return ("inf", -1 if neg else 1, True, True)
        return ("fin", -acc.max_norm if neg else acc.max_norm, True, True)
    return ("fin", -r if neg else r, inexact, False)


# ---------------------------------------------------------------------------------------------------------------
# Abstract outcome sets
# ---------------------------------------------------------------------------------------------------------------

# A finite endpoint is (x, zsign) where zsign orders zeros: -0 = (0, -1) < +0 = (0, 1). Nonzero x use sign(x).
Key = tuple[int, int]


def fkey(x: int, neg_zero: bool = False) -> Key:
    if x == 0:
        return (0, -1 if neg_zero else 1)
    return (x, 1 if x > 0 else -1)


@dataclass
class Outcome:
    """Over-approximation of the outcomes of reducing one multiset of leaves."""

    lo: Key | None = None  # finite interval, or None if no finite outcome is possible
    hi: Key | None = None
    pos_inf: bool = False
    neg_inf: bool = False
    nan: bool = False
    must_nan: bool = False
    snan: bool = False  # an unconsumed signaling NaN leaf (only a lone leaf)
    may: int = 0  # flags that may be raised
    must: int = 0  # flags that must be raised
    # Finite interval reachable without raising OF, or None if every outcome has raised OF
    clean_lo: Key | None = None
    clean_hi: Key | None = None

    def has_fin(self) -> bool:
        return self.lo is not None


def _join(a: Outcome | None, b: Outcome) -> Outcome:
    """Union of two outcome sets (one tree or another)."""
    if a is None:
        return b
    return Outcome(
        lo=_lower(a.lo, b.lo),
        hi=_upper(a.hi, b.hi),
        clean_lo=_lower(a.clean_lo, b.clean_lo),
        clean_hi=_upper(a.clean_hi, b.clean_hi),
        pos_inf=a.pos_inf or b.pos_inf,
        neg_inf=a.neg_inf or b.neg_inf,
        nan=a.nan or b.nan,
        must_nan=a.must_nan and b.must_nan,
        may=a.may | b.may,
        must=a.must & b.must,
    )


def _lower(a: Key | None, b: Key | None) -> Key | None:
    return a if b is None else (b if a is None else min(a, b))


def _upper(a: Key | None, b: Key | None) -> Key | None:
    return a if b is None else (b if a is None else max(a, b))


def leaf_outcome(leaf: Leaf) -> Outcome:
    if leaf.kind == "fin":
        k = fkey(leaf.x, leaf.neg)
        return Outcome(lo=k, hi=k, clean_lo=k, clean_hi=k)
    if leaf.kind == "inf":
        return Outcome(pos_inf=not leaf.neg, neg_inf=leaf.neg)
    return Outcome(nan=True, must_nan=True, snan=leaf.kind == "snan")


def _closure(x: int, mode: int, acc: Fmt, low: bool, clean: bool = False) -> tuple[int, Cands]:
    """
    Lowest (low) or highest value reachable from x by rounding it any number of times, with the flags and
    infinities met on the way; if clean, only through roundings that do not overflow. Each rounding is monotone, so
    taking the extreme at every step is optimal.
    """

    def extreme(c: Cands) -> int:
        if clean:
            return c.clean_lo if low else c.clean_hi
        return c.lo if low else c.hi

    c = round_any(x, mode, acc)
    info = Cands(c.lo, c.hi, c.clean_lo, c.clean_hi, c.pos_inf, c.neg_inf, c.inexact, c.overflow)
    cur = extreme(c)
    while cur != 0:
        n = round_any(cur, mode, acc)
        info.neg_inf |= n.neg_inf
        info.pos_inf |= n.pos_inf
        info.inexact |= n.inexact
        info.overflow |= n.overflow
        nxt = extreme(n)
        if nxt == cur:
            break
        cur = nxt
    return cur, info


def _zero_sign(a: Key, b: Key, mode: int) -> int:
    """Sign of an exact-zero sum of a and b: -1 for -0, which needs two -0s, or any exact zero at RDN."""
    if mode == RDN:
        return 1 if (a == (0, 1) and b == (0, 1)) else -1
    return -1 if (a == (0, -1) and b == (0, -1)) else 1


def combine(a: Outcome, b: Outcome, mode: int, acc: Fmt) -> Outcome:
    """Outcomes of one tree node adding a value from a and a value from b (then any number of re-roundings)."""
    out = Outcome()
    # NaN inputs, and signaling NaNs that this node consumes
    if a.nan or b.nan:
        out.nan = True
    out.must_nan = a.must_nan or b.must_nan
    if a.snan or b.snan:
        out.must |= NV
        out.may |= NV
    # Infinities
    if (a.pos_inf and b.neg_inf) or (a.neg_inf and b.pos_inf):
        out.nan = True
        out.may |= NV
    if (a.pos_inf and (b.pos_inf or b.has_fin())) or (b.pos_inf and a.has_fin()):
        out.pos_inf = True
    if (a.neg_inf and (b.neg_inf or b.has_fin())) or (b.neg_inf and a.has_fin()):
        out.neg_inf = True
    # +inf + -inf is certain when both are certain (no finite or NaN alternative on either side)
    a_only_pinf = a.pos_inf and not (a.neg_inf or a.nan or a.has_fin())
    a_only_ninf = a.neg_inf and not (a.pos_inf or a.nan or a.has_fin())
    b_only_pinf = b.pos_inf and not (b.neg_inf or b.nan or b.has_fin())
    b_only_ninf = b.neg_inf and not (b.pos_inf or b.nan or b.has_fin())
    if (a_only_pinf and b_only_ninf) or (a_only_ninf and b_only_pinf):
        out.must_nan = True
        out.must |= NV
    # Finite + finite
    if a.has_fin() and b.has_fin():
        assert a.lo and a.hi and b.lo and b.hi
        lo_x = a.lo[0] + b.lo[0]
        hi_x = a.hi[0] + b.hi[0]
        ends: list[Key] = []
        for x, ka, kb, low in ((lo_x, a.lo, b.lo, True), (hi_x, a.hi, b.hi, False)):
            if x == 0:
                ends.append((0, _zero_sign(ka, kb, mode)))
                continue
            v, info = _closure(x, mode, acc, low)
            ends.append(fkey(v))
            out.pos_inf |= info.pos_inf
            out.neg_inf |= info.neg_inf
            out.may |= (NX if info.inexact else 0) | (OF if info.overflow else 0)
        out.lo, out.hi = min(ends), max(ends)
        # Interior points may round even if the corners are exact
        if lo_x != hi_x:
            out.may |= _interior_flags(lo_x, hi_x, acc)
    # The same, for values reached without raising OF
    if a.clean_lo and a.clean_hi and b.clean_lo and b.clean_hi:
        clean_ends: list[Key] = []
        for ka, kb, low in ((a.clean_lo, b.clean_lo, True), (a.clean_hi, b.clean_hi, False)):
            x = ka[0] + kb[0]
            clean_ends.append((0, _zero_sign(ka, kb, mode)) if x == 0 else fkey(_closure(x, mode, acc, low, True)[0]))
        out.clean_lo, out.clean_hi = min(clean_ends), max(clean_ends)
    if out.must_nan:
        out.lo = out.hi = out.clean_lo = out.clean_hi = None
        out.pos_inf = out.neg_inf = False
        out.nan = True
    out.may |= a.may | b.may | out.must
    out.must |= a.must | b.must
    return out


def _interior_flags(lo_x: int, hi_x: int, acc: Fmt) -> int:
    """Flags that rounding some value strictly between lo_x and hi_x may raise."""
    flags = 0
    # Any interval wider than one grid point contains a value that is not on acc's grid
    if hi_x - lo_x > 1 or not (representable(lo_x, acc) and representable(hi_x, acc)):
        flags |= NX
    if max(abs(lo_x), abs(hi_x)) >= acc.max_norm:
        flags |= OF | NX
    return flags


def finish(o: Outcome, mode: int, acc: Fmt) -> Outcome:
    """Apply the final rounding of the root to acc. Rounding is monotone, so the endpoints map to endpoints."""
    out = Outcome(pos_inf=o.pos_inf, neg_inf=o.neg_inf, nan=o.nan, must_nan=o.must_nan, may=o.may, must=o.must)
    if not o.has_fin():
        return out
    assert o.lo and o.hi
    ends: list[Key | None] = []
    for x, zs in (o.lo, o.hi):
        if x == 0:
            ends.append((0, zs))
            continue
        kind, v, inexact, overflow = round_final(x, mode, acc)
        out.may |= (NX if inexact else 0) | (OF if overflow else 0)
        if kind == "inf":
            if v > 0:
                out.pos_inf = True
            else:
                out.neg_inf = True
            ends.append(None)
        else:
            ends.append(fkey(v))
    lo, hi = ends
    if lo is None and o.lo[0] > 0:
        return out  # every finite candidate overflows to +inf
    if hi is None and o.hi[0] < 0:
        return out  # every finite candidate overflows to -inf
    out.lo = lo if lo is not None else fkey(-acc.max_norm)
    out.hi = hi if hi is not None else fkey(acc.max_norm)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Reduction over a multiset of leaves
# ---------------------------------------------------------------------------------------------------------------


# Outcomes of every multiset already reduced, by (leaf kinds, rounding mode, accumulator format)
_DP_CACHE: dict[tuple, dict[tuple[int, ...], Outcome]] = {}


def _key(leaf: Leaf) -> tuple:
    return (leaf.kind, leaf.x, leaf.neg)


@dataclass
class Result:
    """Legal outcomes of one reduction, ready to check against a DUT result."""

    lo_bits: int | None  # finite range in acc encoding (inclusive), or None
    hi_bits: int | None
    pos_inf: bool
    neg_inf: bool
    nan: bool  # canonical NaN allowed
    must_nan: bool
    may: int
    must: int
    passthrough: int | None = None  # no active elements: vs1 bits may also be returned unchanged with no flags
    passthrough_canon_flags: int = 0  # flags when such a NaN scalar is canonicalized instead
    exact_sum: int | None = None


def _all_zero_sign(leaves: list[Leaf], mode: int) -> bool:
    """Sign of the exact-zero result when every leaf is a zero: True for -0."""
    if mode == RDN:
        return not all(not lf.neg for lf in leaves)
    return all(lf.neg for lf in leaves)


def reduce_outcomes(scalar: Leaf, elems: list[Leaf], mode: int, acc: Fmt) -> Result:
    """Legal outcomes of reducing the scalar and the active elements (already promoted to acc)."""
    if not elems:
        return _no_active(scalar, acc)
    leaves = [scalar, *elems]
    nonzero = [lf for lf in leaves if not (lf.kind == "fin" and lf.x == 0)]
    if not nonzero:
        neg = _all_zero_sign(leaves, mode)
        z = encode(0, neg, acc)
        return Result(z, z, False, False, False, False, 0, 0, exact_sum=0)
    # Group equal leaves. A multiset of leaves is then a tuple of counts, one per distinct leaf (kind).
    leaf_counts: dict[tuple, int] = {}
    leaf_of_kind: dict[tuple, Leaf] = {}
    for leaf in nonzero:
        kind = _key(leaf)
        leaf_counts[kind] = leaf_counts.get(kind, 0) + 1
        leaf_of_kind[kind] = leaf
    kinds = tuple(sorted(leaf_counts))
    full = tuple(leaf_counts[kind] for kind in kinds)
    # Outcomes of every sub-multiset, shared across calls with the same leaf kinds, rounding mode and format
    memo = _DP_CACHE.setdefault((kinds, mode, acc), {})
    for counts in sorted(_sub_multisets(full), key=sum):  # smaller multisets first
        if counts in memo or sum(counts) == 0:
            continue
        if sum(counts) == 1:
            memo[counts] = leaf_outcome(leaf_of_kind[kinds[counts.index(1)]])
            continue
        # The root node of any tree over these leaves adds a tree over one part to a tree over the rest
        outcome: Outcome | None = None
        for part in _sub_multisets(counts):
            rest = tuple(n - k for n, k in zip(counts, part, strict=True))
            if sum(part) == 0 or sum(rest) == 0 or part > rest:  # each split once, both sides nonempty
                continue
            outcome = _join(outcome, combine(memo[part], memo[rest], mode, acc))
        assert outcome is not None
        memo[counts] = outcome
    root = memo[full]
    if sum(full) == 1:
        # The lone nonzero leaf still passes through a node that adds a zero leaf
        root = combine(root, Outcome(lo=(0, 1), hi=(0, 1), clean_lo=(0, 1), clean_hi=(0, 1)), mode, acc)
    fin = finish(root, mode, acc)
    res = _to_result(fin, acc)
    # Every tree adds every leaf, so an inexact exact sum makes the result inexact in every tree
    if all(leaf.kind == "fin" for leaf in leaves):
        exact = sum(leaf.x for leaf in leaves)
        res.exact_sum = exact
        if not res.nan and not representable(exact, acc):
            res.must |= NX
        if _must_overflow(root, mode, acc):
            res.must |= OF | NX
    res.may |= res.must
    return res


def _sub_multisets(counts: tuple[int, ...]) -> list[tuple[int, ...]]:
    """Every sub-multiset of counts, each as a tuple of counts (0 to n of each distinct leaf)."""
    return list(product(*(range(n + 1) for n in counts)))


def _must_overflow(root: Outcome, mode: int, acc: Fmt) -> bool:
    """
    Whether every tree over finite leaves raises OF: every root value reached without raising OF overflows in the
    final rounding to acc. Overflow grows with magnitude, so the value nearest zero decides.
    """
    if root.clean_lo is None or root.clean_hi is None:
        return True  # every tree has already raised OF
    if root.clean_lo[0] > 0:
        nearest_zero = root.clean_lo[0]
    elif root.clean_hi[0] < 0:
        nearest_zero = root.clean_hi[0]
    else:
        return False
    return round_final(nearest_zero, mode, acc)[3]


def _to_result(o: Outcome, acc: Fmt) -> Result:
    lo = hi = None
    if o.has_fin():
        assert o.lo and o.hi
        lo = encode(o.lo[0], o.lo[1] < 0, acc)
        hi = encode(o.hi[0], o.hi[1] < 0, acc)
    nan = o.nan or o.must_nan
    return Result(lo, hi, o.pos_inf, o.neg_inf, nan, o.must_nan, o.may, o.must)


def _no_active(scalar: Leaf, acc: Fmt) -> Result:
    """No active elements: vs1[0] plus additive identities. NaN may pass through or be canonicalized."""
    if scalar.kind == "fin":
        b = encode(scalar.x, scalar.neg, acc)
        return Result(b, b, False, False, False, False, 0, 0, exact_sum=scalar.x)
    if scalar.kind == "inf":
        return Result(None, None, not scalar.neg, scalar.neg, False, False, 0, 0)
    flags = NV if scalar.kind == "snan" else 0
    return Result(None, None, False, False, True, True, flags, 0, passthrough_canon_flags=flags)


def reduce_bits(scalar_bits: int, elem_bits: list[int], mode: int, sew: int, widening: bool) -> Result:
    """Legal outcomes for vs1[0] = scalar_bits and active elements elem_bits (SEW encodings)."""
    efmt = FORMATS[sew]
    acc = FORMATS[2 * sew] if widening else efmt
    scalar = decode(scalar_bits, acc, acc)
    elems = [decode(b, efmt, acc) for b in elem_bits]
    res = reduce_outcomes(scalar, elems, mode, acc)
    if not elem_bits and scalar.kind in ("qnan", "snan"):
        res.passthrough = scalar_bits
    return res


def exact_bits(scalar_bits: int, elem_bits: list[int], mode: int, sew: int, widening: bool) -> Result | None:
    """
    Outcome of a reduction whose every partial sum is exact, or None if that is not guaranteed.

    If all leaves are finite multiples of a power of two u and the sum of their magnitudes is below 2^prec * u and
    at most acc's largest finite value, every subset sum is a value of acc, so every node of every tree is exact:
    the result is the exact sum and no flags are raised. This avoids the multiset search for many distinct leaves.
    """
    efmt = FORMATS[sew]
    acc = FORMATS[2 * sew] if widening else efmt
    leaves = [decode(scalar_bits, acc, acc)] + [decode(b, efmt, acc) for b in elem_bits]
    if any(lf.kind != "fin" for lf in leaves):
        return None
    mags = [abs(lf.x) for lf in leaves]
    nonzero = [m for m in mags if m]
    if not nonzero:
        neg = _all_zero_sign(leaves, mode)
        z = encode(0, neg, acc)
        return Result(z, z, False, False, False, False, 0, 0, exact_sum=0)
    unit = min(m & -m for m in nonzero)
    total = sum(mags)
    if total >= unit << acc.prec or total > acc.max_norm:
        return None
    s = sum(lf.x for lf in leaves)
    b = encode(s, mode == RDN, acc)
    return Result(b, b, False, False, False, False, 0, 0, exact_sum=s)
