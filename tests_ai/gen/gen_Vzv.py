#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the Zv* rule-derived tests: one test per normative rule of src/unpriv/zvbb.adoc, zvbc.adoc, zvfh.adoc,
zvfhmin.adoc, zvfbfmin.adoc, zvfbfwma.adoc and zvk.adoc, written to tests_ai/<extension>/ (Zvbb, Zvkb, Zvbc, Zvfh,
Zvfhmin, Zvfbfmin, Zvfbfwma, Zvkned, Zvknha, Zvknhb, Zvkg, Zvksed, Zvksh and the Zvkn*/Zvks* shorthands).

Expected values come from the instruction descriptions and operation pseudocode in those chapters (vzvlib.py),
whose crypto references reproduce the FIPS-197, FIPS-180, GCM, SM3 and SM4 standard test vectors. VLEN, ELEN and
the supported LMULs are read or probed at run time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import vzvlib as L
from aigen import X, sext
from vzvlib import ILLEGAL, M32, M64, RULES, VT, W, eg_words, msk, pack

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

SUITE = "Vzv"
MUT = os.environ.get("AI_MUTANT", "")
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"

MUTANTS = {
    # bit manipulation (Zvbb/Zvkb)
    "vandn_swapped": "vandn inverts vs2 instead of vs1/rs1",
    "vandn_vx_zext": "vandn.vx zero-extends rs1 to SEW on RV32 with SEW=64",
    "vrol_no_mask": "vrol/vror use log2(2*SEW) bits of the rotate amount",
    "vror_vi_no_i5": "vror.vi ignores uimm[5] (the i5 bit)",
    "vwsll_sext": "vwsll sign-extends vs2 before shifting",
    "vwsll_mask_sew": "vwsll uses only log2(SEW) bits of the shift amount",
    "vclz_zero_sewm1": "vclz of zero gives SEW-1",
    "vctz_zero_sewm1": "vctz of zero gives SEW-1",
    "vrev8_bits": "vrev8 reverses bits instead of bytes",
    "vbrev8_whole": "vbrev8 reverses the whole element",
    "vcpop_low32": "vcpop counts only the low 32 bits",
    "vbrev_bytes": "vbrev reverses bits within bytes only",
    # Zvbc
    "vclmulh_shift1": "vclmulh returns product bits 126:63",
    "vclmul_vx_ignored": "vclmul.vx uses element 0 of vs1 instead of rs1",
    # crypto control
    "vs_uses_group_i": ".vs instructions take the round key from vs2 element group i",
    "vs_needs_lmul_align": "a .vs vs2 that is not LMUL-aligned raises illegal-instruction (VLEN >= 128)",
    "egw_vl0_no_trap": "LMUL*VLEN < EGW does not trap when vl = 0",
    "vstart_ignored": "element-group instructions ignore vstart (group 0 is processed)",
    "vstart_not_reset": "vstart keeps its value after an element-group instruction",
    "vl_ignored": "element-group instructions process VLMAX/EGS groups regardless of vl",
    # crypto arithmetic (vzvlib)
    "aes_shiftrows_swapped": "AES ShiftRows and InvShiftRows swapped",
    "aesdm_mix_before_ark": "vaesdm applies InvMixColumns before AddRoundKey",
    "aeskf_uimm4_used": "vaeskf1/vaeskf2 use uimm[4]",
    "aeskf_no_map": "vaeskf1/vaeskf2 do not map out-of-range rounds",
    "aeskf2_parity_swapped": "vaeskf2 applies RotWord/Rcon on odd rounds",
    "sha2c_hl_swapped": "vsha2ch/vsha2cl message words swapped",
    "ghash_poly_wrong": "GHASH reduces with x^7+x^2+1",
    "ghash_no_add": "vghsh does not add the cipher block",
    "gmul_no_brev": "vgmul does not reverse the bits of each byte",
    "sm4k_uimm43_used": "vsm4k uses uimm[4:3] (round groups 8..31 index past the CK table)",
    "sm4r_key_schedule_l": "vsm4r uses the key-schedule linear transform",
    "sm3_no_byteswap": "vsm3me does not byte-swap",
    "sm3c_round_off_by_one": "vsm3c selects FF/GG one round late",
    # FP
    "fp16_as_bf16": "SEW=16 FP operands use the BF16 format",
    "fp16_ftz": "binary16 subnormal results are flushed to zero",
    "cvt8_wraps": "vfncvt.x.f.w to 8 bits wraps instead of saturating",
    "bf16_ties_away": "vfncvtbf16 rounds ties away from zero under RNE",
    "bf16_frm_ignored": "vfncvtbf16 always rounds to nearest even",
    "bf16_nan_payload": "vfncvtbf16 keeps the NaN payload",
    "bf16_uf_before_rounding": "BF16 tininess is detected before rounding",
    "bf16_wcvt_snan_quiet": "vfwcvtbf16 of a signaling NaN raises no invalid flag",
    "bfwma_double_round": "vfwmaccbf16 rounds the product to FP32 before adding",
    "bfwma_nanbox_ignored": "vfwmaccbf16.vf uses an improperly NaN-boxed scalar as is",
    "fwcvt_nan_payload": "vfwcvt.f.f.v keeps the NaN payload",
}


def out(ext: str) -> str:
    return ext if SUITE == "Vzv" else SUITE


def new(ext: str, rule: str, req: Sequence[object], exts: Sequence[str] | None = None) -> VT:
    """A test of `rule` in tests_ai/<ext>/. req: required extensions besides I (lists are alternatives).
    exts: extensions whose instructions the test assembles (default: the plain names in req)."""
    names = exts or [r for r in req if isinstance(r, str)]
    suffix = f"_{ext}" if SUITE != "Vzv" else ""  # one mutant directory holds every extension's files
    t = VT(out(ext), rule, required=["I", *req], march=L.march(list(names)), suffix=suffix)
    return t


def doc(t: VT, plan: str, context: str = "", issues: str = "") -> None:
    src, text = RULES[t.rule]
    t.describe(rule_text=text, source=src, context=context, issues=issues, plan=plan)


TESTS: list[VT] = []


def add(t: VT) -> VT:
    TESTS.append(t)
    return t


# ================================================================ element-wise helpers (Zvbb, Zvkb, Zvbc)

ZVE64 = "defined(ZVE64X_SUPPORTED)"


