# SPDX-License-Identifier: Apache-2.0
"""Helpers for the rule-derived vector instruction tests (gen_Vinsn.py, tests_ai/V).

A VTest loads its vector operands from data tables (unit-stride loads), runs the instruction under test with a
chosen vtype/vl/vstart/vxrm/frm, stores the destination register group and compares each element with its legal
values. Only the first VLEN=128 bits of each register (the minimum VLEN of V, Zvl128b) hold loaded data, so the
expected values do not depend on VLEN. Rules whose outcome depends on VLMAX compute the expectation at run time.

The module also holds a small IEEE 754 reference (binary32/binary64) built on exact rational arithmetic.
"""

from __future__ import annotations

import hashlib
import math
import random
from fractions import Fraction as Fr
from typing import TYPE_CHECKING

from aigen import POOL_TRAP, TestFile, X, sext

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    # one value (an int or a per-XLEN X), up to three alternatives, or None (any value)
    Legal = int | X | list[int] | list[X] | list[int | X] | None

MARCH = "rv${XLEN}imafdv_zicsr_zifencei"
REQ = ["I", "V"]
VLEN_MIN = 128  # V requires Zvl128b


def ones(eew: int) -> int:
    return (1 << eew) - 1


def m(v: int, eew: int) -> int:
    return v & ones(eew)


def sx(v: int, eew: int) -> int:
    return sext(v, eew)


def lmul_val(lmul: str) -> Fr:
    return Fr(1, int(lmul[1:])) if lmul.startswith("f") else Fr(int(lmul))


def nfit(eew: int, emul: str) -> int:
    """Elements of width eew that fit in the first 128 bits of each register of an emul group."""
    return int(VLEN_MIN * lmul_val(emul) / eew)


def fit_emul(n: int, eew: int, emul: str) -> str:
    """emul, raised (to at most 8) until n elements of eew fit at VLEN = 128."""
    if n <= nfit(eew, emul):
        return emul
    k = 1
    while n * eew > 128 * k:
        k *= 2
    assert k <= 8, f"{n} elements of e{eew} exceed a VLEN=128 m8 group"
    return str(k)


def pol(
    old: Sequence[int],
    new: Sequence[Legal],
    vl: int,
    eew: int,
    *,
    mask: Sequence[int] | None = None,
    vstart: int = 0,
    ta: bool = False,
    ma: bool = False,
) -> list[Legal]:
    """Legal values of each destination element (vector-common.adoc, prestart/body/tail and vta/vma):
    prestart elements keep their old value; active elements take new[i]; inactive and tail elements keep their old
    value, or with vma/vta may also become all ones."""
    out: list[Legal] = []
    for i, o in enumerate(old):
        o = m(o, eew)
        if i < vstart:
            out.append(o)
        elif i < vl:
            if mask is None or mask[i]:
                out.append(new[i])
            else:
                out.append(sorted({o, ones(eew)}) if ma else o)
        else:
            out.append(sorted({o, ones(eew)}) if ta else o)
    return out


def mpol(
    old: Sequence[int],
    new: Sequence[int | None],
    vl: int,
    *,
    mask: Sequence[int] | None = None,
    vstart: int = 0,
    ma: bool = False,
    tailcalc: Sequence[int | None] | None = None,
) -> list[int | None]:
    """Legal bit of each element of a mask destination: 0, 1 or None (either). Mask destination tails are always
    agnostic and may also hold the value computed with vl = VLMAX (tailcalc[i], when the generator knows it)."""
    out: list[int | None] = []
    for i, o in enumerate(old):
        if i < vstart:
            out.append(o)
        elif i < vl:
            if mask is None or mask[i]:
                out.append(new[i])
            else:
                out.append(None if ma and o == 0 else o)
        else:
            calc = tailcalc[i] if tailcalc is not None else None
            # legal: old, 1, calc
            if o == 1 and calc == 1:
                out.append(1)
            else:
                out.append(None)
    return out


