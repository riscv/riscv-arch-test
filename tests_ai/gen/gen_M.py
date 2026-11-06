#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/M: one test per normative rule of the M chapter (src/unpriv/m-st-ext.adoc).

Expected values come from the arithmetic definitions in the rules, computed here per XLEN.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_ALL, TestFile, X, mask, sext

SRC = "src/unpriv/m-st-ext.adoc"
SUITE = "M"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MUL_REQ = ["I", ["M", "Zmmul"]]
MUL_MARCH = "rv${XLEN}i_zmmul_zicsr_zifencei"
DIV_REQ = ["I", "M"]
DIV_MARCH = "rv${XLEN}im_zicsr_zifencei"


# ---------------- reference semantics ----------------
def s(v: int, n: int) -> int:
    return sext(v, n)


def u(v: int, n: int) -> int:
    return v & ((1 << n) - 1)


def tdiv(a: int, b: int) -> int:
    """Signed division truncating toward zero."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def op(insn: str, a: int, b: int, xlen: int) -> int:
    """Result of insn on XLEN-bit register values a, b (as unsigned bit patterns)."""
    w = insn.endswith("w")
    n = 32 if w else xlen
    if insn in ("mul", "mulw"):
        r = s(a, n) * s(b, n)
    elif insn == "mulh":
        r = (s(a, n) * s(b, n)) >> n
    elif insn == "mulhu":
        r = (u(a, n) * u(b, n)) >> n
    elif insn == "mulhsu":
        r = (s(a, n) * u(b, n)) >> n
    elif insn in ("div", "divw"):
        x, y = s(a, n), s(b, n)
        if y == 0:
            r = -1
        elif x == -(1 << (n - 1)) and y == -1:
            r = x
        else:
            r = tdiv(x, y)
    elif insn in ("divu", "divuw"):
        x, y = u(a, n), u(b, n)
        r = (1 << n) - 1 if y == 0 else x // y
    elif insn in ("rem", "remw"):
        x, y = s(a, n), s(b, n)
        if y == 0:
            r = x
        elif x == -(1 << (n - 1)) and y == -1:
            r = 0
        else:
            r = x - tdiv(x, y) * y
    elif insn in ("remu", "remuw"):
        x, y = u(a, n), u(b, n)
        r = x if y == 0 else x % y
    else:
        raise ValueError(insn)
    r = u(r, n)
    if w:
        r = u(s(r, 32), xlen)  # W results are sign-extended to XLEN
    return mask(r, xlen)


# ---------------- operand classes ----------------
def edges(n: int) -> dict[str, int]:
    """Edge values for an n-bit operand, as unsigned bit patterns."""
    a = (1 << n) - 1
    mn = 1 << (n - 1)
    return {
        "0": 0,
        "1": 1,
        "2": 2,
        "-1": a,
        "-2": a - 1,
        "MIN": mn,
        "MIN+1": mn + 1,
        "MAX": mn - 1,
        "MAX-1": mn - 2,
        "2^(n/2)": 1 << (n // 2),
        "2^(n/2)-1": (1 << (n // 2)) - 1,
        "0x55..": int("5" * (n // 4), 16),
        "0xAA..": int("A" * (n // 4), 16),
    }


def class_val(t: TestFile, name: str, w: bool = False) -> X:
    """Per-XLEN value of a named class. For W instructions the low 32 bits carry the class and
    the upper 32 bits (RV64) are random, because they must be ignored."""
    if name == "rand":
        return t.rand_x()
    if name == "rand+":
        return X(t.rand(31), t.rand(63))
    if name == "rand-":
        return X(t.rand(31) | 1 << 31, t.rand(63) | 1 << 63)
    if name == "small+":
        return X(t.rand(8) + 3, t.rand(8) + 3)
    if name == "small-":
        return X(mask(-(t.rand(8) + 3), 32), mask(-(t.rand(8) + 3), 64))
    if w:
        lo = edges(32)[name]
        return X(lo, (t.rand(32) << 32) | lo)
    return X(edges(32)[name], edges(64)[name])


def emit_case(
    t: TestFile, insn: str, a: X, b: X, desc: str, regs: tuple[str, str, str] | None = None, na: str = "", nb: str = ""
) -> None:
    rd, rs1, rs2 = regs or t.regs(3)
    if rs1 != rs2:
        t.load(rs1, a, f"rs1 = {na}" if na else "")
        t.load(rs2, b, f"rs2 = {nb}" if nb else "")
    else:
        t.load(rs1, a, f"rs1 = rs2 = {na}" if na else "")
        b = a
    lab = t.label(insn)
    t.emit(f"{lab}:", 0)
    t.emit(f"{insn} {rd}, {rs1}, {rs2}")
    t.check(rd, X(op(insn, a.num(32), b.num(32), 32), op(insn, a.num(64), b.num(64), 64)), lab, f"{insn} {desc}")


def cross(
    t: TestFile,
    insn: str,
    names_a: list[str],
    names_b: list[str],
    w: bool = False,
    skip: Callable[[str, str], bool] = lambda a, b: False,
) -> None:
    for na in names_a:
        for nb in names_b:
            if skip(na, nb):
                continue
            emit_case(t, insn, class_val(t, na, w), class_val(t, nb, w), f"rs1={na} rs2={nb}", na=na, nb=nb)


def randoms(t: TestFile, insn: str, n: int, w: bool = False, nonzero: bool = False) -> None:
    for _ in range(n):
        a, b = t.rand_x(), t.rand_x()
        if nonzero:
            b = X(b.num(32) | 1, b.num(64) | 1)
        emit_case(t, insn, a, b, "random operands")


def register_classes(t: TestFile, insn: str, nonzero: bool = False) -> None:
    """Operand-register aliasing, x0 operands, and back-to-back dependencies."""
    t.comment("register classes: rd=rs1, rd=rs2, rs1=rs2, rd=rs1=rs2, x0 operands, x0 destination")
    a, b = t.rand_x(), t.rand_x()
    if nonzero:
        b = X(b.num(32) | 1, b.num(64) | 1)
    r1, r2 = t.regs(2)
    emit_case(t, insn, a, b, "rd=rs1", (r1, r1, r2))
    r1, r2 = t.regs(2)
    emit_case(t, insn, a, b, "rd=rs2", (r2, r1, r2))
    r1, r2 = t.regs(2)
    emit_case(t, insn, b, b, "rs1=rs2", (r2, r1, r1))
    r1 = t.regs(1)[0]
    emit_case(t, insn, b, b, "rd=rs1=rs2", (r1, r1, r1))
    # x0 as a source reads zero
    rd, rs = t.regs(2)
    t.load(rs, b)
    lab = t.label(insn)
    t.emit(f"{lab}:", 0)
    t.emit(f"{insn} {rd}, x0, {rs}")
    t.check(rd, X(op(insn, 0, b.num(32), 32), op(insn, 0, b.num(64), 64)), lab, f"{insn} rs1=x0")
    rd, rs = t.regs(2)
    t.load(rs, a)
    lab = t.label(insn)
    t.emit(f"{lab}:", 0)
    t.emit(f"{insn} {rd}, {rs}, x0")
    t.check(rd, X(op(insn, a.num(32), 0, 32), op(insn, a.num(64), 0, 64)), lab, f"{insn} rs2=x0")
    # x0 destination: the result is discarded
    rs1, rs2 = t.regs(2)
    t.load(rs1, a)
    t.load(rs2, b)
    lab = t.label(insn)
    t.emit(f"{lab}:", 0)
    t.emit(f"{insn} x0, {rs1}, {rs2}")
    t.check("x0", 0, lab, f"{insn} rd=x0 leaves x0 zero")
    # back-to-back dependency on the result (forwarding from a multi-cycle unit)
    t.comment("dependent pair: the second instruction consumes the first result immediately")
    c = t.rand_x()
    if nonzero:
        c = X(c.num(32) | 1, c.num(64) | 1)
    ra, rb, rc, rd = t.regs(4)
    t.load(ra, a)
    t.load(rb, b)
    t.load(rc, c)
    lab = t.label(insn)
    t.emit(f"{lab}:", 0)
    t.emit(f"{insn} {rd}, {ra}, {rb}")
    t.emit(f"{insn} {rd}, {rd}, {rc}")
    r1 = X(op(insn, a.num(32), b.num(32), 32), op(insn, a.num(64), b.num(64), 64))
    t.check(
        rd, X(op(insn, r1.num(32), c.num(32), 32), op(insn, r1.num(64), c.num(64), 64)), lab, f"{insn} dependent pair"
    )


def fused_pairs(t: TestFile, hi: str, lo: str) -> None:
    """The spec recommends 'hi rdh,rs1,rs2; lo rdl,rs1,rs2' for fusion. Check the fusible
    form and near misses that must not be fused (rdh overwrites a source of the second)."""
    t.comment(f"recommended fusible sequence {hi} rdh,rs1,rs2; {lo} rdl,rs1,rs2 and near misses")
    for kind in ("fusible", "rdh=rs1", "rdh=rs2", "swapped sources"):
        a, b = t.rand_x(), t.rand_x()
        b = X(b.num(32) | 1, b.num(64) | 1)
        r1, r2, rh, rl = t.regs(4)
        if kind == "rdh=rs1":
            rh = r1
        elif kind == "rdh=rs2":
            rh = r2
        t.load(r1, a)
        t.load(r2, b)
        lab = t.label(f"{hi}_{lo}")
        t.emit(f"{lab}:", 0)
        t.emit(f"{hi} {rh}, {r1}, {r2}")
        h = X(op(hi, a.num(32), b.num(32), 32), op(hi, a.num(64), b.num(64), 64))
        a2 = h if kind == "rdh=rs1" else a
        b2 = h if kind == "rdh=rs2" else b
        if kind == "swapped sources":
            t.emit(f"{lo} {rl}, {r2}, {r1}")
            l = X(op(lo, b2.num(32), a2.num(32), 32), op(lo, b2.num(64), a2.num(64), 64))
        else:
            t.emit(f"{lo} {rl}, {r1}, {r2}")
            l = X(op(lo, a2.num(32), b2.num(32), 32), op(lo, a2.num(64), b2.num(64), 64))
        t.check(rh, h, lab, f"{hi} result of {kind} pair")
        t.check(rl, l, lab, f"{lo} result of {kind} pair")


EDGES = list(edges(32))
SIGNS = ["small+", "small-", "rand+", "rand-"]


def gen() -> list[TestFile]:
    tests = []

    # ---- mul_op ----
    t = TestFile(SUITE, "mul_op", required=MUL_REQ, march=MUL_MARCH, pool=POOL_ALL)
    t.describe(
        source=SRC,
        rule_text="MUL performs an XLEN-bit×XLEN-bit multiplication of rs1 by rs2 and places the lower XLEN "
        "bits in the destination register.",
        context="The low XLEN bits of a product are the same for signed and unsigned operands, so one "
        "instruction serves both. Zmmul provides MUL with identical semantics (Zmmul_enc_same), so the "
        "test runs on M or Zmmul.",
        plan="1. Cross product of 13 edge classes for rs1 x rs2 (0, 1, 2, -1, -2, MIN, MIN+1, MAX, MAX-1, "
        "2^(XLEN/2), 2^(XLEN/2)-1, 0x55.., 0xAA..), which exercises carries across the half-word boundary "
        "and sign handling.\n"
        "2. Sign classes (small and large, positive and negative) crossed.\n"
        "3. 16 random full-width pairs.\n"
        "4. Register classes: rd=rs1, rd=rs2, rs1=rs2, rd=rs1=rs2, x0 sources, x0 destination, and a "
        "dependent pair that consumes the product immediately.",
    )
    cross(t, "mul", EDGES, EDGES)
    cross(t, "mul", SIGNS, SIGNS)
    randoms(t, "mul", 16)
    register_classes(t, "mul")
    tests.append(t)

    # ---- mulh_mulhu_mulhsu_op ----
    t = TestFile(SUITE, "mulh_mulhu_mulhsu_op", required=MUL_REQ, march=MUL_MARCH)
    t.describe(
        source=SRC,
        rule_text="MULH, MULHU, and MULHSU perform the same multiplication but return the upper XLEN bits of "
        "the full 2×XLEN-bit product, for signed×signed, unsigned×unsigned, and rs1×unsigned rs2 "
        "multiplication.",
        context="The spec recommends MULH[[S]U] rdh, rs1, rs2 followed by MUL rdl, rs1, rs2 (rdh not equal "
        "to rs1 or rs2) as a fusible sequence; implementations that fuse it must still honor the "
        "architectural result when the pattern is not exactly met.",
        issues=f"{ISSUE}270 and {ISSUE}463: for MULHSU, rs1 is the signed operand and rs2 the unsigned "
        'one ("rs1×unsigned rs2"; aswaterman in #463: "I\'ll swap multiplier and multiplicand in that text").',
        plan="1. For each of MULH, MULHU, MULHSU: cross product of the 13 edge classes for rs1 x rs2. The "
        "operands with the sign bit set (-1, -2, MIN, MIN+1, 0xAA..) distinguish the three signedness "
        "combinations, so a swapped MULHSU operand order fails.\n"
        "2. Sign classes crossed and 8 random pairs per instruction.\n"
        "3. Register classes and a dependent pair per instruction.\n"
        "4. The recommended high/low sequence (fusible) and near misses (rdh=rs1, rdh=rs2, swapped "
        "sources) for each high instruction with MUL.",
    )
    for insn in ("mulh", "mulhu", "mulhsu"):
        cross(t, insn, EDGES, EDGES)
        cross(t, insn, SIGNS, SIGNS)
        randoms(t, insn, 8)
        register_classes(t, insn)
        fused_pairs(t, insn, "mul")
    tests.append(t)

    # ---- mulw_op ----
    t = TestFile(SUITE, "mulw_op", required=MUL_REQ, march=MUL_MARCH, rv64=True)
    t.describe(
        source=SRC,
        rule_text="MULW is an RV64 instruction that multiplies the lower 32 bits of the source registers, "
        "placing the sign extension of the lower 32 bits of the result into the destination register.",
        plan="1. Cross product of the 13 32-bit edge classes in the low halves of rs1 x rs2, with random "
        "upper halves that must be ignored. Products with bit 31 set check sign extension.\n"
        "2. Operands whose low halves are zero but upper halves nonzero (result 0).\n"
        "3. 16 random pairs, register classes and a dependent pair.",
    )
    cross(t, "mulw", EDGES, EDGES, w=True)
    for _ in range(4):
        a = X(0, t.rand(32) << 32)
        emit_case(t, "mulw", a, t.rand_x(), "rs1 low half zero, upper half nonzero")
    randoms(t, "mulw", 16)
    register_classes(t, "mulw")
    tests.append(t)

    # ---- div_divu_op ----
    def normal_div(na: str, nb: str) -> bool:
        return nb == "0" or (na == "MIN" and nb == "-1")

    t = TestFile(SUITE, "div_divu_op", required=DIV_REQ, march=DIV_MARCH)
    t.describe(
        source=SRC,
        rule_text="DIV and DIVU perform an XLEN bits by XLEN bits signed and unsigned integer division of rs1 "
        "by rs2, rounding towards zero.",
        context="Division by zero and signed overflow have their own rules (div_by_zero, "
        "signed_div_overflow) and are excluded here. The spec recommends DIV rdq,rs1,rs2 followed by REM "
        "rdr,rs1,rs2 as a fusible sequence.",
        plan="1. For DIV and DIVU: cross product of the 13 edge classes, excluding a zero divisor and "
        "MIN / -1.\n"
        "2. Rounding toward zero: inexact quotients for every sign combination of small and large operands.\n"
        "3. 12 random pairs (nonzero divisor), register classes and a dependent pair.\n"
        "4. DIV/REM and DIVU/REMU fusible sequences and near misses.",
    )
    for insn in ("div", "divu"):
        cross(t, insn, EDGES, EDGES, skip=normal_div)
        cross(t, insn, SIGNS, SIGNS)
        randoms(t, insn, 12, nonzero=True)
        register_classes(t, insn, nonzero=True)
    fused_pairs(t, "div", "rem")
    fused_pairs(t, "divu", "remu")
    tests.append(t)

    # ---- rem_remu_op ----
    t = TestFile(SUITE, "rem_remu_op", required=DIV_REQ, march=DIV_MARCH)
    t.describe(
        source=SRC,
        rule_text="REM and REMU provide the remainder of the corresponding division operation.",
        context="The remainder satisfies dividend = divisor × quotient + remainder, with the quotient "
        "rounded toward zero. Zero divisors and signed overflow are covered by rem_by_zero and "
        "signed_div_overflow.",
        plan="1. For REM and REMU: cross product of the 13 edge classes, excluding a zero divisor and "
        "MIN / -1.\n"
        "2. Sign classes crossed, 12 random pairs, register classes and a dependent pair.",
    )
    for insn in ("rem", "remu"):
        cross(t, insn, EDGES, EDGES, skip=normal_div)
        cross(t, insn, SIGNS, SIGNS)
        randoms(t, insn, 12, nonzero=True)
        register_classes(t, insn, nonzero=True)
    tests.append(t)

    # ---- rem_result_sign ----
    t = TestFile(SUITE, "rem_result_sign", required=DIV_REQ, march=DIV_MARCH)
    t.describe(
        source=SRC,
        rule_text="For REM, the sign of a nonzero result equals the sign of the dividend.",
        context="This distinguishes truncating division from floored or Euclidean division, where the "
        "remainder takes the sign of the divisor or is always nonnegative.",
        plan="All four sign combinations of dividend and divisor, with operand magnitudes chosen so the "
        "remainder is nonzero: small and full-width magnitudes, |dividend| < |divisor| (remainder equals "
        "the dividend), and divisors of ±2 and ±(MAX). Each case checks the exact remainder, which fixes "
        "its sign.",
    )
    for sa in (1, -1):
        for sb in (1, -1):
            for _ in range(4):
                a32, b32 = t.rand(30) | 1, t.rand(12) | 2
                a64, b64 = t.rand(62) | 1, t.rand(20) | 2
                a32 += (b32 // 2) if a32 % b32 == 0 else 0
                a64 += (b64 // 2) if a64 % b64 == 0 else 0
                a = X(mask(sa * a32, 32), mask(sa * a64, 64))
                b = X(mask(sb * b32, 32), mask(sb * b64, 64))
                emit_case(t, "rem", a, b, f"dividend sign {sa:+d}, divisor sign {sb:+d}")
            small = X(mask(sa * 5, 32), mask(sa * 5, 64))
            emit_case(t, "rem", small, X(mask(sb * 7, 32), mask(sb * 7, 64)), "|dividend| < |divisor|")
            emit_case(
                t, "rem", X(mask(sa * 7, 32), mask(sa * 7, 64)), X(mask(sb * 2, 32), mask(sb * 2, 64)), "divisor ±2"
            )
            big = X(mask(sb * ((1 << 31) - 1), 32), mask(sb * ((1 << 63) - 1), 64))
            emit_case(t, "rem", X(mask(sa * ((1 << 31) - 2), 32), mask(sa * ((1 << 63) - 2), 64)), big, "divisor ±MAX")
    emit_case(t, "rem", class_val(t, "MIN"), class_val(t, "MAX"), "MIN rem MAX = -1")
    tests.append(t)

    # ---- divw_divuw_op ----
    def normal_divw(na: str, nb: str) -> bool:
        return nb == "0" or (na == "MIN" and nb == "-1")

    t = TestFile(SUITE, "divw_divuw_op", required=DIV_REQ, march=DIV_MARCH, rv64=True)
    t.describe(
        source=SRC,
        rule_text="DIVW and DIVUW are RV64 instructions that divide the lower 32 bits of rs1 by the lower 32 "
        "bits of rs2, treating them as signed and unsigned integers, placing the 32-bit quotient in rd, "
        "sign-extended to 64 bits.",
        context="DIVUW sign-extends its 32-bit unsigned quotient, so a quotient with bit 31 set reads as "
        "negative in rd.",
        plan="1. For DIVW and DIVUW: cross product of the 13 32-bit edge classes in the low halves, with "
        "random upper halves that must be ignored, excluding zero divisors and MIN / -1.\n"
        "2. Upper halves that would change a full 64-bit division (rs2 = 2 + k·2^32, rs1 with a set bit 63).\n"
        "3. 12 random pairs, register classes and a dependent pair.",
    )
    for insn in ("divw", "divuw"):
        cross(t, insn, EDGES, EDGES, w=True, skip=normal_divw)
        for _ in range(4):
            a = X(0, (t.rand(32) << 32) | t.rand(32))
            b = X(0, ((t.rand(31) | 1) << 32) | 2)
            emit_case(t, insn, a, b, "divisor low half 2, upper half nonzero")
        randoms(t, insn, 12, nonzero=True)
        register_classes(t, insn, nonzero=True)
    tests.append(t)

    # ---- remw_remuw_op ----
    t = TestFile(SUITE, "remw_remuw_op", required=DIV_REQ, march=DIV_MARCH, rv64=True)
    t.describe(
        source=SRC,
        rule_text="REMW and REMUW are RV64 instructions that provide the corresponding signed and unsigned "
        "remainder operations.",
        plan="1. For REMW and REMUW: cross product of the 13 32-bit edge classes in the low halves with "
        "random upper halves, excluding zero divisors and MIN / -1.\n"
        "2. 12 random pairs, register classes and a dependent pair.",
    )
    for insn in ("remw", "remuw"):
        cross(t, insn, EDGES, EDGES, w=True, skip=normal_divw)
        randoms(t, insn, 12, nonzero=True)
        register_classes(t, insn, nonzero=True)
    tests.append(t)

    # ---- remw_remuw_result_sign ----
    t = TestFile(SUITE, "remw_remuw_result_sign", required=DIV_REQ, march=DIV_MARCH, rv64=True)
    t.describe(
        source=SRC,
        rule_text="Both REMW and REMUW always sign-extend the 32-bit result to 64 bits, including on a divide by zero.",
        issues=f'{ISSUE}56: "The result is sign-extended." On a divide by zero, "dividend" '
        'means rs1[31:0] and "remainder" means rd[31:0].',
        plan="1. REMUW and REMW results with bit 31 set and clear (e.g. 0xFFFFFFFF remu 0x80000000+k).\n"
        "2. Divide by zero with low-half dividends that have bit 31 set and clear, random upper halves in "
        "both operands (a divisor whose low half is zero is a divide by zero).\n"
        "3. Signed overflow (remainder 0) with random upper halves.",
    )
    for insn in ("remuw", "remw"):
        for _ in range(4):
            lo = (1 << 31) | t.rand(31)
            d = (1 << 31) | t.rand(31)
            if lo < d:
                lo, d = d, lo
            emit_case(
                t, insn, X(0, (t.rand(32) << 32) | lo), X(0, (t.rand(32) << 32) | d), "32-bit operands with bit 31 set"
            )
            emit_case(
                t, insn, X(0, (t.rand(32) << 32) | t.rand(30)), X(0, (t.rand(32) << 32) | 7), "small positive remainder"
            )
        for bit31 in (0, 1):
            for _ in range(3):
                lo = (bit31 << 31) | t.rand(31)
                emit_case(
                    t,
                    insn,
                    X(0, (t.rand(32) << 32) | lo),
                    X(0, t.rand(32) << 32),
                    f"divide by zero, dividend bit 31 = {bit31}",
                )
        emit_case(t, insn, X(0, (t.rand(32) << 32) | 1 << 31), X(0, (t.rand(32) << 32) | 0xFFFFFFFF), "MIN32 by -1")
    tests.append(t)

    # ---- div_by_zero ----
    t = TestFile(SUITE, "div_by_zero", required=DIV_REQ, march=DIV_MARCH)
    t.describe(
        source=SRC,
        rule_text="The quotient of division by zero has all bits set",
        context="Table divby0: DIVU/DIVUW give 2^L-1 and DIV/DIVW give -1, where L is XLEN or 32 for the W "
        "forms. No exception is raised. For the W forms, a divisor is zero when its low 32 bits are zero.",
        plan="1. DIV and DIVU by zero for every edge-class dividend and 4 random dividends.\n"
        "2. RV64: DIVW and DIVUW by a divisor with zero low half and zero or random upper half, for every "
        "edge-class dividend (random upper half).\n"
        "3. rd=rs1 and rd=rs2 aliasing, x0 by x0, and a divide by zero whose quotient is used by the "
        "next instruction (quotient + 1 = 0).",
    )
    zero = X(0, 0)
    for insn in ("div", "divu"):
        for na in EDGES:
            emit_case(t, insn, class_val(t, na), zero, f"rs1={na} rs2=0")
        for _ in range(4):
            emit_case(t, insn, t.rand_x(), zero, "random dividend, rs2=0")
        r1, r2 = t.regs(2)
        emit_case(t, insn, t.rand_x(), zero, "rd=rs1, rs2=0", (r1, r1, r2))
        r1, r2 = t.regs(2)
        emit_case(t, insn, t.rand_x(), zero, "rd=rs2=0", (r2, r1, r2))
        r1 = t.regs(1)[0]
        lab = t.label(insn)
        t.emit(f"{lab}:", 0)
        t.emit(f"{insn} {r1}, x0, x0")
        t.check(r1, -1, lab, f"{insn} x0 by x0")
        # dependent use: the all-ones quotient feeds an add immediately
        ra, rb, rd = t.regs(3)
        a = t.rand_x()
        t.load(ra, a, "random dividend")
        t.emit(f"mv {rb}, x0")
        lab = t.label(insn)
        t.emit(f"{lab}:", 0)
        t.emit(f"{insn} {rd}, {ra}, {rb}")
        t.emit(f"addi {rd}, {rd}, 1")
        t.check(rd, 0, lab, f"{insn} by zero, quotient + 1 used immediately")
    with t.rv64_only():
        for i, na in enumerate(EDGES):
            upper = 0 if i % 3 == 0 else t.rand(32) << 32
            emit_case(
                t,
                ("divw", "divuw")[i % 2],
                class_val(t, na, w=True),
                X(0, upper),
                f"rs1={na} rs2 low half 0, upper half {'0' if upper == 0 else 'nonzero'}",
            )
            emit_case(
                t,
                ("divuw", "divw")[i % 2],
                class_val(t, na, w=True),
                X(0, upper),
                f"rs1={na} rs2 low half 0, upper half {'0' if upper == 0 else 'nonzero'}",
            )
    tests.append(t)

    # ---- rem_by_zero ----
    t = TestFile(SUITE, "rem_by_zero", required=DIV_REQ, march=DIV_MARCH)
    t.describe(
        source=SRC,
        rule_text="the remainder of division by zero equals the dividend.",
        context="Table divby0: REM, REMU, REMW and REMUW return x, the dividend. For the W forms the result "
        "is the 32-bit dividend sign-extended (remw_remuw_result_sign).",
        issues=f"{ISSUE}56: for REMW/REMUW the dividend is rs1[31:0] and the result is sign-extended.",
        plan="1. REM and REMU by zero for every edge-class dividend and 4 random dividends, plus rd=rs1 and "
        "rd=rs2 aliasing.\n"
        "2. RV64: REMW and REMUW by a divisor with zero low half (random upper half) for every edge-class "
        "dividend with random upper half.",
    )
    for insn in ("rem", "remu"):
        for na in EDGES:
            emit_case(t, insn, class_val(t, na), zero, f"rs1={na} rs2=0")
        for _ in range(4):
            emit_case(t, insn, t.rand_x(), zero, "random dividend, rs2=0")
        r1, r2 = t.regs(2)
        emit_case(t, insn, t.rand_x(), zero, "rd=rs1, rs2=0", (r1, r1, r2))
        r1, r2 = t.regs(2)
        emit_case(t, insn, t.rand_x(), zero, "rd=rs2=0", (r2, r1, r2))
    with t.rv64_only():
        for insn in ("remw", "remuw"):
            for na in EDGES:
                emit_case(t, insn, class_val(t, na, w=True), X(0, t.rand(32) << 32), f"rs1={na} rs2 low half 0")
    tests.append(t)

    # ---- signed_div_overflow ----
    t = TestFile(SUITE, "signed_div_overflow", required=DIV_REQ, march=DIV_MARCH)
    t.describe(
        source=SRC,
        rule_text="Signed division overflow occurs only when the most-negative integer is divided by −1. "
        "The quotient of a signed division with overflow is equal to the dividend, and the remainder is "
        "zero.",
        context="Unsigned division overflow cannot occur. For DIVW/REMW the operands are the low 32 bits.",
        plan="1. DIV and REM of MIN by -1 (overflow), with register aliasing (rd=rs1, rd=rs2) and a dependent "
        "use of the quotient by the next instruction.\n"
        "2. Near misses that must not be treated as overflow: MIN/1, MIN/-2, MIN/MAX, (MIN+1)/-1, "
        "-1/MIN, and the unsigned DIVU/REMU of the same bit patterns.\n"
        "3. RV64: DIVW and REMW of 0x80000000 by 0xFFFFFFFF in the low halves with random upper halves "
        "(overflow), full 64-bit DIV/REM of the same register values (no overflow), and DIVUW/REMUW of the "
        "same values (unsigned: no special case).",
    )
    near = [("MIN", "-1"), ("MIN", "1"), ("MIN", "-2"), ("MIN", "MAX"), ("MIN+1", "-1"), ("-1", "MIN")]
    for insn in ("div", "rem", "divu", "remu"):
        for na, nb in near:
            emit_case(t, insn, class_val(t, na), class_val(t, nb), f"rs1={na} rs2={nb}")
    for insn in ("div", "rem"):
        r1, r2 = t.regs(2)
        emit_case(t, insn, class_val(t, "MIN"), class_val(t, "-1"), "MIN/-1 rd=rs1", (r1, r1, r2))
        r1, r2 = t.regs(2)
        emit_case(t, insn, class_val(t, "MIN"), class_val(t, "-1"), "MIN/-1 rd=rs2", (r2, r1, r2))
    ra, rb, rd = t.regs(3)
    t.load(ra, class_val(t, "MIN"), "MIN")
    t.load(rb, class_val(t, "-1"), "-1")
    lab = t.label("div_dep")
    t.emit(f"{lab}:", 0)
    t.emit(f"div {rd}, {ra}, {rb}")
    t.emit(f"sub {rd}, {rd}, {ra}")
    t.check(rd, 0, lab, "MIN/-1 quotient used immediately: quotient - dividend = 0")
    with t.rv64_only():
        for insn in ("divw", "remw", "div", "rem", "divuw", "remuw"):
            for _ in range(2):
                a = X(0, (t.rand(32) << 32) | 0x80000000)
                b = X(0, (t.rand(32) << 32) | 0xFFFFFFFF)
                emit_case(t, insn, a, b, "low halves 0x80000000 / 0xFFFFFFFF, random upper halves")
    tests.append(t)

    return tests


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