def edges(sew: int, t: VT) -> list[int]:
    m = msk(sew)
    return [0, 1, m, 1 << (sew - 1), (1 << (sew - 1)) - 1, int("5" * (sew // 4), 16), int("a" * (sew // 4), 16),
            t.rand(sew)]  # fmt: skip


def ew(
    t: VT,
    mn: str,
    sew: int,
    vs2: Sequence[int],
    ref: Callable[[int, int, int], int | X],
    *,
    vs1: Sequence[int] | None = None,
    rs1: int | X | None = None,
    imm: int | None = None,
    widen: bool = False,
    desc: str = "",
    regs: tuple[str, str, str] = ("v8", "v16", "v24"),
) -> None:
    """One element-wise instruction on len(vs2) <= 8 elements. ref(a, b, xlen) gives element i from vs2[i] and the
    second operand (vs1[i], rs1 or imm)."""
    n = len(vs2)
    vd, v2, v1 = regs
    lmul = "m4" if widen else "m8"
    t.vset(n, sew, lmul)
    t.vload(v2, pack(vs2, sew), sew)
    if vs1 is not None:
        if v1 != v2:
            t.vload(v1, pack(vs1, sew), sew)
        op = v1
        seconds: list[int | X] = list(vs1)
    elif rs1 is not None:
        t.load("x7", rs1)
        op = "x7"
        seconds = [rs1] * n
    elif imm is not None:
        op = str(imm)
        seconds = [imm] * n
    else:
        op = ""
        seconds = [0] * n
    line = f"{mn} {vd}, {v2}" + (f", {op}" if op else "")
    lab = t.insn(line)
    rsew = 2 * sew if widen else sew
    res = {}
    for xlen in (32, 64):
        vals = []
        for a, b in zip(vs2, seconds):
            bv = b.num(xlen) if isinstance(b, X) else b
            r = ref(a, bv, xlen)
            vals.append(r.num(xlen) if isinstance(r, X) else r)
        res[xlen] = pack(vals, rsew)
    words: list[int | X] = [w32 if w32 == w64 else X(w32, w64) for w32, w64 in zip(res[32], res[64])]
    if widen:
        t.vset(n, rsew, "m8")
    t.vcheck(vd, words, lab, f"{desc or line} (SEW={sew})", eew=rsew, nbytes=n * rsew // 8)


def ew_all(t: VT, sews: Sequence[int], body: Callable[[int], None]) -> None:
    for sew in sews:
        if sew == 64:
            with t.only_if(ZVE64):
                body(sew)
        else:
            body(sew)


# reference semantics with mutants
def r_vandn(a: int, b: int, sew: int) -> int:
    if MUT == "vandn_swapped":
        return ~a & b & msk(sew)
    return ~b & a & msk(sew)


def rs1_op(b: int, xlen: int, sew: int) -> int:
    """A scalar operand sign-extended or truncated to SEW."""
    if MUT == "vandn_vx_zext" and xlen == 32:
        return b & M32 & msk(sew)
    return sext(b, xlen) & msk(sew)


def r_rot(a: int, b: int, sew: int, left: bool) -> int:
    if MUT == "vrol_no_mask" and (b & (2 * sew - 1)) >= sew:
        return 0  # the mutant shifts by the unmasked amount, so every bit is shifted out
    amt = b & (sew - 1)
    return L.rol(a, amt, sew) if left else L.ror(a, amt, sew)


def r_vwsll(a: int, b: int, sew: int) -> int:
    av = sext(a, sew) & msk(2 * sew) if MUT == "vwsll_sext" else a & msk(sew)
    amt = b & ((sew - 1) if MUT == "vwsll_mask_sew" else (2 * sew - 1))
    return (av << amt) & msk(2 * sew)


def r_clz(a: int, sew: int) -> int:
    if MUT == "vclz_zero_sewm1" and a & msk(sew) == 0:
        return sew - 1
    return L.clz(a, sew)


def r_ctz(a: int, sew: int) -> int:
    if MUT == "vctz_zero_sewm1" and a & msk(sew) == 0:
        return sew - 1
    return L.ctz(a, sew)


def r_rev8(a: int, sew: int) -> int:
    return L.brev(a, sew) if MUT == "vrev8_bits" else L.rev8(a, sew)


def r_brev8(a: int, sew: int) -> int:
    return L.brev(a, sew) if MUT == "vbrev8_whole" else L.brev8(a, sew)


def r_brev(a: int, sew: int) -> int:
    return L.brev8(a, sew) if MUT == "vbrev_bytes" else L.brev(a, sew)


def r_cpop(a: int, sew: int) -> int:
    return L.cpop(a & M32 if MUT == "vcpop_low32" else a, sew)


def unary(t: VT, mn: str, sew: int, vals: Sequence[int], f: Callable[[int, int], int], desc: str = "") -> None:
    ew(t, mn, sew, vals, lambda a, b, x: f(a, sew), desc=desc)


# ================================================================ Zvbb and Zvkb


def gen_zvkb() -> None:
    ZB = ["Zvkb"]
    SEWS = (8, 16, 32, 64)

    t = add(new("Zvkb", "vandn_op", ZB))
    doc(t, "vandn.vv and vandn.vx at SEW=8, 16, 32 and 64 (Zve64x): Op2 (vs2) ANDed with the complement of Op1 on "
           "edge values (0, 1, all ones, MSB, MAX, 0x55.., 0xAA.., random) against all-ones, alternating and random "
           "second operands.")  # fmt: skip

    def b_vandn(sew: int) -> None:
        a = edges(sew, t)
        b = [msk(sew), int("a" * (sew // 4), 16), t.rand(sew), 0, msk(sew), t.rand(sew), t.rand(sew), msk(sew)]
        ew(t, "vandn.vv", sew, a, lambda x, y, xl: r_vandn(x, y, sew), vs1=b)
        ew(t, "vandn.vx", sew, a, lambda x, y, xl: r_vandn(x, rs1_op(y, xl, sew), sew), rs1=X(t.rand(32), t.rand(64)))

    ew_all(t, SEWS, b_vandn)

    t = add(new("Zvkb", "vandn-vx_rs1", ZB))
    doc(t, "vandn.vx with vs2 all ones, so vd = ~Op1 shows Op1. SEW < XLEN: rs1 has random bits above SEW, which "
           "are truncated. SEW=64 (Zve64x): on RV32, rs1 with bit 31 set and clear (sign-extended to 64 bits); on "
           "RV64 the full register. Also rs1 = x0.")  # fmt: skip

    def b_vx(sew: int) -> None:
        ones = [msk(sew)] * 4
        for v in (X(0x80000001 | t.rand(31), (1 << 63) | t.rand(63)), X(t.rand(31), t.rand(63)),
                  X(0xFFFFFFFF, M64), X(1 << 31, 1 << 63)):  # fmt: skip
            ew(t, "vandn.vx", sew, ones, lambda x, y, xl: r_vandn(x, rs1_op(y, xl, sew), sew), rs1=v,
               desc="vandn.vx vd, vs2=all ones, rs1")  # fmt: skip
        n = 4
        t.vset(n, sew)
        t.vload("v16", pack(ones, sew), sew)
        lab = t.insn("vandn.vx v8, v16, x0")
        t.vcheck("v8", pack(ones, sew), lab, f"vandn.vx rs1=x0 (SEW={sew})", eew=sew)

    ew_all(t, SEWS, b_vx)

    t = add(new("Zvkb", "vandn-vv_vs1", ZB))
    doc(t, "vandn.vv with asymmetric operands (the complemented operand is vs1): random vs1/vs2 at every SEW, "
           "vd = vs1 and vd = vs2 aliasing (sources are read before the write), and vs1 = vs2 (result 0).")  # fmt: skip

    def b_vv(sew: int) -> None:
        a = [t.rand(sew) for _ in range(4)] + [msk(sew), 0, msk(sew), 0x5A & msk(sew)]
        b = [t.rand(sew) for _ in range(4)] + [0, msk(sew), 1, 0xF0 & msk(sew)]
        f = lambda x, y, xl: r_vandn(x, y, sew)
        ew(t, "vandn.vv", sew, a, f, vs1=b)
        ew(t, "vandn.vv", sew, a, f, vs1=b, regs=("v24", "v16", "v24"), desc="vandn.vv vd=vs1")
        ew(t, "vandn.vv", sew, a, f, vs1=b, regs=("v16", "v16", "v24"), desc="vandn.vv vd=vs2")
        ew(t, "vandn.vv", sew, a, f, vs1=a, regs=("v8", "v16", "v16"), desc="vandn.vv vs1=vs2")

    ew_all(t, SEWS, b_vv)

    t = add(new("Zvkb", "vbrev8-v_op", ZB))
    doc(t, "vbrev8.v at SEW=8..64: single-bit, byte-asymmetric (0x01, 0x80, 0x0F, 0x12..) and random elements; bits "
           "are reversed within each byte, the byte order is kept.")  # fmt: skip

    def b_brev8(sew: int) -> None:
        unary(t, "vbrev8.v", sew, edges(sew, t), r_brev8)
        nb = sew // 8
        vals = [int("12" * nb, 16), int("0f" * nb, 16), 0x8001 & msk(sew), 1 << (sew - 8), t.rand(sew), t.rand(sew),
                0x80, int("01" * nb, 16)]  # fmt: skip
        unary(t, "vbrev8.v", sew, vals, r_brev8)

    ew_all(t, SEWS, b_brev8)

    t = add(new("Zvkb", "vrev8-v_op", ZB))
    doc(t, "vrev8.v at SEW=8 (identity), 16, 32 and 64: elements with distinct bytes (0x0102..), single bytes at "
           "each end, and random values.")  # fmt: skip

    def b_rev8(sew: int) -> None:
        nb = sew // 8
        vals = [int("".join(f"{k + 1:02x}" for k in range(nb)), 16), 0xFF, 0xFF << (sew - 8), 1, 1 << (sew - 1),
                t.rand(sew), t.rand(sew), int("a5" + "00" * (nb - 1), 16)]  # fmt: skip
        unary(t, "vrev8.v", sew, vals, r_rev8)

    ew_all(t, SEWS, b_rev8)

    t = add(new("Zvkb", "vrol_op", ZB))
    doc(t, "vrol.vv and vrol.vx at every SEW: rotate amounts 0, 1, SEW-1, SEW (= 0), SEW+1, 2*SEW-1, all ones and "
           "amounts with only high bits set, so only log2(SEW) bits count; rs1 with random upper bits (all XLEN "
           "bits above log2(SEW) ignored, also on RV32 at SEW=64).")  # fmt: skip

    def b_rol(sew: int) -> None:
        data = [t.rand(sew) | 1 | (1 << (sew - 1)) for _ in range(8)]
        amts = [0, 1, sew - 1, sew, sew + 1, 2 * sew - 1, msk(sew), (msk(sew) & ~(sew - 1)) | 3]
        ew(t, "vrol.vv", sew, data, lambda a, b, x: r_rot(a, b, sew, True), vs1=amts)
        for r in (X(0xFFFFFF00 | 5, M64 & ~0xFF | 5), X(sew + 3, sew + 3), X(t.rand(32), t.rand(64))):
            ew(t, "vrol.vx", sew, data[:4], lambda a, b, x: r_rot(a, b, sew, True), rs1=r)

    ew_all(t, SEWS, b_rol)

    t = add(new("Zvkb", "vror_op", ZB))
    doc(t, "vror.vv, vror.vx and vror.vi at every SEW: amounts as for vrol, rs1 with random upper bits, and uimm "
           "values 0, 1, SEW-1 and above SEW (uimm[5] is the i5 bit; at SEW=64 amounts 32..63 need it, at SEW<64 "
           "uimm >= SEW is reduced mod SEW).")  # fmt: skip

    def b_ror(sew: int) -> None:
        data = [t.rand(sew) | 1 | (1 << (sew - 1)) for _ in range(8)]
        amts = [0, 1, sew - 1, sew, sew + 1, 2 * sew - 1, msk(sew), (msk(sew) & ~(sew - 1)) | 5]
        ew(t, "vror.vv", sew, data, lambda a, b, x: r_rot(a, b, sew, False), vs1=amts)
        for r in (X(0xFFFFFF00 | 7, M64 & ~0xFF | 7), X(t.rand(32), t.rand(64))):
            ew(t, "vror.vx", sew, data[:4], lambda a, b, x: r_rot(a, b, sew, False), rs1=r)
        for u in sorted({0, 1, sew - 1, 31, 32, 33, 47, 63, sew + 2 if sew < 62 else 62}):

            def ref(a: int, b: int, x: int, u: int = u) -> int:
                uu = u & 31 if MUT == "vror_vi_no_i5" else u
                return r_rot(a, uu, sew, False)

            ew(t, "vror.vi", sew, data[:2], ref, imm=u)

    ew_all(t, SEWS, b_ror)

    t = add(new("Zvkb", "Zvkb_Zvkg_Zvkned_Zvknha_Zvksed_Zvksh_Zvks_Zvksc_Zvksg_Zvkt_depZve32x",
                [["Zvkb", "Zvkg", "Zvkned", "Zvknha", "Zvksed", "Zvksh"]], exts=["zve32x"]))  # fmt: skip
    doc(t, "The Zve32x dependency is observable as Zve32x features being present: vsetvli with SEW=8, 16 and 32 at "
           "LMUL=1 does not set vill (Zve32x supports every SEW <= 32 at LMUL=1), vlenb >= 4 (VLEN >= 32), and a "
           "vadd.vv at SEW=32 computes element-wise sums.")  # fmt: skip
    dep_zve(t, 32)


def dep_zve(t: VT, elen: int) -> None:
    """Zve32x/Zve64x presence: SEWs up to elen are legal at LMUL=1, VLEN >= elen, integer vector arithmetic works."""
    for sew in (8, 16, 32, 64):
        if sew > elen:
            break
        t.vset(1, sew, "m1")
        lab = t.label("vtype")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, vtype")
        t.emit("slt x7, x7, x0  // vill")
        t.check("x7", 0, lab, f"e{sew}, m1 is a legal vtype (vill = 0)")
    lab = t.label("vlenb")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, vlenb")
    t.emit(f"sltiu x7, x7, {elen // 8}")
    t.check("x7", 0, lab, f"vlenb >= {elen // 8} (VLEN >= ELEN = {elen})")
    vals = [t.rand(elen) for _ in range(4)]
    vals2 = [t.rand(elen) for _ in range(4)]
    ew(t, "vadd.vv", elen, vals, lambda a, b, x: (a + b) & msk(elen), vs1=vals2)


def gen_zvbb() -> None:
    ZB = ["Zvbb"]

    def every(t: VT, sew: int) -> None:
        a = [0x81 & msk(sew) | (1 << (sew - 1)), t.rand(sew)]
        b = [3, t.rand(sew)]
        ew(t, "vandn.vv", sew, a, lambda x, y, xl: r_vandn(x, y, sew), vs1=b)
        ew(
            t,
            "vandn.vx",
            sew,
            a,
            lambda x, y, xl: r_vandn(x, rs1_op(y, xl, sew), sew),
            rs1=X(0x5A5A5A5A, 0x5A5A5A5A5A5A5A5A),
        )
        for mn, f in (("vbrev.v", r_brev), ("vbrev8.v", r_brev8), ("vrev8.v", r_rev8), ("vclz.v", r_clz),
                      ("vctz.v", r_ctz), ("vcpop.v", r_cpop)):  # fmt: skip
            unary(t, mn, sew, a, f)
        ew(t, "vrol.vv", sew, a, lambda x, y, xl: r_rot(x, y, sew, True), vs1=[1, sew - 1])
        ew(t, "vrol.vx", sew, a, lambda x, y, xl: r_rot(x, y, sew, True), rs1=3)
        ew(t, "vror.vv", sew, a, lambda x, y, xl: r_rot(x, y, sew, False), vs1=[1, sew - 1])
        ew(t, "vror.vx", sew, a, lambda x, y, xl: r_rot(x, y, sew, False), rs1=3)
        ew(t, "vror.vi", sew, a, lambda x, y, xl: r_rot(x, y, sew, False), imm=5)

    def wsll(t: VT, sew: int) -> None:
        a = [1 << (sew - 1) | 1, t.rand(sew)]
        ew(t, "vwsll.vv", sew, a, lambda x, y, xl: r_vwsll(x, y, sew), vs1=[sew, 3], widen=True)
        ew(t, "vwsll.vx", sew, a, lambda x, y, xl: r_vwsll(x, y, sew), rs1=sew + 1, widen=True)
        ew(t, "vwsll.vi", sew, a, lambda x, y, xl: r_vwsll(x, y, sew), imm=7, widen=True)

    t = add(new("Zvbb", "Zvbb_eew", ZB))
    doc(t, "Every Zvbb instruction (vandn.vv/.vx, vbrev, vbrev8, vrev8, vclz, vctz, vcpop, vrol.vv/.vx, "
           "vror.vv/.vx/.vi) executes at SEW=8, 16 and 32 (LMUL=8) on two elements with the defined result; "
           "vwsll.vv/.vx/.vi at SEW=8 and 16 (EEW 16 and 32 results; SEW=32 widening to EEW=64 needs Zve64x and is "
           "in Zvbb_eew_Zve64x).")  # fmt: skip
    for sew in (8, 16, 32):
        every(t, sew)
    for sew in (8, 16):
        wsll(t, sew)

    t = add(new("Zvbb", "Zvbb_eew_Zve64x", [*ZB, "Zve64x"], exts=["Zvbb", "zve64x"]))
    doc(t, "Requires Zve64x. Every Zvbb instruction at SEW=64 on two elements, and vwsll.vv/.vx/.vi at SEW=32 "
           "(EEW=64 results).")  # fmt: skip
    every(t, 64)
    wsll(t, 32)

    sews = (8, 16, 32, 64)
    for rule, mn, f, plan in (
        ("vbrev-v_op", "vbrev.v", r_brev, ("vbrev.v at every SEW: 0, 1 (-> MSB), MSB (-> 1), all ones, 0x55.., "
         "0xAA.. (-> each other's complement pattern), MAX and random elements.")),
        ("vclz-v_op", "vclz.v", r_clz, ("vclz.v at every SEW: 1 (SEW-1), MSB (0), all ones (0), MAX (1), single bits "
         "at every byte position, and random elements.")),
        ("vcpop-v_op", "vcpop.v", r_cpop, ("vcpop.v at every SEW: 0, all ones (SEW), single bits, 0x55.. (SEW/2), "
         "values with only the upper half set, and random elements.")),
        ("vctz-v_op", "vctz.v", r_ctz, ("vctz.v at every SEW: 0 (SEW, as the operation's loop gives), 1 (0), MSB "
         "(SEW-1), single bits at every byte position, and random elements.")),
    ):  # fmt: skip
        t = add(new("Zvbb", rule, ZB))
        doc(t, plan)

        def body(sew: int, t: VT = t, mn: str = mn, f: Callable = f) -> None:
            unary(t, mn, sew, edges(sew, t), f)
            singles = [1 << b for b in range(3, sew, max(1, sew // 8))][:6] + [msk(sew) ^ msk(sew // 2), msk(sew // 2)]
            unary(t, mn, sew, singles[:8], f)

        ew_all(t, sews, body)

    t = add(new("Zvbb", "vclz-v_op_zeroinput", ZB))
    doc(t, "vclz.v on zero elements at every SEW gives SEW (8, 16, 32, 64), with zero elements next to nonzero ones "
           "(so a shared count does not leak), at LMUL=8 and at LMUL=1 with vl=1.")  # fmt: skip

    def zclz(sew: int) -> None:
        unary(t, "vclz.v", sew, [0, 1, 0, msk(sew), 0, 0, 1 << (sew - 1), 0], r_clz)
        t.vset(1, sew, "m1")
        t.vload("v3", pack([0], sew), sew)
        lab = t.insn("vclz.v v5, v3")
        t.vcheck("v5", pack([r_clz(0, sew)], sew), lab, f"vclz.v of 0, LMUL=1 (SEW={sew})", sew, nbytes=sew // 8)

    ew_all(t, sews, zclz)

    t = add(new("Zvbb", "vwsll_op", ZB))
    doc(t, "vwsll.vv, .vx and .vi at SEW=8, 16 and 32 (Zve64x): data with the MSB set (zero-extension, not "
           "sign-extension), shift amounts 0, 1, SEW-1, SEW, SEW+1, 2*SEW-1, 2*SEW (-> 0) and all ones (only "
           "log2(2*SEW) bits count); rs1 with random upper bits; uimm 0..31 (at SEW=8, uimm >= 16 wraps).")  # fmt: skip

    def b_wsll(sew: int) -> None:
        data = [1 << (sew - 1) | 1, msk(sew), t.rand(sew) | 1 << (sew - 1), t.rand(sew), 1, msk(sew), 1 << (sew - 1),
                t.rand(sew)]  # fmt: skip
        amts = [0, 1, sew - 1, sew, sew + 1, 2 * sew - 1, (2 * sew) & msk(sew), msk(sew)]
        ew(t, "vwsll.vv", sew, data, lambda a, b, x: r_vwsll(a, b, sew), vs1=amts, widen=True)
        for r in (X(0xFFFFFF00 | (sew + 3), (M64 & ~0xFF) | (sew + 3)), X(t.rand(32), t.rand(64)), X(2 * sew, 2 * sew)):
            ew(t, "vwsll.vx", sew, data[:4], lambda a, b, x: r_vwsll(a, b, sew), rs1=r, widen=True)
        for u in sorted({0, 1, sew - 1, sew, 2 * sew - 1, 17, 31} & set(range(32))):
            ew(t, "vwsll.vi", sew, data[:2], lambda a, b, x: r_vwsll(a, b, sew), imm=u, widen=True)

    for sew in (8, 16):
        b_wsll(sew)
    with t.only_if(ZVE64):
        b_wsll(32)

    t = add(new("Zvbb", "Zvbb_dependent_Zve32x", ZB, exts=["zve32x"]))
    doc(t, "The Zve32x dependency, observed as its features: SEW=8, 16 and 32 at LMUL=1 are legal vtypes, VLEN >= "
           "32, and vadd.vv works at SEW=32.")  # fmt: skip
    dep_zve(t, 32)


# ================================================================ Zvbc


def r_clmul(a: int, b: int, high: bool) -> int:
    p = L.clmul_full(a & M64, b & M64)
    if high:
        return ((p >> 63) if MUT == "vclmulh_shift1" else (p >> 64)) & M64
    return p & M64


def gen_zvbc() -> None:
    ZC = ["Zve64x", "Zvbc"]
    for rule, high in (("vclmul_op", False), ("vclmulh_op", True)):
        mn = "vclmulh" if high else "vclmul"
        t = add(new("Zvbc", rule, ZC, exts=["Zvbc"]))
        doc(t, f"{mn}.vv and {mn}.vx at SEW=64: operands 0, 1, MSB, all ones, 0x55.., 0xAA.. and random against "
               "random multipliers (so every product bit position is exercised); vd = vs1 aliasing. On RV32, .vx "
               "takes rs1 with bit 31 clear (same value either way) and with bit 31 set, where the 64-bit operand is "
               "accepted zero-extended (the operation pseudocode's zext_or_truncate_to_sew) or sign-extended (the "
               "usual vector-scalar convention): the text only says 'the 64-bit value from integer register rs1'.",
            context="zvbc.adoc pseudocode: op1 = zext_or_truncate_to_sew(X(rs1)) for .vx.")  # fmt: skip
        a = edges(64, t)
        b = [t.rand(64) for _ in range(6)] + [M64, 1 << 63]
        ew(t, f"{mn}.vv", 64, a, lambda x, y, xl, high=high: r_clmul(x, y, high), vs1=b)
        ew(t, f"{mn}.vv", 64, a, lambda x, y, xl, high=high: r_clmul(x, y, high), vs1=b, regs=("v24", "v16", "v24"),
           desc=f"{mn}.vv vd=vs1")  # fmt: skip
        for r in (X(0x7FFFFFFF & t.rand(32) | 1, t.rand(64)), X(1, M64)):
            ew(t, f"{mn}.vx", 64, a[:4], lambda x, y, xl, high=high: r_clmul(x, y & msk(xl), high)
               if MUT != "vclmul_vx_ignored" else r_clmul(x, 0, high), rs1=r)  # fmt: skip
        # RV32, rs1 bit 31 set: zero- or sign-extended
        with t.rv32_only():
            rs1 = 0x80000000 | t.rand(31)
            data = [t.rand(64), M64]
            t.vset(2, 64)
            t.vload("v16", pack(data, 64), 64)
            t.li("x7", sext(rs1, 32))
            lab = t.insn(f"{mn}.vx v8, v16, x7")
            t.la("x1", t.out)
            t.emit("vse64.v v8, (x1)")
            for i, d in enumerate(data):
                z = pack([r_clmul(d, rs1, high)], 64)
                s = pack([r_clmul(d, sext(rs1, 32) & M64, high)], 64)
                t.emit(f"lw x6, {8 * i}(x1)")
                t.emit(f"lw x8, {8 * i + 4}(x1)")
                # ok = (lo == zlo && hi == zhi) || (lo == slo && hi == shi)
                t.li("x9", sext(z[0], 32))
                t.emit("xor x9, x9, x6")
                t.li("x10", sext(z[1], 32))
                t.emit("xor x10, x10, x8")
                t.emit("or x9, x9, x10")
                t.emit("seqz x9, x9")
                t.li("x10", sext(s[0], 32))
                t.emit("xor x10, x10, x6")
                t.li("x11", sext(s[1], 32))
                t.emit("xor x11, x11, x8")
                t.emit("or x10, x10, x11")
                t.emit("seqz x10, x10")
                t.emit("or x9, x9, x10")
                t.check_bool("x9", lab, f"{mn}.vx RV32 rs1 bit 31 set, element {i}: the zero- or sign-extended "
                                        f"product (0x{z[1]:08x}{z[0]:08x} or 0x{s[1]:08x}{s[0]:08x})")  # fmt: skip

    t = add(new("Zvbc", "Zvbc_sew64only", ZC, exts=["Zvbc"]))
    doc(t, "The instructions are defined for SEW=64 (other SEWs are reserved and not tested): vclmul.vv/.vx and "
           "vclmulh.vv/.vx execute at SEW=64 with LMUL=1, 2, 4 and 8 on one element.")  # fmt: skip
    for lmul in ("m1", "m2", "m4", "m8"):
        a, b = t.rand(64), t.rand(64)
        for mn, hi in (("vclmul", False), ("vclmulh", True)):
            t.vset(1, 64, lmul)
            t.vload("v16", pack([a], 64), 64)
            t.vload("v24", pack([b], 64), 64)
            lab = t.insn(f"{mn}.vv v8, v16, v24")
            t.vcheck("v8", pack([r_clmul(a, b, hi)], 64), lab, f"{mn}.vv SEW=64 {lmul}", 64)

    t = add(new("Zvbc", "Zvbc_dependent_Zve64x", ZC, exts=["zve64x"]))
    doc(t, "The Zve64x dependency, observed as its features: SEW=8..64 at LMUL=1 are legal vtypes, VLEN >= 64, and "
           "vadd.vv works at SEW=64.")  # fmt: skip
    dep_zve(t, 64)


# ================================================================ vector FP helpers (Zvfh, Zvfhmin, Zvfbf*)


def fp_run(
    t: VT,
    line: str,
    vtype: tuple[int, int, str],
    loads: Sequence[tuple[str, Sequence[int], int]],
    store: tuple[str, int, int],
    expected: Sequence[int],
    flags: int | None,
    desc: str,
    rm: int = L.RNE,
    fregs: Sequence[tuple[str, int]] = (),
) -> str:
    """Set frm and vtype (vl, sew, lmul), load vector registers ((vreg, elements, eew)) and f registers ((freg,
    32-bit pattern)), run line, store (vreg, eew, n) and check the elements and fflags."""
    vl, sew, lmul = vtype
    t.frm(rm)
    t.vset(vl, sew, lmul)
    for vreg, elems, eew in loads:
        t.vload(vreg, pack(elems, eew), eew)
    for freg, bits in fregs:
        t.li("x7", sext(bits & M32, 32))
        t.emit(f"fmv.w.x {freg}, x7")
    t.clear_flags()
    lab = t.insn(line)
    if flags is not None:
        t.check_flags(flags, lab, desc)
    vreg, eew, n = store
    t.vset(n, eew, "m8")
    t.vcheck(vreg, pack(expected, eew), lab, desc, eew=eew, nbytes=n * eew // 8)
    return lab


h = L.h16
F16M = L.BF16 if MUT == "fp16_as_bf16" else L.F16  # the mutant reads SEW=16 FP bit patterns as BF16


def or_flags(results: Sequence[tuple[int, int]]) -> tuple[list[int], int]:
    fl = 0
    for _, f in results:
        fl |= f
    return [b for b, _ in results], fl


def ftz16(bits: int) -> int:
    if MUT == "fp16_ftz" and bits & 0x7C00 == 0:
        return bits & 0x8000
    return bits


def gen_zvfh() -> None:
    ZH = ["Zvfh"]
    t = add(new("Zvfh", "Zvfh_instr", ZH))
    doc(t, "One representative of each listed section at SEW=16 (LMUL=8, vl=4), with exact binary16 operands: "
           "vfadd.vv, vfmul.vf, vfmacc.vv, vfsqrt.v, vfmin.vv, vfsgnjn.vv, vfclass.v, vmflt.vv, vfcvt.x.f.v, vfwadd.vv "
           "(EEW 32 result) and vfncvt.f.f.w (sec-vector-float); vfredusum.vs and vfredmax.vs (reductions); "
           "vfwredosum.vs (widening reduction); vfmv.v.f, vfmv.s.f and vfmv.f.s (moves, the f result NaN-boxed); "
           "vfslide1up.vf and vfslide1down.vf. fflags is checked after each instruction.")  # fmt: skip
    a = [1.5, -2.0, 0.25, 1024.0]
    b = [2.25, 0.5, -0.25, 3.0]
    E16 = (4, 16, "m8")

    def hs(xs: Sequence[float]) -> list[int]:
        return [h(x) for x in xs]

    def r2(fn: Callable[[float, float], float], xs: Sequence[float], ys: Sequence[float]) -> list[int]:
        return [h(fn(x, y)) for x, y in zip(xs, ys)]

    fp_run(t, "vfadd.vv v8, v16, v24", E16, [("v16", hs(a), 16), ("v24", hs(b), 16)], ("v8", 16, 4),
           [h(3.75), h(-1.5), h(0.0), h(1027.0)], 0, "vfadd.vv SEW=16")  # fmt: skip
    fp_run(t, "vfmul.vf v8, v16, f1", E16, [("v16", hs([3.0, 6.0, -1.5, 0.125]), 16)], ("v8", 16, 4),
           hs([-1.5, -3.0, 0.75, -0.0625]), 0, "vfmul.vf SEW=16, f1 = -0.5", fregs=[("f1", 0xFFFF0000 | h(-0.5))])  # fmt: skip
    fp_run(t, "vfmacc.vv v8, v24, v16", E16, [("v8", hs([1, 2, 3, 4]), 16), ("v24", hs([2, 2, 2, 2]), 16),
           ("v16", hs([0.5, 1, 1.5, 2]), 16)], ("v8", 16, 4), hs([2, 4, 6, 8]), 0, "vfmacc.vv SEW=16")  # fmt: skip
    fp_run(t, "vfsqrt.v v8, v16", E16, [("v16", hs([2.25, 4, 0.0625, 1]), 16)], ("v8", 16, 4),
           hs([1.5, 2, 0.25, 1]), 0, "vfsqrt.v SEW=16")  # fmt: skip
    fp_run(t, "vfmin.vv v8, v16, v24", E16, [("v16", hs([1, -2, 3, -0.0]), 16), ("v24", hs([2, -3, 3, 0.0]), 16)],
           ("v8", 16, 4), hs([1, -3, 3, -0.0]), 0, "vfmin.vv SEW=16")  # fmt: skip
    fp_run(t, "vfsgnjn.vv v8, v16, v24", E16, [("v16", hs([1.5, -1.5, 2, -2]), 16), ("v24", hs([1, 1, -1, -1]), 16)],
           ("v8", 16, 4), hs([-1.5, -1.5, 2, 2]), 0, "vfsgnjn.vv SEW=16")  # fmt: skip
    cls_in = [0xFC00, h(-1.0), 0x8001, 0x8000, 0x0000, 0x0001, h(1.0), 0x7E00]
    fp_run(t, "vfclass.v v8, v16", (8, 16, "m8"), [("v16", cls_in, 16)], ("v8", 16, 8),
           [1, 2, 4, 8, 16, 32, 64, 512], 0, "vfclass.v SEW=16 (-inf, -normal, -subnormal, -0, +0, +subnormal, "
           "+normal, qNaN)")  # fmt: skip
    # vmflt.vv: mask result
    t.frm(0)
    t.vset(4, 16, "m8")
    t.vload("v16", pack(hs([1, 3, -2, 5]), 16), 16)
    t.vload("v24", pack(hs([2, 3, -1, 4]), 16), 16)
    t.clear_flags()
    lab = t.insn("vmflt.vv v1, v16, v24")
    t.check_flags(0, lab, "vmflt.vv SEW=16")
    t.vset(1, 8, "m1")
    t.emit("vmv.x.s x6, v1")
    t.emit("andi x6, x6, 15")
    t.check("x6", 0b0101, lab, "vmflt.vv SEW=16 mask bits (1<2, 3<3, -2<-1, 5<4)")
    fp_run(t, "vfcvt.x.f.v v8, v16", E16, [("v16", hs([2.5, -3.5, 100.75, -0.0]), 16)], ("v8", 16, 4),
           [2, msk(16) & -4, 101, 0], L.NX, "vfcvt.x.f.v SEW=16 (RNE)")  # fmt: skip
    fp_run(t, "vfwadd.vv v8, v16, v24", (2, 16, "m4"), [("v16", hs([1.5, 65504]), 16), ("v24", hs([2, 65504]), 16)],
           ("v8", 32, 2), [L.f32(3.5), L.f32(131008.0)], 0, "vfwadd.vv SEW=16 (FP32 results)")  # fmt: skip
    fp_run(t, "vfncvt.f.f.w v8, v16", (4, 16, "m4"), [("v16", [L.f32(x) for x in (1.0, 3.0, -0.5, 2.0**-14)], 32)],
           ("v8", 16, 4), hs([1.0, 3.0, -0.5, 2.0**-14]), 0, "vfncvt.f.f.w SEW=16")  # fmt: skip
    # reductions: vd preset to zero, tail undisturbed
    fp_run(t, "vfredusum.vs v8, v16, v24", E16, [("v8", [0] * 4, 16), ("v16", hs([1, 2, 4, 8]), 16),
           ("v24", hs([16, 0, 0, 0]), 16)], ("v8", 16, 2), [h(31.0), 0], 0, "vfredusum.vs SEW=16")  # fmt: skip
    fp_run(t, "vfredmax.vs v8, v16, v24", E16, [("v8", [0] * 4, 16), ("v16", hs([1, -5, 7, 3]), 16),
           ("v24", hs([2, 0, 0, 0]), 16)], ("v8", 16, 2), [h(7.0), 0], 0, "vfredmax.vs SEW=16")  # fmt: skip
    fp_run(t, "vfwredosum.vs v8, v16, v24", E16, [("v8", [0] * 4, 16), ("v16", hs([1.5, 2.5, 1024, 0.25]), 16),
           ("v24", [L.f32(1.0) & 0xFFFF, L.f32(1.0) >> 16, 0, 0], 16)], ("v8", 32, 1),
           [L.f32(1029.25)], 0, "vfwredosum.vs SEW=16 (FP32 sum)")  # fmt: skip
    # moves
    fp_run(t, "vfmv.v.f v8, f1", E16, [], ("v8", 16, 4), [h(1.25)] * 4, 0, "vfmv.v.f SEW=16",
           fregs=[("f1", 0xFFFF0000 | h(1.25))])  # fmt: skip
    fp_run(t, "vfmv.s.f v8, f1", E16, [("v8", hs([7, 7, 7, 7]), 16)], ("v8", 16, 4), [h(-3.0)] + hs([7, 7, 7]), 0,
           "vfmv.s.f SEW=16 (elements 1..3 undisturbed)", fregs=[("f1", 0xFFFF0000 | h(-3.0))])  # fmt: skip
    t.vset(4, 16, "m8")
    t.vload("v16", pack(hs([0.75, 9, 9, 9]), 16), 16)
    lab = t.insn("vfmv.f.s f2, v16")
    t.emit("fmv.x.w x6, f2")
    t.check("x6", W(0xFFFF0000 | h(0.75)), lab, "vfmv.f.s SEW=16: f2 holds the NaN-boxed binary16 value")
    fp_run(t, "vfslide1up.vf v8, v16, f1", E16, [("v16", hs([1, 2, 3, 4]), 16)], ("v8", 16, 4), hs([-8, 1, 2, 3]),
           0, "vfslide1up.vf SEW=16", fregs=[("f1", 0xFFFF0000 | h(-8.0))])  # fmt: skip
    fp_run(t, "vfslide1down.vf v8, v16, f1", E16, [("v16", hs([1, 2, 3, 4]), 16)], ("v8", 16, 4), hs([2, 3, 4, -8]),
           0, "vfslide1down.vf SEW=16", fregs=[("f1", 0xFFFF0000 | h(-8.0))])  # fmt: skip

    t = add(new("Zvfh", "Zvfh_eew16", ZH))
    doc(t, "binary16 format at SEW=16, one element per instruction so each case's fflags is checked: rounding at "
           "11 bits (1 + 2^-11 ties to 1.0; 1 + 3*2^-11 ties to 1 + 2^-9), the exponent range (65504 + 16 ties to "
           "overflow: infinity under RNE, 65504 under RTZ), subnormals (2^-24 + 2^-24 = 2^-23 exactly; 2^-24 * 0.5 "
           "underflows to 0 under RNE and to 2^-24 under RUP), the canonical NaN 0x7e00 (inf - inf, NV; a "
           "signaling NaN input, NV), division by zero (DZ), binary16 1.0 = 0x3c00 in vfadd.vf (f1 NaN-boxed), and EEW=16 operands of widening "
           "(vfwcvt.f.f.v of a subnormal, a negative subnormal and 65504) and narrowing (vfncvt.f.f.w ties, a "
           "subnormal result by mode) instructions.")  # fmt: skip
    one = h(1.0)
    cases = [
        ("vfadd.vv", one, h(2.0**-11), L.RNE), ("vfadd.vv", one, h(3 * 2.0**-11), L.RNE),
        ("vfadd.vv", h(65504.0), h(16.0), L.RNE), ("vfadd.vv", h(65504.0), h(16.0), L.RTZ),
        ("vfadd.vv", 0x0001, 0x0001, L.RNE), ("vfmul.vv", 0x0001, h(0.5), L.RNE), ("vfmul.vv", 0x0001, h(0.5), L.RUP),
        ("vfsub.vv", 0x7C00, 0x7C00, L.RNE), ("vfadd.vv", 0x7D00, one, L.RNE),
        ("vfdiv.vv", one, 0, L.RNE),
    ]  # fmt: skip
    for mn, x, y, rm in cases:
        if mn == "vfadd.vv":
            r, fl = L.add(F16M, x, y, rm)
        elif mn == "vfsub.vv":
            r, fl = L.add(F16M, x, y ^ (1 << 15), rm)
        elif mn == "vfmul.vv":
            r, fl = L.fma(F16M, (F16M, x), (F16M, y), (F16M, 0), rm)
        else:  # 1/0
            r, fl = F16M.inf, L.DZ
        r = ftz16(r)
        fp_run(t, f"{mn} v8, v16, v24", (1, 16, "m8"), [("v16", [x], 16), ("v24", [y], 16)], ("v8", 16, 1),
               [r], fl, f"{mn} SEW=16 0x{x:04x}, 0x{y:04x}, frm={rm}", rm=rm)  # fmt: skip
    # EEW=16 operands of widening and narrowing instructions
    for b in (0x0001, 0x8200, 0x7BFF):
        r, fl = L.convert(F16M, L.F32, b, L.RNE)
        fp_run(t, "vfwcvt.f.f.v v8, v16", (1, 16, "m4"), [("v16", [b], 16)], ("v8", 32, 1), [r], fl,
               f"vfwcvt.f.f.v SEW=16 binary16 0x{b:04x}")  # fmt: skip
    for b, rm in ((L.f32(1 + 2.0**-11), L.RNE), (L.f32(1 + 3 * 2.0**-11), L.RNE), (L.f32(2.0**-25), L.RUP),
                  (L.f32(3 * 2.0**-26), L.RNE)):  # fmt: skip
        r, fl = L.convert(L.F32, F16M, b, rm)
        r = ftz16(r)
        fp_run(t, "vfncvt.f.f.w v8, v16", (1, 16, "m4"), [("v16", [b], 32)], ("v8", 16, 1), [r], fl,
               f"vfncvt.f.f.w SEW=16 FP32 0x{b:08x}, frm={rm}", rm=rm)  # fmt: skip
    fp_run(t, "vfadd.vf v8, v16, f1", (1, 16, "m8"), [("v16", [one], 16)], ("v8", 16, 1), [L.add(F16M, one, one, 0)[0]], 0,
           "vfadd.vf SEW=16: 1.0 (0x3c00) + 1.0", fregs=[("f1", 0xFFFF0000 | one)])  # fmt: skip

    t = add(new("Zvfh", "Zvfh_instr_cvt", ZH))
    doc(t, "SEW=8 conversions between 8-bit integers and binary16 (LMUL=4, vl=4): vfwcvt.f.x.v (-128, 127, 0, -1) "
           "and vfwcvt.f.xu.v (255, 128, 1, 0), exact; vfncvt.x.f.w and vfncvt.xu.f.w under RNE with ties, "
           "inexact values and out-of-range values and NaN that saturate with NV; vfncvt.rtz.x.f.w and "
           "vfncvt.rtz.xu.f.w truncate regardless of frm (frm = RUP).")  # fmt: skip
    E8 = (4, 8, "m4")
    ints = [-128, 127, 0, -1]
    res = [L.i2f(L.F16, v, L.RNE) for v in ints]
    fp_run(t, "vfwcvt.f.x.v v8, v16", E8, [("v16", [v & 0xFF for v in ints], 8)], ("v8", 16, 4),
           [b for b, _ in res], 0, "vfwcvt.f.x.v SEW=8")  # fmt: skip
    uints = [255, 128, 1, 0]
    res = [L.i2f(L.F16, v, L.RNE) for v in uints]
    fp_run(t, "vfwcvt.f.xu.v v8, v16", E8, [("v16", uints, 8)], ("v8", 16, 4), [b for b, _ in res], 0,
           "vfwcvt.f.xu.v SEW=8")  # fmt: skip
    for mn, signed, rm, rtz, vals in (
        ("vfncvt.x.f.w", True, L.RNE, False, [2.5, -2.5, 127.25, -128.5]),
        ("vfncvt.x.f.w", True, L.RNE, False, [-129.0, 300.0, 1.0, "nan"]),
        ("vfncvt.xu.f.w", False, L.RNE, False, [255.5, -0.25, -1.0, 200.0]),
        ("vfncvt.rtz.x.f.w", True, L.RUP, True, [-2.75, 2.75, 126.5, -0.5]),
        ("vfncvt.rtz.xu.f.w", False, L.RUP, True, [255.75, 0.5, 3.25, 1.0]),
    ):
        src = [L.F16.cnan if v == "nan" else h(v) for v in vals]  # type: ignore[arg-type]
        rr = [L.f2i(L.F16, b, 8, signed, L.RTZ if rtz else rm) for b in src]
        exp, fl = or_flags(rr)
        fp_run(t, f"{mn} v8, v16", E8, [("v16", src, 16)], ("v8", 8, 4), exp, fl, f"{mn} SEW=8 {vals}", rm=rm)

    t = add(new("Zvfh", "Zvfh_dependent_Zve32f_Zfhmin", ZH))
    doc(t, "The dependencies, observed as their features: Zve32f's vfadd.vv at SEW=32, and Zfhmin's flh, fsh, "
           "fcvt.s.h and fcvt.h.s on binary16 values.")  # fmt: skip
    fp_run(t, "vfadd.vv v8, v16, v24", (2, 32, "m8"), [("v16", [L.f32(1.5), L.f32(-4.0)], 32),
           ("v24", [L.f32(2.25), L.f32(0.5)], 32)], ("v8", 32, 2), [L.f32(3.75), L.f32(-3.5)], 0, "vfadd.vv SEW=32")  # fmt: skip
    zfhmin(t)


def zfhmin(t: VT) -> None:
    lab_d = t.words([L.h16(1.5) | L.h16(-0.25) << 16])
    t.la("x1", lab_d)
    lab = t.insn("flh f3, 0(x1)")
    t.emit("fmv.x.w x6, f3")
    t.check("x6", W(0xFFFF0000 | L.h16(1.5)), lab, "flh: f3 holds the NaN-boxed binary16 1.5")
    t.emit("flh f4, 2(x1)")
    lab = t.insn("fcvt.s.h f5, f4")
    t.emit("fmv.x.w x6, f5")
    t.check("x6", W(L.f32(-0.25)), lab, "fcvt.s.h of -0.25")
    t.li("x7", sext(L.f32(3.0), 32))
    t.emit("fmv.w.x f6, x7")
    lab = t.insn("fcvt.h.s f7, f6")
    t.la("x1", t.out)
    t.emit("fsh f7, 0(x1)")
    t.emit("lhu x6, 0(x1)")
    t.check("x6", L.h16(3.0), lab, "fcvt.h.s of 3.0, stored with fsh")


def gen_zvfhmin() -> None:
    t = add(new("Zvfhmin", "Zvfhmin_dependent_Zve32f", ["Zvfhmin"]))
    doc(t, "The chapter's only tag is the Zve32f dependency, observed as vfadd.vv at SEW=32. The chapter also says "
           "vfwcvt.f.f.v and vfncvt.f.f.w become defined at SEW=16 with binary16 operands; both are exercised: "
           "vfwcvt.f.f.v of 1.0, -2.5, the smallest subnormal (exact), infinity, a quiet NaN with a payload and a "
           "signaling NaN (canonical NaN 0x7fc00000, NV); vfncvt.f.f.w of 1.0, 1 + 2^-11 (ties to 1.0), 65520 "
           "(overflows to infinity), 2^-25 (ties to 0, underflow) and a NaN with a payload (0x7e00).",
        context="zvfhmin.adoc: When the Zvfhmin extension is implemented, the vfwcvt.f.f.v and vfncvt.f.f.w "
                "instructions become defined when SEW=16. The EEW=16 floating-point operands of these instructions "
                "use the binary16 format.")  # fmt: skip
    fp_run(t, "vfadd.vv v8, v16, v24", (2, 32, "m8"), [("v16", [L.f32(1.5), L.f32(-4.0)], 32),
           ("v24", [L.f32(2.25), L.f32(0.5)], 32)], ("v8", 32, 2), [L.f32(3.75), L.f32(-3.5)], 0, "vfadd.vv SEW=32")  # fmt: skip
    src = [L.h16(1.0), L.h16(-2.5), 0x0001, 0x7C00, 0x7E01, 0x7C01]
    rr = [L.convert(L.F16, L.F32, b, L.RNE) for b in src]
    if MUT == "fwcvt_nan_payload":
        rr[4] = (0x7FC02000, 0)
    exp, fl = or_flags(rr)
    fp_run(t, "vfwcvt.f.f.v v8, v16", (6, 16, "m4"), [("v16", src, 16)], ("v8", 32, 6), exp, fl,
           "vfwcvt.f.f.v SEW=16")  # fmt: skip
    for vals in ([1.0, 1 + 2.0**-11, 3.0, -1.0], [65520.0, 2.0**-25, 1.0, 1.0]):
        src = [L.f32(v) for v in vals]
        rr = [L.convert(L.F32, L.F16, b, L.RNE) for b in src]
        exp, fl = or_flags(rr)
        fp_run(t, "vfncvt.f.f.w v8, v16", (4, 16, "m4"), [("v16", src, 32)], ("v8", 16, 4), exp, fl,
               f"vfncvt.f.f.w SEW=16 {vals}")  # fmt: skip
    src = [0x7FC12345, L.f32(2.0)]
    rr = [L.convert(L.F32, L.F16, b, L.RNE) for b in src]
    exp, fl = or_flags(rr)
    fp_run(t, "vfncvt.f.f.w v8, v16", (2, 16, "m4"), [("v16", src, 32)], ("v8", 16, 2), exp, fl,
           "vfncvt.f.f.w SEW=16 NaN with payload -> 0x7e00")  # fmt: skip


# ================================================================ Zvfbfmin, Zvfbfwma


def enc_v(funct6: int, vm: int, vs2: int, f5: int, funct3: int, vd: int) -> int:
    return funct6 << 26 | vm << 25 | vs2 << 20 | f5 << 15 | funct3 << 12 | vd << 7 | 0x57


def ncvt_bf16(bits: int, rm: int) -> tuple[int, int]:
    """vfncvtbf16.f.f.w: FP32 -> BF16 rounded by frm (with the mutants' wrong rules)."""
    if MUT == "bf16_frm_ignored":
        rm = L.RNE
    if MUT == "bf16_ties_away" and rm == L.RNE:
        rm = L.RMM
    kind, _, mag = L.F32.decode(bits)
    if MUT == "bf16_nan_payload" and kind in ("qnan", "snan"):
        return (bits >> 16) | 0x0040, L.NV if kind == "snan" else 0
    r, fl = L.convert(L.F32, L.BF16, bits, rm)
    if MUT == "bf16_uf_before_rounding" and kind == "num" and 0 < mag < L.Fraction(2) ** -126 and fl & L.NX:
        fl |= L.UF
    return r, fl


def wcvt_bf16(bits: int) -> tuple[int, int]:
    r, fl = L.convert(L.BF16, L.F32, bits, L.RNE)
    if MUT == "bf16_wcvt_snan_quiet":
        fl = 0
    return r, fl


def bfwma(a: int, b: int, c: int, rm: int) -> tuple[int, int]:
    """vfwmaccbf16: BF16 a * BF16 b + FP32 c, one rounding (two under the bfwma_double_round mutant)."""
    if MUT == "bfwma_double_round":
        p, f1 = L.fma(L.F32, (L.BF16, a), (L.BF16, b), (L.F32, 0x80000000), rm)
        one = 0x3F80
        r, f2 = L.fma(L.F32, (L.F32, p), (L.BF16, one), (L.F32, c), rm)
        return r, f1 | f2
    return L.fma(L.F32, (L.BF16, a), (L.BF16, b), (L.F32, c), rm)


def gen_zvfbf() -> None:
    ZB = ["Zvfbfmin"]
    t = add(new("Zvfbfmin", "Zvfbfmin_depends_Zve32f", ZB))
    doc(t, "The Zve32f dependency, observed as vfadd.vv and vfmul.vv at SEW=32.")
    fp_run(t, "vfadd.vv v8, v16, v24", (2, 32, "m8"), [("v16", [L.f32(1.5), L.f32(-4.0)], 32),
           ("v24", [L.f32(2.25), L.f32(0.5)], 32)], ("v8", 32, 2), [L.f32(3.75), L.f32(-3.5)], 0, "vfadd.vv SEW=32")  # fmt: skip
    fp_run(t, "vfmul.vv v8, v16, v24", (2, 32, "m8"), [("v16", [L.f32(1.5), L.f32(-4.0)], 32),
           ("v24", [L.f32(2.25), L.f32(0.5)], 32)], ("v8", 32, 2), [L.f32(3.375), L.f32(-2.0)], 0, "vfmul.vv SEW=32")  # fmt: skip

    # ---- encodings: .word built from the diagrams; vm=1 and vm=0 (v0 = 0b0101: elements 1 and 3 inactive, mu)
    for rule, f5, narrow in (("vfncvtbf16-f-f-w_enc", 0b11101, True), ("vfwcvtbf16-f-f-v_enc", 0b01101, False)):
        t = add(new("Zvfbfmin", rule, ZB))
        mn = "vfncvtbf16.f.f.w" if narrow else "vfwcvtbf16.f.f.v"
        doc(t, f"{mn} executed from .word encodings assembled from the diagram's fields (OP-V 1010111, OPFVV 001, "
               f"vs1 field {f5:05b}, VFUNARY0 010010), with vd=v8 and vs2=v16 at SEW=16 (LMUL=4, vl=4): vm=1 "
               "converts every element; vm=0 with v0 = 0b0101 converts elements 0 and 2 and leaves 1 and 3 "
               "undisturbed (mask-undisturbed policy).")  # fmt: skip
        if narrow:
            src = [L.f32(1.0), L.f32(-2.0), 0x3F818000, L.f32(0.15625)]
            exp = [ncvt_bf16(b, L.RNE)[0] for b in src]
            ieew, oeew = 32, 16
        else:
            src = [L.bf(1.0), L.bf(-2.0), L.bf(3.5), L.bf(2.0**-10)]
            exp = [wcvt_bf16(b)[0] for b in src]
            ieew, oeew = 16, 32
        old = [0x1234, 0x5678, 0x9ABC, 0x2468] if narrow else [0x11111111, 0x22222222, 0x33333333, 0x44444444]
        for vm in (1, 0):
            word = enc_v(0b010010, vm, 16, f5, 0b001, 8)
            t.frm(L.RNE)
            t.vset(4, 16, "m4", "tu, mu")
            t.vload("v16", pack(src, ieew), ieew)
            t.vload("v8", pack(old, oeew), oeew)
            if vm == 0:
                t.vset(1, 8, "m1")
                t.li("x7", 0b0101)
                t.emit("vmv.s.x v0, x7")
                t.vset(4, 16, "m4", "tu, mu")
            lab = t.insn(f".word 0x{word:08x}  // {mn} v8, v16{'' if vm else ', v0.t'}")
            e = exp if vm else [x if i % 2 == 0 else o for i, (x, o) in enumerate(zip(exp, old))]
            t.vset(4, oeew, "m8")
            t.vcheck("v8", pack(e, oeew), lab, f"{mn} encoding 0x{word:08x}", eew=oeew)

    t = add(new("Zvfbfmin", "vfncvtbf16-f-f-w_op", ZB))
    doc(t, "vfncvtbf16.f.f.w at SEW=16, one element per instruction so each case's fflags is checked, rounding by "
           "the frm CSR (the instruction has no rm field): ties (1 + 2^-8 to even, 1 + 3*2^-8 to even upward, "
           "negative ties) under all five modes, and negative values under RTZ (which differs from RDN there); "
           "overflow from 0x7f7fffff and 0xff7fffff (OF|NX when the result is infinity, NX only when it is the "
           "largest finite value, as overflow is judged after rounding); quiet and signaling NaNs with payloads give the canonical NaN 0x7fc0 (NV for signaling); "
           "infinity and -0 convert exactly; FP32 subnormals: 0x007fffff rounds to 2^-126 under RNE with NX only "
           "(tininess is detected after rounding), 0x00408000 ties to 0x0040 with UF|NX, 0x00010000 is exact.",
        context="zfbfmin.adoc bf16_subnorm: Tininess is detected after rounding. bf16_canonical_nan: For BF16, the "
                "canonical NaN corresponds to the pattern 0x7fc0.")  # fmt: skip
    cases = [(0x3F808000, rm) for rm in range(5)] + [(0xBF808000, rm) for rm in (L.RDN, L.RUP, L.RMM, L.RNE)]
    cases += [(0x3F818000, L.RNE), (0x3F808001, L.RNE), (0x3F808001, L.RTZ)]
    cases += [(0x7F7FFFFF, rm) for rm in range(4)] + [(0xFF7FFFFF, L.RDN), (0xFF7FFFFF, L.RUP)]
    cases += [(0x7FC12345, L.RNE), (0x7F812345, L.RNE), (0xFFC00001, L.RTZ), (0x7F800000, L.RNE), (0x80000000, L.RNE)]
    cases += [(0x007FFFFF, L.RNE), (0x007FFFFF, L.RTZ), (0x00408000, L.RNE), (0x00010000, L.RNE), (0x80408000, L.RDN)]
    cases += [(0xBF808000, L.RTZ), (0xFF7FFFFF, L.RTZ), (0x80408000, L.RTZ)]  # negative: RTZ differs from RDN
    for bits, rm in cases:
        r, fl = ncvt_bf16(bits, rm)
        fp_run(t, "vfncvtbf16.f.f.w v8, v16", (1, 16, "m4"), [("v16", [bits], 32)], ("v8", 16, 1), [r], fl,
               f"vfncvtbf16.f.f.w 0x{bits:08x}, frm={rm}", rm=rm)  # fmt: skip

    t = add(new("Zvfbfmin", "vfwcvtbf16-f-f-v_op", ZB))
    doc(t, "vfwcvtbf16.f.f.v at SEW=16 (LMUL=4): normal, negative, subnormal (0x0001), -0, -infinity and the "
           "largest finite BF16 convert exactly (the encoding shifted left by 16, no flags) under every frm; a quiet "
           "NaN with a payload gives the canonical NaN 0x7fc00000 with no flags; a signaling NaN gives 0x7fc00000 "
           "with NV.")  # fmt: skip
    ex = [L.bf(1.0), L.bf(-5.0), 0x0001, 0x8000, 0xFF80, 0x7F7F]
    for rm in (L.RNE, L.RDN, L.RUP):
        rr = [wcvt_bf16(b) for b in ex]
        exp, fl = or_flags(rr)
        fp_run(t, "vfwcvtbf16.f.f.v v8, v16", (6, 16, "m4"), [("v16", ex, 16)], ("v8", 32, 6), exp, fl,
               f"vfwcvtbf16.f.f.v exact values, frm={rm}", rm=rm)  # fmt: skip
    for b in (0x7FC1, 0x7F81, 0xFF81):
        r, fl = wcvt_bf16(b)
        fp_run(t, "vfwcvtbf16.f.f.v v8, v16", (1, 16, "m4"), [("v16", [b], 16)], ("v8", 32, 1), [r], fl,
               f"vfwcvtbf16.f.f.v NaN 0x{b:04x}")  # fmt: skip

    # ---- Zvfbfwma
    ZW = ["Zvfbfwma"]
    t = add(new("Zvfbfwma", "Zvfbfwma_depends", ZW))
    doc(t, "The Zvfbfmin and Zfbfmin dependencies, observed as their instructions: vfwcvtbf16.f.f.v at SEW=16, and "
           "the scalar fcvt.s.bf16 and fcvt.bf16.s (with flh/fsh of the BF16 value).")  # fmt: skip
    fp_run(t, "vfwcvtbf16.f.f.v v8, v16", (2, 16, "m4"), [("v16", [L.bf(1.5), L.bf(-0.75)], 16)], ("v8", 32, 2),
           [L.f32(1.5), L.f32(-0.75)], 0, "vfwcvtbf16.f.f.v")  # fmt: skip
    lab_d = t.words([L.bf(-6.5) | L.bf(0.5) << 16])
    t.la("x1", lab_d)
    t.emit("flh f3, 0(x1)")
    lab = t.insn("fcvt.s.bf16 f4, f3")
    t.emit("fmv.x.w x6, f4")
    t.check("x6", W(L.f32(-6.5)), lab, "fcvt.s.bf16 of -6.5")
    t.li("x7", sext(L.f32(0.375), 32))
    t.emit("fmv.w.x f5, x7")
    lab = t.insn("fcvt.bf16.s f6, f5")
    t.la("x1", t.out)
    t.emit("fsh f6, 0(x1)")
    t.emit("lhu x6, 0(x1)")
    t.check("x6", L.bf(0.375), lab, "fcvt.bf16.s of 0.375")

    for rule, vf in (("vfwmaccbf16_encoding_vv", False), ("vfwmaccbf16_encoding_vf", True)):
        t = add(new("Zvfbfwma", rule, ZW))
        doc(t, f"vfwmaccbf16.{'vf' if vf else 'vv'} executed from .word encodings built from the diagram (OP-V, "
               f"{'OPFVF 101, rs1 = f1' if vf else 'OPFVV 001, vs1 = v24'}, vs2 = v16, vd = v8, funct6 111011) at "
               "SEW=16 (LMUL=4, vl=4) with vm=1, and vm=0 with v0 = 0b0101 (elements 1 and 3 undisturbed).")  # fmt: skip
        acc = [L.f32(x) for x in (1.0, 2.0, -3.0, 0.5)]
        b2 = [L.bf(x) for x in (1.5, -2.0, 4.0, 0.25)]
        b1 = [L.bf(2.0)] * 4 if vf else [L.bf(x) for x in (2.0, 3.0, -0.5, 8.0)]
        exp = [bfwma(x, y, c, L.RNE)[0] for x, y, c in zip(b1, b2, acc)]
        for vm in (1, 0):
            word = enc_v(0b111011, vm, 16, 1 if vf else 24, 0b101 if vf else 0b001, 8)
            t.frm(L.RNE)
            t.vset(4, 16, "m4", "tu, mu")
            t.vload("v16", pack(b2, 16), 16)
            if not vf:
                t.vload("v24", pack(b1, 16), 16)
            else:
                t.li("x7", sext(0xFFFF0000 | L.bf(2.0), 32))
                t.emit("fmv.w.x f1, x7")
            t.vset(4, 32, "m8")
            t.vload("v8", acc, 32)
            if vm == 0:
                t.vset(1, 8, "m1")
                t.li("x7", 0b0101)
                t.emit("vmv.s.x v0, x7")
            t.vset(4, 16, "m4", "tu, mu")
            lab = t.insn(f".word 0x{word:08x}  // vfwmaccbf16.{'vf v8, f1' if vf else 'vv v8, v24'}, v16"
                         f"{'' if vm else ', v0.t'}")  # fmt: skip
            e = exp if vm else [x if i % 2 == 0 else o for i, (x, o) in enumerate(zip(exp, acc))]
            t.vset(4, 32, "m8")
            t.vcheck("v8", e, lab, f"vfwmaccbf16 encoding 0x{word:08x}")

    t = add(new("Zvfbfwma", "vfwmaccbf16_op", ZW))
    doc(t, "vfwmaccbf16.vv, one element per case so fflags is checked: an exact case; the sum rounded by frm (1 + "
           "2^-24 under RNE and RUP); an unrounded product: (-2^-100 * 2^-100) + 1 under RTZ gives 0x3f7fffff and "
           "(2^-100 * 2^-100) + 1 under RNE gives 1.0 with NX only (a product rounded to FP32 first would give 1.0, "
           "or set UF); overflow (largest BF16 * 2, OF|NX, infinity or the largest FP32 by mode); invalid "
           "operations (infinity * 0, infinity - infinity: canonical NaN, NV); NaN inputs (quiet: no flags, "
           "signaling: NV); signed zeros ((+0 * -1) + -0 = -0, (1 * -1) + 1 = +0, or -0 under RDN); an exact "
           "subnormal FP32 result, and 3 * 2^-150 rounding to 2^-148 with UF|NX.")  # fmt: skip
    p100, m100 = 0x0D80, 0x8D80  # +-2^-100 in BF16
    cases = [
        (L.bf(1.5), L.bf(2.0), L.f32(0.25), L.RNE), (L.bf(2.0**-12), L.bf(2.0**-12), L.f32(1.0), L.RNE),
        (L.bf(2.0**-12), L.bf(2.0**-12), L.f32(1.0), L.RUP), (m100, p100, L.f32(1.0), L.RTZ),
        (p100, p100, L.f32(1.0), L.RNE), (0x7F7F, L.bf(2.0), 0, L.RNE), (0x7F7F, L.bf(2.0), 0, L.RTZ),
        (0x7F80, 0x0000, L.f32(1.0), L.RNE), (0x7F80, L.bf(1.0), 0xFF800000, L.RNE),
        (0x7FC1, L.bf(1.0), L.f32(1.0), L.RNE), (0x7F81, L.bf(1.0), L.f32(1.0), L.RNE),
        (L.bf(1.0), L.bf(1.0), 0x7F800001, L.RNE),
        (0x0000, L.bf(-1.0), 0x80000000, L.RNE), (L.bf(1.0), L.bf(-1.0), L.f32(1.0), L.RNE),
        (L.bf(1.0), L.bf(-1.0), L.f32(1.0), L.RDN), (L.bf(2.0**-70), L.bf(2.0**-70), 0, L.RNE),
        (L.bf(3 * 2.0**-75), L.bf(2.0**-75), 0, L.RNE),
    ]  # fmt: skip
    for a, b, c, rm in cases:
        r, fl = bfwma(a, b, c, rm)
        fp_run(t, "vfwmaccbf16.vv v8, v24, v16", (1, 16, "m4"), [("v24", [a], 16), ("v16", [b], 16),
               ("v8", [c], 32)], ("v8", 32, 1), [r], fl, f"vfwmaccbf16.vv 0x{a:04x} * 0x{b:04x} + 0x{c:08x}, "
               f"frm={rm}", rm=rm)  # fmt: skip

    t = add(new("Zvfbfwma", "vfwmaccbf16-vv", ZW))
    doc(t, "vfwmaccbf16.vv operand roles at SEW=16 (LMUL=4, vl=4): vd holds the FP32 accumulator, vs1 and vs2 the "
           "BF16 factors, and the FP32 sum is written to vd; values are chosen so that reading the accumulator or "
           "a factor from the wrong register changes the result. Also vs1 = vs2 (squares).")  # fmt: skip
    acc = [L.f32(x) for x in (10.0, 0.5, -1.0, 100.0)]
    f1 = [L.bf(x) for x in (2.0, 4.0, 0.5, -3.0)]
    f2 = [L.bf(x) for x in (3.0, -1.0, 8.0, 0.25)]
    exp = [bfwma(x, y, c, L.RNE)[0] for x, y, c in zip(f1, f2, acc)]
    fp_run(t, "vfwmaccbf16.vv v8, v24, v16", (4, 16, "m4"), [("v24", f1, 16), ("v16", f2, 16), ("v8", acc, 32)],
           ("v8", 32, 4), exp, 0, "vfwmaccbf16.vv vd, vs1, vs2")  # fmt: skip
    exp = [bfwma(y, y, c, L.RNE)[0] for y, c in zip(f2, acc)]
    fp_run(t, "vfwmaccbf16.vv v8, v16, v16", (4, 16, "m4"), [("v16", f2, 16), ("v8", acc, 32)], ("v8", 32, 4), exp,
           0, "vfwmaccbf16.vv vs1 = vs2")  # fmt: skip

    t = add(new("Zvfbfwma", "vfwmaccbf16-vf", ZW))
    doc(t, "vfwmaccbf16.vf at SEW=16 (LMUL=4, vl=4): the BF16 scalar comes from f1. Properly NaN-boxed (bits 31:16 "
           "of the written 32-bit pattern all ones, so boxed for any FLEN) it is used for every element; not boxed "
           "(bits 31:16 = 0x0000, 0x7fff or 0xfffe, so a check of only bit 31 or only the top byte is caught) "
           "the canonical NaN is used, so every result is 0x7fc00000 with no flags (a quiet NaN). "
           "The vector operand comes from vs2 and the accumulator from vd.")  # fmt: skip
    acc = [L.f32(1.0)] * 4
    f2 = [L.bf(x) for x in (1.5, -3.0, 0.25, 8.0)]
    for box in (0xFFFF0000, 0, 0x7FFF0000, 0xFFFE0000):
        boxed = box == 0xFFFF0000
        s = L.bf(2.0) | box
        sv = L.bf(2.0) if boxed or MUT == "bfwma_nanbox_ignored" else L.BF16.cnan
        rr = [bfwma(sv, y, c, L.RNE) for y, c in zip(f2, acc)]
        exp, fl = or_flags(rr)
        fp_run(t, "vfwmaccbf16.vf v8, f1, v16", (4, 16, "m4"), [("v16", f2, 16), ("v8", acc, 32)], ("v8", 32, 4),
               exp, fl, f"vfwmaccbf16.vf, f1 = 0x{s:08x} ({'boxed' if boxed else 'not NaN-boxed'})",
               fregs=[("f1", s)])  # fmt: skip


# ================================================================ vector crypto: element groups

AESI = ("vaesef", "vaesem", "vaesdf", "vaesdm", "vaesz")
IMM_FORMS = ("vaeskf1", "vaeskf2", "vsm4k", "vsm3c")
VS1_FORMS = ("vsha2ch", "vsha2cl", "vsha2ms", "vghsh", "vsm3me")


def egs_of(mn: str) -> int:
    return 8 if mn.startswith("vsm3") else 4


def eg_ref(mn: str, vd: list[int], vs2: list[int], vs1: list[int] | None, imm: int | None, sew: int) -> list[int]:
    base = mn.split(".")[0]
    if base in AESI:
        return L.aes_round(base, vd, vs2)
    if base == "vaeskf1":
        return L.aeskf1(vs2, imm or 0)
    if base == "vaeskf2":
        return L.aeskf2(vd, vs2, imm or 0)
    if base in ("vsha2ch", "vsha2cl"):
        return L.sha2c(base == "vsha2ch", vd, vs2, vs1 or [], sew)
    if base == "vsha2ms":
        return L.sha2ms(vd, vs2, vs1 or [], sew)
    if base == "vghsh":
        return L.vghsh(vd, vs2, vs1 or [])
    if base == "vgmul":
        return L.vgmul(vd, vs2)
    if base == "vsm4k":
        return L.vsm4k(vs2, imm or 0)
    if base == "vsm4r":
        return L.vsm4r(vd, vs2)
    if base == "vsm3me":
        return L.vsm3me(vs2, vs1 or [])
    if base == "vsm3c":
        return L.vsm3c(vd, vs2, imm or 0)
    raise ValueError(mn)


def eg_line(mn: str, vs2: str = "v16", imm: int | None = None, vd: str = "v8", vs1: str = "v24") -> str:
    base = mn.split(".")[0]
    if base in IMM_FORMS:
        return f"{mn} {vd}, {vs2}, {imm}"
    if base in VS1_FORMS:
        return f"{mn} {vd}, {vs2}, {vs1}"
    return f"{mn} {vd}, {vs2}"


class G:
    """One element group's operands: vd, vs2 and vs1 element lists (SEW-wide elements)."""

    def __init__(self, vd: list[int], vs2: list[int] | None = None, vs1: list[int] | None = None) -> None:
        self.vd, self.vs2, self.vs1 = vd, vs2, vs1


def rnd_group(t: VT, egs: int, sew: int) -> list[int]:
    return [t.rand(sew) for _ in range(egs)]


def rnd_G(t: VT, mn: str, sew: int) -> G:
    e = egs_of(mn)
    base = mn.split(".")[0]
    return G(rnd_group(t, e, sew), rnd_group(t, e, sew), rnd_group(t, e, sew) if base in VS1_FORMS else None)


def load_groups(t: VT, mn: str, sew: int, groups: Sequence[G], key: list[int] | None, decoy: list[int] | None,
                lmul: str = "m8", vsreg: str = "v16", vsl: str = "m8") -> int:  # fmt: skip
    """Load vd (v8), vs2 (v16; for .vs the scalar group, in vsreg loaded at LMUL vsl) and vs1 (v24); vtype ends at
    vl = n groups."""
    egs = egs_of(mn)
    n = len(groups) * egs
    if mn.endswith(".vs"):
        # scalar element group in v16 (LMUL-aligned; EMUL = ceil(128/VLEN)); a decoy group follows the key
        t.vset(2 * egs, sew, vsl)
        t.vload(vsreg, pack((key or []) + (decoy or []), sew), sew)
    t.vset(n, sew, lmul)
    t.vload("v8", eg_words([g.vd for g in groups], sew), sew)
    if not mn.endswith(".vs") and groups[0].vs2 is not None:
        t.vload("v16", eg_words([g.vs2 or [] for g in groups], sew), sew)
    if groups[0].vs1 is not None:
        t.vload("v24", eg_words([g.vs1 or [] for g in groups], sew), sew)
    return n


def expect_groups(mn: str, sew: int, groups: Sequence[G], key: list[int] | None, decoy: list[int] | None,
                  imm: int | None) -> list[list[int]]:  # fmt: skip
    out = []
    for i, g in enumerate(groups):
        k = (key if i == 0 or MUT != "vs_uses_group_i" else decoy) if mn.endswith(".vs") else g.vs2
        out.append(eg_ref(mn, g.vd, k or [], g.vs1, imm, sew))
    return out


def fit(t: VT, nelem: int, sew: int, body: Callable[[], None]) -> None:
    """Run body, which uses nelem SEW-wide elements at LMUL=8, only when VLMAX holds them: directly when VLEN=32
    suffices (8*32 bits), otherwise under a run-time VLEN check."""
    bits = nelem * sew // 8  # minimum VLEN at LMUL=8
    if bits <= 32:
        body()
        return
    vlen = 64
    while vlen < bits:
        vlen *= 2
    vlen_at_least(t, vlen, body)


def eg_case(t: VT, mn: str, sew: int, groups: Sequence[G], *, imm: int | None = None, key: list[int] | None = None,
            decoy: list[int] | None = None, desc: str = "", lmul: str = "m8", vsreg: str = "v16",
            vsl: str = "m8") -> list[list[int]]:  # fmt: skip
    """Run mn on len(groups) element groups (v8 = vd, v16 = vs2, v24 = vs1; .vs: the scalar group key in vsreg,
    followed by a decoy group) and check every element of vd. Returns the expected groups. Cases that need more
    than VLEN=32 holds at LMUL=8 run only when VLEN is large enough."""
    if mn.endswith(".vs") and decoy is None:
        decoy = [x ^ 0xA5A5A5A5 for x in key or []]
    exp = expect_groups(mn, sew, groups, key, decoy, imm)

    def body() -> None:
        load_groups(t, mn, sew, groups, key, decoy, lmul, vsreg, vsl)
        lab = t.insn(eg_line(mn, vsreg if mn.endswith(".vs") else "v16", imm))
        t.vcheck("v8", eg_words(exp, sew), lab, desc or eg_line(mn, imm=imm), eew=sew)

    if lmul == "m8":
        fit(t, len(groups) * egs_of(mn), sew, body)
    else:
        body()
    return exp


def vlen_at_least(t: VT, bits: int, body: Callable[[], object]) -> None:
    """Run body only when VLEN >= bits (vlenb read at run time)."""
    t.emit("csrr x10, vlenb")
    t.emit(f"sltiu x10, x10, {bits // 8}")
    t.emit("xori x10, x10, 1")
    t.either("x10", body, lambda: None)


def _eg_vl(t: VT, mn: str, sew: int, imm: int | None = None) -> None:
    """vl = EGS: only group 0 is processed and group 1 (tail, tu) is undisturbed; vl = 0: nothing is written."""
    egs = egs_of(mn)
    g = [rnd_G(t, mn, sew), rnd_G(t, mn, sew)]
    key = rnd_group(t, egs, sew)
    decoy = rnd_group(t, egs, sew)
    exp = expect_groups(mn, sew, g, key, decoy, imm)
    load_groups(t, mn, sew, g, key, decoy)
    t.vset(egs, sew, "m8", "tu, mu")
    lab = t.insn(eg_line(mn, "v16", imm))
    t.vset(2 * egs, sew, "m8")
    second = exp[1] if MUT == "vl_ignored" else g[1].vd
    t.vcheck("v8", eg_words([exp[0], second], sew), lab, f"{mn} vl=EGS={egs}: group 0 processed, group 1 (tail) "
             "undisturbed", eew=sew)  # fmt: skip
    load_groups(t, mn, sew, g, key, decoy)
    t.vset(0, sew, "m8", "tu, mu")
    lab = t.insn(eg_line(mn, "v16", imm))
    t.vset(2 * egs, sew, "m8")
    t.vcheck("v8", eg_words(exp if MUT == "vl_ignored" else [x.vd for x in g], sew), lab,
             f"{mn} vl=0: vd unchanged", eew=sew)  # fmt: skip


def _eg_vstart(t: VT, mn: str, sew: int, imm: int | None = None) -> None:
    """vstart = EGS with vl = 2*EGS: the instruction may raise illegal-instruction (vstart_vtype_dep); if it runs,
    group 0 (prestart) is undisturbed, group 1 is processed and vstart reads 0; if it traps, vstart and vd are
    unchanged."""
    egs = egs_of(mn)
    g = [rnd_G(t, mn, sew), rnd_G(t, mn, sew)]
    key = rnd_group(t, egs, sew)
    decoy = rnd_group(t, egs, sew)
    exp = expect_groups(mn, sew, g, key, decoy, imm)
    load_groups(t, mn, sew, g, key, decoy)
    t.li("x7", egs)
    line = eg_line(mn, "v16", imm)
    lab = t.trapwin(line, ["ok", ILLEGAL], f"{mn} with vstart={egs}", pre=["csrw vstart, x7"])
    t.no_trap_flag("x8")
    t.emit("csrr x10, vstart")

    def ran() -> None:
        t.check("x10", egs if MUT == "vstart_not_reset" else 0, lab, f"{mn}: vstart reads 0 after execution")
        t.vset(2 * egs, sew, "m8")
        first = exp[0] if MUT == "vstart_ignored" else g[0].vd
        t.vcheck("v8", eg_words([first, exp[1]], sew), lab, f"{mn} vstart={egs}: group 0 (prestart) undisturbed, "
                 "group 1 processed", eew=sew)  # fmt: skip

    def trapped() -> None:
        t.check("x10", egs, lab, f"{mn}: vstart is unchanged by the illegal-instruction trap")
        t.vset(2 * egs, sew, "m8")
        t.vcheck("v8", eg_words([x.vd for x in g], sew), lab, f"{mn}: vd unchanged by the trap", eew=sew)

    t.either("x8", ran, trapped)


def eg_vl(t: VT, mn: str, sew: int, imm: int | None = None) -> None:
    fit(t, 2 * egs_of(mn), sew, lambda: _eg_vl(t, mn, sew, imm))


def eg_vstart(t: VT, mn: str, sew: int, imm: int | None = None) -> None:
    fit(t, 2 * egs_of(mn), sew, lambda: _eg_vstart(t, mn, sew, imm))


LMULS = (("mf8", -3), ("mf4", -2), ("mf2", -1), ("m1", 0), ("m2", 1), ("m4", 2), ("m8", 3))


def eg_egw(t: VT, mns: Sequence[tuple[str, int | None]], sew: int, egw: int) -> None:
    """For every LMUL, with vl = 0: illegal-instruction when vtype is vill or LMUL*VLEN < EGW, otherwise no trap."""
    for lmul, lg in LMULS:
        t.vset(0, sew, lmul)
        t.emit("csrr x10, vtype")
        t.emit("slt x10, x10, x0  // vill")
        t.emit("csrr x11, vlenb")
        if lg + 3 >= 0:
            t.emit(f"slli x11, x11, {lg + 3}  // LMUL*VLEN")
        else:
            t.emit(f"srli x11, x11, {-(lg + 3)}  // LMUL*VLEN")
        t.emit(f"sltiu x11, x11, {egw}  // LMUL*VLEN < EGW")
        for mn, imm in mns:
            line = eg_line(mn, "v16", imm)

            def small(line: str = line, lmul: str = lmul) -> None:
                t.trapwin(line, "ok" if MUT == "egw_vl0_no_trap" else ILLEGAL, f"{line}: LMUL={lmul}, LMUL*VLEN < "
                          f"EGW={egw}, vl=0")  # fmt: skip

            def big(line: str = line, lmul: str = lmul) -> None:
                t.either("x11", small, lambda: t.trapwin(line, "ok", f"{line}: LMUL={lmul}, LMUL*VLEN >= EGW={egw}, "
                                                                     "vl=0"))  # fmt: skip

            t.either("x10", lambda line=line, lmul=lmul: t.trapwin(line, ILLEGAL, f"{line}: LMUL={lmul} is vill"), big)


def b2e(hexs: str) -> list[int]:
    """16 bytes in memory order -> four little-endian 32-bit elements."""
    return L.eg_elems(list(bytes.fromhex(hexs)))


def common_eg(ext: str, req: list, mns: Sequence[tuple[str, int | None]], sew: int, egw: int, vs: str | None) -> None:
    """The cross-cutting element-group rules, for the instructions of one extension."""
    egs = egs_of(mns[0][0])
    t = add(new(ext, "veccrypto_eeweqsew", req))
    doc(t, f"EEW = SEW = {sew}: with vl = {2 * egs} at SEW={sew}, each instruction processes exactly two element "
           f"groups of {egs} SEW-wide elements (vd elements {2 * egs}..{3 * egs - 1}, loaded beforehand, stay "
           "undisturbed), and the results match the operation on SEW-wide elements.")  # fmt: skip
    for mn, imm in mns:
        g = [rnd_G(t, mn, sew) for _ in range(3)]
        key = rnd_group(t, egs, sew)
        decoy = rnd_group(t, egs, sew)
        exp = expect_groups(mn, sew, g, key, decoy, imm)

        def body(mn: str = mn, imm: int | None = imm, g: list = g, key: list = key, decoy: list = decoy,
                 exp: list = exp) -> None:  # fmt: skip
            load_groups(t, mn, sew, g, key, decoy)
            t.vset(2 * egs, sew, "m8", "tu, mu")
            lab = t.insn(eg_line(mn, "v16", imm))
            t.vset(3 * egs, sew, "m8")
            t.vcheck("v8", eg_words([exp[0], exp[1], g[2].vd], sew), lab, f"{mn}: two {egs}-element groups at "
                     f"SEW={sew}", eew=sew)  # fmt: skip

        fit(t, 3 * egs, sew, body)

    t = add(new(ext, "veccrypto_vl_vstart_egsconstr", req))
    doc(t, f"vl and vstart that are multiples of EGS={egs} (the non-reserved cases): vl = {egs} and {2 * egs} "
           f"process vl/EGS groups, vl = 0 none; vstart = {egs} starts at group 1 (or raises illegal-instruction, "
           "which vstart_vtype_dep permits, leaving vstart and vd unchanged). Values that are not multiples are "
           "reserved and not tested.")  # fmt: skip
    for mn, imm in mns:
        eg_vl(t, mn, sew, imm)
        g = [rnd_G(t, mn, sew), rnd_G(t, mn, sew)]
        key = rnd_group(t, egs, sew)
        eg_case(t, mn, sew, g, imm=imm, key=key, desc=f"{mn}: vl = {2 * egs}")
    eg_vstart(t, mns[0][0], sew, mns[0][1])

    t = add(new(ext, "veccrypto_lmul_egwconstr", req))
    doc(t, f"vl = 0 at every LMUL (mf8..m8) and SEW={sew}: each instruction raises illegal-instruction when "
           f"LMUL*VLEN < EGW={egw} (computed from vlenb at run time), and executes without a trap when LMUL*VLEN >= "
           "EGW. LMULs that the hart does not support (vill) must raise illegal-instruction too. xtval is 0 or the "
           "instruction bits.")  # fmt: skip
    eg_egw(t, mns, sew, egw)

    if vs is None:
        return
    vmn = vs
    t = add(new(ext, "veccrypto_vsins_vs2", req))
    doc(t, f"{vmn} reads a 128-bit scalar element group from vs2 (EMUL = ceil(128/VLEN)): with LMUL=8, vs2 = v16 "
           "and vs2 = v4 (aligned to 4, not to 8), each with a decoy group after the key; and, when VLEN >= 128, vs2 = v3 (a single "
           "register that is not LMUL-aligned, which is legal because VLEN >= EGW) at LMUL=8 and at LMUL=1, with "
           "decoys in v4 and in v3 beyond element 3. Every vd group uses the key.",
        issues=f"{ISSUE}2612: 'vector-scalar defines two EMUL, one for vd (and if necessary vs1) and one for the "
               "scalar element group read from the vs2 group'; e.g. for VLEN=64, LMUL=4, vl=8, vaesdf.vs v8, v12 reads "
               "the scalar group from v12-v13 (EMUL=2), and every vd element group uses it. zvk.adoc: 'For "
               "implementations with VLEN >= 128, vs2 refers to a single register' and 'Scalar element group operands "
               "do not need to be aligned to LMUL for any implementation with VLEN >= EGW'.")  # fmt: skip
    key = rnd_group(t, 4, 32)
    eg_case(t, vmn, 32, [G(rnd_group(t, 4, 32)), G(rnd_group(t, 4, 32))], key=key, desc=f"{vmn} v8, v16 (LMUL=8)")
    g = [G(rnd_group(t, 4, 32)), G(rnd_group(t, 4, 32))]
    decoy = rnd_group(t, 4, 32)
    load_groups(t, vmn, 32, g, key, decoy, "m8", "v4", "m4")
    line = eg_line(vmn, "v4")
    lab = t.trapwin(line, ILLEGAL if MUT == "vs_needs_lmul_align" else "ok", f"{line}: vs2 = v4 (EMUL <= 4) is a "
                    "legal scalar element group for LMUL=8")  # fmt: skip
    t.vcheck("v8", eg_words(expect_groups(vmn, 32, g, key, decoy, None), 32), lab, f"{line} (LMUL=8)")

    def v3() -> None:
        for lmul in ("m8", "m1"):
            k = rnd_group(t, 4, 32)
            d = rnd_group(t, 4, 32)
            t.vset(8, 32, "m1")
            t.vload("v3", pack(k + d, 32), 32)
            t.vload("v4", pack(d, 32), 32)
            ng = 2 if lmul == "m8" else 1
            groups = [G(rnd_group(t, 4, 32)) for _ in range(ng)]
            t.vset(4 * ng, 32, lmul)
            vd = "v8" if lmul == "m8" else "v1"
            t.vload(vd, eg_words([x.vd for x in groups], 32), 32)
            line = eg_line(vmn, "v3", vd=vd)
            lab = t.trapwin(line, "ok",
                            f"{line}: vs2 = v3 is a legal scalar element group for LMUL={lmul}")  # fmt: skip
            exp = [eg_ref(vmn, x.vd, k, None, None, 32) for x in groups]
            t.vcheck(vd, eg_words(exp, 32), lab, f"{line} (LMUL={lmul})")

    vlen_at_least(t, 128, v3)

    t = add(new(ext, "veccrypto_vsins_vd", req))
    doc(t, f"{vmn} returns its results to vd, which is also the state operand: two vd groups with different "
           "states, one key; the result is the operation on each group's own state, written back to the same "
           "group. vd elements past vl stay undisturbed (tu).")  # fmt: skip
    g = [G(rnd_group(t, 4, 32)), G(rnd_group(t, 4, 32)), G(rnd_group(t, 4, 32))]
    key = rnd_group(t, 4, 32)
    decoy = rnd_group(t, 4, 32)
    exp = expect_groups(vmn, 32, g, key, decoy, None)

    def vd_body() -> None:
        load_groups(t, vmn, 32, g, key, decoy)
        t.vset(8, 32, "m8", "tu, mu")
        lab = t.insn(eg_line(vmn, "v16"))
        t.vset(12, 32, "m8")
        t.vcheck("v8", eg_words([exp[0], exp[1], g[2].vd], 32), lab, f"{vmn}: vd groups 0 and 1 updated, 2 "
                 "undisturbed")  # fmt: skip

    fit(t, 12, 32, vd_body)

    t = add(new(ext, "veccrypto_vsins_vs2function", req))
    doc(t, f"{vmn}: the single key in the vs2 scalar element group is applied to every element group of vd: two "
           "groups (a decoy group after the key in the vs2 register group must not be used), and four groups when "
           "VLEN >= 64 (vl = 16 at LMUL=8).")  # fmt: skip
    eg_case(t, vmn, 32, [G(rnd_group(t, 4, 32)) for _ in range(2)], key=rnd_group(t, 4, 32), desc=f"{vmn}, 2 groups")
    vlen_at_least(t, 64, lambda: eg_case(t, vmn, 32, [G(rnd_group(t, 4, 32)) for _ in range(4)],
                                         key=rnd_group(t, 4, 32), desc=f"{vmn}, 4 groups"))  # fmt: skip


def ext_rules(ext: str, req: list, prefix: str, egw: int, egs: int, mns: Sequence[tuple[str, int | None]], sew: int,
              group_rule: str, group_text: str) -> None:  # fmt: skip
    """<ext>_vl, <ext>_vstart and the element-group shape rule."""
    t = add(new(ext, f"{prefix}_vl", req))
    doc(t, f"The number of element groups processed is vl/EGS (EGS={egs}): for each instruction, vl = {egs} "
           f"processes group 0 only (group 1, in the tail, stays undisturbed with tu) and vl = 0 writes nothing.")  # fmt: skip
    for mn, imm in mns:
        eg_vl(t, mn, sew, imm)
    t = add(new(ext, f"{prefix}_vstart", req))
    doc(t, f"vstart = {egs} (a multiple of EGS) with vl = {2 * egs}, for each instruction: if it executes (an "
           "implementation may instead raise illegal-instruction for a nonzero vstart, vstart_vtype_dep), group 0 "
           "is a prestart group and stays undisturbed, group 1 is processed and vstart reads 0 afterwards; if it "
           "traps, vstart and vd are unchanged and xtval is 0 or the instruction bits.")  # fmt: skip
    for mn, imm in mns:
        eg_vstart(t, mn, sew, imm)
    t = add(new(ext, group_rule, req))
    doc(t, f"{group_text}: each instruction on two element groups at vl = {2 * egs}, SEW={sew}, LMUL=8, with "
           "distinct data in every element, so a wrong group size or element width moves results between groups.")  # fmt: skip
    for mn, imm in mns:
        eg_case(t, mn, sew, [rnd_G(t, mn, sew), rnd_G(t, mn, sew)], imm=imm, key=rnd_group(t, egs, sew))


# ---------------------------------------------------------------- Zvkned (AES)


def gen_zvkned() -> None:
    ext, req = "Zvkned", ["Zvkned"]
    mns = [("vaesef.vv", None), ("vaesem.vs", None), ("vaesdf.vv", None), ("vaesdm.vs", None), ("vaeskf1.vi", 3),
           ("vaeskf2.vi", 6), ("vaesz.vs", None)]  # fmt: skip
    ext_rules(ext, req, "Zvkned", 128, 4, mns, 32, "Zvkned_egw128b_elem32b",
              "128-bit element groups of four 32-bit elements")  # fmt: skip
    common_eg(ext, req, mns, 32, 128, "vaesef.vs")

    # FIPS-197 C.1 (AES-128) and C.3 (AES-256) round states
    key = b2e("000102030405060708090a0b0c0d0e0f")
    key256 = b2e("000102030405060708090a0b0c0d0e0f") + b2e("101112131415161718191a1b1c1d1e1f")
    pt = b2e("00112233445566778899aabbccddeeff")
    rk = L.aes_key_expand(key)
    rk2 = L.aes_key_expand256(key256)
    enc = [L.aes_round("vaesz", pt, rk[0])]
    for r in range(1, 10):
        enc.append(L.aes_round("vaesem", enc[-1], rk[r]))
    ct = L.aes_round("vaesef", enc[-1], rk[10])
    enc2 = [L.aes_round("vaesz", pt, rk2[0])]
    for r in range(1, 14):
        enc2.append(L.aes_round("vaesem", enc2[-1], rk2[r]))
    ct2 = L.aes_round("vaesef", enc2[-1], rk2[14])
    dec = [L.aes_round("vaesz", ct, rk[10])]
    for r in range(9, 0, -1):
        dec.append(L.aes_round("vaesdm", dec[-1], rk[r]))
    dec2 = [L.aes_round("vaesz", ct2, rk2[14])]
    for r in range(13, 0, -1):
        dec2.append(L.aes_round("vaesdm", dec2[-1], rk2[r]))
    fips = ("FIPS-197 Appendix C.1 (AES-128, key 000102..0f, plaintext 00112233..ff, ciphertext 69c4e0d8..c55a) "
            "and C.3 (AES-256, ciphertext 8ea2b7ca..6089)")  # fmt: skip

    def kat(rule: str, mn: str, groups: list[tuple[list[int], list[int]]], what: str) -> None:
        t = add(new(ext, rule, req))
        doc(t, f"Known answers from {fips}: {what}, as {mn}.vv with group 0 from AES-128 and group 1 from AES-256 "
               f"(each with its own round key), and as {mn}.vs with group 0's round key applied to both groups.")  # fmt: skip
        eg_case(t, f"{mn}.vv", 32, [G(s, k) for s, k in groups], desc=f"{mn}.vv FIPS-197 states")
        eg_case(t, f"{mn}.vs", 32, [G(s) for s, _ in groups], key=groups[0][1], desc=f"{mn}.vs FIPS-197 states")

    kat("vaesef_final", "vaesef", [(enc[9], rk[10]), (enc2[13], rk2[14])], "the last encryption round from the "
        "round-10 (round-14) state gives the ciphertext")  # fmt: skip
    kat("vaesem_mid", "vaesem", [(enc[0], rk[1]), (enc2[6], rk2[7])], "middle encryption rounds 1 (AES-128) and 7 "
        "(AES-256)")  # fmt: skip
    kat("vaesdf_final", "vaesdf", [(dec[9], rk[0]), (dec2[13], rk2[0])], "the last decryption round gives the "
        "plaintext")  # fmt: skip
    kat("vaesdm_mid", "vaesdm", [(dec[0], rk[9]), (dec2[4], rk2[9])], "middle decryption rounds (InvCipher round "
        "keys 9)")  # fmt: skip

    for rule, mn, what in (
        ("vaesef_ops", "vaesef", "SubBytes then ShiftRows (no MixColumns)"),
        ("vaesem_ops", "vaesem", "SubBytes, ShiftRows and MixColumns"),
        ("vaesdf_ops", "vaesdf", "InvShiftRows then InvSubBytes (no InvMixColumns)"),
        ("vaesdm_ops", "vaesdm", "InvShiftRows and InvSubBytes (then AddRoundKey and InvMixColumns)"),
    ):
        t = add(new(ext, rule, req))
        doc(t, f"{mn}.vv with an all-zero round key, so vd shows {what} alone: a state with 16 distinct bytes "
               "00..0f (any wrong row shift or direction moves a byte), a state of 0x00 (S-box(0) = 0x63, "
               "InvS-box(0) = 0x52) and 0xff bytes, and random states; two groups per instruction.")  # fmt: skip
        z = [0, 0, 0, 0]
        states = [b2e("000102030405060708090a0b0c0d0e0f"), [0] * 4, [M32] * 4, rnd_group(t, 4, 32),
                  rnd_group(t, 4, 32), b2e("f0e1d2c3b4a5968778695a4b3c2d1e0f")]  # fmt: skip
        for i in range(0, len(states), 2):
            eg_case(t, f"{mn}.vv", 32, [G(states[i], z), G(states[i + 1], z)], desc=f"{mn}.vv, round key 0")

    for rule, mn in (("vaesef_xor_form", "vaesef"), ("vaesem_xor_form", "vaesem"), ("vaesdf_xor_form", "vaesdf"),
                     ("vaesdm_xor_form", "vaesdm")):  # fmt: skip
        t = add(new(ext, rule, req))
        doc(t, f"The round key is XORed in from vs2: {mn}.vv with a different random key per group (the key of "
               f"group i is vs2 group i), the same state under two keys, and {mn}.vs where group 0 of the vs2 "
               "scalar element group is the key for both vd groups (a decoy group follows it).")  # fmt: skip
        s = rnd_group(t, 4, 32)
        eg_case(t, f"{mn}.vv", 32, [G(s, rnd_group(t, 4, 32)), G(s, rnd_group(t, 4, 32))], desc=f"{mn}.vv")
        eg_case(t, f"{mn}.vv", 32, [rnd_G(t, f"{mn}.vv", 32), rnd_G(t, f"{mn}.vv", 32)], desc=f"{mn}.vv")
        eg_case(t, f"{mn}.vs", 32, [G(rnd_group(t, 4, 32)), G(rnd_group(t, 4, 32))], key=rnd_group(t, 4, 32),
                desc=f"{mn}.vs")  # fmt: skip

    t = add(new(ext, "vaesdm_invmix", req))
    doc(t, "vaesdm applies InvMixColumns after AddRoundKey: random states with nonzero random keys (InvMixColumns "
           "of the key differs from the key, so the order is visible), single-byte states, and FIPS-197 "
           "InvCipher round 5.")  # fmt: skip
    eg_case(t, "vaesdm.vv", 32, [rnd_G(t, "vaesdm.vv", 32), rnd_G(t, "vaesdm.vv", 32)])
    eg_case(t, "vaesdm.vv", 32, [G([1, 0, 0, 0], [0, 0, 0, 0x01000000]), G([0, 0x80, 0, 0], [0x1B, 0, 0, 0])])
    eg_case(t, "vaesdm.vs", 32, [G(dec[4]), G(dec[5])], key=rk[5], desc="vaesdm.vs FIPS-197 InvCipher round 5")

    # ---- key schedule
    t = add(new(ext, "vaeskf1_round", req))
    doc(t, "vaeskf1.vi with uimm = 1..10 reproduces the FIPS-197 A.1 AES-128 key expansion (key 2b7e1516..), "
           "one round per instruction, in group 0; group 1 holds a random key at the same round.")  # fmt: skip
    k = b2e("2b7e151628aed2a6abf7158809cf4f3c")
    for r in range(1, 11):
        nxt = eg_case(t, "vaeskf1.vi", 32, [G([0] * 4, k), G([0] * 4, rnd_group(t, 4, 32))], imm=r)
        k = nxt[0]
    t = add(new(ext, "vaeskf1_wordgen", req))
    doc(t, "vaeskf1.vi word chaining: w[0] = SubWord(RotWord(key[3])) ^ Rcon ^ key[0], w[i] = w[i-1] ^ key[i]. "
           "Keys with a single nonzero word (word 0, 1, 2 or 3) show which words feed each output word; vd's prior "
           "contents are not used (random).")  # fmt: skip
    for i in range(4):
        kk = [0] * 4
        kk[i] = t.rand(32) | 1
        eg_case(t, "vaeskf1.vi", 32, [G(rnd_group(t, 4, 32), kk), G(rnd_group(t, 4, 32), [0] * 4)], imm=1)
    t = add(new(ext, "vaeskf1_uimm_src", req))
    doc(t, "vaeskf1.vi takes the round number from uimm[3:0]; uimm[4] is ignored: uimm = 17..26 give the same "
           "results as rounds 1..10.")  # fmt: skip
    for u in range(17, 27):
        eg_case(t, "vaeskf1.vi", 32, [rnd_G(t, "vaeskf1.vi", 32), rnd_G(t, "vaeskf1.vi", 32)], imm=u)
    t = add(new(ext, "vaeskf1_uimm_map", req))
    doc(t, "Out-of-range vaeskf1 rounds are mapped by inverting uimm[3]: uimm[3:0] = 0 -> 8, 11 -> 3, 12 -> 4, "
           "13 -> 5, 14 -> 6, 15 -> 7, also with uimm[4] set (16, 27, 31).")  # fmt: skip
    for u in (0, 11, 12, 13, 14, 15, 16, 27, 31):
        eg_case(t, "vaeskf1.vi", 32, [rnd_G(t, "vaeskf1.vi", 32), rnd_G(t, "vaeskf1.vi", 32)], imm=u)

    t = add(new(ext, "vaeskf2_round", req))
    doc(t, "vaeskf2.vi with uimm = 2..14 reproduces the FIPS-197 A.3 AES-256 key expansion (key 603deb10..): vd "
           "holds round key r-2, vs2 round key r-1, and the result is round key r; group 1 random.")  # fmt: skip
    kk = b2e("603deb1015ca71be2b73aef0857d7781") + b2e("1f352c073b6108d72d9810a30914dff4")
    ks = [kk[:4], kk[4:]]
    for r in range(2, 15):
        nxt = eg_case(t, "vaeskf2.vi", 32, [G(ks[-2], ks[-1]), rnd_G(t, "vaeskf2.vi", 32)], imm=r)
        ks.append(nxt[0])
    t = add(new(ext, "vaeskf2_wordgen", req))
    doc(t, "vaeskf2.vi word chaining from the previous round key in vd: w[0] = f(vs2[3]) ^ vd[0], w[i] = w[i-1] ^ "
           "vd[i]. vd with a single nonzero word (0..3) and vs2 with only word 3 nonzero, at an even (4) and an odd "
           "(5) round; vs2 words 0..2 must not be used.")  # fmt: skip
    for r in (4, 5):
        for i in range(4):
            vd = [0] * 4
            vd[i] = t.rand(32) | 1
            eg_case(t, "vaeskf2.vi", 32, [G(vd, [t.rand(32), 0, 0, t.rand(32)]), G(vd, [0, 0, 0, 0])], imm=r)
    t = add(new(ext, "vaeskf2_rcon_lsw", req))
    doc(t, "vaeskf2.vi on even rounds 2..14: the least significant word is SubWord(RotWord(vs2[3])) ^ Rcon[r/2-1] "
           "^ vd[0] (Rcon 01, 02, .., 40); vs2[3] = 0 in group 0 isolates the Rcon and S-box(0) contribution.")  # fmt: skip
    for r in range(2, 15, 2):
        eg_case(t, "vaeskf2.vi", 32, [G([0] * 4, [0] * 4), rnd_G(t, "vaeskf2.vi", 32)], imm=r)
    t = add(new(ext, "vaeskf2_rcon_func", req))
    doc(t, "The round number selects the function: odd rounds use SubWord(vs2[3]) with no RotWord and no Rcon, "
           "even rounds SubWord(RotWord(vs2[3])) ^ Rcon. The same operands at rounds 3/4, 5/6 and 13/14.")  # fmt: skip
    a, b = rnd_G(t, "vaeskf2.vi", 32), rnd_G(t, "vaeskf2.vi", 32)
    for r in (3, 4, 5, 6, 13, 14):
        eg_case(t, "vaeskf2.vi", 32, [a, b], imm=r)
    t = add(new(ext, "vaeskf2_uimm_src", req))
    doc(t, "vaeskf2.vi takes the round number from uimm[3:0]; uimm[4] is ignored: uimm = 18..30 give the same "
           "results as rounds 2..14.")  # fmt: skip
    for u in range(18, 31, 3):
        eg_case(t, "vaeskf2.vi", 32, [rnd_G(t, "vaeskf2.vi", 32), rnd_G(t, "vaeskf2.vi", 32)], imm=u)
    t = add(new(ext, "vaeskf2_uimm_map", req))
    doc(t, "Out-of-range vaeskf2 rounds are mapped by inverting uimm[3]: uimm[3:0] = 0 -> 8, 1 -> 9, 15 -> 7, also "
           "with uimm[4] set (16, 17, 31).")  # fmt: skip
    for u in (0, 1, 15, 16, 17, 31):
        eg_case(t, "vaeskf2.vi", 32, [rnd_G(t, "vaeskf2.vi", 32), rnd_G(t, "vaeskf2.vi", 32)], imm=u)

    t = add(new(ext, "vaesz_round0", req))
    doc(t, "vaesz.vs is the round-0 AddRoundKey: FIPS-197 C.1 plaintext XOR key 0 gives the round-1 start state "
           "(00102030..), for two groups (the second with the AES-256 plaintext state, same key); also an all-ones "
           "key.")  # fmt: skip
    eg_case(t, "vaesz.vs", 32, [G(pt), G(rnd_group(t, 4, 32))], key=key, desc="vaesz.vs FIPS-197 round 0")
    eg_case(t, "vaesz.vs", 32, [G(rnd_group(t, 4, 32)), G(pt)], key=[M32] * 4, desc="vaesz.vs, all-ones key")
    t = add(new(ext, "vaesz-vs_only", req))
    doc(t, "vaesz exists only as .vs: its vs2 operand is always a scalar element group, so with LMUL=8 and vl = 4, "
           "8 (and 16 when VLEN >= 64), every vd group uses vs2 group 0 and never the decoy group that follows it.")  # fmt: skip
    for n in (1, 2):
        eg_case(t, "vaesz.vs", 32, [G(rnd_group(t, 4, 32)) for _ in range(n)], key=rnd_group(t, 4, 32))
    vlen_at_least(t, 64, lambda: eg_case(t, "vaesz.vs", 32, [G(rnd_group(t, 4, 32)) for _ in range(4)],
                                         key=rnd_group(t, 4, 32)))  # fmt: skip
    t = add(new(ext, "vaesz_vs2_rk", req))
    doc(t, "vaesz.vs: vs2 holds the round key used for all round-state groups: two vd groups with distinct "
           "states, a random key and a decoy group in the vs2 register group; and vd = 0 states (result = key).")  # fmt: skip
    eg_case(t, "vaesz.vs", 32, [G(rnd_group(t, 4, 32)), G(rnd_group(t, 4, 32))], key=rnd_group(t, 4, 32))
    eg_case(t, "vaesz.vs", 32, [G([0] * 4), G([0] * 4)], key=rnd_group(t, 4, 32))


# ---------------------------------------------------------------- Zvknha / Zvknhb (SHA-2)


def _primes(n: int) -> list[int]:
    p: list[int] = []
    c = 2
    while len(p) < n:
        if all(c % q for q in p):
            p.append(c)
        c += 1
    return p


def _iroot(n: int, k: int) -> int:
    lo, hi = 0, 1 << (n.bit_length() // k + 2)
    while lo < hi:
        m = (lo + hi + 1) // 2
        if m**k <= n:
            lo = m
        else:
            hi = m - 1
    return lo


def sha_abc(sew: int) -> tuple[list[int], list[int], list[int]]:
    """FIPS 180-4 SHA-256 (sew=32) or SHA-512 (sew=64) of "abc": (initial state H0, message schedule W[0..], K)."""
    import struct

    frac = sew  # fractional bits of the constants
    k = [_iroot(p << (3 * frac), 3) & msk(sew) for p in _primes(64 if sew == 32 else 80)]
    h0 = [_iroot(p << (2 * frac), 2) & msk(sew) for p in _primes(8)]
    if sew == 32:
        msg = b"abc\x80" + b"\0" * 52 + struct.pack(">Q", 24)
        w = list(struct.unpack(">16I", msg))
    else:
        msg = b"abc\x80" + b"\0" * 108 + struct.pack(">QQ", 0, 24)
        w = list(struct.unpack(">16Q", msg))
    return h0, w, k


def gen_zvknh() -> None:
    for ext, req, sew in (("Zvknha", ["Zvknha"], 32), ("Zvknhb", ["Zvknhb"], 64)):
        egw = 4 * sew
        mns = [("vsha2ch.vv", None), ("vsha2cl.vv", None), ("vsha2ms.vv", None)]
        if ext == "Zvknha":
            ext_rules(ext, req, "Zvknha_Zvknhb", egw, 4, mns, sew, "Zvknha_Zvknhb_sha256_egw128b_elem32b",
                      "SHA-256: 128-bit element groups of four 32-bit elements")  # fmt: skip
        else:
            ext_rules(ext, req, "Zvknha_Zvknhb", egw, 4, mns, sew, "Zvknhb_sha512_egw256b_elem64b",
                      "SHA-512: 256-bit element groups of four 64-bit elements")  # fmt: skip
        common_eg(ext, req, mns, sew, egw, None)

        h0, w, k = sha_abc(sew)
        a, b, c, d, e, f, g, hh = h0
        abef, cdgh = [f, e, b, a], [hh, g, d, c]
        for j in range(16, 20 if sew == 32 else 24):
            w.append(L.sha2ms(w[j - 16:j - 12], [w[j - 12], w[j - 7], w[j - 6], w[j - 5]], w[j - 4:j], sew)[j % 4]
                     if j % 4 == 0 or True else 0)  # fmt: skip
        w = w[:16]
        ms = L.sha2ms(w[0:4], [w[4], w[9], w[10], w[11]], w[12:16], sew)
        alg = "SHA-256" if sew == 32 else "SHA-512"
        name = "sew32" if sew == 32 else "sew64"
        wk = [(w[i] + k[i]) & msk(sew) for i in range(4)]

        t = add(new(ext, f"vsha2chl-vv_op_{name}", req))
        doc(t, f"SEW={sew}: two rounds of {alg} compression per instruction. Known answer: {alg}('abc') "
               "(FIPS 180-4): from H0 in {f,e,b,a} (vs2) and {h,g,d,c} (vd), vsha2cl with W[0..3]+K[0..3] (rounds "
               "0-1) then vsha2ch (rounds 2-3), the old {f,e,b,a} becoming the next {h,g,d,c}; group 1 random.",
            context="Results are cross-checked: chaining these instructions over all rounds reproduces "
                    f"{alg}('abc').")  # fmt: skip
        r1 = eg_case(t, "vsha2cl.vv", sew, [G(cdgh, abef, wk), rnd_G(t, "vsha2cl.vv", sew)])
        eg_case(t, "vsha2ch.vv", sew, [G(abef, r1[0], wk), rnd_G(t, "vsha2ch.vv", sew)])

        t = add(new(ext, f"vsha2ms-vv_op_{name}", req))
        doc(t, f"SEW={sew}: four rounds of {alg} message-schedule expansion. Known answer: W[16..19] of "
               f"{alg}('abc') from vd = W[0..3], vs2 = {{W[4], W[9], W[10], W[11]}}, vs1 = W[12..15]; group 1 "
               "random.")  # fmt: skip
        eg_case(t, "vsha2ms.vv", sew, [G(w[0:4], [w[4], w[9], w[10], w[11]], w[12:16]), rnd_G(t, "vsha2ms.vv", sew)])
        _ = ms

        if ext == "Zvknha":
            t = add(new(ext, "vsha2chl-vv_op", req))
            doc(t, "Two words of vs1 are used with the 8 state words in vd and vs2: vsha2cl uses vs1 elements 0-1 "
                   "and vsha2ch elements 2-3. Both run on the same operands (so swapping them is visible); vs1 with "
                   "only elements 0-1 or only 2-3 nonzero; state words each set alone (a, b, e, f in vs2; c, d, g, "
                   "h in vd) to show which inputs feed the four output words. SEW=32 (SEW=64 is in Zvknhb).")  # fmt: skip
            for mn in ("vsha2cl.vv", "vsha2ch.vv"):
                gg = [rnd_G(t, mn, 32), rnd_G(t, mn, 32)]
                eg_case(t, mn, 32, gg)
                eg_case(t, mn, 32, [G(gg[0].vd, gg[0].vs2, [t.rand(32), t.rand(32), 0, 0]),
                                    G(gg[1].vd, gg[1].vs2, [0, 0, t.rand(32), t.rand(32)])])  # fmt: skip
                for i in range(4):
                    one = [0] * 4
                    one[i] = t.rand(32)
                    eg_case(t, mn, 32, [G([0] * 4, one, [0] * 4), G(one, [0] * 4, [0] * 4)])
            t = add(new(ext, "vsha2ms-vv_op", req))
            doc(t, "Eleven of the last 16 message words are used: vd = W[0..3] (oldest), vs2 = {W[4], W[9], W[10], "
                   "W[11]}, vs1 = W[12..15] (most recent). Each input element set alone (others zero) shows its "
                   "role in W[16..19]; W[5..8] have no operand. SEW=32.")  # fmt: skip
            for reg in ("vd", "vs2", "vs1"):
                for i in range(4):
                    one = [0] * 4
                    one[i] = t.rand(32) | 1 << 31
                    z = [0] * 4
                    gg = G(one if reg == "vd" else z, one if reg == "vs2" else z, one if reg == "vs1" else z)
                    eg_case(t, "vsha2ms.vv", 32, [gg, rnd_G(t, "vsha2ms.vv", 32)], desc=f"vsha2ms.vv {reg}[{i}] alone")
            t = add(new(ext, "Zvknha_sha256", req))
            doc(t, "Zvknha supports SHA-256: vsha2ch, vsha2cl and vsha2ms execute at SEW=32 (SEW=64 is reserved for "
                   "Zvknha and not tested).")  # fmt: skip
            for mn, _ in mns:
                eg_case(t, mn, 32, [rnd_G(t, mn, 32)])
        else:
            t = add(new(ext, "Zvknhb_sha256_sha512", req))
            doc(t, "Zvknhb supports SHA-256 and SHA-512: each instruction at SEW=32 and at SEW=64 in one test.")
            for s in (32, 64):
                for mn, _ in mns:
                    eg_case(t, mn, s, [rnd_G(t, mn, s)])
            t = add(new(ext, "Zvknhb_impZvknha", req))
            doc(t, "Zvknhb implies Zvknha: the SHA-256 instructions (SEW=32) work on a Zvknhb hart, with the SHA-256 "
                   "('abc') known answers for vsha2cl, vsha2ch and vsha2ms.")  # fmt: skip
            h0, w32, k32 = sha_abc(32)
            a, b, c, d, e, f, g, hh = h0
            wk = [(w32[i] + k32[i]) & M32 for i in range(4)]
            r1 = eg_case(t, "vsha2cl.vv", 32, [G([hh, g, d, c], [f, e, b, a], wk)])
            eg_case(t, "vsha2ch.vv", 32, [G([f, e, b, a], r1[0], wk)])
            eg_case(t, "vsha2ms.vv", 32, [G(w32[0:4], [w32[4], w32[9], w32[10], w32[11]], w32[12:16])])
            t = add(new(ext, "Zvknhb_Zvkn_Zvknc_Zvkng_Zvksc_depZve64x", req))
            doc(t, "The Zve64x dependency, observed as its features: SEW=8..64 at LMUL=1 are legal vtypes, VLEN >= 64, "
                   "and vadd.vv works at SEW=64.")  # fmt: skip
            dep_zve(t, 64)


# ---------------------------------------------------------------- Zvkg (GHASH)


def gcm_poly(coeffs: Sequence[int]) -> list[int]:
    """A GF(2^128) element in GCM bit order (coefficient i is bit 7 - i%8 of byte i//8) as four elements."""
    b = [0] * 16
    for c in coeffs:
        b[c // 8] |= 0x80 >> (c % 8)
    return L.eg_elems(b)


def gen_zvkg() -> None:
    ext, req = "Zvkg", ["Zvkg"]
    mns = [("vghsh.vv", None), ("vgmul.vv", None)]
    ext_rules(ext, req, "Zvkg", 128, 4, mns, 32, "Zvkg_egw128b_elem32b", "128-bit element groups of four 32-bit "
              "elements")  # fmt: skip
    common_eg(ext, req, mns, 32, 128, None)
    hkey = b2e("66e94bd4ef8a2c3b884cfa59ca342b2e")
    c = b2e("0388dace60b6a392f328c2b971b2fe78")
    lenb = b2e("00000000000000000000000000000080")
    gcm = ("GCM specification test case 2 (key 0, IV 0, one zero plaintext block: H = 66e94bd4.., C = 0388dace.., "
           "GHASH = f38cbb1a..)")  # fmt: skip

    t = add(new(ext, "vghsh-vv_op", req))
    doc(t, f"Known answer from the {gcm}: Y1 = (0 + C) * H, then Y2 = (Y1 + len) * H = GHASH, as two vghsh.vv "
           "steps; group 1 random. vd = Y, vs1 = X, vs2 = H.")  # fmt: skip
    y1 = eg_case(t, "vghsh.vv", 32, [G([0] * 4, hkey, c), rnd_G(t, "vghsh.vv", 32)])[0]
    eg_case(t, "vghsh.vv", 32, [G(y1, hkey, lenb), rnd_G(t, "vghsh.vv", 32)])
    t = add(new(ext, "vgmul-vv_op", req))
    doc(t, f"Known answer from the {gcm}: vgmul.vv of vd = C and vs2 = H gives Y1 = C * H; then (Y1 + len) * H with "
           "the addition done beforehand (vxor) gives GHASH; group 1 random.")  # fmt: skip
    y1 = eg_case(t, "vgmul.vv", 32, [G(c, hkey), rnd_G(t, "vgmul.vv", 32)])[0]
    eg_case(t, "vgmul.vv", 32, [G([a ^ b for a, b in zip(y1, lenb)], hkey), rnd_G(t, "vgmul.vv", 32)])

    for mn, rule in (("vghsh.vv", "vghsh-vv_op_gf"), ("vgmul.vv", "vgmul-vv_op_gf")):
        t = add(new(ext, rule, req))
        doc(t, f"{mn}: multiplication modulo x^128 + x^7 + x^2 + x + 1: x^127 * x = x^128 = x^7 + x^2 + x + 1 "
               "(byte 0 = 0xe1), x^127 * x^127, x^64 * x^64 = x^128, (x^127 + 1) * x, and a random product; "
               f"{'for vghsh the factor is vd + vs1 (vs1 = 0 here, or vd = 0)' if mn == 'vghsh.vv' else 'vd * vs2'}.")  # fmt: skip
        pairs = [([127], [1]), ([127], [127]), ([64], [64]), ([127, 0], [1]), (None, None)]
        gs = []
        for p, q in pairs:
            a = gcm_poly(p) if p is not None else rnd_group(t, 4, 32)
            b = gcm_poly(q) if q is not None else rnd_group(t, 4, 32)
            gs.append(G(a, b, [0] * 4) if mn == "vghsh.vv" else G(a, b))
        if mn == "vghsh.vv":
            gs.append(G([0] * 4, gcm_poly([1]), gcm_poly([127])))
        for i in range(0, len(gs) - 1, 2):
            eg_case(t, mn, 32, [gs[i], gs[i + 1]])
        if len(gs) % 2:
            eg_case(t, mn, 32, [gs[-1]])

    for mn, rule in (("vghsh.vv", "vghsh-vv_op_coeff"), ("vgmul.vv", "vgmul-vv_op_coeff")):
        t = add(new(ext, rule, req))
        doc(t, f"{mn}: coefficient order (x^0 is bit 7 of byte 0, the bits of each byte are reversed internally): "
               "1 (byte 0 = 0x80) times H gives H; x^7 (byte 0 = 0x01) times x (0x40) gives x^8 (byte 1 = 0x80); "
               "x^8 times x^120 (byte 15 = 0x80) gives x^128 (0xe1); single coefficients at byte boundaries; for vghsh also X (vs1) as a single coefficient with Y = 0.")  # fmt: skip
        hh = rnd_group(t, 4, 32)
        pairs = [(gcm_poly([0]), hh), (gcm_poly([7]), gcm_poly([1])), (gcm_poly([8]), gcm_poly([120])),
                 (gcm_poly([15]), gcm_poly([9])), (gcm_poly([31]), gcm_poly([32])), (gcm_poly([63]), gcm_poly([0]))]  # fmt: skip
        for i in range(0, len(pairs), 2):
            gs = []
            for a, b in pairs[i : i + 2]:
                gs.append(G(a, b, [0] * 4) if mn == "vghsh.vv" else G(a, b))
            eg_case(t, mn, 32, gs)
        if mn == "vghsh.vv":  # the coefficient order of X (vs1): vd = 0, vs1 a single coefficient
            eg_case(t, mn, 32, [G([0] * 4, gcm_poly([1]), gcm_poly([7])), G([0] * 4, gcm_poly([9]), gcm_poly([120]))])


# ---------------------------------------------------------------- Zvksed (SM4)


def gen_zvksed() -> None:
    ext, req = "Zvksed", ["Zvksed"]
    mns = [("vsm4k.vi", 5), ("vsm4r.vv", None), ("vsm4r.vs", None)]
    ext_rules(ext, req, "Zvksed", 128, 4, mns, 32, "Zvksed_egw128b_elem32b", "128-bit element groups of four "
              "32-bit elements")  # fmt: skip
    common_eg(ext, req, mns, 32, 128, "vsm4r.vs")
    mk = [0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210]
    fk = [0xA3B1BAC6, 0x56AA3350, 0x677D9197, 0xB27022DC]
    std = ("GB/T 32907 (SM4) standard example: key = plaintext = 0123456789abcdeffedcba9876543210, ciphertext "
           "681edf34d206965e86b3e94f536e4246 (words as 32-bit element values)")  # fmt: skip

    t = add(new(ext, "vsm4k-vi_op", req))
    doc(t, f"Known answer from the {std}: from K = MK ^ FK, vsm4k.vi rounds 0..7 give round keys rk0..rk31 "
           "(rk0 = f12186f9, rk31 = 9124a012), four per instruction, each output feeding the next; group 1 random.")  # fmt: skip
    kk = [a ^ b for a, b in zip(mk, fk)]
    rks: list[int] = []
    for r in range(8):
        kk = eg_case(t, "vsm4k.vi", 32, [G(rnd_group(t, 4, 32), kk), rnd_G(t, "vsm4k.vi", 32)], imm=r)[0]
        rks += kk
    assert rks[0] == 0xF12186F9 and rks[31] == 0x9124A012 or MUT

    t = add(new(ext, "vsm4k-vi_op_sm4k", req))
    doc(t, "vsm4k.vi key expansion structure: rk[i+4] = rk[i] ^ L'(S(rk[i+1] ^ rk[i+2] ^ rk[i+3] ^ CK[4r+i])), "
           "iterated so each new key feeds the next. Inputs with a single nonzero word (0..3), all zero (only CK "
           "and S-box(0) contribute) at rounds 0 and 7, and random words.")  # fmt: skip
    for i in range(4):
        one = [0] * 4
        one[i] = t.rand(32) | 1
        eg_case(t, "vsm4k.vi", 32, [G(rnd_group(t, 4, 32), one), G(rnd_group(t, 4, 32), [0] * 4)], imm=i)
    eg_case(t, "vsm4k.vi", 32, [G([0] * 4, [0] * 4), G([0] * 4, [0] * 4)], imm=7)
    t = add(new(ext, "vsm4k-vi_op_rnd", req))
    doc(t, "The round group number is uimm[2:0]; uimm[4:3] are ignored: the same operands with uimm = r, r+8, r+16 "
           "and r+24 for r = 1 and 6, and uimm = 31.")  # fmt: skip
    gg = [rnd_G(t, "vsm4k.vi", 32), rnd_G(t, "vsm4k.vi", 32)]
    for u in (1, 9, 17, 25, 6, 14, 22, 30, 31):
        eg_case(t, "vsm4k.vi", 32, gg, imm=u)

    t = add(new(ext, "vsm4r_op", req))
    doc(t, f"Known answer from the {std}: eight vsm4r.vv instructions (four rounds each, round keys from the "
           "standard key expansion) take the plaintext to X32..X35, whose reverse is the ciphertext; group 1 "
           "random.")  # fmt: skip
    x = list(mk)
    for r in range(8):
        x = eg_case(t, "vsm4r.vv", 32, [G(x, rks[4 * r : 4 * r + 4]), rnd_G(t, "vsm4r.vv", 32)])[0]
    assert x[::-1] == [0x681EDF34, 0xD206965E, 0x86B3E94F, 0x536E4246] or MUT
    t = add(new(ext, "vsm4r_op_sm4encdec", req))
    doc(t, "vsm4r round keys come from the corresponding vs2 group (.vv) or the scalar group (.vs); encryption and "
           "decryption are the same rounds with the key order reversed: the standard ciphertext "
           "decrypts with rk31..rk0 back to the plaintext, as .vs (one key group for both vd groups, the second a "
           "random state) and as .vv.")  # fmt: skip
    y = [0x681EDF34, 0xD206965E, 0x86B3E94F, 0x536E4246]
    dk = rks[::-1]
    for r in range(8):
        y = eg_case(t, "vsm4r.vs", 32, [G(y), G(rnd_group(t, 4, 32))], key=dk[4 * r:4 * r + 4],
                    desc=f"vsm4r.vs decryption rounds {4 * r}-{4 * r + 3}")[0]  # fmt: skip
    assert y[::-1] == mk or MUT
    eg_case(t, "vsm4r.vv", 32, [G(mk, rks[0:4]), G(mk, dk[0:4])], desc="vsm4r.vv, two key groups")


# ---------------------------------------------------------------- Zvksh (SM3)


def sm3_abc() -> tuple[list[int], list[int], list[list[int]]]:
    """SM3('abc') (GB/T 32905): message words as element values (byte-swapped), W[0..67], and the state before
    each two-round step."""
    import struct

    iv = [0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600, 0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E]
    msg = b"abc\x80" + b"\0" * 52 + struct.pack(">Q", 24)
    we = [L.rev8(v, 32) for v in struct.unpack(">16I", msg)]
    while len(we) < 68:
        j = len(we)
        we += L.vsm3me(we[j - 8 : j], we[j - 16 : j - 8])
    st = [L.rev8(v, 32) for v in iv]
    states = [st]
    for r in range(32):
        st = L.vsm3c(st, we[2 * r : 2 * r + 8], r)
        states.append(st)
    return iv, we, states


def gen_zvksh() -> None:
    ext, req = "Zvksh", ["Zvksh"]
    mns = [("vsm3me.vv", None), ("vsm3c.vi", 9)]
    ext_rules(ext, req, "Zvksh", 256, 8, mns, 32, "Zvksh_egw256b_elem32b", "256-bit element groups of eight 32-bit "
              "elements")  # fmt: skip
    common_eg(ext, req, mns, 32, 256, None)
    _iv, we, states = sm3_abc()
    std = "SM3('abc') (GB/T 32905, digest 66c7f0f4..8f4ba8e0; message and state words byte-swapped into elements)"

    t = add(new(ext, "vsm3me-vv_op", req))
    doc(t, f"Known answer from {std}: vsm3me.vv with vs1 = W[0..7] and vs2 = W[8..15] gives W[16..23], then W[8..15] "
           "and W[16..23] give W[24..31]; one group per instruction (EGS = 8, vl = 8).")  # fmt: skip
    eg_case(t, "vsm3me.vv", 32, [G(rnd_group(t, 8, 32), we[8:16], we[0:8])])
    eg_case(t, "vsm3me.vv", 32, [G(rnd_group(t, 8, 32), we[16:24], we[8:16])])
    t = add(new(ext, "vsm3me-vv_op_sm3", req))
    doc(t, "vsm3me.vv reads the 16 most recent message words as two 8-element groups (vs1 older, vs2 newer), "
           "byte-swaps them in and out: inputs with a single nonzero byte at each byte position of one word, and "
           "random words; vd's prior contents are not used.")  # fmt: skip
    for k in range(4):
        w = [0] * 16
        w[3 + 4 * k] = 0xA5 << (8 * k)
        eg_case(t, "vsm3me.vv", 32, [G(rnd_group(t, 8, 32), w[8:16], w[0:8])])
    eg_case(t, "vsm3me.vv", 32, [rnd_G(t, "vsm3me.vv", 32)])

    t = add(new(ext, "vsm3c-vi_op", req))
    doc(t, f"Known answer from {std}: vsm3c.vi with uimm = 0 (rounds 0-1) from the IV, uimm = 8 (rounds 16-17, "
           "the second FF/GG/T family) and uimm = 31 (rounds 62-63) from the intermediate states; vs2 holds "
           "W[2u..2u+7].")  # fmt: skip
    for u in (0, 8, 31):
        eg_case(t, "vsm3c.vi", 32, [G(states[u], we[2 * u : 2 * u + 8])], imm=u)
    t = add(new(ext, "vsm3c-vi_op_sm3", req))
    doc(t, "vsm3c.vi uses only message words 0, 1, 4 and 5 of vs2 (W[j], W[j+1], W[j+4], W[j+5]): the same state "
           "and words with different decoys in elements 2, 3, 6, 7 give the same result; each used word alone "
           "(others zero) shows its role; state elements byte-swapped in and out.")  # fmt: skip
    st, w8 = rnd_group(t, 8, 32), rnd_group(t, 8, 32)
    for _ in range(2):
        d = list(w8)
        for i in (2, 3, 6, 7):
            d[i] = t.rand(32)
        eg_case(t, "vsm3c.vi", 32, [G(st, d)], imm=3)
    for i in (0, 1, 4, 5):
        one = [0] * 8
        one[i] = t.rand(32)
        eg_case(t, "vsm3c.vi", 32, [G(st, one)], imm=3)
    t = add(new(ext, "vsm3c-vi_op_rnd", req))
    doc(t, "The 5-bit uimm selects rounds 2*uimm and 2*uimm+1: the same state and words at uimm = 0, 1, 7 (rounds "
           "14-15, last of the first family), 8 (16-17, first of the second), 15, 16 (rounds 32-33: T_j rotated by "
           "j mod 32 = 0) and 31.")  # fmt: skip
    st, w8 = rnd_group(t, 8, 32), rnd_group(t, 8, 32)
    for u in (0, 1, 7, 8, 15, 16, 31):
        eg_case(t, "vsm3c.vi", 32, [G(st, w8)], imm=u)


# ---------------------------------------------------------------- shorthands


def gen_shorthands() -> None:
    def aes(t: VT) -> None:
        eg_case(t, "vaesz.vs", 32, [G(rnd_group(t, 4, 32))], key=rnd_group(t, 4, 32))
        eg_case(t, "vaesem.vv", 32, [rnd_G(t, "vaesem.vv", 32)])

    def sha512(t: VT) -> None:
        eg_case(t, "vsha2ms.vv", 64, [rnd_G(t, "vsha2ms.vv", 64)])
        eg_case(t, "vsha2ch.vv", 32, [rnd_G(t, "vsha2ch.vv", 32)])

    def kb(t: VT) -> None:
        ew(t, "vandn.vv", 32, [t.rand(32) for _ in range(4)], lambda a, b, x: r_vandn(a, b, 32),
           vs1=[t.rand(32) for _ in range(4)])  # fmt: skip
        unary(t, "vrev8.v", 32, [t.rand(32) for _ in range(4)], r_rev8)

    def bc(t: VT) -> None:
        a, b = [t.rand(64) for _ in range(2)], [t.rand(64) for _ in range(2)]
        ew(t, "vclmul.vv", 64, a, lambda x, y, xl: r_clmul(x, y, False), vs1=b)

    def gcm(t: VT) -> None:
        eg_case(t, "vghsh.vv", 32, [rnd_G(t, "vghsh.vv", 32)])

    def sm4(t: VT) -> None:
        eg_case(t, "vsm4r.vs", 32, [G(rnd_group(t, 4, 32))], key=rnd_group(t, 4, 32))
        eg_case(t, "vsm4k.vi", 32, [rnd_G(t, "vsm4k.vi", 32)], imm=2)

    def sm3(t: VT) -> None:
        eg_case(t, "vsm3me.vv", 32, [rnd_G(t, "vsm3me.vv", 32)])
        eg_case(t, "vsm3c.vi", 32, [rnd_G(t, "vsm3c.vi", 32)], imm=4)

    defs = {
        "Zvkn": (["Zvkned", "Zvknhb", "Zvkb"], [aes, sha512, kb]),
        "Zvknc": (["Zvkned", "Zvknhb", "Zvkb", "Zvbc"], [aes, sha512, kb, bc]),
        "Zvkng": (["Zvkned", "Zvknhb", "Zvkb", "Zvkg"], [aes, sha512, kb, gcm]),
        "Zvks": (["Zvksed", "Zvksh", "Zvkb"], [sm4, sm3, kb]),
        "Zvksc": (["Zvksed", "Zvksh", "Zvkb", "Zvbc"], [sm4, sm3, kb, bc]),
        "Zvksg": (["Zvksed", "Zvksh", "Zvkb", "Zvkg"], [sm4, sm3, kb, gcm]),
    }
    for ext, (inc, fns) in defs.items():
        t = add(new(ext, f"{ext}_def", [ext], exts=inc))
        doc(t, f"{ext} includes {', '.join(inc)} and Zvkt: one instruction (or two) of each included extension "
               "executes with the defined result (Zvkt's data-independent latency is not observable).")  # fmt: skip
        for f in fns:
            f(t)


def gen() -> list[VT]:
    TESTS.clear()
    gen_zvkb()
    gen_zvbb()
    gen_zvbc()
    gen_zvfh()
    gen_zvfhmin()
    gen_zvfbf()
    gen_zvkned()
    gen_zvknh()
    gen_zvkg()
    gen_zvksed()
    gen_zvksh()
    gen_shorthands()
    names = [f"{t.suite}/{t.rule}{t.suffix}" for t in TESTS]
    dup = {n for n in names if names.count(n) > 1}
    assert not dup, f"duplicate tests: {dup}"
    return list(TESTS)


def main() -> None:
    only = set(sys.argv[1:])
    for t in gen():
        if only and t.rule not in only and t.suite not in only:
            continue
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