class VTest(TestFile):
    """TestFile with vector operand tables. x1 is the library's scratch register; x6-x9 carry operands and results."""

    RES = "vinsn_res"

    def __init__(self, *a: object, **kw: object) -> None:
        kw.setdefault("march", MARCH)
        kw.setdefault("pool", POOL_TRAP)
        super().__init__(*a, **kw)  # type: ignore[arg-type]
        # seed from the rule alone, so a mutant's tests differ from the originals only where the mutant changes them
        self.rng = random.Random(int(hashlib.sha256(f"V/{self.rule}{self.suffix}".encode()).hexdigest()[:16], 16))
        self._nd = 0
        self.extra_data += ["  .p2align 4", f"{self.RES}:", "  .zero 1024"]

    # ---------------------------------------------------------------- data
    def data(self, eew: int, values: Sequence[int]) -> str:
        self._nd += 1
        lab = f"vinsn_d{self._nd}"
        d = {8: ".byte", 16: ".half", 32: ".word", 64: ".dword"}[eew]
        self.extra_data += ["  .p2align 4", f"{lab}:"]
        vals = [m(v, eew) for v in values] or [0]
        for i in range(0, len(vals), 8):
            self.extra_data.append(f"  {d} " + ", ".join(hex(v) for v in vals[i : i + 8]))
        return lab

    # ---------------------------------------------------------------- vtype
    def vset(
        self, vl: int | str, sew: int, lmul: str = "1", ta: bool = False, ma: bool = False, rd: str = "x0"
    ) -> None:
        """vl: an int (vsetivli when < 32), "max" (VLMAX, vsetvli rd, x0 with rd x1 unless given) or a register."""
        pol_ = f"e{sew}, m{lmul}, {'ta' if ta else 'tu'}, {'ma' if ma else 'mu'}"
        if vl == "max":
            self.emit(f"vsetvli {'x1' if rd == 'x0' else rd}, x0, {pol_}")
        elif isinstance(vl, str):
            self.emit(f"vsetvli {rd}, {vl}, {pol_}")
        elif vl < 32:
            self.emit(f"vsetivli {rd}, {vl}, {pol_}")
        else:
            self.li("x1", vl)
            self.emit(f"vsetvli {rd}, x1, {pol_}")

    # ---------------------------------------------------------------- loads and stores
    def vload(self, vreg: str, eew: int, values: Sequence[int], emul: str = "1") -> None:
        n = len(values)
        emul = fit_emul(n, eew, emul)
        lab = self.data(eew, values)
        self.vset(n, eew, emul)
        self.la("x1", lab)
        self.emit(f"vle{eew}.v {vreg}, (x1)")

    def mload(self, vreg: str, bits: Sequence[int]) -> None:
        """Load a mask register: bits[i] is element i (the first 128 elements at most)."""
        nbytes = (len(bits) + 7) // 8
        by = [sum(bits[8 * j + k] << k for k in range(8) if 8 * j + k < len(bits)) for j in range(nbytes)]
        self.vload(vreg, 8, by)

    def fload(self, freg: str, bits: int, width: int) -> None:
        """Load an f register from memory: flw NaN-boxes a 32-bit value; fld loads 64 raw bits."""
        lab = self.data(width, [bits])
        self.la("x1", lab)
        self.emit(f"{'flw' if width == 32 else 'fld'} {freg}, 0(x1)")

    def vstore(self, vreg: str, eew: int, n: int, emul: str = "1") -> None:
        self.vset(n, eew, fit_emul(n, eew, emul))
        self.la("x1", self.RES)
        self.emit(f"vse{eew}.v {vreg}, (x1)")

    def check_elems(
        self, eew: int, legal: Sequence[Legal], lab: str, desc: str, reg: str = "x8", base: int = 0
    ) -> None:
        """Check the stored elements at RES (+base bytes) against their legal values (None: not checked). A legal
        value is an int, an X (per-XLEN value) or a list of up to three of those."""
        self.la("x1", self.RES)
        for i, lv in enumerate(legal):
            if lv is None:
                continue
            alts = [a if isinstance(a, X) else X(a, a) for a in (lv if isinstance(lv, list) else [lv])]
            per = {x: sorted({m(a.num(x), eew) for a in alts}) for x in (32, 64)}
            off = base + i * eew // 8
            d = f"{desc}: element {i}"
            if eew == 64:
                with self.rv64_only():
                    self.emit(f"ld {reg}, {off}(x1)")
                    self.check(reg, [X(0, a) for a in per[64]], lab, d)
                with self.rv32_only():
                    if len(per[32]) == 1:
                        for half in (0, 1):
                            hv = (per[32][0] >> (32 * half)) & 0xFFFFFFFF
                            self.emit(f"lw {reg}, {off + 4 * half}(x1)")
                            self.check(reg, X(hv, 0), lab, f"{d} ({'low' if half == 0 else 'high'} word)")
                    else:
                        # both words must match the same alternative: x5 = OR over alternatives of (lo == a.lo && hi == a.hi)
                        self.emit(f"lw {reg}, {off}(x1)")
                        self.emit(f"lw x9, {off + 4}(x1)")
                        self.emit("li x5, 0")
                        for a in per[32]:
                            self.load("x6", X(a & 0xFFFFFFFF, 0))
                            self.load("x7", X(a >> 32, 0))
                            self.emit(f"xor x6, x6, {reg}")
                            self.emit("xor x7, x7, x9")
                            self.emit("or x6, x6, x7")
                            self.emit("seqz x6, x6")
                            self.emit("or x5, x5, x6")
                        self.emit("mv x9, x5")
                        alts_s = " or ".join(f"0x{a:016x}" for a in per[32])
                        self.check_bool("x9", lab, f"{d}: 64-bit element is one of {alts_s}")
            else:
                ld = {8: "lbu", 16: "lhu", 32: "lw"}[eew]
                cv = {x: [sx(a, 32) if eew == 32 else a for a in per[x]] for x in (32, 64)}
                if len(cv[32]) == len(cv[64]):
                    exp = [X(p, q) for p, q in zip(cv[32], cv[64])]
                    self.emit(f"{ld} {reg}, {off}(x1)")
                    self.check(reg, exp, lab, d)
                else:
                    for x, cond in ((64, self.rv64_only), (32, self.rv32_only)):
                        with cond():
                            self.emit(f"{ld} {reg}, {off}(x1)")
                            self.check(reg, [X(v, v) for v in cv[x]], lab, d)

    def check_mask(self, vreg: str, bits: Sequence[int | None], lab: str, desc: str, reg: str = "x8") -> None:
        """Store mask register vreg and check each bit that is not None."""
        n = len(bits)
        nw = (n + 31) // 32
        self.vstore(vreg, 8, 4 * nw)
        self.la("x1", self.RES)
        for w in range(nw):
            fixed = val = 0
            for k in range(32):
                i = 32 * w + k
                b = bits[i] if i < n else None
                if b is not None:
                    fixed |= 1 << k
                    val |= b << k
            if not fixed:
                continue
            self.emit(f"lw {reg}, {4 * w}(x1)")
            self.check_masked(reg, fixed, val, lab, f"{desc}: mask bits {32 * w}..{32 * w + 31} under 0x{fixed:08x}")

    def check_vreg(self, vreg: str, eew: int, legal: Sequence[Legal], lab: str, desc: str, emul: str = "1") -> None:
        if eew == 1:
            self.check_mask(vreg, legal, lab, desc)  # type: ignore[arg-type]
            return
        self.vstore(vreg, eew, len(legal), emul)
        self.check_elems(eew, legal, lab, desc)

    def check_freg(self, freg: str, width: int, legal: Legal, lab: str, desc: str) -> None:
        self.la("x1", self.RES)
        self.emit(f"{'fsw' if width == 32 else 'fsd'} {freg}, 0(x1)")
        self.check_elems(width, [legal], lab, desc)

    # ---------------------------------------------------------------- CSRs
    def set_vxrm(self, k: int) -> None:
        self.emit(f"csrwi vxrm, {k}")

    def clear_vxsat(self) -> None:
        self.emit("csrwi vxsat, 0")

    def check_vxsat(self, expect: int | list[int], lab: str, desc: str, reg: str = "x9") -> None:
        self.emit(f"csrr {reg}, vxsat")
        self.check(reg, expect if isinstance(expect, list) else [expect], lab, f"{desc}: vxsat")

    def set_frm(self, k: int) -> None:
        self.emit(f"fsrmi x0, {k}")

    def clear_fflags(self) -> None:
        self.emit("fsflagsi x0, 0")

    def check_fflags(self, expect: int | list[int], lab: str, desc: str, reg: str = "x9") -> None:
        self.emit(f"frflags {reg}")
        self.check(reg, expect if isinstance(expect, list) else [expect], lab, f"{desc}: fflags")

    def set_vstart(self, k: int | str) -> None:
        if isinstance(k, str):
            self.emit(f"csrw vstart, {k}")
        else:
            self.emit(f"csrwi vstart, {k}")

    # ---------------------------------------------------------------- one instruction
    def op(
        self,
        asm: str,
        *,
        sew: int,
        lmul: str | None = None,
        vl: int | str,
        ta: bool = False,
        ma: bool = False,
        srcs: dict[str, tuple[int, str, Sequence[int]]] | None = None,
        mask: Sequence[int] | None = None,
        xs: Mapping[str, int | X] | None = None,
        fs: dict[str, tuple[int, int]] | None = None,
        vstart: int = 0,
        vxrm: int | None = None,
        frm: int | None = None,
        clear_flags: bool = False,
    ) -> str:
        """Load operands (srcs: vreg -> (eew, emul, values); eew 1 = mask bits), set vtype and the CSRs, run asm,
        and return its label. A mask (v0) is loaded first, so srcs may overwrite v0."""
        if mask is not None:
            self.mload("v0", mask)
        for vr, (eew, emul, vals) in (srcs or {}).items():
            if eew == 1:
                self.mload(vr, vals)
            else:
                self.vload(vr, eew, vals, emul)
        for r, v in (xs or {}).items():
            self.load(r, v)
        for fr, (bits, w) in (fs or {}).items():
            self.fload(fr, bits, w)
        if vxrm is not None:
            self.set_vxrm(vxrm)
        if frm is not None:
            self.set_frm(frm)
        if clear_flags or vxrm is not None:
            self.clear_vxsat()
        if clear_flags or frm is not None:
            self.clear_fflags()
        if lmul is None:
            lmul = fit_emul(vl if isinstance(vl, int) else 1, sew, "1")
        assert not isinstance(vl, int) or vl <= nfit(sew, lmul), (
            f"{self.rule}: vl={vl} > VLMAX at VLEN=128 (e{sew} m{lmul})"
        )
        self.vset(vl, sew, lmul, ta, ma)
        if vstart:
            self.set_vstart(vstart)
        lab = self.label("insn")
        self.emit(f"{lab}:", 0)
        self.emit(asm)
        return lab

    # ---------------------------------------------------------------- trap windows
    def ill_window(self, lines: list[str], expect: object, desc: str, check_tval: bool = True) -> str:
        """Run lines (the first may trap) in the current mode and check the outcome. On a trap, xtval must be 0 or the
        instruction bits (read back from the code). No origin check: the lowest mode is U, S or M depending on the
        hart."""
        lab = self.label("win")
        self.allow(1)
        self.emit(f"{lab}:", 0)
        for ln in lines:
            self.emit(ln)
        self.outcome(expect, lab, desc, None, epc=True)  # type: ignore[arg-type]
        alts = expect if isinstance(expect, list) else [expect]
        if check_tval and "ok" not in alts:
            self.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
            self.la("x1", lab)
            self.emit("lw x6, 0(x1)")
            with self.rv64_only():
                self.emit("slli x6, x6, 32")
                self.emit("srli x6, x6, 32")
            self.emit("sub x7, x15, x6")
            self.emit("seqz x7, x7")
            self.emit("seqz x6, x15")
            self.emit("or x7, x7, x6")
            self.check_bool("x7", lab, f"{desc}: xtval is 0 or the instruction bits")
        return lab


# ==================================================================== fixed point (vxrm)
def roundoff(v: int, d: int, rm: int) -> int:
    """vector-common.adoc vxrm_op: (v >> d) + r, on an infinitely precise integer v."""
    if d == 0:
        return v
    bit = lambda k: (v >> k) & 1
    low = v & ((1 << (d - 1)) - 1) if d >= 2 else 0
    if rm == 0:
        r = bit(d - 1)
    elif rm == 1:
        r = bit(d - 1) & int(low != 0 or bit(d) == 1)
    elif rm == 2:
        r = 0
    else:
        r = int(not bit(d)) & int((v & ((1 << d) - 1)) != 0)
    return (v >> d) + r


# ==================================================================== IEEE 754
NV, DZ, OF, UF, NX = 16, 8, 4, 2, 1
RNE, RTZ, RDN, RUP, RMM = 0, 1, 2, 3, 4
FMT = {16: (5, 10), 32: (8, 23), 64: (11, 52)}
CNAN = {16: 0x7E00, 32: 0x7FC00000, 64: 0x7FF8000000000000}


def fparams(w: int) -> tuple[int, int, int, int]:
    e, f = FMT[w]
    bias = (1 << (e - 1)) - 1
    return e, f, bias, 1 - bias


def fpinf(w: int, neg: bool = False) -> int:
    e, f, _, _ = fparams(w)
    return (int(neg) << (w - 1)) | (ones(e) << f)


def fpmax(w: int, neg: bool = False) -> int:
    return fpinf(w, neg) - 1


def fpzero(w: int, neg: bool = False) -> int:
    return int(neg) << (w - 1)


def snan(w: int) -> int:
    e, f, _, _ = fparams(w)
    return (ones(e) << f) | 1


def qnan(w: int, payload: int = 1) -> int:
    e, f, _, _ = fparams(w)
    return (ones(e) << f) | (1 << (f - 1)) | payload


def isnan(b: int, w: int) -> bool:
    e, f, _, _ = fparams(w)
    return (b >> f) & ones(e) == ones(e) and b & ones(f) != 0


def issnan(b: int, w: int) -> bool:
    _, f, _, _ = fparams(w)
    return isnan(b, w) and not (b >> (f - 1)) & 1


def isinf(b: int, w: int) -> bool:
    e, f, _, _ = fparams(w)
    return (b >> f) & ones(e) == ones(e) and b & ones(f) == 0


def sign(b: int, w: int) -> bool:
    return bool((b >> (w - 1)) & 1)


def val(b: int, w: int) -> Fr:
    """Exact value of a finite encoding."""
    e, f, bias, emin = fparams(w)
    ex = (b >> f) & ones(e)
    mant = b & ones(f)
    v = Fr(mant, 1 << f) * Fr(2) ** emin if ex == 0 else (1 + Fr(mant, 1 << f)) * Fr(2) ** (ex - bias)
    return -v if sign(b, w) else v


def _log2floor(a: Fr) -> int:
    k = a.numerator.bit_length() - a.denominator.bit_length()
    while Fr(2) ** k > a:
        k -= 1
    while Fr(2) ** (k + 1) <= a:
        k += 1
    return k


def _rnd_int(q: Fr, neg: bool, rm: int, sticky: bool = False) -> tuple[int, bool]:
    """Round the non-negative rational q to an integer (sign neg gives the direction); returns (n, inexact)."""
    n = q.numerator // q.denominator
    rem = q - n
    inexact = rem != 0 or sticky
    if not inexact:
        return n, False
    if rm == RNE:
        up = rem > Fr(1, 2) or (rem == Fr(1, 2) and not sticky and n & 1) or (rem == Fr(1, 2) and sticky)
    elif rm == RMM:
        up = rem >= Fr(1, 2)
    elif rm == RTZ:
        up = False
    elif rm == RDN:
        up = neg
    else:  # RUP
        up = not neg
    return n + int(up), True


