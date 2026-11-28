# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Zv* rule-derived tests (gen_Vzv.py): reference semantics taken from the instruction
descriptions and operation pseudocode in src/unpriv/zvbb.adoc, zvbc.adoc, zvk.adoc, zvfh.adoc, zvfbfmin.adoc and
zvfbfwma.adoc, IEEE 754 rounding for binary16/BF16/binary32, and assembly emitters for vector cases.

Vector data never goes through the XLEN table: operands are .word arrays in the data section, loaded with vle*.v.
Results are stored with vse*.v to a per-test buffer and checked word by word with lw, so one expected word is
valid for both XLENs (sign-extended on RV64)."""

from __future__ import annotations

import os
import struct
from fractions import Fraction
from typing import TYPE_CHECKING

from aigen import TestFile, X, sext

if TYPE_CHECKING:
    from collections.abc import Sequence

MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations
M32 = (1 << 32) - 1
M64 = (1 << 64) - 1
ILLEGAL = 2

# ---------------------------------------------------------------- bit utilities (zvbb.adoc)


def msk(n: int) -> int:
    return (1 << n) - 1


def brev(v: int, n: int) -> int:
    return int(f"{v & msk(n):0{n}b}"[::-1], 2)


def brev8(v: int, n: int) -> int:
    """Reverse the bits of each byte (vbrev8.v)."""
    return sum(brev((v >> i) & 0xFF, 8) << i for i in range(0, n, 8))


def rev8(v: int, n: int) -> int:
    """Reverse the bytes of an n-bit value (vrev8.v)."""
    return int.from_bytes((v & msk(n)).to_bytes(n // 8, "little"), "big")


def clz(v: int, n: int) -> int:
    v &= msk(n)
    return n - v.bit_length()


def ctz(v: int, n: int) -> int:
    v &= msk(n)
    return n if v == 0 else (v & -v).bit_length() - 1


def cpop(v: int, n: int) -> int:
    return bin(v & msk(n)).count("1")  # noqa: FURB161  # int.bit_count needs Python 3.10


def rol(v: int, s: int, n: int) -> int:
    v &= msk(n)
    s %= n
    return ((v << s) | (v >> (n - s))) & msk(n)


def ror(v: int, s: int, n: int) -> int:
    return rol(v, n - (s % n), n)


def clmul_full(a: int, b: int, n: int = 64) -> int:
    r = 0
    for i in range(n):
        if (b >> i) & 1:
            r ^= a << i
    return r


# ---------------------------------------------------------------- packing


def pack(vals: Sequence[int], eew: int) -> list[int]:
    """Elements of width eew (bits) -> little-endian 32-bit words (padded with zero bytes)."""
    b = b"".join((v & msk(eew)).to_bytes(eew // 8, "little") for v in vals)
    b += b"\0" * (-len(b) % 4)
    return [int.from_bytes(b[i : i + 4], "little") for i in range(0, len(b), 4)]


def unpack(words: Sequence[int], eew: int) -> list[int]:
    b = b"".join((w & M32).to_bytes(4, "little") for w in words)
    return [int.from_bytes(b[i : i + eew // 8], "little") for i in range(0, len(b), eew // 8)]


def W(v: int | X) -> X:
    """The value lw reads for a 32-bit memory word: as is on RV32, sign-extended on RV64."""
    if isinstance(v, X):
        return X(v.num(32) & M32, sext(v.num(64), 32) & M64)
    return X(v & M32, sext(v, 32) & M64)


# ---------------------------------------------------------------- AES (zvk.adoc, FIPS-197)


def _gmul(a: int, b: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = ((a << 1) ^ (0x11B if a & 0x80 else 0)) & 0xFF
        b >>= 1
    return r


def _aes_sbox() -> list[int]:
    inv = [0] * 256
    for x in range(1, 256):
        for y in range(1, 256):
            if _gmul(x, y) == 1:
                inv[x] = y
                break
    sb = []
    for x in range(256):
        b = inv[x]
        s = b
        for k in range(1, 5):
            s ^= ((b << k) | (b >> (8 - k))) & 0xFF
        sb.append(s ^ 0x63)
    return sb


AES_SBOX = _aes_sbox()
AES_INV_SBOX = [AES_SBOX.index(i) for i in range(256)]


def eg_bytes(elems: Sequence[int], eew: int = 32) -> list[int]:
    b: list[int] = []
    for e in elems:
        b += list((e & msk(eew)).to_bytes(eew // 8, "little"))
    return b


def eg_elems(b: Sequence[int], eew: int = 32) -> list[int]:
    n = eew // 8
    return [int.from_bytes(bytes(b[i : i + n]), "little") for i in range(0, len(b), n)]


def aes_sub(s: list[int], inv: bool = False) -> list[int]:
    t = AES_INV_SBOX if inv else AES_SBOX
    return [t[x] for x in s]


def aes_shift_rows(s: list[int], inv: bool = False) -> list[int]:
    """State byte 4c+r is row r of column c (the 32-bit element c holds column c)."""
    if MUT == "aes_shiftrows_swapped":
        inv = not inv
    o = [0] * 16
    for c in range(4):
        for r in range(4):
            if inv:
                o[r + 4 * ((c + r) % 4)] = s[r + 4 * c]
            else:
                o[r + 4 * c] = s[r + 4 * ((c + r) % 4)]
    return o


def aes_mix(s: list[int], inv: bool = False) -> list[int]:
    m = [14, 11, 13, 9] if inv else [2, 3, 1, 1]
    o = []
    for c in range(4):
        col = s[4 * c : 4 * c + 4]
        for r in range(4):
            o.append(
                _gmul(col[0], m[(0 - r) % 4])
                ^ _gmul(col[1], m[(1 - r) % 4])
                ^ _gmul(col[2], m[(2 - r) % 4])
                ^ _gmul(col[3], m[(3 - r) % 4])
            )
    return o


def _x(a: list[int], b: list[int]) -> list[int]:
    return [x ^ y for x, y in zip(a, b)]


def aes_round(insn: str, state: list[int], key: list[int]) -> list[int]:
    """vaesef/vaesem/vaesdf/vaesdm/vaesz on one 128-bit element group (four 32-bit elements)."""
    s, k = eg_bytes(state), eg_bytes(key)
    if insn == "vaesz":
        r = _x(s, k)
    elif insn == "vaesef":
        r = _x(aes_shift_rows(aes_sub(s)), k)
    elif insn == "vaesem":
        r = _x(aes_mix(aes_shift_rows(aes_sub(s))), k)
    elif insn == "vaesdf":
        r = _x(aes_sub(aes_shift_rows(s, True), True), k)
    elif insn == "vaesdm":
        sb = aes_sub(aes_shift_rows(s, True), True)
        r = _x(aes_mix(sb, True), k) if MUT == "aesdm_mix_before_ark" else aes_mix(_x(sb, k), True)
    else:
        raise ValueError(insn)
    return eg_elems(r)


def aes_subword(w: int) -> int:
    return eg_elems(aes_sub(eg_bytes([w])))[0]


def aes_rotword(w: int) -> int:
    """FIPS RotWord [a0,a1,a2,a3] -> [a1,a2,a3,a0], a0 in the low byte."""
    return ror(w, 8, 32)


RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def kf1_round(uimm: int) -> int:
    """vaeskf1: uimm[4] is ignored; uimm[3:0] of 0 and 11-15 are mapped by inverting bit 3."""
    r = uimm & (0x1F if MUT == "aeskf_uimm4_used" else 0xF)
    if MUT != "aeskf_no_map" and (r > 10 or r == 0):
        r ^= 8
    return r


def kf2_round(uimm: int) -> int:
    r = uimm & (0x1F if MUT == "aeskf_uimm4_used" else 0xF)
    if MUT != "aeskf_no_map" and (r < 2 or r > 14):
        r ^= 8
    return r


def aeskf1(key: list[int], uimm: int) -> list[int]:
    rnd = kf1_round(uimm)
    rc = RCON[(rnd - 1) % 16] if 1 <= rnd <= 10 else 0
    w0 = aes_subword(aes_rotword(key[3])) ^ rc ^ key[0]
    w1 = w0 ^ key[1]
    w2 = w1 ^ key[2]
    w3 = w2 ^ key[3]
    return [w0, w1, w2, w3]


def aeskf2(prev: list[int], cur: list[int], uimm: int) -> list[int]:
    """vaeskf2: prev is the round key two rounds back (vd), cur the current one (vs2)."""
    rnd = kf2_round(uimm)
    odd = rnd & 1
    if MUT == "aeskf2_parity_swapped":
        odd ^= 1
    if odd:
        w0 = aes_subword(cur[3]) ^ prev[0]
    else:
        w0 = aes_subword(aes_rotword(cur[3])) ^ RCON[((rnd >> 1) - 1) % 10] ^ prev[0]
    w1 = w0 ^ prev[1]
    w2 = w1 ^ prev[2]
    w3 = w2 ^ prev[3]
    return [w0, w1, w2, w3]


def aes_key_expand(key: list[int]) -> list[list[int]]:
    """AES-128 round keys 0..10 (FIPS-197 key expansion), each as four 32-bit elements."""
    rk = [list(key)]
    for r in range(1, 11):
        rk.append(aeskf1(rk[-1], r))
    return rk


def aes_key_expand256(key: list[int]) -> list[list[int]]:
    """AES-256 round keys 0..14 from an 8-word key."""
    rk = [list(key[:4]), list(key[4:])]
    for r in range(2, 15):
        rk.append(aeskf2(rk[-2], rk[-1], r))
    return rk


# ---------------------------------------------------------------- SHA-2 (zvk.adoc vsha2ch/cl/ms)


def _sha_fns(sew: int):  # noqa: ANN202
    def r(x: int, n: int) -> int:
        return ror(x, n, sew)

    if sew == 32:
        s0 = lambda x: r(x, 2) ^ r(x, 13) ^ r(x, 22)
        s1 = lambda x: r(x, 6) ^ r(x, 11) ^ r(x, 25)
        g0 = lambda x: r(x, 7) ^ r(x, 18) ^ (x >> 3)
        g1 = lambda x: r(x, 17) ^ r(x, 19) ^ (x >> 10)
    else:
        s0 = lambda x: r(x, 28) ^ r(x, 34) ^ r(x, 39)
        s1 = lambda x: r(x, 14) ^ r(x, 18) ^ r(x, 41)
        g0 = lambda x: r(x, 1) ^ r(x, 8) ^ (x >> 7)
        g1 = lambda x: r(x, 19) ^ r(x, 61) ^ (x >> 6)
    return s0, s1, g0, g1


def sha2c(high: bool, vd: list[int], vs2: list[int], vs1: list[int], sew: int) -> list[int]:
    """vsha2ch (high) / vsha2cl: vs2 = {f, e, b, a} (element 0 first), vd = {h, g, d, c}, vs1 = message
    schedule plus constants; returns the new {f, e, b, a}."""
    m = msk(sew)
    s0, s1, _, _ = _sha_fns(sew)
    f, e, b, a = vs2
    h, g, d, c = vd
    if MUT == "sha2c_hl_swapped":
        high = not high
    w0, w1 = (vs1[2], vs1[3]) if high else (vs1[0], vs1[1])
    for w in (w0, w1):
        t1 = (h + s1(e) + ((e & f) ^ (~e & g)) + w) & m
        t2 = (s0(a) + ((a & b) ^ (a & c) ^ (b & c))) & m
        h, g, f, e, d, c, b, a = g, f, e, (d + t1) & m, c, b, a, (t1 + t2) & m
    return [f, e, b, a]


def sha2ms(vd: list[int], vs2: list[int], vs1: list[int], sew: int) -> list[int]:
    m = msk(sew)
    _, _, g0, g1 = _sha_fns(sew)
    w = [0] * 20
    w[0:4] = vd
    w[4], w[9], w[10], w[11] = vs2
    w[12:16] = vs1
    for j in range(16, 20):
        w[j] = (g1(w[j - 2]) + w[j - 7] + g0(w[j - 15]) + w[j - 16]) & m
    return w[16:20]


# ---------------------------------------------------------------- GHASH (zvk.adoc vghsh/vgmul)


def _eg128(elems: Sequence[int]) -> int:
    return sum((e & M32) << (32 * i) for i, e in enumerate(elems))


def _elems128(v: int) -> list[int]:
    return [(v >> (32 * i)) & M32 for i in range(4)]


def _gf_mul(y: int, h: int) -> int:
    z = 0
    for bit in range(128):
        if (y >> bit) & 1:
            z ^= h
        red = h >> 127
        h = (h << 1) & msk(128)
        if red:
            h ^= 0x87 if MUT != "ghash_poly_wrong" else 0x85
    return z


def vghsh(vd: list[int], vs2: list[int], vs1: list[int]) -> list[int]:
    y, x = _eg128(vd), _eg128(vs1)
    h = brev8(_eg128(vs2), 128)
    s = brev8(y ^ x, 128) if MUT != "ghash_no_add" else brev8(y, 128)
    return _elems128(brev8(_gf_mul(s, h), 128))


def vgmul(vd: list[int], vs2: list[int]) -> list[int]:
    y = brev8(_eg128(vd), 128)
    h = brev8(_eg128(vs2), 128)
    if MUT == "gmul_no_brev":
        return _elems128(_gf_mul(_eg128(vd), _eg128(vs2)))
    return _elems128(brev8(_gf_mul(y, h), 128))


# ---------------------------------------------------------------- SM4 (zvk.adoc vsm4k/vsm4r)

SM4_SBOX = bytes.fromhex(
    "d690e9fecce13db716b614c228fb2c052b679a762abe04c3aa44132649860699"
    "9c4250f491ef987a33540b43edcfac62e4b31ca9c908e89580df94fa758f3fa6"
    "4707a7fcf37317ba83593c19e6854fa8686b81b27164da8bf8eb0f4b70569d35"
    "1e240e5e6358d1a225227c3b01217887d40046579fd327524c3602e7a0c4c89e"
    "eabf8ad240c738b5a3f7f2cef96115a1e0ae5da49b341a55ad933230f58cb1e3"
    "1df6e22e8266ca60c02923ab0d534e6fd5db3745defd8e2f03ff6a726d6c5b51"
    "8d1baf92bbddbc7f11d95c411f105ad80ac13188a5cd7bbd2d74d012b8e5b4b0"
    "8969974a0c96777e65b9f109c56ec68418f07dec3adc4d2079ee5f3ed7cb3948"
)
SM4_CK = [
    0x00070E15, 0x1C232A31, 0x383F464D, 0x545B6269, 0x70777E85, 0x8C939AA1, 0xA8AFB6BD, 0xC4CBD2D9,
    0xE0E7EEF5, 0xFC030A11, 0x181F262D, 0x343B4249, 0x50575E65, 0x6C737A81, 0x888F969D, 0xA4ABB2B9,
    0xC0C7CED5, 0xDCE3EAF1, 0xF8FF060D, 0x141B2229, 0x30373E45, 0x4C535A61, 0x686F767D, 0x848B9299,
    0xA0A7AEB5, 0xBCC3CAD1, 0xD8DFE6ED, 0xF4FB0209, 0x10171E25, 0x2C333A41, 0x484F565D, 0x646B7279,
]  # fmt: skip


def sm4_subword(x: int) -> int:
    return sum(SM4_SBOX[(x >> s) & 0xFF] << s for s in (0, 8, 16, 24))


def vsm4k(rk: list[int], uimm: int) -> list[int]:
    rnd = uimm & (0x1F if MUT == "sm4k_uimm43_used" else 7)
    k = list(rk)
    for j in range(4):
        i = 4 * rnd + j
        ck = SM4_CK[i] if i < 32 else 0  # the mutant indexes past the 32-entry CK table (reads 0)
        b = k[j + 1] ^ k[j + 2] ^ k[j + 3] ^ ck
        s = sm4_subword(b)
        k.append(k[j] ^ s ^ rol(s, 13, 32) ^ rol(s, 23, 32))
    return k[4:]


def vsm4r(state: list[int], rk: list[int]) -> list[int]:
    x = list(state)
    for j in range(4):
        b = x[j + 1] ^ x[j + 2] ^ x[j + 3] ^ rk[j]
        s = sm4_subword(b)
        if MUT == "sm4r_key_schedule_l":
            lin = s ^ rol(s, 13, 32) ^ rol(s, 23, 32)
        else:
            lin = s ^ rol(s, 2, 32) ^ rol(s, 10, 32) ^ rol(s, 18, 32) ^ rol(s, 24, 32)
        x.append(x[j] ^ lin)
    return x[4:]


# ---------------------------------------------------------------- SM3 (zvk.adoc vsm3c/vsm3me)


def _r32(x: int) -> int:
    return rev8(x, 32)


def _p0(x: int) -> int:
    return x ^ rol(x, 9, 32) ^ rol(x, 17, 32)


def _p1(x: int) -> int:
    return x ^ rol(x, 15, 32) ^ rol(x, 23, 32)


def vsm3me(vs2: list[int], vs1: list[int]) -> list[int]:
    """vs1 holds W[7:0], vs2 W[15:8], all big-endian words; returns W[23:16] (big-endian)."""
    w = [_r32(v) for v in list(vs1) + list(vs2)]
    if MUT == "sm3_no_byteswap":
        w = list(vs1) + list(vs2)
    for j in range(16, 24):
        w.append(_p1(w[j - 16] ^ w[j - 9] ^ rol(w[j - 3], 15, 32)) ^ rol(w[j - 13], 7, 32) ^ w[j - 6])
    out = w[16:24]
    return out if MUT == "sm3_no_byteswap" else [_r32(v) for v in out]


def vsm3c(vd: list[int], vs2: list[int], uimm: int) -> list[int]:
    """vd = {A..H} big-endian (element 0 = A); vs2 = message words W[j..j+7] (only 0, 1, 4, 5 are used)."""
    m = M32
    a, b, c, d, e, f, g, h = (_r32(v) for v in vd)
    w0, w1, w4, w5 = (_r32(vs2[i]) for i in (0, 1, 4, 5))
    out = []
    for k, (wj, wpj) in enumerate(((w0, w0 ^ w4), (w1, w1 ^ w5))):
        j = 2 * uimm + k
        tj = 0x79CC4519 if j <= 15 else 0x7A879D8A
        if MUT == "sm3c_round_off_by_one":
            j += 1
        ff = (a ^ b ^ c) if j <= 15 else ((a & b) | (a & c) | (b & c))
        gg = (e ^ f ^ g) if j <= 15 else ((e & f) | (~e & g & m))
        ss1 = rol((rol(a, 12, 32) + e + rol(tj, j % 32, 32)) & m, 7, 32)
        ss2 = ss1 ^ rol(a, 12, 32)
        tt1 = (ff + d + ss2 + wpj) & m
        tt2 = (gg + h + ss1 + wj) & m
        d, c, b, a = c, rol(b, 9, 32), a, tt1
        h, g, f, e = g, rol(f, 19, 32), e, _p0(tt2)
        out.append((a, c, e, g))
    (a1, c1, e1, g1), (a2, c2, e2, g2) = out
    return [_r32(v) for v in (a2, a1, c2, c1, e2, e1, g2, g1)]


# ---------------------------------------------------------------- floating point (IEEE 754)

RNE, RTZ, RDN, RUP, RMM = range(5)
NV, DZ, OF, UF, NX = 16, 8, 4, 2, 1


class Fmt:
    def __init__(self, e: int, m: int) -> None:
        self.e, self.m = e, m
        self.bias = (1 << (e - 1)) - 1
        self.w = 1 + e + m
        self.cnan = ((1 << e) - 1) << m | 1 << (m - 1)
        self.inf = ((1 << e) - 1) << m

    def decode(self, bits: int) -> tuple[str, int, Fraction]:
        """('num'|'inf'|'qnan'|'snan', sign, magnitude)."""
        s = (bits >> (self.w - 1)) & 1
        ex = (bits >> self.m) & msk(self.e)
        man = bits & msk(self.m)
        if ex == msk(self.e):
            if man == 0:
                return "inf", s, Fraction(0)
            return ("qnan" if man >> (self.m - 1) else "snan"), s, Fraction(0)
        if ex == 0:
            return "num", s, Fraction(man, 1 << (self.m + self.bias - 1))
        return "num", s, Fraction((1 << self.m) | man) * Fraction(2) ** (ex - self.bias - self.m)

    def round(self, sign: int, mag: Fraction, rm: int) -> tuple[int, int]:
        """Round a finite nonzero-or-zero exact value; returns (bits, flags). Tininess after rounding."""
        if mag == 0:
            return sign << (self.w - 1), 0
        emin = 1 - self.bias
        emax = self.bias
        p = self.m + 1

        def rnd(q: Fraction) -> int:
            fl = q.numerator // q.denominator
            rem = q - fl
            if rem == 0:
                return fl
            if rm == RNE:
                return fl + 1 if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl & 1) else fl
            if rm == RMM:
                return fl + 1 if rem >= Fraction(1, 2) else fl
            if rm == RTZ:
                return fl
            if rm == RDN:
                return fl + 1 if sign else fl
            return fl if sign else fl + 1  # RUP

        e = mag.numerator.bit_length() - mag.denominator.bit_length()
        if Fraction(2) ** e > mag:
            e -= 1
        # tininess after rounding: round to p bits with an unbounded exponent
        q_unb = rnd(mag / Fraction(2) ** (e - p + 1)) * Fraction(2) ** (e - p + 1)
        tiny = q_unb < Fraction(2) ** emin
        quantum = Fraction(2) ** (max(e, emin) - self.m)
        qi = rnd(mag / quantum)
        inexact = qi * quantum != mag
        val = qi * quantum
        flags = NX if inexact else 0
        if tiny and inexact:
            flags |= UF
        if val >= Fraction(2) ** (emax + 1):
            flags |= OF | NX
            to_inf = rm in (RNE, RMM) or (rm == RUP and not sign) or (rm == RDN and sign)
            bits = self.inf if to_inf else self.inf - 1
            return sign << (self.w - 1) | bits, flags
        if val < Fraction(2) ** emin:
            bits = int(val / Fraction(2) ** (emin - self.m))
        else:
            ee = val.numerator.bit_length() - val.denominator.bit_length()
            if Fraction(2) ** ee > val:
                ee -= 1
            man = int(val / Fraction(2) ** (ee - self.m)) - (1 << self.m)
            bits = (ee + self.bias) << self.m | man
        return sign << (self.w - 1) | bits, flags


F16, BF16, F32, F64 = Fmt(5, 10), Fmt(8, 7), Fmt(8, 23), Fmt(11, 52)


def fbits(fmt: Fmt, x: float) -> int:
    """Encoding of an exactly representable value."""
    v = Fraction(x)
    b, fl = fmt.round(1 if x < 0 or (x == 0 and str(x).startswith("-")) else 0, abs(v), RNE)
    assert fl == 0, f"{x} is not exact in this format"
    return b


def convert(src: Fmt, dst: Fmt, bits: int, rm: int) -> tuple[int, int]:
    """FP-to-FP conversion; NaN results are the canonical NaN, signaling NaN inputs raise NV."""
    kind, s, mag = src.decode(bits)
    if kind in ("qnan", "snan"):
        return dst.cnan, NV if kind == "snan" else 0
    if kind == "inf":
        return s << (dst.w - 1) | dst.inf, 0
    return dst.round(s, mag, rm)


def fma(fmt: Fmt, a: tuple[Fmt, int], b: tuple[Fmt, int], c: tuple[Fmt, int], rm: int) -> tuple[int, int]:
    """a*b + c with one rounding into fmt (vfwmaccbf16: BF16 * BF16 + FP32)."""
    ka, sa, ma = a[0].decode(a[1])
    kb, sb, mb = b[0].decode(b[1])
    kc, sc, mc = c[0].decode(c[1])
    kinds = (ka, kb, kc)
    nv = NV if "snan" in kinds else 0
    pinf = "inf" in (ka, kb)
    pzero = (ka == "num" and ma == 0) or (kb == "num" and mb == 0)
    if pinf and pzero:
        return fmt.cnan, NV
    if "qnan" in kinds or "snan" in kinds:
        return fmt.cnan, nv
    ps = sa ^ sb
    if pinf:
        if kc == "inf" and sc != ps:
            return fmt.cnan, NV
        return ps << (fmt.w - 1) | fmt.inf, 0
    if kc == "inf":
        return sc << (fmt.w - 1) | fmt.inf, 0
    p = ma * mb * (-1 if ps else 1)
    cv = mc * (-1 if sc else 1)
    r = p + cv
    if r == 0:
        if p == 0 and cv == 0 and ps == sc:
            return ps << (fmt.w - 1), 0
        return (1 if rm == RDN else 0) << (fmt.w - 1), 0
    return fmt.round(1 if r < 0 else 0, abs(r), rm)


def add(fmt: Fmt, a: int, b: int, rm: int) -> tuple[int, int]:
    one = fbits(fmt, 1.0)
    return fma(fmt, (fmt, a), (fmt, one), (fmt, b), rm)


def f2i(fmt: Fmt, bits: int, width: int, signed: bool, rm: int) -> tuple[int, int]:
    """FP-to-integer conversion: NaN and out-of-range values saturate with NV (NaN gives the maximum)."""
    kind, s, mag = fmt.decode(bits)
    lo, hi = (-(1 << (width - 1)), (1 << (width - 1)) - 1) if signed else (0, (1 << width) - 1)
    if kind in ("qnan", "snan"):
        return hi & msk(width), NV
    if kind == "inf":
        return (lo if s else hi) & msk(width), NV
    q = mag
    fl = q.numerator // q.denominator
    rem = q - fl
    if rem == 0:
        r = fl
    elif rm == RNE:
        r = fl + 1 if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl & 1) else fl
    elif rm == RMM:
        r = fl + 1 if rem >= Fraction(1, 2) else fl
    elif rm == RTZ:
        r = fl
    elif rm == RDN:
        r = fl + 1 if s else fl
    else:
        r = fl if s else fl + 1
    v = -r if s else r
    if v < lo or v > hi:
        if MUT == "cvt8_wraps" and width == 8:
            return v & msk(width), NV
        return (lo if v < lo else hi) & msk(width), NV
    return v & msk(width), (NX if rem else 0)


def i2f(fmt: Fmt, v: int, rm: int) -> tuple[int, int]:
    return fmt.round(1 if v < 0 else 0, Fraction(abs(v)), rm)


def h16(x: float) -> int:
    return fbits(F16, x)


def bf(x: float) -> int:
    return fbits(BF16, x)


def f32(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


# ---------------------------------------------------------------- test construction

SUITE = "Vzv"
POOL = ["x1", "x6", "x7", "x8", "x9", "x10", "x11", "x12"]  # x13-x15: trap-window state; no T-SBI here
EXTS = {  # assembler names needed by the instructions of each extension
    "Zvbb": ["zve64x", "zvbb"],  # SEW=64 sections are under #if ZVE64X_SUPPORTED
    "Zvkb": ["zve64x", "zvkb"],
    "Zvbc": ["zve64x", "zvbc"],
    "Zvfh": ["f", "zfhmin", "zve32f", "zvfh"],
    "Zvfhmin": ["f", "zve32f", "zvfhmin"],
    "Zvfbfmin": ["f", "zve32f", "zvfbfmin"],
    "Zvfbfwma": ["f", "zfbfmin", "zve32f", "zvfbfmin", "zvfbfwma"],
    "Zvkned": ["zve32x", "zvkned"],
    "Zvknha": ["zve32x", "zvknha"],
    "Zvknhb": ["zve64x", "zvknhb"],
    "Zvkg": ["zve32x", "zvkg"],
    "Zvksed": ["zve32x", "zvksed"],
    "Zvksh": ["zve32x", "zvksh"],
}


def march(exts: list[str]) -> str:
    seen: list[str] = []
    for e in exts:
        for a in EXTS.get(e, [e.lower()]):
            if a not in seen:
                seen.append(a)
    singles = "".join(a for a in seen if len(a) == 1)
    multi = "_".join(a for a in seen if len(a) > 1)
    return f"rv${{XLEN}}i{singles}_zicsr_zifencei" + (f"_{multi}" if multi else "")


class VT(TestFile):
    """A Zv* test: unprivileged (runs in the lowest mode), with vector data in the data section."""

    def __init__(self, suite: str, rule: str, *, required: list, march: str, **kw: object) -> None:
        super().__init__(suite, rule, required=required, march=march, pool=POOL, **kw)  # type: ignore[arg-type]
        self.out = f"{rule.replace('-', '_')}_vzv_out"
        self.extra_data += [".p2align 4", f"{self.out}:", "  .space 512"]

    # ---- vector configuration
    def vset(self, avl: int, sew: int, lmul: str = "m8", pol: str = "tu, mu", rd: str = "x0") -> None:
        self.emit(f"vsetivli {rd}, {avl}, e{sew}, {lmul}, {pol}")

    # ---- data
    def words(self, words: Sequence[int]) -> str:
        lab = self.label("data")
        self.extra_data += [".p2align 3", f"{lab}:"]
        ws = [w & M32 for w in words] or [0]
        for i in range(0, len(ws), 8):
            self.extra_data.append("  .word " + ", ".join(f"0x{w:08x}" for w in ws[i : i + 8]))
        return lab

    def vload(self, vreg: str, words: Sequence[int], eew: int = 32, ptr: str = "x1") -> None:
        """vle<eew>.v vreg from a data array, with the current vl."""
        self.la(ptr, self.words(words))
        self.emit(f"vle{eew}.v {vreg}, ({ptr})")

    def vcheck(
        self,
        vreg: str,
        expected: Sequence[int | X | None],
        lab: str,
        desc: str,
        eew: int = 32,
        ptr: str = "x1",
        nbytes: int | None = None,
    ) -> None:
        """vse<eew>.v vreg (current vl) to the buffer and check each 32-bit word (None: not checked). nbytes: the
        number of bytes the store writes, when the last word is partial (its other bytes are not checked)."""
        self.la(ptr, self.out)
        self.emit(f"vse{eew}.v {vreg}, ({ptr})")
        for i, w in enumerate(expected):
            if w is None:
                continue
            self.emit(f"lw x6, {4 * i}({ptr})")
            part = None if nbytes is None else nbytes - 4 * i
            if part is not None and part < 4:
                m = (1 << (8 * part)) - 1
                wv = w.num(32) if isinstance(w, X) else w
                self.check_masked("x6", W(m), W(wv & m), lab, f"{desc}: word {i} (low {part} bytes)")
            else:
                self.check("x6", W(w), lab, f"{desc}: word {i}")

    def insn(self, line: str) -> str:
        lab = self.label("i")
        self.emit(f"{lab}:", 0)
        self.emit(line)
        return lab

    # ---- trap windows (in the current, lowest, mode)
    def trapwin(self, line: str, expect: object, desc: str, pre: Sequence[str] = ()) -> str:
        """Run one instruction in a trap window. expect: "ok", ILLEGAL or ["ok", ILLEGAL]. For an illegal-
        instruction trap, xtval must be 0 or the instruction bits (read from memory at the label)."""
        lab = self.label("w")
        self.allow(1)
        for p in pre:
            self.emit(p)
        self.emit(f"{lab}:", 0)
        self.emit(line)
        self.outcome(expect, lab, desc, tval=None, epc=True, origin=None)  # type: ignore[arg-type]
        alts = expect if isinstance(expect, list) else [expect]
        if ILLEGAL in alts:
            self.emit("addi x9, x14, 1")
            self.emit("seqz x9, x9  // no trap")
            self.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
            self.la("x7", lab)
            self.emit("lw x7, 0(x7)")
            with self.rv64_only():
                self.emit("slli x7, x7, 32")
                self.emit("srli x7, x7, 32")
            self.emit("xor x7, x7, x15")
            self.emit("seqz x7, x7  // xtval = instruction bits")
            self.emit("seqz x15, x15  // xtval = 0")
            self.emit("or x7, x7, x15")
            self.emit("or x7, x7, x9")
            self.check_bool("x7", lab, f"{desc}: xtval is 0 or the instruction bits")
        return lab

    def no_trap_flag(self, reg: str) -> None:
        """reg = 1 when the last window took no trap (x14 = -1)."""
        self.emit(f"addi {reg}, x14, 1")
        self.emit(f"seqz {reg}, {reg}")

    # ---- FP
    def frm(self, rm: int) -> None:
        self.emit(f"csrwi frm, {rm}")

    def clear_flags(self) -> None:
        self.emit("csrwi fflags, 0")

    def check_flags(self, flags: int, lab: str, desc: str) -> None:
        self.emit("csrr x7, fflags")
        self.check("x7", flags, lab, f"{desc}: fflags")


def eg_words(groups: Sequence[Sequence[int]], sew: int) -> list[int]:
    out: list[int] = []
    for g in groups:
        out += pack(g, sew)
    return out


def rule_doc(t: VT, rule_text: str, source: str, plan: str, context: str = "", issues: str = "") -> None:
    t.describe(rule_text=rule_text, source=source, context=context, issues=issues, plan=plan)


# ---------------------------------------------------------------- rule texts (norm_rules.py, upstream/main)
RULES = {
    "Zvbb_dependent_Zve32x": ("src/unpriv/zvbb.adoc", "zvbb depends upon the zve32x extension."),
    "Zvbb_eew": ("src/unpriv/zvbb.adoc", "zvbb provides support for EEW of 8, 16, and 32."),
    "Zvbb_eew_Zve64x": ("src/unpriv/zvbb.adoc", "If zve64x is supported then zvbb also adds support for EEW=64."),
    "vandn_op": (
        "src/unpriv/zvbb.adoc",
        "Each bit of `Op1` is inverted and logically ANDed with the corresponding bits in _vs2_.",
    ),
    "vandn-vx_rs1": (
        "src/unpriv/zvbb.adoc",
        "In the vector-scalar version, `Op1` is the sign-extended or truncated value in scalar register _rs1_.",
    ),
    "vandn-vv_vs1": ("src/unpriv/zvbb.adoc", "In the vector-vector version, `Op1` is _vs1_."),
    "vbrev-v_op": ("src/unpriv/zvbb.adoc", "A bit reversal is performed on the bits of each element."),
    "vbrev8-v_op": ("src/unpriv/zvbb.adoc", "A bit reversal is performed on the bits of each byte."),
    "vclz-v_op": ("src/unpriv/zvbb.adoc", "A leading zero count is performed on each element."),
    "vclz-v_op_zeroinput": ("src/unpriv/zvbb.adoc", "The result for zero-valued inputs is the value SEW."),
    "vcpop-v_op": ("src/unpriv/zvbb.adoc", "A population count is performed on each element."),
    "vctz-v_op": ("src/unpriv/zvbb.adoc", "A trailing zero count is performed on each element."),
    "vrev8-v_op": (
        "src/unpriv/zvbb.adoc",
        "A byte reversal is performed on each element of _vs2_, effectively performing an endian swap.",
    ),
    "vrol_op": (
        "src/unpriv/zvbb.adoc",
        "The elements in _vs2_ are rotated left by the rotate amount specified by either the corresponding elements of _vs1_ (vector-vector), or integer register _rs1_ (vector-scalar). Only the low log2(SEW) bits of the rotate-amount value are used, all other bits are ignored.",
    ),
    "vror_op": (
        "src/unpriv/zvbb.adoc",
        "The elements in _vs2_ are rotated right by the rotate amount specified by either the corresponding elements of _vs1_ (vector-vector), integer register _rs1_ (vector-scalar), or an immediate value (vector-immediate). Only the low log2(SEW) bits of the rotate-amount value are used, all other bits are ignored.",
    ),
    "vwsll_op": (
        "src/unpriv/zvbb.adoc",
        "The elements in _vs2_ are zero-extended to 2{times}SEW bits, then shifted left by the shift amount specified by either the corresponding elements of _vs1_ (vector-vector), integer register _rs1_ (vector-scalar), or an immediate value (vector-immediate). Only the low log2(2{times}SEW) bits of the shift-amount value are used, all other bits are ignored.",
    ),
    "Zvbc_dependent_Zve64x": ("src/unpriv/zvbc.adoc", "zvbc depends upon the zve64x extension."),
    "Zvbc_sew64only": ("src/unpriv/zvbc.adoc", "The instructions in zvbc are only defined for SEW=64."),
    "vclmul_sewn64_rsv": ("src/unpriv/zvbc.adoc", "SEW is any value other than 64"),
    "vclmul_op": (
        "src/unpriv/zvbc.adoc",
        "Each 64-bit element in the _vs2_ vector register is carry-less multiplied by either each 64-bit element in _vs1_ (vector-vector), or the 64-bit value from integer register _rs1_ (vector-scalar). The result is the least significant 64 bits of the carry-less product.",
    ),
    "vclmulh_sewn64_rsv": ("src/unpriv/zvbc.adoc", "SEW is any value other than 64"),
    "vclmulh_op": (
        "src/unpriv/zvbc.adoc",
        "Each 64-bit element in the _vs2_ vector register is carry-less multiplied by either each 64-bit element in _vs1_ (vector-vector), or the 64-bit value from integer register _rs1_ (vector-scalar). The result is the most significant 64 bits of the carry-less product.",
    ),
    "Zvfh_instr": (
        "src/unpriv/zvfh.adoc",
        "When the zvfh extension is implemented, all instructions in <<sec-vector-float>>, <<sec-vector-float-reduce>>, <<sec-vector-float-reduce-widen>>, <<sec-vector-float-move>>, <<sec-vfslide1up>>, and <<sec-vfslide1down>> become defined when SEW=16.",
    ),
    "Zvfh_eew16": (
        "src/unpriv/zvfh.adoc",
        "The EEW=16 floating-point operands of these instructions use the binary16 format.",
    ),
    "Zvfh_instr_cvt": (
        "src/unpriv/zvfh.adoc",
        "Additionally, conversions between 8-bit integers and binary16 values are provided. The floating-point-to-integer narrowing conversions (vfncvt.x.f.w, vfncvt.xu.f.w, vfncvt.rtz.x.f.w, and vfncvt.rtz.xu.f.w) and integer-to-floating-point widening conversions (vfwcvt.f.x.v and vfwcvt.f.xu.v) become defined when SEW=8.",
    ),
    "Zvfh_dependent_Zve32f_Zfhmin": (
        "src/unpriv/zvfh.adoc",
        "The zvfh extension depends on the extlink:zve32f[] and extlink:zfhmin[] extensions.",
    ),
    "Zvfhmin_dependent_Zve32f": (
        "src/unpriv/zvfhmin.adoc",
        "The zvfhmin extension depends on the extlink:zve32f[] extension.",
    ),
    "Zvfbfmin_depends_Zve32f": ("src/unpriv/zvfbfmin.adoc", "This extension depends upon the zve32f extension."),
    "vfncvtbf16-f-f-w_enc": (
        "src/unpriv/zvfbfmin.adoc",
        "(encoding diagram) {bits: 7, name: '1010111', attr:['OP-V']}, {bits: 5, name: 'vd'}, {bits: 3, name: '001', attr:['OPFVV']}, {bits: 5, name: '11101', attr:['vfncvtbf16']}, {bits: 5, name: 'vs2'}, {bits: 1, name: 'vm'}, {bits: 6, name: '010010', attr:['VFUNARY0']},",
    ),
    "vfncvtbf16-f-f-w_sew_rsv": ("src/unpriv/zvfbfmin.adoc", "* `SEW` is any value other than 16"),
    "vfncvtbf16-f-f-w_op": (
        "src/unpriv/zvfbfmin.adoc",
        "Narrowing convert from FP32 to BF16. Round according to the _frm_ register.",
    ),
    "vfwcvtbf16-f-f-v_enc": (
        "src/unpriv/zvfbfmin.adoc",
        "(encoding diagram) {bits: 7, name: '1010111', attr:['OP-V']}, {bits: 5, name: 'vd'}, {bits: 3, name: '001', attr:['OPFVV']}, {bits: 5, name: '01101', attr:['vfwcvtbf16']}, {bits: 5, name: 'vs2'}, {bits: 1, name: 'vm'}, {bits: 6, name: '010010', attr:['VFUNARY0']},",
    ),
    "vfwcvtbf16-f-f-v_sew_rsv": ("src/unpriv/zvfbfmin.adoc", "* `SEW` is any value other than 16"),
    "vfwcvtbf16-f-f-v_op": ("src/unpriv/zvfbfmin.adoc", "Widening convert from BF16 to FP32. The conversion is exact."),
    "Zvfbfwma_depends": (
        "src/unpriv/zvfbfwma.adoc",
        "This extension depends upon the zvfbfmin and zfbfmin extensions.",
    ),
    "vfwmaccbf16_encoding_vv": (
        "src/unpriv/zvfbfwma.adoc",
        "(encoding diagram) {bits: 7, name: '1010111', attr:['OP-V']}, {bits: 5, name: 'vd'}, {bits: 3, name: '001', attr:['OPFVV']}, {bits: 5, name: 'vs1'}, {bits: 5, name: 'vs2'}, {bits: 1, name: 'vm'}, {bits: 6, name: '111011', attr:['vfwmaccbf16']},",
    ),
    "vfwmaccbf16_encoding_vf": (
        "src/unpriv/zvfbfwma.adoc",
        "(encoding diagram) {bits: 7, name: '1010111', attr:['OP-V']}, {bits: 5, name: 'vd'}, {bits: 3, name: '101', attr:['OPFVF']}, {bits: 5, name: 'rs1'}, {bits: 5, name: 'vs2'}, {bits: 1, name: 'vm'}, {bits: 6, name: '111011', attr:['vfwmaccbf16']},",
    ),
    "vfwmaccbf16_sew_rsv": ("src/unpriv/zvfbfwma.adoc", "* `SEW` is any value other than 16"),
    "vfwmaccbf16_op": (
        "src/unpriv/zvfbfwma.adoc",
        "This instruction performs a widening fused multiply-accumulate operation, where each pair of BF16 values are multiplied and their unrounded product is added to the corresponding FP32 accumulate value. The sum is rounded according to the _frm_ register.",
    ),
    "vfwmaccbf16-vv": (
        "src/unpriv/zvfbfwma.adoc",
        "In the vector-vector version, the BF16 elements are read from `vs1` and `vs2` and FP32 accumulate value is read from `vd`. The FP32 result is written to the destination register `vd`.",
    ),
    "vfwmaccbf16-vf": (
        "src/unpriv/zvfbfwma.adoc",
        "The vector-scalar version is similar, but instead of reading elements from `vs1`, a scalar BF16 value is read from the FPU register `rs1`.",
    ),
    "zvk_dataindep_timing": (
        "src/unpriv/zvk.adoc",
        "All instructions shall be implemented with data-independent timing. That is, the latency of the execution of these instructions shall not vary with different input values.",
    ),
    "veccrypto_eeweqsew": (
        "src/unpriv/zvk.adoc",
        "For all of the vector crypto instructions in this specification, EEW=SEW.",
    ),
    "veccrypto_vl_vstart_egsconstr": (
        "src/unpriv/zvk.adoc",
        "Since vl and vstart refer to elements, Vector Crypto instructions that use elements groups (See <<crypto-vector-element-groups>>) require that these values are an integer multiple of the Element Group Size (EGS).",
    ),
    "veccrypto_vl_vstart_rsv": (
        "src/unpriv/zvk.adoc",
        "Instructions that violate the vl or vstart requirements are _reserved_.",
    ),
    "veccrypto_lmul_egwconstr": (
        "src/unpriv/zvk.adoc",
        "For element-group instructions, LMUL{times}VLEN must always be at least as large as EGW, otherwise an _illegal-instruction exception_ is raised, even if vl=0.",
    ),
    "veccrypto_sew_rsv": (
        "src/unpriv/zvk.adoc",
        "Some Vector Crypto instructions are only defined for a specific SEW. In such a case all other SEW values are _reserved_.",
    ),
    "veccrypto_vsins_vs2": (
        "src/unpriv/zvk.adoc",
        "In the case of the insn:*.vs[] instructions defined in this specification, _vs2_ holds a 128-bit scalar element group.",
    ),
    "veccrypto_vsins_vdvs2overlap": (
        "src/unpriv/zvk.adoc",
        "For implementations with VLEN ≥ 128, _vs2_ refers to a single register. Thus, the _vd_ register group must not overlap the _vs2_ register. However, in implementations where VLEN < 128, _vs2_ refers to a register group comprised of the number of registers needed to hold the 128-bit scalar element group. In this case, the _vd_ register group must not overlap this _vs2_ register group.",
    ),
    "veccrypto_vsins_vd": (
        "src/unpriv/zvk.adoc",
        "they return _vector_ results to _vd_, which is also a source vector operand.",
    ),
    "veccrypto_vsins_vs2function": (
        "src/unpriv/zvk.adoc",
        "These instructions enable a single key, specified as a scalar element group in _vs2_, to be applied to each element group of register group _vd_.",
    ),
    "Zvknhb_Zvkn_Zvknc_Zvkng_Zvksc_depZve64x": (
        "src/unpriv/zvk.adoc",
        "The extlink:zvknhb[], extlink:zvkn[], extlink:zvknc[], extlink:zvkng[], and extlink:zvksc[] depend on zve64x.",
    ),
    "Zvkb_Zvkg_Zvkned_Zvknha_Zvksed_Zvksh_Zvks_Zvksc_Zvksg_Zvkt_depZve32x": (
        "src/unpriv/zvk.adoc",
        "All of the other Vector Crypto Extensions depend on zve32x.",
    ),
    "Zvknhb_impZvknha": ("src/unpriv/zvk.adoc", "zvknhb implies zvknha."),
    "veccrypto_indepZkt": (
        "src/unpriv/zvk.adoc",
        "It is important to note that the Vector Crypto instructions are independent of the implementation of the zkt extension and do not require that zkt is implemented.",
    ),
    "Zvkg_egw128b_elem32b": (
        "src/unpriv/zvk.adoc",
        "All of these instructions work on 128-bit element groups comprised of four 32-bit elements.",
    ),
    "Zvkg_dataindeptiming": (
        "src/unpriv/zvk.adoc",
        "To help avoid side-channel timing attacks, these instructions shall be implemented with data-independent timing.",
    ),
    "Zvkg_vl": (
        "src/unpriv/zvk.adoc",
        "The number of element groups to be processed is vl/EGS. vl must be set to the number of SEW=32 elements to be processed and therefore must be a multiple of EGS=4.",
    ),
    "Zvkg_vstart": ("src/unpriv/zvk.adoc", "Likewise, vstart must be a multiple of EGS=4."),
    "Zvkned_egw128b_elem32b": (
        "src/unpriv/zvk.adoc",
        "All of these instructions work on 128-bit element groups comprised of four 32-bit elements.",
    ),
    "Zvkned_dataindeptiming": (
        "src/unpriv/zvk.adoc",
        "To help avoid side-channel timing attacks, these instructions shall be implemented with data-independent timing.",
    ),
    "Zvkned_vl": (
        "src/unpriv/zvk.adoc",
        "The number of element groups to be processed is vl/EGS. vl must be set to the number of SEW=32 elements to be processed and therefore must be a multiple of EGS=4.",
    ),
    "Zvkned_vstart": ("src/unpriv/zvk.adoc", "Likewise, vstart must be a multiple of EGS=4."),
    "Zvknha_Zvknhb_sha256_egw128b_elem32b": (
        "src/unpriv/zvk.adoc",
        "SHA-256: these instructions work on 128-bit element groups comprised of four 32-bit elements.",
    ),
    "Zvknhb_sha512_egw256b_elem64b": (
        "src/unpriv/zvk.adoc",
        "SHA-512: these instructions work on 256-bit element groups comprised of four 64-bit elements.",
    ),
    "Zvknhb_sha256_sha512": ("src/unpriv/zvk.adoc", "zvknhb supports SHA-256 and SHA-512."),
    "Zvknha_sha256": ("src/unpriv/zvk.adoc", "zvknha supports only SHA-256."),
    "Zvknha_Zvknhb_dataindeptiming": (
        "src/unpriv/zvk.adoc",
        "To help avoid side-channel timing attacks, these instructions shall be implemented with data-independent timing.",
    ),
    "Zvknha_Zvknhb_vl": (
        "src/unpriv/zvk.adoc",
        "The number of element groups to be processed is vl/EGS. vl must be set to the number of SEW elements to be processed and therefore must be a multiple of EGS=4.",
    ),
    "Zvknha_Zvknhb_vstart": ("src/unpriv/zvk.adoc", "Likewise, vstart must be a multiple of EGS=4."),
    "Zvksed_egw128b_elem32b": (
        "src/unpriv/zvk.adoc",
        "All of these instructions work on 128-bit element groups comprised of four 32-bit elements.",
    ),
    "Zvksed_dataindeptiming": (
        "src/unpriv/zvk.adoc",
        "To help avoid side-channel timing attacks, these instructions shall be implemented with data-independent timing.",
    ),
    "Zvksed_vl": (
        "src/unpriv/zvk.adoc",
        "The number of element groups to be processed is vl/EGS. vl must be set to the number of SEW=32 elements to be processed and therefore must be a multiple of EGS=4.",
    ),
    "Zvksed_vstart": ("src/unpriv/zvk.adoc", "Likewise, vstart must be a multiple of EGS=4."),
    "Zvksh_egw256b_elem32b": (
        "src/unpriv/zvk.adoc",
        "All of these instructions work on 256-bit element groups comprised of eight 32-bit elements.",
    ),
    "Zvksh_dataindeptiming": (
        "src/unpriv/zvk.adoc",
        "To help avoid side-channel timing attacks, these instructions shall be implemented with data-independent timing.",
    ),
    "Zvksh_vl": (
        "src/unpriv/zvk.adoc",
        "The number of element groups to be processed is vl/EGS. vl must be set to the number of SEW=32 elements to be processed and therefore must be a multiple of EGS=8.",
    ),
    "Zvksh_vstart": ("src/unpriv/zvk.adoc", "Likewise, vstart must be a multiple of EGS=8."),
    "Zvkn_def": ("src/unpriv/zvk.adoc", "(table of included extensions)"),
    "Zvknc_def": ("src/unpriv/zvk.adoc", "(table of included extensions)"),
    "Zvkng_def": ("src/unpriv/zvk.adoc", "(table of included extensions)"),
    "Zvks_def": ("src/unpriv/zvk.adoc", "(table of included extensions)"),
    "Zvksc_def": ("src/unpriv/zvk.adoc", "(table of included extensions)"),
    "Zvksg_def": ("src/unpriv/zvk.adoc", "(table of included extensions)"),
    "Zvkt_req": (
        "src/unpriv/zvk.adoc",
        "The Zvkt extension requires all implemented instructions from the following list to be executed with data-independent execution latency as defined in the <<#crypto_scalar_instructions,RISC-V Scalar Cryptography Extensions specification>>.",
    ),
    "Zvkt_diel_def": (
        "src/unpriv/zvk.adoc",
        "Data-independent execution latency (DIEL) applies to all _data operands_ of an instruction, even those that are not a part of the body or that are inactive. However, DIEL does not apply to other values such as vl, vtype, and the mask (when used to control execution of a masked vector instruction).",
    ),
    "Zvkt_diel_constants_exempt": (
        "src/unpriv/zvk.adoc",
        "Also, DIEL does not apply to constant values specified in the instruction encoding such as the use of the zero register (`x0`), and, in the case of immediate forms of an instruction, the values in the immediate fields (i.e., _imm_ and _uimm_).",
    ),
    "Zvkt_diel_control_exempt": (
        "src/unpriv/zvk.adoc",
        "In some cases--which are explicitly specified in the lists below--operands that are used as control rather than data are exempt from DIEL.",
    ),
    "vaesdf_final": ("src/unpriv/zvk.adoc", "A final-round AES block cipher decryption is performed."),
    "vaesdf_ops": (
        "src/unpriv/zvk.adoc",
        "The InvShiftRows and InvSubBytes steps are applied to each round state element group from _vd_.",
    ),
    "vaesdf_xor_form": (
        "src/unpriv/zvk.adoc",
        "This is then XORed with the round key in either the corresponding element group in _vs2_ (vector-vector form) or scalar element group in _vs2_ (vector-scalar form).",
    ),
    "vaesdm_mid": ("src/unpriv/zvk.adoc", "A middle-round AES block cipher decryption is performed."),
    "vaesdm_ops": (
        "src/unpriv/zvk.adoc",
        "The InvShiftRows and InvSubBytes steps are applied to each round state element group from _vd_.",
    ),
    "vaesdm_xor_form": (
        "src/unpriv/zvk.adoc",
        "This is then XORed with the round key in either the corresponding element group in _vs2_ (vector-vector form) or the scalar element group in _vs2_ (vector-scalar form).",
    ),
    "vaesdm_invmix": ("src/unpriv/zvk.adoc", "InvMixColumns step."),
    "vaesef_final": ("src/unpriv/zvk.adoc", "A final-round encryption function of the AES block cipher is performed."),
    "vaesef_ops": (
        "src/unpriv/zvk.adoc",
        "The SubBytes and ShiftRows steps are applied to each round state element group from _vd_.",
    ),
    "vaesef_xor_form": (
        "src/unpriv/zvk.adoc",
        "This is then XORed with the round key in either the corresponding element group in _vs2_ (vector-vector form) or the scalar element group in _vs2_ (vector-scalar form).",
    ),
    "vaesem_mid": ("src/unpriv/zvk.adoc", "A middle-round encryption function of the AES block cipher is performed."),
    "vaesem_ops": (
        "src/unpriv/zvk.adoc",
        "The SubBytes, ShiftRows, and MixColumns steps are applied to each round state element group from _vd_.",
    ),
    "vaesem_xor_form": (
        "src/unpriv/zvk.adoc",
        "This is then XORed with the round key in either the corresponding element group in _vs2_ (vector-vector form) or the scalar element group in _vs2_ (vector-scalar form).",
    ),
    "vaeskf1_round": ("src/unpriv/zvk.adoc", "A single round of the forward AES-128 KeySchedule is performed."),
    "vaeskf1_wordgen": (
        "src/unpriv/zvk.adoc",
        "The next round key is generated word by word from the current round key element group in _vs2_ and the immediately previous word of the round key.",
    ),
    "vaeskf1_uimm_src": ("src/unpriv/zvk.adoc", "ranges from 1 to 10, comes from _uimm[3:0]_; _uimm[4]_ is ignored."),
    "vaeskf1_uimm_map": (
        "src/unpriv/zvk.adoc",
        "The out-of-range _uimm[3:0]_ values of 0 and 11{endash}15 are mapped to in-range values by inverting _uimm[3]_.",
    ),
    "vaeskf2_round": ("src/unpriv/zvk.adoc", "A single round of the forward AES-256 KeySchedule is performed."),
    "vaeskf2_wordgen": (
        "src/unpriv/zvk.adoc",
        "The next round key is generated word by word from the previous round key element group in _vd_ and the immediately previous word of the round key.",
    ),
    "vaeskf2_rcon_lsw": (
        "src/unpriv/zvk.adoc",
        "least significant word of the next round key is generated by applying a function to the most significant word of the current round key and then XORing the result with the round constant.",
    ),
    "vaeskf2_rcon_func": (
        "src/unpriv/zvk.adoc",
        "The round number is used to select the round constant as well as the function.",
    ),
    "vaeskf2_uimm_src": ("src/unpriv/zvk.adoc", "ranges from 2 to 14, comes from _uimm[3:0]_; _uimm[4]_ is ignored."),
    "vaeskf2_uimm_map": (
        "src/unpriv/zvk.adoc",
        "The out-of-range _uimm[3:0]_ values of 0{endash}1 and 15 are mapped to in-range values by inverting _uimm[3]_.",
    ),
    "vaesz_round0": ("src/unpriv/zvk.adoc", "A round-0 AES block cipher operation is performed."),
    "vaesz-vs_only": ("src/unpriv/zvk.adoc", "There is only a insn:*.vs[] form of the instruction."),
    "vaesz_vs2_rk": (
        "src/unpriv/zvk.adoc",
        "_vs2_ holds a scalar element group that is used as the round key for all of the round state element groups.",
    ),
    "vghsh-vv_sewn32_rsv": ("src/unpriv/zvk.adoc", "SEW is any value other than 32"),
    "vghsh-vv_op": (
        "src/unpriv/zvk.adoc",
        "This instruction treats all of the inputs and outputs as 128-bit polynomials and performs operations over GF[2]. It produces the next partial hash (Y~i+1~) by adding the current partial hash (Y~i~) to the cipher text block (X~i~) and then multiplying (over GF(2^128^)) this sum by the Hash Subkey (H).",
    ),
    "vghsh-vv_op_gf": (
        "src/unpriv/zvk.adoc",
        "The multiplication over GF(2^128^) is a carry-less multiply of two 128-bit polynomials modulo GHASH's irreducible polynomial (x^128^ + x^7^ + x^2^ + x + 1).",
    ),
    "vghsh-vv_op_coeff": (
        "src/unpriv/zvk.adoc",
        "The NIST specification (see extlink:zvkg[]) orders the coefficients from left to right x~0~x~1~x~2~...x~127~ for a polynomial x~0~ + x~1~u +x~2~ u^2^ + ... + x~127~u^127^. This can be viewed as a collection of byte elements in memory with the byte containing the lowest coefficients (i.e., 0,1,2,3,4,5,6,7) residing at the lowest memory address. Since the bits in the bytes are reversed, this instruction internally performs bit swaps within bytes to put the bits in the standard ordering (e.g., 7,6,5,4,3,2,1,0).",
    ),
    "vghsh-vv_exeindepdata": (
        "src/unpriv/zvk.adoc",
        "This instruction must always be implemented such that its execution latency does not depend on the data being operated upon.",
    ),
    "vgmul-vv_sewn32_rsv": ("src/unpriv/zvk.adoc", "SEW is any value other than 32"),
    "vgmul-vv_op": (
        "src/unpriv/zvk.adoc",
        "This instruction treats all of the inputs and outputs as 128-bit polynomials and performs operations over GF[2]. It produces the product over GF(2^128^) of the two 128-bit inputs.",
    ),
    "vgmul-vv_op_gf": (
        "src/unpriv/zvk.adoc",
        "The multiplication over GF(2^128^) is a carry-less multiply of two 128-bit polynomials modulo GHASH's irreducible polynomial (x^128^ + x^7^ + x^2^ + x + 1).",
    ),
    "vgmul-vv_op_coeff": (
        "src/unpriv/zvk.adoc",
        "The NIST specification (see extlink:zvkg[]) orders the coefficients from left to right x~0~x~1~x~2~...x~127~ for a polynomial x~0~ + x~1~u +x~2~ u^2^ + ... + x~127~u^127^. This can be viewed as a collection of byte elements in memory with the byte containing the lowest coefficients (i.e., 0,1,2,3,4,5,6,7) residing at the lowest memory address. Since the bits in the bytes are reversed, This instruction internally performs bit swaps within bytes to put the bits in the standard ordering (e.g., 7,6,5,4,3,2,1,0).",
    ),
    "vgmul-vv_exeindepdata": (
        "src/unpriv/zvk.adoc",
        "This instruction must always be implemented such that its execution latency does not depend on the data being operated upon.",
    ),
    "vsha2chl-vv_Zvknha_sewn32_rsv": ("src/unpriv/zvk.adoc", "zvknha: SEW is any value other than 32"),
    "vsha2chl-vv_Zvknhb_sewn32or64_rsv": ("src/unpriv/zvk.adoc", "zvknhb: SEW is any value other than 32 or 64"),
    "vsha2chl-vv_vdoverlapvs1vs2_rsv": (
        "src/unpriv/zvk.adoc",
        "The _vd_ register group overlaps with either _vs1_ or _vs2_",
    ),
    "vsha2chl-vv_op_sew32": (
        "src/unpriv/zvk.adoc",
        "SEW=32: 2 rounds of SHA-256 compression are performed (zvknha and zvknhb)",
    ),
    "vsha2chl-vv_op_sew64": ("src/unpriv/zvk.adoc", "SEW=64: 2 rounds of SHA-512 compression are performed (zvknhb)"),
    "vsha2chl-vv_op": (
        "src/unpriv/zvk.adoc",
        "Two words of _vs1_ are processed with the 8 words of current state held in _vd_ and _vs2_ to perform two rounds of hash computation producing four words of the next state.",
    ),
    "vsha2ms-vv_Zvknha_sewn32_rsv": ("src/unpriv/zvk.adoc", "zvknha: SEW is any value other than 32"),
    "vsha2ms-vv_Zvknhb_sewn32or64_rsv": ("src/unpriv/zvk.adoc", "zvknhb: SEW is any value other than 32 or 64"),
    "vsha2ms-vv_vdoverlapvs1vs2_rsv": (
        "src/unpriv/zvk.adoc",
        "The _vd_ register group overlaps with either _vs1_ or _vs2_",
    ),
    "vsha2ms-vv_op_sew32": (
        "src/unpriv/zvk.adoc",
        "SEW=32: Four rounds of SHA-256 message schedule expansion are performed (zvknha and zvknhb)",
    ),
    "vsha2ms-vv_op_sew64": (
        "src/unpriv/zvk.adoc",
        "SEW=64: Four rounds of SHA-512 message schedule expansion are performed (zvknhb)",
    ),
    "vsha2ms-vv_op": (
        "src/unpriv/zvk.adoc",
        "Eleven of the last 16 SEW-sized message-schedule words from _vd_ (oldest), _vs2_, and _vs1_ (most recent) are processed to produce the next 4 message-schedule words.",
    ),
    "vsm3c-vi_sewn32_rsv": ("src/unpriv/zvk.adoc", "SEW is any value other than 32"),
    "vsm3c-vi_vdoverlapvs2_rsv": (
        "src/unpriv/zvk.adoc",
        "The _vd_ register group overlaps with the _vs2_ register group",
    ),
    "vsm3c-vi_op": ("src/unpriv/zvk.adoc", "Two rounds of SM3 compression are performed."),
    "vsm3c-vi_op_sm3": (
        "src/unpriv/zvk.adoc",
        "The current state of eight 32-bit words is read in as an element group from _vd_. Eight 32-bit message words are read in as an element group from _vs2_, although only four of them are used. All of the 32-bit input words are byte-swapped from big endian to little endian. These inputs are processed somewhat differently based on the round group (as specified in _uimm_), and the next state is generated as an element group of eight 32-bit words. The next state of eight 32-bit words are generated, swapped from little endian to big endian, and are returned in an eight-element group.",
    ),
    "vsm3c-vi_op_rnd": (
        "src/unpriv/zvk.adoc",
        "The round number is provided by the 5-bit _uimm_ unsigned immediate. Legal values are 0{endash}31 and indicate which group of two rounds are being performed. For example, if _uimm_=1, then rounds 2 and 3 are being performed.",
    ),
    "vsm3me-vv_sewn32_rsv": ("src/unpriv/zvk.adoc", "SEW is any value other than 32"),
    "vsm3me-vv_vdoverlapvs2_rsv": (
        "src/unpriv/zvk.adoc",
        "The _vd_ register group overlaps with the _vs2_ register group.",
    ),
    "vsm3me-vv_op": ("src/unpriv/zvk.adoc", "Eight rounds of SM3 message expansion are performed."),
    "vsm3me-vv_op_sm3": (
        "src/unpriv/zvk.adoc",
        "The sixteen most recent 32-bit message words are read in as two eight-element groups from _vs1_ and _vs2_. Each of these words is swapped from big endian to little endian. The next eight 32-bit message words are generated, swapped from little endian to big endian, and are returned in an eight-element group.",
    ),
    "vsm4k-vi_sewn32_rsv": ("src/unpriv/zvk.adoc", "SEW is any value other than 32"),
    "vsm4k-vi_op": ("src/unpriv/zvk.adoc", "Four rounds of the SM4 Key Expansion are performed."),
    "vsm4k-vi_op_sm4k": (
        "src/unpriv/zvk.adoc",
        "Four round keys are read in as a 4-element group from _vs2_. Each of the next four round keys are generated by iteratively XORing the last three round keys with a constant that is indexed by the Round Group Number, performing a byte-wise substitution, and then performing XORs between rotated versions of this value and the corresponding current round key.",
    ),
    "vsm4k-vi_op_rnd": (
        "src/unpriv/zvk.adoc",
        "The Round group number comes from _uimm[2:0]_; the bits in _uimm[4:3]_ are ignored. Round group numbers range from 0 to 7 and indicate which group of four round keys are being generated. Round Keys range from 0{endash}31. For example, if _uimm_=1, then round keys 4, 5, 6, and 7 are being generated.",
    ),
    "vsm4r_sewn32_rsv": ("src/unpriv/zvk.adoc", "SEW is any value other than 32"),
    "vsm4r-vs_vdoverlapvs2_rsv": (
        "src/unpriv/zvk.adoc",
        "Only for the insn:*.vs[] form: the _vd_ register group overlaps the _vs2_ register",
    ),
    "vsm4r_op": ("src/unpriv/zvk.adoc", "Four rounds of SM4 Encryption/Decryption are performed."),
    "vsm4r_op_sm4encdec": (
        "src/unpriv/zvk.adoc",
        "The four words of current state are read as a 4-element group from _vd_ and the round keys are read from either the corresponding 4-element group in _vs2_ (vector-vector form) or the scalar element group in _vs2_ (vector-scalar form). The next four words of state are generated by iteratively XORing the last three words of the state with the corresponding round key, performing a byte-wise substitution, and then performing XORs between rotated versions of this value and the corresponding current state.",
    ),
}