def fround(x: Fr, w: int, rm: int, zero_neg: bool = False, sticky: bool = False) -> tuple[int, int]:
    """Round the exact value x to format w; (bits, flags). Tininess is detected after rounding (RISC-V).
    sticky marks a value just above |x| (an irrational result)."""
    _e, f, bias, emin = fparams(w)
    emax = bias
    if x == 0 and not sticky:
        return fpzero(w, zero_neg), 0
    neg = x < 0
    a = -x if neg else x
    k = _log2floor(a) if a else emin - f - 2
    # unbounded-exponent rounding, for tininess
    qu = a / Fr(2) ** (k - f)
    nu, _ = _rnd_int(qu, neg, rm, sticky)
    unb = nu * Fr(2) ** (k - f)
    tiny = unb < Fr(2) ** emin
    kk = max(k, emin)
    q = a / Fr(2) ** (kk - f)
    n, inexact = _rnd_int(q, neg, rm, sticky)
    r = n * Fr(2) ** (kk - f)
    flags = NX if inexact else 0
    if tiny and inexact:
        flags |= UF
    if r >= Fr(2) ** (emax + 1):
        flags |= OF | NX
        to_inf = rm in (RNE, RMM) or (rm == RUP and not neg) or (rm == RDN and neg)
        return (fpinf(w, neg) if to_inf else fpmax(w, neg)), flags
    if r == 0:
        return fpzero(w, neg), flags
    if r < Fr(2) ** emin:
        return (int(neg) << (w - 1)) | int(r / Fr(2) ** (emin - f)), flags
    k2 = _log2floor(r)
    mant = int(r / Fr(2) ** (k2 - f)) - (1 << f)
    return (int(neg) << (w - 1)) | ((k2 + bias) << f) | mant, flags


def fenc(x: float | Fr, w: int) -> int:
    """Encode an exactly representable value."""
    b, fl = fround(Fr(x), w, RNE, zero_neg=isinstance(x, float) and math.copysign(1, x) < 0)
    assert fl == 0, f"{x} is not exact in binary{w}"
    return b


def _nan_in(w: int, *bs: int) -> tuple[int, int] | None:
    if any(isnan(b, w) for b in bs):
        return CNAN[w], NV if any(issnan(b, w) for b in bs) else 0
    return None


def fadd(a: int, b: int, w: int, rm: int, sub: bool = False) -> tuple[int, int]:
    if sub:
        b ^= 1 << (w - 1)
    n = _nan_in(w, a, b)
    if n:
        return n
    if isinf(a, w) or isinf(b, w):
        if isinf(a, w) and isinf(b, w) and sign(a, w) != sign(b, w):
            return CNAN[w], NV
        return (a if isinf(a, w) else b), 0
    x = val(a, w) + val(b, w)
    if x == 0:
        if val(a, w) == 0 and val(b, w) == 0 and sign(a, w) == sign(b, w):
            return fpzero(w, sign(a, w)), 0
        return fpzero(w, rm == RDN), 0
    return fround(x, w, rm)


def fmul(a: int, b: int, w: int, rm: int) -> tuple[int, int]:
    n = _nan_in(w, a, b)
    if n:
        return n
    s = sign(a, w) != sign(b, w)
    if isinf(a, w) or isinf(b, w):
        if (not isinf(a, w) and val(a, w) == 0) or (not isinf(b, w) and val(b, w) == 0):
            return CNAN[w], NV
        return fpinf(w, s), 0
    return fround(val(a, w) * val(b, w), w, rm, zero_neg=s)


def fma(a: int, b: int, c: int, w: int, rm: int, neg_prod: bool = False, neg_c: bool = False) -> tuple[int, int]:
    """(+/-)(a*b) + (+/-)c, fused (RISC-V: 0*inf + qNaN raises NV)."""
    sb = 1 << (w - 1)
    if neg_prod:
        a ^= sb
    if neg_c:
        c ^= sb
    zinf = (isinf(a, w) and not isnan(b, w) and not isinf(b, w) and val(b, w) == 0) or (
        isinf(b, w) and not isnan(a, w) and not isinf(a, w) and val(a, w) == 0
    )
    if zinf:
        return CNAN[w], NV
    n = _nan_in(w, a, b, c)
    if n:
        return n
    ps = sign(a, w) != sign(b, w)
    if isinf(a, w) or isinf(b, w):
        if isinf(c, w) and sign(c, w) != ps:
            return CNAN[w], NV
        return fpinf(w, ps), 0
    if isinf(c, w):
        return c, 0
    p = val(a, w) * val(b, w)
    x = p + val(c, w)
    if x == 0:
        if p == 0 and val(c, w) == 0 and ps == sign(c, w):
            return fpzero(w, ps), 0
        return fpzero(w, rm == RDN), 0
    return fround(x, w, rm)


def fdiv(a: int, b: int, w: int, rm: int) -> tuple[int, int]:
    n = _nan_in(w, a, b)
    if n:
        return n
    s = sign(a, w) != sign(b, w)
    if isinf(a, w):
        return (CNAN[w], NV) if isinf(b, w) else (fpinf(w, s), 0)
    if isinf(b, w):
        return fpzero(w, s), 0
    if val(b, w) == 0:
        return (CNAN[w], NV) if val(a, w) == 0 else (fpinf(w, s), DZ)
    return fround(val(a, w) / val(b, w), w, rm, zero_neg=s)


def fsqrt(a: int, w: int, rm: int) -> tuple[int, int]:
    n = _nan_in(w, a)
    if n:
        return n
    if not isinf(a, w) and val(a, w) == 0:
        return a, 0
    if sign(a, w):
        return CNAN[w], NV
    if isinf(a, w):
        return a, 0
    x = val(a, w)
    s = 300
    num = x.numerator * (1 << (2 * s)) * x.denominator
    r = math.isqrt(num)
    exact = r * r == num
    return fround(Fr(r, (1 << s) * x.denominator), w, rm, sticky=not exact)


def fcmp(a: int, b: int, w: int, op: str) -> tuple[int, int]:
    """eq/ne quiet (NV on sNaN only); lt/le/gt/ge signaling (NV on any NaN)."""
    if isnan(a, w) or isnan(b, w):
        fl = (NV if issnan(a, w) or issnan(b, w) else 0) if op in ("eq", "ne") else NV
        return int(op == "ne"), fl
    x = val(a, w) if not isinf(a, w) else (Fr(-1) if sign(a, w) else Fr(1)) * Fr(10) ** 400
    y = val(b, w) if not isinf(b, w) else (Fr(-1) if sign(b, w) else Fr(1)) * Fr(10) ** 400
    r = {"eq": x == y, "ne": x != y, "lt": x < y, "le": x <= y, "gt": x > y, "ge": x >= y}[op]
    return int(r), 0


def fminmax(a: int, b: int, w: int, is_max: bool) -> tuple[int, int]:
    """IEEE 754-2019 minimumNumber/maximumNumber (RISC-V fmin/fmax): -0 < +0."""
    fl = NV if issnan(a, w) or issnan(b, w) else 0
    if isnan(a, w) and isnan(b, w):
        return CNAN[w], fl
    if isnan(a, w):
        return b, fl
    if isnan(b, w):
        return a, fl

    def key(x: int) -> tuple:
        if isinf(x, w):
            return (1 if not sign(x, w) else -1, 0, 0)
        return (0, val(x, w), 0 if sign(x, w) else 1)

    return (max(a, b, key=key) if is_max else min(a, b, key=key)), fl


def fclass(b: int, w: int) -> int:
    e, f, _, _ = fparams(w)
    ex = (b >> f) & ones(e)
    mant = b & ones(f)
    s = sign(b, w)
    if isnan(b, w):
        return 1 << 8 if issnan(b, w) else 1 << 9
    if isinf(b, w):
        return 1 << 0 if s else 1 << 7
    if ex == 0 and mant == 0:
        return 1 << 3 if s else 1 << 4
    if ex == 0:
        return 1 << 2 if s else 1 << 5
    return 1 << 1 if s else 1 << 6


def f2i(a: int, w: int, n: int, signed: bool, rm: int) -> tuple[int, int]:
    """Float to n-bit integer (scalar fcvt rules): NaN -> max, saturate with NV, NX when inexact."""
    lo, hi = (-(1 << (n - 1)), (1 << (n - 1)) - 1) if signed else (0, (1 << n) - 1)
    if isnan(a, w):
        return m(hi, n), NV
    if isinf(a, w):
        return m(lo if sign(a, w) else hi, n), NV
    x = val(a, w)
    neg = x < 0
    r, inexact = _rnd_int(-x if neg else x, neg, rm)
    r = -r if neg else r
    if r < lo or r > hi:
        return m(lo if neg else hi, n), NV
    return m(r, n), NX if inexact else 0


def i2f(v: int, n: int, signed: bool, w: int, rm: int) -> tuple[int, int]:
    x = sx(v, n) if signed else m(v, n)
    return fround(Fr(x), w, rm)


def fcvt_ff(a: int, wi: int, wo: int, rm: int, rod: bool = False) -> tuple[int, int]:
    """Convert between float formats; rod: round to odd (overflow gives the largest finite value)."""
    if isnan(a, wi):
        return CNAN[wo], NV if issnan(a, wi) else 0
    if isinf(a, wi):
        return fpinf(wo, sign(a, wi)), 0
    x = val(a, wi)
    if x == 0:
        return fpzero(wo, sign(a, wi)), 0
    if not rod:
        return fround(x, wo, rm)
    b, fl = fround(x, wo, RTZ)
    if fl & NX and not fl & OF:
        b |= 1  # round to odd: jam the inexact bit into the LSB
    return b, fl


def frec7(a: int, w: int, rm: int, table: Sequence[int]) -> tuple[int, int]:
    """vfrec7.v (vector-common.adoc: exception table, vfrec7_op_precise/subnorm/output)."""
    e, f, bias, _ = fparams(w)
    s = sign(a, w)
    if isnan(a, w):
        return CNAN[w], NV if issnan(a, w) else 0
    if isinf(a, w):
        return fpzero(w, s), 0
    ex = (a >> f) & ones(e)
    sig = a & ones(f)
    if ex == 0 and sig == 0:
        return fpinf(w, s), DZ
    if ex == 0:  # subnormal: normalize
        lz = f - sig.bit_length()  # leading zeros in the f-bit significand
        nexp = -lz
        nsig = (sig << (1 - nexp)) & ones(f)
    else:
        nexp, nsig = ex, sig
    oexp = 2 * bias - 1 - nexp
    if oexp < -1 or oexp > 2 * bias:
        to_inf = rm in (RNE, RMM) or (rm == RUP and not s) or (rm == RDN and s)
        return (fpinf(w, s) if to_inf else fpmax(w, s)), OF | NX
    osig = table[nsig >> (f - 7)] << (f - 7)
    if oexp in (0, -1):
        osig = ((1 << f) | osig) >> (1 - oexp)
        oexp = 0
    return (int(s) << (w - 1)) | (oexp << f) | osig, 0


def frsqrt7(a: int, w: int, table: Sequence[int]) -> tuple[int, int]:
    e, f, bias, _ = fparams(w)
    s = sign(a, w)
    if isnan(a, w):
        return CNAN[w], NV if issnan(a, w) else 0
    ex = (a >> f) & ones(e)
    sig = a & ones(f)
    if ex == 0 and sig == 0:
        return fpinf(w, s), DZ
    if s:
        return CNAN[w], NV
    if isinf(a, w):
        return fpzero(w), 0
    if ex == 0:
        lz = f - sig.bit_length()
        nexp = -lz
        nsig = (sig << (1 - nexp)) & ones(f)
    else:
        nexp, nsig = ex, sig
    oexp = (3 * bias - 1 - nexp) // 2
    idx = ((nexp & 1) << 6) | (nsig >> (f - 6))
    osig = table[idx] << (f - 7)
    return (oexp << f) | osig, 0


# Lookup tables from vector-common.adoc (images/wavedrom/vfrsqrt7.edn, vfrec7.edn): index -> 7 output MSBs
RSQRT7 = [
    52,
    51,
    50,
    48,
    47,
    46,
    44,
    43,
    42,
    41,
    40,
    39,
    38,
    36,
    35,
    34,
    33,
    32,
    31,
    30,
    30,
    29,
    28,
    27,
    26,
    25,
    24,
    23,
    23,
    22,
    21,
    20,
    19,
    19,
    18,
    17,
    16,
    16,
    15,
    14,
    14,
    13,
    12,
    12,
    11,
    10,
    10,
    9,
    9,
    8,
    7,
    7,
    6,
    6,
    5,
    4,
    4,
    3,
    3,
    2,
    2,
    1,
    1,
    0,
    127,
    125,
    123,
    121,
    119,
    118,
    116,
    114,
    113,
    111,
    109,
    108,
    106,
    105,
    103,
    102,
    100,
    99,
    97,
    96,
    95,
    93,
    92,
    91,
    90,
    88,
    87,
    86,
    85,
    84,
    83,
    82,
    80,
    79,
    78,
    77,
    76,
    75,
    74,
    73,
    72,
    71,
    70,
    70,
    69,
    68,
    67,
    66,
    65,
    64,
    63,
    63,
    62,
    61,
    60,
    59,
    59,
    58,
    57,
    56,
    56,
    55,
    54,
    53,
]
REC7 = [
    127,
    125,
    123,
    121,
    119,
    117,
    116,
    114,
    112,
    110,
    109,
    107,
    105,
    104,
    102,
    100,
    99,
    97,
    96,
    94,
    93,
    91,
    90,
    88,
    87,
    85,
    84,
    83,
    81,
    80,
    79,
    77,
    76,
    75,
    74,
    72,
    71,
    70,
    69,
    68,
    66,
    65,
    64,
    63,
    62,
    61,
    60,
    59,
    58,
    57,
    56,
    55,
    54,
    53,
    52,
    51,
    50,
    49,
    48,
    47,
    46,
    45,
    44,
    43,
    42,
    41,
    40,
    40,
    39,
    38,
    37,
    36,
    35,
    35,
    34,
    33,
    32,
    31,
    31,
    30,
    29,
    28,
    28,
    27,
    26,
    25,
    25,
    24,
    23,
    23,
    22,
    21,
    21,
    20,
    19,
    19,
    18,
    17,
    17,
    16,
    15,
    15,
    14,
    14,
    13,
    12,
    12,
    11,
    11,
    10,
    9,
    9,
    8,
    8,
    7,
    7,
    6,
    5,
    5,
    4,
    4,
    3,
    3,
    2,
    2,
    1,
    1,
    0,
]


# ==================================================================== rule texts
# norm: rules of src/unpriv/vector-common.adoc (Integer Arithmetic through FP Permutation), from
# tests_ai/gen/norm_rules.py at riscv-isa-manual upstream/main 717aeca3: name -> (line, text)
RULES: dict[str, tuple[int, str]] = {
    "vadd_vsub_op": (2462, "Vector integer add and subtract are provided."),
    "vrsub_op": (2462, "Reverse-subtract instructions are also provided for the vector-scalar forms."),
    "vwaddu_vwadd_vwsubu_vwsub_op": (
        2486,
        "The widening add/subtract instructions are provided in both signed and unsigned variants, depending on whether the narrower source operands are first sign- or zero-extended before forming the double-width sum.",
    ),
    "vsext_vzext_op": (
        2523,
        "The vector integer extension instructions zero- or sign-extend a source vector integer operand with EEW less than SEW to fill SEW-sized elements in the destination.",
    ),
    "vsext_vzext_vs_eew_emul": (
        2525,
        "The EEW of the source is 1/2, 1/4, or 1/8 of SEW, while EMUL of the source is (EEW/SEW)*LMUL.",
    ),
    "vsext_vzext_vd_eew_emul": (2526, "The destination has EEW equal to SEW and EMUL equal to LMUL."),
    "vsext_vzext_ill_eew_emul_rsv": (
        2538,
        "If the source EEW is not a supported width, or source EMUL would be below the minimum legal LMUL, the instruction encoding is reserved.",
    ),
    "vmadc_vmsbc_vadc_vsbc_carry_v0": (
        2559,
        "The carry inputs and outputs are represented using the mask register layout as described in <<sec-mask-register-layout>>. Due to encoding constraints, the carry input must come from the implicit `v0` register,",
    ),
    "vadc_vsbc_op": (
        2565,
        "vadc and vsbc add or subtract the source operands and the carry-in or borrow-in, and write the result to vector register `vd`.",
    ),
    "vadc_vsbc_masked_write_all_elem": (
        2567,
        "These instructions are encoded as masked instructions (`vm=0`), but they operate on and write back all body elements.",
    ),
    "vadc_vsbc_unmasked_rsv": (2569, "Encodings corresponding to the unmasked versions (`vm=1`) are reserved."),
    "vmadc_vmsbc_op_masked": (
        2571,
        "vmadc and vmsbc add or subtract the source operands, optionally add the carry-in or subtract the borrow-in if masked (`vm=0`), and write the resulting carry-out or borrow-out back to mask register `vd`.",
    ),
    "vmadc_vmsbc_op_unmasked": (2574, "If unmasked (`vm=1`), there is no carry-in or borrow-in."),
    "vmadc_vmsbc_masked_write_all_elem": (
        2574,
        "These instructions operate on and write back all body elements, even if masked.",
    ),
    "vmadc_vmsbc_tail_agnostic": (
        2575,
        "Because these instructions produce a mask value, they always operate with a tail-agnostic policy.",
    ),
    "vmsbc_borrow_neg": (
        2651,
        "For vmsbc, the borrow is defined to be 1 iff the difference, prior to truncation, is negative.",
    ),
    "vadc_vsbc_vd_v0_rsv": (
        2654,
        "For vadc and vsbc, the instruction encoding is reserved if the destination vector register is `v0`.",
    ),
    "vand_vor_vxor_op": (
        2662,
        "---- # Bitwise logical operations. vand.vv vd, vs2, vs1, vm # Vector-vector vand.vx vd, vs2, rs1, vm # vector-scalar vand.vi vd, vs2, imm, vm # vector-immediate",
    ),
    "vsll_vsrl_vsra_op": (
        2684,
        "A full set of vector shift instructions are provided, including logical shift left (sll), and logical (zero-extending srl) and arithmetic (sign-extending sra) shift right. The data to be shifted is in the vector register group specified by `vs2` and the shift amount value can come from a vector register group `vs1`, a scalar integer register `rs1`, or a zero-extended 5-bit immediate.",
    ),
    "vsll_vsrl_vsra_shamt": (
        2689,
        "Only the low lg2(SEW) bits of the shift-amount value are used to control the shift amount.",
    ),
    "vnsrl_vnsra_op": (
        2710,
        "The narrowing right shifts extract a smaller field from a wider operand and have both zero-extending (srl) and sign-extending (sra) forms. The shift amount can come from a vector register group, or a scalar `x` register, or a zero-extended 5-bit immediate.",
    ),
    "vnsrl_vnsra_shamt": (
        2714,
        "The low lg2(2*SEW) bits of the shift-amount value are used (e.g., the low 6 bits for a SEW=64-bit to SEW=32-bit narrowing operation).",
    ),
    "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_op": (
        2739,
        "The following integer compare instructions write 1 to the destination mask register element if the comparison evaluates to true, and 0 otherwise. The destination mask vector is always held in a single vector register, with a layout of elements as described in <<sec-mask-register-layout>>.",
    ),
    "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_vd_v0_legal": (
        2743,
        "The destination mask vector register may be the same as the source vector mask register (`v0`).",
    ),
    "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_maskundisturbed": (
        2896,
        "Compares effectively AND in the mask under a mask-undisturbed policy if the destination register is `v0`,",
    ),
    "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_tail_agnostic": (
        2904,
        "Compares write mask registers, and so always operate under a tail-agnostic policy.",
    ),
    "vminu_vmin_vmaxu_vmax_op": (2909, "Signed and unsigned integer minimum and maximum instructions are supported."),
    "vmul_vmulh_vmulhu_vmulhsu_op": (
        2932,
        "The single-width multiply instructions perform a SEW-bit*SEW-bit multiply to generate a 2*SEW-bit product, then return one half of the product in the SEW-bit-wide destination. The `*mul*` versions write the low half of the product to the destination register, while the `*mulh*` versions write the high half of the product to the destination register.",
    ),
    "vdivu_vdiv_vremu_vrem_op": (
        2970,
        "The divide and remainder instructions are equivalent to the RISC-V standard scalar integer multiply/divides, with the same results for extreme inputs.",
    ),
    "vwmul_vwmulu_vwmulsu_op": (
        3003,
        "The widening integer multiply instructions return the full 2*SEW-bit product from an SEW-bit*SEW-bit multiply.",
    ),
    "vmacc_vnmsac_vmadd_vnmsub_op": (
        3022,
        "The integer multiply-add instructions are destructive and are provided in two forms, one that overwrites the addend or minuend (vmacc, vnmsac) and one that overwrites the first multiplicand (vmadd, vnmsub).",
    ),
    "vmacc_vnmsac_vmadd_vnmsub_op_lowhalf": (
        3027,
        "The low half of the product is added or subtracted from the third operand.",
    ),
    "vwmaccu_vwmacc_vwmaccsu_vwmaccus_op": (
        3054,
        "The widening integer multiply-add instructions add the full 2*SEW-bit product from a SEW-bit*SEW-bit multiply to a 2*SEW-bit value and produce a 2*SEW-bit result.",
    ),
    "vmerge_op": (3078, "The vector integer merge instructions combine two source operands based on a mask."),
    "vmerge_all_elem": (
        3079,
        "Unlike regular arithmetic instructions, the merge operates on all body elements (i.e., the set of elements from vstart up to the current vector length in vl).",
    ),
    "vmerge_op_mask": (
        3083,
        "The vmerge instructions are encoded as masked instructions (`vm=0`). The instructions combine two sources as follows. At elements where the mask value is zero, the first operand is copied to the destination element, otherwise the second operand is copied to the destination element. The first operand is always a vector register group specified by `vs2`. The second operand is a vector register group specified by `vs1` or a scalar `x` register specified by `rs1` or a 5-bit sign-extended immediate.",
    ),
    "vmv_op": (
        3101,
        "The vector integer move instructions copy a source operand to a vector register group. The vmv.v.v variant copies a vector register group, whereas the vmv.v.x and vmv.v.i variants __splat__ a scalar register or immediate to all active elements of the destination vector register group.",
    ),
    "vmv_vs2_nv0_rsv": (
        3107,
        "The first operand specifier (`vs2`) must contain `v0`, and any other vector register number in `vs2` is _reserved_.",
    ),
    "vsaddu_vsadd_vssubu_vssub_op": (
        3156,
        "Saturating forms of integer add and subtract are provided, for both signed and unsigned integers.",
    ),
    "vsaddu_vsadd_vssubu_vssub_op_overflow_vxsat_op_vsaddsub": (
        3157,
        "If the result would overflow the destination, the result is replaced with the closest representable value, and the vxsat bit is set.",
    ),
    "vaaddu_vaadd_vasubu_vasub_op": (
        3183,
        "The averaging add and subtract instructions right shift the result by one bit and round off the result according to the setting in vxrm. Computation is performed in infinite precision before rounding and truncating.",
    ),
    "vasub_vasubu_op_overflow": (3188, "For vasub and vasubu, overflow is ignored and the result wraps around."),
    "vsmul_op": (
        3217,
        "The signed fractional multiply instruction produces a 2*SEW product of the two SEW inputs, then shifts the result right by SEW-1 bits, rounding these bits according to vxrm, then saturates the result to fit into SEW bits.",
    ),
    "vxsat_op_vsmul": (3220, "If the result causes saturation, the vxsat bit is set."),
    "vssrl_vssra_op": (
        3246,
        "These instructions shift the input value right, and round off the shifted out bits according to vxrm. The scaling right shifts have both zero-extending (vssrl) and sign-extending (vssra) forms. The data to be shifted is in the vector register group specified by `vs2` and the shift amount value can come from a vector register group `vs1`, a scalar integer register `rs1`, or a zero-extended 5-bit immediate.",
    ),
    "vssrl_vssra_shamt": (
        3252,
        "Only the low lg2(SEW) bits of the shift-amount value are used to control the shift amount.",
    ),
    "vnclipu_vnclip_op": (
        3268,
        "The vnclip instructions are used to pack a fixed-point value into a narrower destination. The instructions support rounding, scaling, and saturation into the final destination format. The source data is in the vector register group specified by `vs2`. The scaling shift amount value can come from a vector register group `vs1`, a scalar integer register `rs1`, or a zero-extended 5-bit immediate.",
    ),
    "vnclipu_vnclip_shamt": (
        3273,
        "The low lg2(2*SEW) bits of the vector or scalar shift-amount value (e.g., the low 6 bits for a SEW=64-bit to SEW=32-bit narrowing operation) are used to control the right shift amount, which provides the scaling.",
    ),
    "vnclipu_vnclip_rounding": (
        3290,
        "For vnclipu and vnclip, the rounding mode is specified in the vxrm CSR. Rounding occurs around the least-significant bit of the destination and before saturation.",
    ),
    "vnclipu_overflow": (
        3294,
        "For vnclipu, the shifted rounded source value is treated as an unsigned integer and saturates if the result would overflow the destination viewed as an unsigned integer.",
    ),
    "vnclip_overflow": (
        3306,
        "For vnclip, the shifted rounded source value is treated as a signed integer and saturates if the result would overflow the destination viewed as a signed integer.",
    ),
    "vxsat_op_vnclip_u": (
        3310,
        "If any destination element is saturated, the least-significant bit is set in the vxsat register.",
    ),
    "V_fp_eew_ieee_nsupported_rsv": (
        3317,
        "If the EEW of a vector floating-point operand does not correspond to a supported IEEE floating-point type, the instruction encoding is reserved.",
    ),
    "vf_requires_vx": (
        3328,
        "Vector floating-point instructions require the presence of base scalar floating-point extensions corresponding to the supported vector floating-point element widths.",
    ),
    "mstatus_fs_off_V_fp_ill": (
        3336,
        "If the floating-point unit status field mstatus[fs] is `Off` then any attempt to execute a vector floating-point instruction will raise an illegal-instruction exception.",
    ),
    "mstatus_fs_dirty_V_fp": (
        3338,
        "Any vector floating-point instruction that modifies any floating-point extension state (i.e., floating-point CSRs or `f` registers) must set mstatus[fs] to `Dirty`.",
    ),
    "vsstatus_mstatus_fs_off_hypervisor_V_fp_ill": (
        3342,
        "If the hypervisor extension is implemented and V=1, the vsstatus[fs] field is additionally in effect for vector floating-point instructions. If vsstatus[fs] or mstatus[fs] is `Off` then any attempt to execute a vector floating-point instruction will raise an illegal-instruction exception.",
    ),
    "vsstatus_mstatus_fs_dirty_hypervisor_V_fp": (
        3346,
        "Any vector floating-point instruction that modifies any floating-point extension state (i.e., floating-point CSRs or `f` registers) must set both mstatus[fs] and vsstatus[fs] to `Dirty`.",
    ),
    "fflags_op_V_fp": (
        3358,
        "A vector floating-point exception at any active floating-point element sets the standard FP exception flags in the fflags register. Inactive elements do not set FP exception flags.",
    ),
    "vfadd_vfsub_vfrsub_op": (
        3364,
        "---- # Floating-point add vfadd.vv vd, vs2, vs1, vm # Vector-vector vfadd.vf vd, vs2, rs1, vm # vector-scalar",
    ),
    "vfwadd_op": (
        3378,
        "---- # Widening FP add/subtract, 2*SEW = SEW +/- SEW vfwadd.vv vd, vs2, vs1, vm # vector-vector vfwadd.vf vd, vs2, rs1, vm # vector-scalar vfwsub.vv vd, vs2, vs1, vm # vector-vector vfwsub.vf vd, vs2, rs1, vm # vector-scalar",
    ),
    "vfmul_vfdiv_vfrdiv_op": (
        3395,
        "---- # Floating-point multiply vfmul.vv vd, vs2, vs1, vm # Vector-vector vfmul.vf vd, vs2, rs1, vm # vector-scalar",
    ),
    "vfwmul_op": (
        3410,
        "---- # Widening floating-point multiply vfwmul.vv vd, vs2, vs1, vm # vector-vector vfwmul.vf vd, vs2, rs1, vm # vector-scalar ----",
    ),
    "vfmacc_vfnmacc_vfmsac_vfnmsac_vfmadd_vfnmadd_vfmsub_vfnmsub_op": (
        3419,
        "All four varieties of fused multiply-add are provided, and in two destructive forms that overwrite one of the operands, either the addend or the first multiplicand.",
    ),
    "vfwmacc_vfwnmacc_vfwmsac_vfwnmsac_op": (
        3464,
        "The widening floating-point fused multiply-add instructions all overwrite the wide addend with the result. The multiplier inputs are all SEW wide, while the addend and destination is 2*SEW bits wide.",
    ),
    "vfsqrt_op": (3488, "The vfsqrt.v instruction is a unary vector-vector instruction."),
    "vfrsqrt7_op": (
        3503,
        "This is a unary vector-vector instruction that returns an estimate of 1/sqrt(x) accurate to 7 bits.",
    ),
    "vfrsqrt7_op_unex": (
        3527,
        "For the non-exceptional cases, the low bit of the exponent and the six high bits of significand (after the leading one) are concatenated and used to address the following table. The output of the table becomes the seven high bits of the result significand (after the leading one); the remainder of the result significand is zero. Subnormal inputs are normalized and the exponent adjusted appropriately before the lookup. The output exponent is chosen to make the result approximate the reciprocal of the square root of the argument.",
    ),
    "vfrsqrt7_op_precise": (
        3537,
        "More precisely, the result is computed as follows. Let the normalized input exponent be equal to the input exponent if the input is normal, or 0 minus the number of leading zeros in the significand otherwise. If the input is subnormal, the normalized input significand is given by shifting the input significand left by 1 minus the normalized input exponent, discarding the leading 1 bit. The output exponent equals floor((3*B - 1 - the normalized input exponent) / 2), where B is the exponent bias. The output sign equals the input sign.",
    ),
    "vfrec7_op": (
        3567,
        "This is a unary vector-vector instruction that returns an estimate of 1/x accurate to 7 bits.",
    ),
    "vfrec7_op_unex": (
        3608,
        "For the non-exceptional cases, the seven high bits of significand (after the leading one) are used to address the following table. The output of the table becomes the seven high bits of the result significand (after the leading one); the remainder of the result significand is zero. Subnormal inputs are normalized and the exponent adjusted appropriately before the lookup. The output exponent is chosen to make the result approximate the reciprocal of the argument, and subnormal outputs are denormalized accordingly.",
    ),
    "vfrec7_op_precise": (
        3617,
        "More precisely, the result is computed as follows. Let the normalized input exponent be equal to the input exponent if the input is normal, or 0 minus the number of leading zeros in the significand otherwise. The normalized output exponent equals (2*B - 1 - the normalized input exponent). If the normalized output exponent is outside the range [-1, 2*B], the result corresponds to one of the exceptional cases in the table above.",
    ),
    "vfrec7_op_subnorm": (
        3625,
        "If the input is subnormal, the normalized input significand is given by shifting the input significand left by 1 minus the normalized input exponent, discarding the leading 1 bit. Otherwise, the normalized input significand equals the input significand. The following table gives the seven MSBs of the normalized output significand as a function of the seven MSBs of the normalized input significand; the other bits of the normalized output significand are zero.",
    ),
    "vfrec7_op_output": (
        3635,
        "If the normalized output exponent is 0 or -1, the result is subnormal: the output exponent is 0, and the output significand is given by concatenating a 1 bit to the left of the normalized output significand, then shifting that quantity right by 1 minus the normalized output exponent. Otherwise, the output exponent equals the normalized output exponent, and the output significand equals the normalized output significand. The output sign equals the input sign.",
    ),
    "vfmin_vfmax_op": (
        3652,
        "The vector floating-point vfmin and vfmax instructions have the same behavior as the corresponding scalar floating-point instructions in the f, d, and q extensions: they perform the IEEE 754-2019 `minimumNumber` or `maximumNumber` operation on active elements.",
    ),
    "vfsgnj_vfsgnjn_vfsgnjx_op": (
        3669,
        "Vector versions of the scalar sign-injection instructions. The result takes all bits except the sign bit from the vector `vs2` operands.",
    ),
    "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_op": (
        3694,
        "These vector FP compare instructions compare two source operands and write the comparison result to a mask register.",
    ),
    "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_vd_single_vreg": (
        3695,
        "The destination mask vector is always held in a single vector register, with a layout of elements as described in <<sec-mask-register-layout>>.",
    ),
    "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_vd_eq_v0": (
        3697,
        "The destination mask vector register may be the same as the source vector mask register (`v0`).",
    ),
    "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_tail_agnostic": (
        3699,
        "Compares write mask registers, and so always operate under a tail-agnostic policy.",
    ),
    "vmfeq_vmfne_snan_invalid": (
        3703,
        "vmfeq and vmfne raise the invalid operation exception only on signaling NaN inputs.",
    ),
    "vmflt_vmfle_vmfgt_vmfge_sqnan_invalid": (
        3704,
        "vmflt, vmfle, vmfgt, and vmfge raise the invalid operation exception on both signaling and quiet NaN inputs.",
    ),
    "vmfne_vdval1_nan": (3707, "vmfne writes 1 to the destination element when either operand is NaN,"),
    "vmfeq_vmflt_vmfle_vmfgt_vmfge_vdval0_nan": (
        3708,
        "whereas the other compares write 0 when either operand is NaN.",
    ),
    "vfclass_op": (
        3776,
        "This is a unary vector-vector instruction that operates in the same way as the scalar classify instruction.",
    ),
    "vfclass_op_result": (
        3783,
        "The 10-bit mask produced by this instruction is placed in the least-significant bits of the result elements. The upper (SEW-10) bits of the result are filled with zeros.",
    ),
    "vfclass_sewge16": (
        3785,
        "The instruction is only defined for SEW=16b and above, so the result will always fit in the destination elements.",
    ),
    "vfmerge_op": (3791, "A vector-scalar floating-point merge instruction is provided,"),
    "vfmerge_all_elem": (
        3792,
        "operates on all body elements from vstart up to the current vector length in vl regardless of mask value.",
    ),
    "vfmerge_op_mask": (
        3796,
        "At elements where the mask value is zero, the first vector operand is copied to the destination element, otherwise a scalar floating-point register value is copied to the destination element.",
    ),
    "vfmv_op": (
        3806,
        "The vector floating-point move instruction __splats__ a floating-point scalar operand to a vector register group. The instruction copies a scalar `f` register value to all active elements of a vector register group.",
    ),
    "vfmv_vs2_nv0_rsv": (
        3810,
        "The instruction must have the `vs2` field set to `v0`, with all other values for `vs2` reserved.",
    ),
    "vfcvt_op": (
        3822,
        "Conversion operations are provided to convert to and from floating-point values and unsigned and signed integers, where both source and destination are SEW wide.",
    ),
    "vfcvt_op_exceptions": (
        3837,
        "The conversions follow the same rules on exceptional conditions as the scalar conversion instructions.",
    ),
    "vfcvt_op_frm": (
        3839,
        "The conversions use the dynamic rounding mode in frm, except for the `rtz` variants, which round towards zero.",
    ),
    "vfwcvt_op": (
        3847,
        "A set of conversion instructions is provided to convert between narrower integer and floating-point datatypes to a type of twice the width.",
    ),
    "vfwcvt_vreg_constr": (
        3864,
        "These instructions have the same constraints on vector register overlap as other widening instructions (see <<sec-widening>>).",
    ),
    "vfncvt_op": (
        3880,
        "A set of conversion instructions is provided to convert wider integer and floating-point datatypes to a type of half the width.",
    ),
    "vfncvt_vreg_constr": (
        3898,
        "These instructions have the same constraints on vector register overlap as other narrowing instructions (see <<sec-narrowing>>).",
    ),
    "vreduction_scalar_def": (
        3913,
        "Vector reduction operations take a vector register group of elements and a scalar held in element 0 of a vector register group, and perform a reduction using some binary operator, to produce a scalar result in element 0 of a vector register group.",
    ),
    "vreduction_scalar_disregard_lmul": (
        3916,
        "The scalar input and output operands are held in element 0 of a group with EMUL = ceil(EEW/VLEN), regardless of LMUL setting.",
    ),
    "vreduction_vd_overlap_vs": (
        3919,
        "The destination vector register can overlap the source operands, including the mask register.",
    ),
    "vreduction_scalar_disregard_maskval": (
        3928,
        "Inactive elements from the source vector register group are excluded from the reduction, but the scalar operand is always included regardless of the mask values.",
    ),
    "vreduction_tail_policy": (
        3932,
        "The other elements in the destination vector register (0 < index < VLEN/SEW) are considered the tail and are managed with the current tail agnostic/undisturbed policy.",
    ),
    "vreduction_vl_0": (3936, "If vl=0, no operation is performed and the destination register is not updated."),
    "vreduction_trap": (3952, "Traps on vector reduction instructions are always reported with a vstart of 0."),
    "vreduction_vstart_n0_ill": (
        3953,
        "Vector reduction operations raise an illegal-instruction exception if vstart is non-zero.",
    ),
    "vredsum_vredmaxu_vredmax_vredminu_vredmin_vredand_vredor_vredxor_op": (
        3964,
        "All operands and results of single-width reduction instructions have the same SEW width.",
    ),
    "vredsum_vredmaxu_vredmax_vredminu_vredmin_vredand_vredor_vredxor_overflow": (
        3965,
        "Overflows wrap around on arithmetic sums.",
    ),
    "vwredsumu_op": (
        3982,
        "The unsigned vwredsumu.vs instruction zero-extends the SEW-wide vector elements before summing them, then adds the 2*SEW-width scalar element, and stores the result in a 2*SEW-width scalar element.",
    ),
    "vwredsum_op": (3986, "The vwredsum.vs instruction sign-extends the SEW-wide vector elements before summing them."),
    "vwredsumu_vwredsum_op_overflow": (3989, "For both vwredsumu.vs and vwredsum.vs, overflows wrap around."),
    "vfredosum_op": (
        4012,
        "The vfredosum instruction must sum the floating-point values in element order, starting with the scalar in `vs1[0]`",
    ),
    "vfredosum_op_exceptions": (
        4019,
        "where each addition operates identically to the scalar floating-point instructions in terms of raising exception flags and generating or propagating special values.",
    ),
    "vfredosum_maskoff": (
        4026,
        "When the operation is masked (`vm=0`), the masked-off elements do not affect the result or the exception flags.",
    ),
    "vfredusum_op": (
        4040,
        "The implementation must produce a result equivalent to a reduction tree composed of binary operator nodes, with the inputs being elements from the source vector register group (`vs2`) and the source scalar value (`vs1[0]`). Each operator in the tree accepts two inputs and produces one result. Each operator first computes an exact sum as a RISC-V scalar floating-point addition with infinite exponent range and precision, then converts this exact sum to a floating-point format with range and precision each at least as great as the element floating-point format indicated by SEW, rounding using the currently active floating-point dynamic rounding mode and raising exception flags as necessary. A different floating-point range and precision may be chosen for the result of each operator. A node where one input is derived only from elements masked-off or beyond the active vector length may either treat that input as the additive identity of the appropriate EEW or simply copy the other input to its output. The rounded result from the root node in the tree is converted (rounded again, using the dynamic rounding mode) to the standard floating-point format indicated by SEW.",
    ),
    "vfredusum_additive_impl": (
        4062,
        "The additive identity is +0.0 when rounding down (towards -{inf}) or -0.0 for all other rounding modes.",
    ),
    "vfredusum_redtree": (
        4065,
        "The reduction tree structure must be deterministic for a given value in vtype and vl.",
    ),
    "vfredmin_vfredmax_op": (
        4081,
        "The vfredmin and vfredmax instructions reduce the scalar argument in `vs1[0]` and active elements in `vs2` using the IEEE 754-2019 `minimumNumber` and `maximumNumber` operations, respectively.",
    ),
    "vfwredosum_vfwredusum_op": (
        4096,
        "Widening forms of the sum reductions are provided that read and write a double-width reduction result.",
    ),
    "vfwredosum_vfwredusum_op_reduction": (
        4105,
        "The reduction of the SEW-width elements is performed as in the single-width reduction case, with the elements in `vs2` promoted to 2*SEW bits before adding to the 2*SEW-bit accumulator.",
    ),
    "vmask_maskreg_def": (
        4121,
        "Vector mask-register logical operations operate on mask registers. Each element in a mask register is a single bit,",
    ),
    "instrgrp_vmask_disregard_vlmul": (
        4122,
        "so these instructions all operate on single vector registers regardless of the setting of the vlmul field in vtype. They do not change the value of vlmul.",
    ),
    "vmask_vd_overlap_vs": (4125, "The destination vector register may be the same as either source vector register."),
    "vmask_vstart": (
        4128,
        "As with other vector instructions, the elements with indices less than vstart are unchanged, and vstart is reset to zero after execution.",
    ),
    "vmasklogical_unmasked": (4130, "Vector mask logical instructions are always unmasked,"),
    "vmasklogical_masked_rsv": (4130, "so there are no inactive elements, and the encodings with `vm=0` are reserved."),
    "vmasklogical_tail_agnostic": (
        4132,
        "Mask elements past vl, the tail elements, are always updated with a tail-agnostic policy.",
    ),
    "vmand_vmnand_vmandn_vmxor_vmor_vmnor_vmorn_vmxnor_op": (
        4135,
        "---- vmand.mm vd, vs2, vs1 # vd.mask[i] = vs2.mask[i] && vs1.mask[i] vmnand.mm vd, vs2, vs1 # vd.mask[i] = !(vs2.mask[i] && vs1.mask[i]) vmandn.mm vd, vs2, vs1 # vd.mask[i] = vs2.mask[i] && !vs1.mask[i] vmxor.mm vd, vs2, vs1 # vd.mask[i] = vs2.mask[i] ^^ vs1.mask[i] vmor.mm vd, vs2, vs1 # vd.mask[i] = vs2.mask[i] || vs1.mask[i] vmnor.mm vd, vs2, vs1 # vd.mask[i] = !(vs2.mask[i] || vs1.mask[i]) vmorn.mm vd, vs2, vs1 # vd.mask[i] = vs2.mask[i] || !vs1.mask[i] vmxnor.mm vd, vs2, vs1 # vd.mask[i] = !(vs2.mask[i] ^^ vs1.mask[i]) ----",
    ),
    "vcpop_vs_single_vreg": (
        4209,
        "The source operand is a single vector register holding mask register values as described in <<sec-mask-register-layout>>.",
    ),
    "vcpop_op": (
        4212,
        "The vcpop.m instruction counts the number of mask elements of the active elements of the vector source mask register that have the value 1 and writes the result to a scalar `x` register.",
    ),
    "vcpop_op_mask": (
        4216,
        "The operation can be performed under a mask, in which case only the masked elements are counted.",
    ),
    "vcpop_vl0": (
        4223,
        "The vcpop.m instruction writes `x[rd]` even if vl=0 (with the value 0, since no mask elements are active).",
    ),
    "vcpop_trap": (4226, "Traps on vcpop.m are always reported with a vstart of 0."),
    "vcpop_vstart_n0_ill": (
        4226,
        "The vcpop.m instruction will raise an illegal-instruction exception if vstart is non-zero.",
    ),
    "vfirst_op": (
        4236,
        "The vfirst instruction finds the lowest-numbered active element of the source mask vector that has the value 1 and writes that element's index to _rd_. If no active element has the value 1, -1 is written to _rd_.",
    ),
    "vfirst_vl0": (
        4245,
        "The vfirst.m instruction writes `x[rd]` even if `vl`=0 (with the value -1, since no mask elements are active).",
    ),
    "vfirst_trap": (4248, "Traps on vfirst are always reported with a vstart of 0."),
    "vfirst_vstart_n0_ill": (
        4248,
        "The vfirst instruction will raise an illegal-instruction exception if vstart is non-zero.",
    ),
    "vmsbf_op": (
        4279,
        "The vmsbf.m instruction takes a mask register as input and writes results to a mask register. The instruction writes a 1 to all active mask elements before the first active source element that is a 1, then writes a 0 to that element and all following active elements. If there is no set bit in the active elements of the source vector, then all active elements in the destination are written with a 1.",
    ),
    "vmsbf_tail_agnostic": (
        4286,
        "The tail elements in the destination mask register are updated under a tail-agnostic policy.",
    ),
    "vmsbf_trap": (4289, "Traps on vmsbf.m are always reported with a vstart of 0."),
    "vmsbf_vstart_n0_ill": (
        4289,
        "The vmsbf.m instruction will raise an illegal-instruction exception if vstart is non-zero.",
    ),
    "vmsbf_vreg_constr": (
        4293,
        "The destination register cannot overlap the source register and, if masked, cannot overlap the mask register (`v0`).",
    ),
    "vmsif_op": (
        4298,
        "The vector mask set-including-first instruction is similar to set-before-first, except it also includes the element with a set bit.",
    ),
    "vmsif_tail_agnostic": (
        4322,
        "The tail elements in the destination mask register are updated under a tail-agnostic policy.",
    ),
    "vmsif_trap": (4325, "Traps on vmsif.m are always reported with a vstart of 0."),
    "vmsif_vstart_n0_ill": (
        4325,
        "The vmsif.m instruction will raise an illegal-instruction exception if vstart is non-zero.",
    ),
    "vmsif_vreg_constr": (
        4329,
        "The destination register cannot overlap the source register and, if masked, cannot overlap the mask register (`v0`).",
    ),
    "vmsof_op": (
        4334,
        "The vector mask set-only-first instruction is similar to set-before-first, except it only sets the first element with a bit set, if any.",
    ),
    "vmsof_tail_agnostic": (
        4359,
        "The tail elements in the destination mask register are updated under a tail-agnostic policy.",
    ),
    "vmsof_trap": (4362, "Traps on vmsof.m are always reported with a vstart of 0."),
    "vmsof_vstart_n0_ill": (
        4362,
        "The vmsof.m instruction will raise an illegal-instruction exception if vstart is non-zero.",
    ),
    "vmsof_vreg_constr": (
        4366,
        "The destination register cannot overlap the source register and, if masked, cannot overlap the mask register (`v0`).",
    ),
    "viota_op": (
        4382,
        "The viota.m instruction reads a source vector mask register and writes to each element of the destination vector register group the sum of all the bits of elements in the mask register whose index is less than the element, e.g., a parallel prefix sum of the mask values.",
    ),
    "viota_op_masked": (
        4388,
        "This instruction can be masked, in which case only the enabled elements contribute to the sum.",
    ),
    "viota_op_zext": (
        4409,
        "The result value is zero-extended to fill the destination element if SEW is wider than the result.",
    ),
    "viota_op_overflow": (
        4410,
        "If the result value would overflow the destination SEW, the least-significant SEW bits are retained.",
    ),
    "viota_trap": (4413, "Traps on viota.m are always reported with a vstart of 0,"),
    "viota_restart": (4414, "execution is always restarted from the beginning when resuming after a trap handler."),
    "viota_vstart_n0_ill": (4415, "An illegal-instruction exception is raised if vstart is non-zero."),
    "viota_vreg_constr": (
        4418,
        "The destination register group cannot overlap the source register and, if masked, cannot overlap the mask register (`v0`).",
    ),
    "vid_op": (
        4470,
        "The vid.v instruction writes each element's index to the destination vector register group, from 0 to vl-1.",
    ),
    "vid_op_mask": (
        4477,
        "The instruction can be masked. Masking does not change the index value written to active elements.",
    ),
    "vid_vs2_nv0_rsv": (
        4480,
        "The `vs2` field of the instruction must be set to `v0`, otherwise the encoding is _reserved_.",
    ),
    "vid_op_zext": (
        4483,
        "The result value is zero-extended to fill the destination element if SEW is wider than the result.",
    ),
    "vid_op_overflow": (
        4484,
        "If the result value would overflow the destination SEW, the least-significant SEW bits are retained.",
    ),
    "vmv-x-s_vmv-s-x_ignorelmul": (4500, "The instructions ignore LMUL; EMUL is computed as ceil(EEW/VLEN)."),
    "vmv-x-s_op": (
        4507,
        "The vmv.x.s instruction copies a single SEW-wide element from index 0 of the source vector register to a destination integer register. If SEW > XLEN, the least-significant XLEN bits are transferred and the upper SEW-XLEN bits are ignored. If SEW < XLEN, the value is sign-extended to XLEN bits.",
    ),
    "vmv-s-x_op": (
        4514,
        "The vmv.s.x instruction copies the scalar integer register to element 0 of the destination vector register group with EMUL = ceil(EEW/VLEN). If SEW < XLEN, the least-significant bits are copied and the upper XLEN-SEW bits are ignored. If SEW > XLEN, the value is sign-extended to SEW bits. The other elements in the destination vector register ( 0 < index < VLEN/SEW) are treated as tail elements using the current tail agnostic/undisturbed policy.",
    ),
    "vmv-s-x_vstart_ge_vl": (
        4519,
        "If vstart {ge} vl, no operation is performed and the destination register is not updated.",
    ),
    "vmv-s-x_vmv-x-s_masked_rsv": (
        4525,
        "The encodings corresponding to the masked versions (`vm=0`) of vmv.x.s and vmv.s.x are reserved.",
    ),
    "vslide_vstart_ge_vl": (
        4539,
        "For all of the vslideup, vslidedown, vslide1up, vfslide1up, vslide1down, and vfslide1down instructions, if vstart {ge} vl, the instruction performs no operation and leaves the destination vector register unchanged.",
    ),
    "vslide_mask": (
        4548,
        "The slide instructions may be masked, with mask element _i_ controlling whether _destination_ element _i_ is written. The mask undisturbed/agnostic policy is followed for inactive elements.",
    ),
    "vslideup_op": (
        4559,
        "For vslideup, the value in vl specifies the maximum number of destination elements that are written. The start index (_OFFSET_) for the destination can be either specified using an unsigned integer in the `x` register specified by `rs1`, or a 5-bit immediate, zero-extended to XLEN bits. If XLEN > SEW, _OFFSET_ is _not_ truncated to SEW bits. Destination elements _OFFSET_ through vl-1 are written if unmasked and if _OFFSET_ < vl.",
    ),
    "vslideup_vreg_constr": (
        4577,
        "The destination vector register group for vslideup cannot overlap the source vector register group, otherwise the instruction encoding is reserved.",
    ),
    "vslidedown_op": (
        4592,
        "For vslidedown, the value in vl specifies the maximum number of destination elements that are written. The remaining elements past vl are handled according to the current tail policy (<<sec-agnostic>>).",
    ),
    "vslidedown_op_src": (
        4597,
        "The start index (_OFFSET_) for the source can be either specified using an unsigned integer in the `x` register specified by `rs1`, or a 5-bit immediate, zero-extended to XLEN bits. If XLEN > SEW, _OFFSET_ is _not_ truncated to SEW bits.",
    ),
    "vslide1up-vx_op": (
        4623,
        "The vslide1up instruction places the `x` register argument at location 0 of the destination vector register group, provided that element 0 is active, otherwise the destination element update follows the current mask agnostic/undisturbed policy. If XLEN < SEW, the value is sign-extended to SEW bits. If XLEN > SEW, the least-significant bits are copied over and the high XLEN-SEW bits are ignored.",
    ),
    "vslide1up-vx_op_rem_elem": (
        4630,
        "The remaining active vl-1 elements are copied over from index _i_ in the source vector register group to index _i_+1 in the destination vector register group.",
    ),
    "vslide1up-vx_op_vl": (
        4634,
        "The vl register specifies the maximum number of destination vector register elements updated with source values, and remaining elements past vl are handled according to the current tail policy (<<sec-agnostic>>).",
    ),
    "vslide1up-vx_vreg_constr": (
        4649,
        "The vslide1up instruction requires that the destination vector register group does not overlap the source vector register group. Otherwise, the instruction encoding is reserved.",
    ),
    "vslide1down-vx_op": (
        4655,
        "The vslide1down instruction copies the first vl-1 active elements values from index _i_+1 in the source vector register group to index _i_ in the destination vector register group.",
    ),
    "vslide1down-vx_op_vl": (
        4659,
        "The vl register specifies the maximum number of destination vector register elements written with source values, and remaining elements past vl are handled according to the current tail policy (<<sec-agnostic>>).",
    ),
    "vslide1down-vx_op_details": (
        4668,
        "The vslide1down instruction places the `x` register argument at location vl-1 in the destination vector register, provided that element vl-1 is active, otherwise the destination element update follows the current mask agnostic/undisturbed policy. If XLEN < SEW, the value is sign-extended to SEW bits. If XLEN > SEW, the least-significant bits are copied over and the high SEW-XLEN bits are ignored.",
    ),
    "vrgather_vrgatherei16_vs2_uint": (4695, "The index values in the second vector are treated as unsigned integers."),
    "vrgather_vrgatherei16_vs_ignore_vl": (
        4696,
        "The source vector can be read at any index < VLMAX regardless of vl.",
    ),
    "vrgather_vrgatherei16_vl": (
        4697,
        "The maximum number of elements to write to the destination register is given by vl,",
    ),
    "vrgather_vrgatherei16_tail": (
        4698,
        "and the remaining elements past vl are handled according to the current tail policy (<<sec-agnostic>>).",
    ),
    "vrgather_vrgatherei16_mask": (
        4700,
        "The operation can be masked, and the mask undisturbed/agnostic policy is followed for inactive elements.",
    ),
    "vrgather-vv_op_vrgatherei16-vv_op": (
        4703,
        "---- vrgather.vv vd, vs2, vs1, vm # vd[i] = (vs1[i] >= VLMAX) ? 0 : vs2[vs1[i]]; vrgatherei16.vv vd, vs2, vs1, vm # vd[i] = (vs1[i] >= VLMAX) ? 0 : vs2[vs1[i]]; ----",
    ),
    "vrgather-vv_sew_lmul": (4709, "The vrgather.vv form uses SEW/LMUL for both the data and indices."),
    "vrgatherei16-vv_sew_lmul": (
        4710,
        "The vrgatherei16.vv form uses SEW/LMUL for the data in `vs2` but EEW=16 and EMUL = (16/SEW)*LMUL for the indices in `vs1`.",
    ),
    "vrgather_vrgatherei16_id_ge_vlmax": (
        4718,
        "If an element index is out of range ( `vs1[i]` {ge} VLMAX ) then zero is returned for the element value.",
    ),
    "vrgather-vx_vrgather-vi_op": (
        4721,
        "Vector-scalar and vector-immediate forms of the register gather are also provided. These read one element from the source vector at the given index, and write this value to the active elements of the destination vector register. The index value in the scalar register and the immediate, zero-extended to XLEN bits, are treated as unsigned integers. If XLEN > SEW, the index value is _not_ truncated to SEW bits.",
    ),
    "vrgather_vrgatherei16_vreg_constr": (
        4736,
        "For any vrgather instruction, the destination vector register group cannot overlap with the source vector register groups, otherwise the instruction encoding is reserved.",
    ),
    "vcompress_op": (
        4751,
        "The vector mask register specified by `vs1` indicates which of the first vl elements of vector register group `vs2` should be extracted and packed into contiguous elements at the beginning of vector register `vd`. The remaining elements of `vd` are treated as tail elements according to the current tail policy (<<sec-agnostic>>).",
    ),
    "vcompress_enc": (4771, "vcompress is encoded as an unmasked instruction (`vm=1`)."),
    "vcompress_masked_rsv": (4771, "The equivalent masked instruction (`vm=0`) is reserved."),
    "vcompress_vreg_constr": (
        4774,
        "The destination vector register group cannot overlap the source vector register group or the source mask register, otherwise the instruction encoding is reserved.",
    ),
    "vcompress_trap": (4778, "A trap on a vcompress instruction is always reported with a vstart of 0."),
    "vcompress_vstart_n0_ill": (
        4779,
        "Executing a vcompress instruction with a non-zero vstart raises an illegal-instruction exception.",
    ),
    "vmv-nr-r_op": (4822, "The insn:vmv&"),
    "vmv-nr-r_enc": (
        4844,
        "The instruction is encoded as an OPIVI instruction. The number of vector registers to copy is encoded in the low three bits of the `imm` field (`imm[2:0]`) using the same encoding as the `nf[2:0]` field for memory instructions (Figure <<fig-nf>>), i.e., `imm[2:0]` = NREG-1.",
    ),
    "vmv-nr-r_nreg_rsv": (
        4849,
        "The value of NREG must be 1, 2, 4, or 8, and values of `imm[4:0]` other than 0, 1, 3, and 7 are reserved.",
    ),
    "vmv-nr-r_vreg_constr": (
        4869,
        "The source and destination vector register numbers must be aligned appropriately for the vector register group size,",
    ),
    "vmv-nr-r_unaligned_rsv": (4870, "encodings with other vector register numbers are reserved."),
    "vfmv-f-s_vfmv-s-f_ignorelmul": (4886, "The instructions ignore LMUL; EMUL is computed as ceil(EEW/VLEN)."),
    "vfmv-f-s_op": (
        4893,
        "The vfmv.f.s instruction copies a single SEW-wide element from index 0 of the source vector register to a destination scalar floating-point register.",
    ),
    "vfmv-s-f_op": (
        4899,
        "The vfmv.s.f instruction copies the scalar floating-point register to element 0 of the destination vector register. The other elements in the destination vector register (0 < index < VLEN/SEW) are treated as tail elements using the current tail agnostic/undisturbed policy.",
    ),
    "vfmv-s-f_vstart_ge_vl": (
        4903,
        "If vstart {ge} vl, no operation is performed and the destination register is not updated.",
    ),
    "vfmv-s-f_masked_rsv": (
        4909,
        "The encodings corresponding to the masked versions (`vm=0`) of vfmv.f.s and vfmv.s.f are reserved.",
    ),
    "vslide1up-vf_op": (
        4919,
        "The vfslide1up instruction is defined analogously to vslide1up, but sources its scalar argument from an `f` register.",
    ),
    "vslide1down-vf_op": (
        4929,
        "The vfslide1down instruction is defined analogously to vslide1down, but sources its scalar argument from an `f` register.",
    ),
}
