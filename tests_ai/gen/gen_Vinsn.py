#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the vector instruction part of tests_ai/V: one test per normative rule of the Integer Arithmetic,
Fixed-Point, Floating-Point, Reduction, Mask, Integer Permutation and FP Permutation sections of
src/unpriv/vector-common.adoc.

Expected values come from the instruction definitions in the rules (integer arithmetic, vxrm rounding, and an exact
rational IEEE 754 model in vinsnlib). Each test checks the cases the spec calls out for its rule; the human ACT
vector plans (testplans/Vx.csv, Vf.csv) already cross operand values with SEW, LMUL and policies.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Sequence
from fractions import Fraction as Fr
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict, cast

sys.path.insert(0, str(Path(__file__).parent))
from aigen import X
from vinsnlib import (
    CNAN,
    FMT,
    NV,
    NX,
    OF,
    REC7,
    REQ,
    RSQRT7,
    RTZ,
    RULES,
    VTest,
    f2i,
    fadd,
    fclass,
    fcmp,
    fcvt_ff,
    fdiv,
    fenc,
    fma,
    fminmax,
    fmul,
    fparams,
    fpinf,
    fpmax,
    fpzero,
    frec7,
    frsqrt7,
    fsqrt,
    i2f,
    isnan,
    lmul_val,
    m,
    mpol,
    ones,
    pol,
    qnan,
    roundoff,
    snan,
    sx,
)

if TYPE_CHECKING:
    from typing_extensions import Unpack
    from vinsnlib import Legal


class MresOptions(TypedDict, total=False):
    """mres's optional keyword arguments, for wrappers that pass them through (**kw: Unpack[...])."""

    lmul: str | None
    vl: int | None
    mask: Sequence[int] | None
    ma: bool
    ta: bool
    old: Sequence[int] | None
    vd: str
    frm: int | None
    aeew: int | None
    bmask: bool


SRC = "src/unpriv/vector-common.adoc"
FMT_P = {w: FMT[w][1] + 1 for w in FMT}  # significand precision
FMTS = {w: fparams(w) for w in FMT}  # (exponent bits, fraction bits, bias, emin)
FISNAN = isnan
SUITE = "Vinsn"
MUT = os.environ.get("AI_MUTANT", "")
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"

MUTANTS = {
    # integer
    "vrsub_order": "vrsub computes vs2 - x instead of x - vs2",
    "vwadd_zext": "vwadd zero-extends its narrow operands (behaves like vwaddu)",
    "vsext_as_zext": "vsext zero-extends",
    "ext_src_emul_lmul": "vzext/vsext read their source with EMUL = LMUL (elements past the first source register "
    "come from the next register)",
    "vadc_masked_off_kept": "vadc leaves elements whose v0 bit is 0 undisturbed",
    "vmadc_unmasked_cin": "unmasked vmadc still adds v0 as carry-in",
    "vmsbc_unsigned_wrong": "vmsbc borrow computed from the signed difference",
    "shamt_unmasked": "vsll/vsrl/vsra use the whole shift amount (shifts >= SEW give 0)",
    "nshamt_sew_bits": "narrowing shifts mask the shift amount to lg2(SEW) instead of lg2(2*SEW) bits",
    "vmsltu_signed": "vmsltu compares signed",
    "vmsleu_vi_zext": "vmsleu.vi zero-extends its immediate",
    "cmp_v0_ignores_mask": "a masked compare into v0 overwrites inactive elements (no AND with the old mask)",
    "mask_tail_zero": "mask-producing instructions clear their tail bits",
    "vmulhsu_swapped": "vmulhsu treats vs1 as the signed operand",
    "vdiv_zero_0": "vdiv/vdivu by zero return 0",
    "vrem_overflow_dividend": "vrem of MIN by -1 returns the dividend",
    "vwmaccus_as_su": "vwmaccus treats x[rs1] as signed and vs2 as unsigned",
    "vnmsac_as_vmadd": "vnmsac adds the product to vs2 instead of subtracting it from vd",
    "vmerge_masked_policy": "vmerge treats mask-0 elements as inactive (mask agnostic overwrites them)",
    # fixed point
    "vsadd_wrap": "vsadd wraps on overflow instead of saturating",
    "vxsat_not_set": "a saturating add does not set vxsat",
    "vxsat_cleared": "a non-saturating instruction clears vxsat",
    "vaadd_rdn_always": "averaging adds ignore vxrm (always truncate)",
    "vasubu_signed": "vasubu treats the difference as signed",
    "vsmul_no_sat": "vsmul does not saturate (-1 * -1 wraps to -1)",
    "vssra_logical": "vssra shifts in zeros",
    "vnclip_sat_after_trunc": "vnclip saturates before rounding",
    "vnclipu_signed": "vnclipu saturates the source as a signed value",
    # floating point
    "vfrsub_order": "vfrsub computes vs2 - f instead of f - vs2",
    "vfwadd_narrow_round": "vfwadd rounds the sum to SEW before widening",
    "vfmsac_sign": "vfmsac computes vd - vs1*vs2",
    "vfma_unfused": "vector FMA rounds the product",
    "vfrec7_no_denorm": "vfrec7 flushes subnormal outputs to zero",
    "vfrsqrt7_exp_parity": "vfrsqrt7 ignores the exponent LSB in the table index",
    "vfrec7_of_rtz_inf": "vfrec7 of a tiny input returns infinity under RTZ",
    "vfmin_nan_prop": "vfmin returns the canonical NaN when one input is NaN",
    "vfmin_zero_order": "vfmin treats -0 and +0 as equal and returns vs2",
    "vmfeq_qnan_nv": "vmfeq raises NV on a quiet NaN",
    "vmflt_qnan_quiet": "vmflt raises no NV on a quiet NaN",
    "vmfne_nan_0": "vmfne writes 0 for a NaN operand",
    "vfclass_snan_qnan": "vfclass swaps the signaling and quiet NaN bits",
    "vfmerge_masked_policy": "vfmerge treats mask-0 elements as inactive",
    "vfcvt_rtz_uses_frm": "vfcvt.rtz.* use frm",
    "vfcvt_nan_min": "vfcvt.x.f.v of NaN returns the most negative integer",
    "vfncvt_rod_rne": "vfncvt.rod.f.f.w rounds to nearest even",
    "fflags_inactive": "masked-off elements raise FP exception flags",
    "fs_off_ok": "vector FP instructions execute with mstatus.FS = Off",
    "fs_not_dirty": "vector FP instructions that set fflags leave mstatus.FS Clean",
    # reductions
    "red_vl0_writes": "a reduction with vl = 0 writes vs1[0] to vd[0]",
    "red_vstart_ok": "a reduction executes with vstart != 0",
    "red_mask_drops_scalar": "a reduction with all elements masked off returns 0 instead of vs1[0]",
    "vredmaxu_signed": "vredmaxu compares signed",
    "vwredsum_zext": "vwredsum zero-extends its elements",
    "vfredosum_unordered": "vfredosum adds the elements before the scalar",
    "vfredosum_maskoff_flags": "masked-off elements of vfredosum raise flags",
    "vfredusum_identity_pos": "vfredusum uses +0 as its additive identity in every rounding mode",
    "vfredmax_nan": "vfredmax returns NaN when one element is NaN",
    "red_scalar_lmul": "the reduction scalar operand is read as an LMUL group (unaligned vs1 traps)",
    # mask
    "vcpop_vl0_nowrite": "vcpop.m with vl = 0 leaves rd unchanged",
    "vfirst_none_0": "vfirst.m with no set bit writes 0",
    "vfirst_ignores_mask": "masked vfirst.m also finds set bits in inactive elements",
    "vmsbf_none_0": "vmsbf.m with no set bit writes 0s",
    "vmsif_as_vmsbf": "vmsif.m does not include the first set element",
    "vmsof_all_after": "vmsof.m sets every element from the first set one",
    "viota_inclusive": "viota.m counts the element itself (inclusive prefix sum)",
    "viota_masked_counts_all": "masked viota.m also counts inactive elements",
    "vid_masked_compact": "masked vid.v writes consecutive indices to the active elements",
    "mask_vstart_ignored": "mask-logical instructions also write elements below vstart",
    "mask_lmul_group": "mask-logical instructions with LMUL=8 also write the next register",
    "vmandn_swapped": "vmandn computes !vs2 && vs1",
    # permutation
    "vmvxs_zext": "vmv.x.s zero-extends elements narrower than XLEN",
    "vmvsx_vl0_writes": "vmv.s.x with vl = 0 writes element 0",
    "vslideup_offset_trunc": "vslideup truncates OFFSET to SEW bits",
    "vslidedown_past_vlmax_keep": "vslidedown reads source elements past VLMAX as their register contents, not 0",
    "vslide_vl0_tail": "slides with vl = 0 overwrite the tail with ones under ta",
    "vslide1down_reads_vl": "vslide1down copies vs2[vl] into vd[vl-1] instead of x[rs1]",
    "vslide1up_zext": "vslide1up zero-extends x[rs1] when XLEN < SEW",
    "vrgather_signed_index": "vrgather treats indices as signed (all ones selects element 0 via wraparound)",
    "vrgather_index_vl": "vrgather returns 0 for indices >= vl",
    "vrgather_vlmax_wrap": "vrgather wraps indices >= VLMAX modulo VLMAX",
    "vrgatherei16_sew_index": "vrgatherei16 reads SEW-wide indices",
    "vcompress_tail_ones": "vcompress fills the unused elements below vl with zeros",
    "vcompress_vstart_ok": "vcompress executes with vstart != 0",
    "vmvnr_vl": "vmv<nr>r.v copies only vl elements",
    "vmvnr_count": "vmv2r.v copies a single register",
    "vfmvfs_no_box": "vfmv.f.s with SEW=32 leaves the upper f-register bits zero",
    "vfmvsf_unboxed_used": "vfmv.s.f uses the low bits of a non-NaN-boxed f register",
}


def out() -> str:
    """The directory a test is written to: V, or the mutant directory."""
    return "V" if SUITE == "Vinsn" else SUITE


def new(
    rule: str, plan: str, *, context: str = "", issues: str = "", required: list | None = None, **kw: object
) -> VTest:
    t = VTest(out(), rule, required=required or REQ, **kw)  # type: ignore[arg-type]
    line, text = RULES[rule]
    t.describe(rule_text=text, source=f"{SRC}:{line}", context=context, issues=issues, plan=plan)
    return t


VD, VS2, VS1 = "v8", "v16", "v24"


def emul_s(lmul: str, eew: int, sew: int) -> str:
    e = lmul_val(lmul) * eew / sew
    return str(int(e)) if e >= 1 else f"f{int(1 / e)}"


def auto_lmul(n: int, sew: int) -> str:
    """The smallest LMUL >= 1 whose groups hold n elements of SEW at VLEN = 128."""
    k = 1
    while n * sew > 128 * k:
        k *= 2
    return str(k)


def rnd(t: VTest, eew: int, n: int) -> list[int]:
    return [t.rand(eew) for _ in range(n)]


def arith(
    t: VTest,
    asm: str,
    *,
    sew: int,
    a: Sequence[int],
    b: object = None,
    kind: str = "vv",
    fn: Callable[..., Legal],
    lmul: str | None = None,
    vl: int | None = None,
    mask: Sequence[int] | None = None,
    ta: bool = False,
    ma: bool = False,
    old: Sequence[int] | None = None,
    deew: int | None = None,
    aeew: int | None = None,
    beew: int | None = None,
    vxrm: int | None = None,
    frm: int | None = None,
    sat: object = None,
    flags: object = None,
    desc: str = "",
    vstart: int = 0,
) -> str:
    """One vector-vector/scalar/immediate instruction: vs2 = a (eew aeew), vs1 = b (vv) or x6/f1/imm = b, vd old values
    old (eew deew). fn(a_i, b_i, old_i) gives an active element's legal value(s). Returns the label."""
    n = len(a)
    lmul = lmul or auto_lmul(n, sew)
    aeew, deew, beew = aeew or sew, deew or sew, beew or sew
    old = old if old is not None else rnd(t, deew, n)
    srcs: dict = {VD: (deew, emul_s(lmul, deew, sew), old)}
    srcs[VS2] = (aeew, emul_s(lmul, aeew, sew), a)
    xs: dict = {}
    fs: dict = {}
    if kind == "vv":
        srcs[VS1] = (beew, emul_s(lmul, beew, sew), b)
        bs = list(b)  # type: ignore[arg-type]
    elif kind == "vx":
        xs["x6"] = (
            b if isinstance(b, X) else X(sx(m(cast(int, b), sew), min(sew, 32)), sx(m(cast(int, b), sew), min(sew, 64)))
        )
        bs = [b] * n
    elif kind == "vf":
        fs["f1"] = (b, sew if not isinstance(b, tuple) else b[1])
        if isinstance(b, tuple):
            fs["f1"] = b
        bs = [b] * n
    else:
        bs = [b] * n
    new = [fn(a[i], bs[i], old[i]) for i in range(n)]
    legal = pol(old, new, vl if vl is not None else n, deew, mask=mask, vstart=vstart, ta=ta, ma=ma)
    lab = t.op(
        asm.format(vd=VD, vs2=VS2, vs1=VS1, rs1="x6", fs1="f1", vm=", v0.t" if mask else ""),
        sew=sew,
        lmul=lmul,
        vl=vl if vl is not None else n,
        ta=ta,
        ma=ma,
        srcs=srcs,
        mask=mask,
        xs=xs,
        fs=fs,
        vstart=vstart,
        vxrm=vxrm,
        frm=frm,
        clear_flags=sat is not None or flags is not None,
    )
    if sat is not None:
        t.check_vxsat(sat, lab, desc)  # type: ignore[arg-type]
    if flags is not None:
        t.check_fflags(flags, lab, desc)  # type: ignore[arg-type]
    t.check_vreg(VD, deew, legal, lab, desc, emul_s(lmul, deew, sew))
    return lab


def mres(
    t: VTest,
    asm: str,
    *,
    sew: int,
    a: Sequence[int],
    b: object = None,
    kind: str = "vv",
    fn: Callable[[int, Any], int],
    lmul: str | None = None,
    vl: int | None = None,
    mask: Sequence[int] | None = None,
    ma: bool = False,
    ta: bool = False,
    old: Sequence[int] | None = None,
    vd: str = VD,
    desc: str = "",
    frm: int | None = None,
    flags: object = None,
    aeew: int | None = None,
    bmask: bool = False,
) -> str:
    """An instruction with a mask destination (compares, vmadc/vmsbc). fn(a_i, b_i) -> bit (b_i also gets the carry-in
    bit as (b_i, v0_i) for .vvm/.vxm/.vim forms when bmask). Tail bits: old, 1, or fn of the tail element."""
    n = len(a)
    lmul = lmul or auto_lmul(n, sew)
    aeew = aeew or sew
    old = list(old) if old is not None else [t.rand(1) for _ in range(n)]
    srcs: dict = {}
    if vd != "v0":
        srcs[vd] = (1, "1", old)
    srcs[VS2] = (aeew, emul_s(lmul, aeew, sew), a)
    xs: dict = {}
    fs: dict = {}
    if kind == "vv":
        srcs[VS1] = (sew, emul_s(lmul, sew, sew), b)
        bs = list(b)  # type: ignore[arg-type]
    elif kind == "vx":
        xs["x6"] = (
            b if isinstance(b, X) else X(sx(m(cast(int, b), sew), min(sew, 32)), sx(m(cast(int, b), sew), min(sew, 64)))
        )
        bs = [b] * n
    elif kind == "vf":
        fs["f1"] = (b, sew)
        bs = [b] * n
    else:
        bs = [b] * n
    if vd == "v0":
        assert mask is not None
        old = list(mask)
    if bmask:
        assert mask is not None
        calc = [fn(a[i], (bs[i], mask[i])) for i in range(n)]
        vlv = vl if vl is not None else n
        new = [calc[i] for i in range(n)]
        legal = mpol(old, new, vlv, tailcalc=calc)
    else:
        calc = [fn(a[i], bs[i]) for i in range(n)]
        vlv = vl if vl is not None else n
        legal = mpol(old, calc, vlv, mask=mask, ma=ma, tailcalc=calc)
    vm = ", v0" if bmask else (", v0.t" if mask is not None else "")
    lab = t.op(
        asm.format(vd=vd, vs2=VS2, vs1=VS1, rs1="x6", fs1="f1", vm=vm),
        sew=sew,
        lmul=lmul,
        vl=vlv,
        ta=ta,
        ma=ma,
        srcs=srcs,
        mask=mask,
        xs=xs,
        fs=fs,
        frm=frm,
        clear_flags=flags is not None,
    )
    if flags is not None:
        t.check_fflags(flags, lab, desc)  # type: ignore[arg-type]
    t.check_mask(vd, legal, lab, desc)
    return lab


def ims(v: int, sew: int) -> int:
    """A 5-bit immediate, sign-extended to SEW."""
    return m(sx(v, 5), sew)


def s(v: int, n: int) -> int:
    return sx(m(v, n), n)


def tdiv(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


EDGE8 = [0x00, 0x01, 0x7F, 0x80, 0xFF, 0xFE, 0x55, 0xAA]


# ==================================================================== integer arithmetic
def g_int() -> list[VTest]:
    out_: list[VTest] = []

    # ---- vadd_vsub_op
    t = new(
        "vadd_vsub_op",
        "vadd.vv/.vx/.vi and vsub.vv/.vx at SEW 8, 16, 32, 64 with operands that wrap around "
        "(MAX+1, MIN-1, -1+1); .vi sign-extends its 5-bit immediate (-16 and 15). One masked case (mask-undisturbed) "
        "with vl below the loaded elements (tail undisturbed): inactive and tail elements keep their old values.",
    )
    for sew in (8, 16, 32, 64):
        mx, mn = (1 << (sew - 1)) - 1, 1 << (sew - 1)
        a = [mx, ones(sew), mn, 5]
        bb = [1, 1, ones(sew), 7]
        arith(
            t,
            "vadd.vv {vd}, {vs2}, {vs1}{vm}",
            sew=sew,
            a=a,
            b=bb,
            fn=lambda x, y, o, w=sew: m(x + y, w),
            desc=f"vadd.vv e{sew}",
        )
        arith(
            t,
            "vsub.vv {vd}, {vs2}, {vs1}{vm}",
            sew=sew,
            a=a,
            b=bb,
            fn=lambda x, y, o, w=sew: m(x - y, w),
            desc=f"vsub.vv e{sew}",
        )
    for sew in (8, 32):
        a = [0x7F, 0x01, 0x80, 0x10] if sew == 8 else [0x7FFFFFFF, 1, 0x80000000, 0x10]
        arith(
            t,
            "vadd.vi {vd}, {vs2}, -16{vm}",
            sew=sew,
            a=a,
            kind="vi",
            b=-16,
            fn=lambda x, y, o, w=sew: m(x + ims(-16, w), w),
            desc=f"vadd.vi -16 e{sew}",
        )
        arith(
            t,
            "vadd.vi {vd}, {vs2}, 15{vm}",
            sew=sew,
            a=a,
            kind="vi",
            b=15,
            fn=lambda x, y, o, w=sew: m(x + 15, w),
            desc=f"vadd.vi 15 e{sew}",
        )
    for sew in (16, 32):
        a = [0, 1, 1 << (sew - 1), ones(sew)]
        arith(
            t,
            "vadd.vx {vd}, {vs2}, {rs1}{vm}",
            sew=sew,
            a=a,
            kind="vx",
            b=ones(sew),
            fn=lambda x, y, o, w=sew: m(x + y, w),
            desc=f"vadd.vx -1 e{sew}",
        )
        arith(
            t,
            "vsub.vx {vd}, {vs2}, {rs1}{vm}",
            sew=sew,
            a=a,
            kind="vx",
            b=1,
            fn=lambda x, y, o, w=sew: m(x - y, w),
            desc=f"vsub.vx 1 e{sew}",
        )
    a = [3, 0xFF, 0x80, 0x7F, 9, 9]
    arith(
        t,
        "vadd.vv {vd}, {vs2}, {vs1}{vm}",
        sew=8,
        a=a,
        b=[1] * 6,
        mask=[1, 0, 1, 0, 1, 1],
        vl=4,
        fn=lambda x, y, o: m(x + y, 8),
        desc="vadd.vv e8 masked, vl=4 of 6 (mu, tu)",
    )
    out_.append(t)

    # ---- vrsub_op
    t = new(
        "vrsub_op",
        "vrsub.vx computes x[rs1] - vs2[i] and vrsub.vi computes imm - vs2[i] (the operand order "
        "differs from vsub). Cases at SEW 8, 32 and 64 with a wrap-around result, the vneg idiom (rs1 = x0) and a "
        "negative immediate.",
    )

    def rsub(x: int, y: int, w: int) -> int:
        return m(x - y, w) if MUT == "vrsub_order" else m(y - x, w)

    arith(
        t,
        "vrsub.vx {vd}, {vs2}, {rs1}{vm}",
        sew=32,
        a=[1, 0x80000000, 7, 0xFFFFFFFF],
        kind="vx",
        b=5,
        fn=lambda x, y, o: rsub(x, y, 32),
        desc="vrsub.vx e32 (5 - vs2)",
    )
    arith(
        t,
        "vrsub.vi {vd}, {vs2}, 3{vm}",
        sew=8,
        a=[1, 0x80, 0x7F, 0xFF, 3, 0x10],
        kind="vi",
        b=3,
        fn=lambda x, y, o: rsub(x, 3, 8),
        desc="vrsub.vi e8 (3 - vs2)",
    )
    arith(
        t,
        "vrsub.vi {vd}, {vs2}, -16{vm}",
        sew=16,
        a=[1, 0x8000, 0x7FFF, 0xFFF0],
        kind="vi",
        b=-16,
        fn=lambda x, y, o: rsub(x, ims(-16, 16), 16),
        desc="vrsub.vi e16 (-16 - vs2)",
    )
    arith(
        t,
        "vrsub.vx {vd}, {vs2}, x0{vm}",
        sew=64,
        a=[1, 1 << 63, (1 << 63) - 1, 0],
        kind="vi",
        b=0,
        fn=lambda x, y, o: rsub(x, 0, 64),
        desc="vneg.v e64 (vrsub.vx with x0)",
    )
    out_.append(t)

    # ---- vwaddu_vwadd_vwsubu_vwsub_op
    t = new(
        "vwaddu_vwadd_vwsubu_vwsub_op",
        "Widening add/subtract: the unsigned forms zero-extend and the signed forms sign-extend the SEW-wide "
        "operands before the 2*SEW-wide sum. .vv/.vx (both narrow) and .wv/.wx (vs2 already 2*SEW wide) at SEW 8, "
        "16 and 32, with operands whose top bit is set so zero- and sign-extension give different sums.",
    )

    def wext(v: int, w: int, signed: bool) -> int:
        return s(v, w) if signed else m(v, w)

    for sew in (8, 16, 32):
        hi = 1 << (sew - 1)
        a = [ones(sew), hi, hi - 1, 1]
        bb = [ones(sew), ones(sew), 1, hi]
        for mn, sg, op in (("vwaddu", False, 1), ("vwadd", True, 1), ("vwsubu", False, -1), ("vwsub", True, -1)):
            sgn = sg if not (MUT == "vwadd_zext" and mn == "vwadd") else False
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                deew=2 * sew,
                fn=lambda x, y, o, w=sew, g=sgn, p=op: m(wext(x, w, g) + p * wext(y, w, g), 2 * w),
                desc=f"{mn}.vv e{sew}",
            )
        wa = [ones(2 * sew), 1 << (2 * sew - 1), 5, 0]
        for mn, sg, op in (("vwaddu", False, 1), ("vwadd", True, 1), ("vwsubu", False, -1), ("vwsub", True, -1)):
            sgn = sg if not (MUT == "vwadd_zext" and mn == "vwadd") else False
            arith(
                t,
                mn + ".wv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=wa,
                b=bb,
                deew=2 * sew,
                aeew=2 * sew,
                fn=lambda x, y, o, w=sew, g=sgn, p=op: m(x + p * wext(y, w, g), 2 * w),
                desc=f"{mn}.wv e{sew}",
            )
    for mn, sg, op in (("vwaddu", False, 1), ("vwadd", True, 1), ("vwsubu", False, -1), ("vwsub", True, -1)):
        sgn = sg if not (MUT == "vwadd_zext" and mn == "vwadd") else False
        arith(
            t,
            mn + ".vx {vd}, {vs2}, {rs1}{vm}",
            sew=16,
            a=[0x8000, 1, 0xFFFF, 0x7FFF],
            kind="vx",
            b=0xFFFF,
            deew=32,
            fn=lambda x, y, o, g=sgn, p=op: m(wext(x, 16, g) + p * wext(y, 16, g), 32),
            desc=f"{mn}.vx e16, x = 0xffff",
        )
        arith(
            t,
            mn + ".wx {vd}, {vs2}, {rs1}{vm}",
            sew=8,
            a=[0x0100, 0xFFFF, 0x8000, 3],
            kind="vx",
            b=0x80,
            deew=16,
            aeew=16,
            fn=lambda x, y, o, g=sgn, p=op: m(x + p * wext(y, 8, g), 16),
            desc=f"{mn}.wx e8, x = 0x80",
        )
    out_.append(t)

    # ---- vsext/vzext
    t = new(
        "vsext_vzext_op",
        "vzext.vf2/vf4/vf8 zero-extend and vsext.vf2/vf4/vf8 sign-extend a source of EEW "
        "SEW/2, SEW/4, SEW/8 into SEW-wide elements. Sources 0x80.., 0x7f.., all ones, 0 and 1 at every legal "
        "SEW, so a missing or wrong extension changes the upper bits.",
    )
    for f_ in (2, 4, 8):
        for sew in (16, 32, 64):
            se = sew // f_
            if se < 8:
                continue
            a = [1 << (se - 1), (1 << (se - 1)) - 1, ones(se), 0, 1]
            for mn, sg in (("vzext", False), ("vsext", True)):
                g = sg and MUT != "vsext_as_zext"
                arith(
                    t,
                    f"{mn}.vf{f_} {{vd}}, {{vs2}}{{vm}}",
                    sew=sew,
                    a=a,
                    aeew=se,
                    kind="none",
                    fn=lambda x, y, o, e=se, w=sew, gg=g: m(s(x, e) if gg else x, w),
                    desc=f"{mn}.vf{f_} e{sew}",
                )
    out_.append(t)

    t = new(
        "vsext_vzext_vs_eew_emul",
        "The source of vzext/vsext.vfN has EEW = SEW/N and EMUL = LMUL/N, so its register number need only be "
        "aligned to EMUL: vsext.vf8 at e64/m8 and vzext.vf4 at e32/m4 read the single register v17 (EMUL 1), "
        "vsext.vf2 at e32/m4 reads the pair v18-v19 (EMUL 2, not 4-aligned), vzext.vf2 at e16/m2 reads v17. "
        "Each runs with vl = the 128-bit-VLEN VLMAX in a window that must not trap, and every destination "
        "element is checked (so a source read from the wrong registers is seen). Fractional source EMUL: "
        "vzext.vf4 at e32/m1 reads an EMUL=1/4 source.",
    )
    for f_, sew, lm, vs, sg in (
        (8, 64, "8", "v17", True),
        (4, 32, "4", "v17", False),
        (2, 32, "4", "v18", True),
        (2, 16, "2", "v17", False),
    ):
        se = sew // f_
        n = int(128 * int(lm) // sew)
        a = [t.rand(se) for _ in range(n)]
        old = rnd(t, sew, n)
        t.vload(VD, sew, old, lm)
        t.vload(vs, se, a, emul_s(lm, se, sew))
        t.vset(n, sew, lm)
        mn = "vsext" if sg else "vzext"
        lab = t.ill_window(
            [f"{mn}.vf{f_} {VD}, {vs}"],
            2 if MUT == "ext_src_emul_lmul" else "ok",
            f"{mn}.vf{f_} e{sew} m{lm} from {vs}",
        )
        t.check_vreg(
            VD, sew, [m(s(x, se), sew) if sg else x for x in a], lab, f"{mn}.vf{f_} e{sew} m{lm} from {vs}", lm
        )
    a = [0x81, 0x7F, 0xFF, 0x01]
    arith(
        t,
        "vzext.vf4 {vd}, {vs2}{vm}",
        sew=32,
        a=a,
        aeew=8,
        kind="none",
        fn=lambda x, y, o: x,
        desc="vzext.vf4 e32 m1 (source EMUL 1/4)",
    )
    out_.append(t)

    t = new(
        "vsext_vzext_vd_eew_emul",
        "The destination of vzext/vsext has EEW = SEW and EMUL = LMUL. vzext.vf2 at e32/m2 with vl = VLMAX "
        "writes the whole group v8-v9: the source v16 is set to its element indices (vid.v at e16), so vd[i] = i; "
        "the test checks v9[0] = VLEN/32 (computed from vlenb) and that v10, just past the group, is unchanged. "
        "Also vsext.vf2 at e16/m4 with vl = 32 at VLEN 128 over 4 destination registers.",
    )
    t.emit("csrr x7, vlenb")
    t.vset("max", 16, "1")
    t.emit(f"vid.v {VS2}")
    t.vload("v10", 32, [0x5A5A5A5A] * 4)
    t.vset("max", 32, "2")
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vzext.vf2 {VD}, {VS2}")
    t.vset(1, 32, "1")
    t.emit("vmv.x.s x8, v9")
    t.emit("srli x7, x7, 2")
    t.emit("sub x8, x8, x7")
    t.emit("seqz x8, x8")
    t.check_bool("x8", lab, "vzext.vf2 e32 m2 vl=VLMAX: v9[0] == VLEN/32 (destination group v8-v9)")
    t.check_vreg("v10", 32, [0x5A5A5A5A] * 4, lab, "v10 (past the destination group) unchanged")
    a = [t.rand(8) for _ in range(32)]
    old = rnd(t, 16, 32)
    lab = t.op(f"vsext.vf2 {VD}, {VS2}", sew=16, lmul="4", vl=32, srcs={VD: (16, "4", old), VS2: (8, "2", a)})
    t.check_vreg(VD, 16, [m(s(x, 8), 16) for x in a], lab, "vsext.vf2 e16 m4 vl=32", "4")
    out_.append(t)

    # ---- add with carry
    t = new(
        "vmadc_vmsbc_vadc_vsbc_carry_v0",
        "The carry-in comes from v0 in the mask layout (element i is bit i of v0) and vmadc/vmsbc write the carry "
        "out in the mask layout. 16 elements at e8 with a v0 pattern that differs per element: vadc.vvm adds "
        "v0[i], vsbc.vvm subtracts it, vmadc.vvm/vmsbc.vvm write the carry/borrow of element i to bit i.",
    )
    v0 = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1]
    a = [0xFF, 0xFF, 0x00, 0x7F, 0x80, 0x01, 0xFE, 0x10, 0xFF, 0x00, 0x01, 0xFF, 0x00, 0x80, 0x7F, 0xFF]
    bb = [0x00, 0x01, 0x00, 0x80, 0x80, 0xFE, 0x01, 0x20, 0xFF, 0x00, 0x02, 0x00, 0x01, 0x7F, 0x80, 0xFF]
    for mn, f in (("vadc", lambda x, y, c: m(x + y + c, 8)), ("vsbc", lambda x, y, c: m(x - y - c, 8))):
        old = rnd(t, 8, 16)
        lab = t.op(
            f"{mn}.vvm {VD}, {VS2}, {VS1}, v0",
            sew=8,
            vl=16,
            mask=v0,
            srcs={VD: (8, "1", old), VS2: (8, "1", a), VS1: (8, "1", bb)},
        )
        t.check_vreg(VD, 8, [f(a[i], bb[i], v0[i]) for i in range(16)], lab, f"{mn}.vvm e8, carry-in v0[i]")
    for mn, f in (("vmadc", lambda x, y, c: int(x + y + c > 0xFF)), ("vmsbc", lambda x, y, c: int(x - y - c < 0))):
        old = [t.rand(1) for _ in range(16)]
        lab = t.op(
            f"{mn}.vvm {VD}, {VS2}, {VS1}, v0",
            sew=8,
            vl=16,
            mask=v0,
            srcs={VD: (1, "1", old), VS2: (8, "1", a), VS1: (8, "1", bb)},
        )
        t.check_mask(VD, [f(a[i], bb[i], v0[i]) for i in range(16)], lab, f"{mn}.vvm e8, carry out to bit i")
    out_.append(t)

    t = new(
        "vadc_vsbc_op",
        "vadc computes vs2 + op + v0[i] and vsbc computes vs2 - op - v0[i] (op = vs1, x[rs1] or "
        "the sign-extended immediate), wrapping around. All forms (.vvm, .vxm, .vim, and vsbc .vvm/.vxm) at SEW 8, "
        "32 and 64 with carry-ins 0 and 1 and wrap-around sums.",
    )
    for sew in (8, 32, 64):
        mx = ones(sew)
        a = [mx, mx, 0, 0, 1 << (sew - 1), 5]
        bb = [0, 1, 0, 1, 1 << (sew - 1), 2]
        v0 = [1, 0, 1, 1, 1, 0]
        for mn, sg in (("vadc", 1), ("vsbc", -1)):
            old = rnd(t, sew, 6)
            lab = t.op(
                f"{mn}.vvm {VD}, {VS2}, {VS1}, v0",
                sew=sew,
                vl=6,
                mask=v0,
                srcs={VD: (sew, "1", old), VS2: (sew, "1", a), VS1: (sew, "1", bb)},
            )
            t.check_vreg(VD, sew, [m(a[i] + sg * (bb[i] + v0[i]), sew) for i in range(6)], lab, f"{mn}.vvm e{sew}")
            if sew != 64:
                old = rnd(t, sew, 6)
                lab = t.op(
                    f"{mn}.vxm {VD}, {VS2}, x6, v0",
                    sew=sew,
                    vl=6,
                    mask=v0,
                    xs={"x6": X(-1, -1)},
                    srcs={VD: (sew, "1", old), VS2: (sew, "1", a)},
                )
                t.check_vreg(
                    VD, sew, [m(a[i] + sg * (mx + v0[i]), sew) for i in range(6)], lab, f"{mn}.vxm e{sew}, x = -1"
                )
        old = rnd(t, sew, 6)
        lab = t.op(
            f"vadc.vim {VD}, {VS2}, -1, v0", sew=sew, vl=6, mask=v0, srcs={VD: (sew, "1", old), VS2: (sew, "1", a)}
        )
        t.check_vreg(VD, sew, [m(a[i] + mx + v0[i], sew) for i in range(6)], lab, f"vadc.vim -1 e{sew}")
    out_.append(t)

    t = new(
        "vadc_vsbc_masked_write_all_elem",
        "vadc/vsbc are encoded with vm=0 but write every body element: elements whose v0 bit is 0 get vs2 + vs1 "
        "(no carry), not their old value or ones, even with vtype.vma = 1. Tail elements (vl = 5 of 8, tu) are "
        "undisturbed.",
    )
    for ma in (False, True):
        for mn, sg in (("vadc", 1), ("vsbc", -1)):
            a = rnd(t, 16, 8)
            bb = rnd(t, 16, 8)
            v0 = [0, 0, 1, 0, 0, 1, 0, 0]
            old = rnd(t, 16, 8)
            lab = t.op(
                f"{mn}.vvm {VD}, {VS2}, {VS1}, v0",
                sew=16,
                vl=5,
                ma=ma,
                mask=v0,
                srcs={VD: (16, "1", old), VS2: (16, "1", a), VS1: (16, "1", bb)},
            )
            exp = [m(a[i] + sg * (bb[i] + v0[i]), 16) if i < 5 else old[i] for i in range(8)]
            if MUT == "vadc_masked_off_kept":
                exp = [old[i] if i < 5 and not v0[i] else exp[i] for i in range(8)]
            t.check_vreg(VD, 16, exp, lab, f"{mn}.vvm e16 vl=5 {'ma' if ma else 'mu'}: v0=0 elements written")
    out_.append(t)

    t = new(
        "vmadc_vmsbc_op_masked",
        "Masked (vm=0) vmadc/vmsbc include the carry-in/borrow-in v0[i] in the carry/borrow out: 0xff + 0 + 1 "
        "carries, 0 - 0 - 1 borrows, and the same operands with v0[i] = 0 do not. .vvm, .vxm and .vim at SEW 8 "
        "and 64.",
    )
    for sew in (8, 64):
        mx = ones(sew)
        a = [mx, mx, 0, 0, mx, 1, 1 << (sew - 1), 1 << (sew - 1)]
        bb = [0, 0, 0, 0, mx, 1, 1 << (sew - 1), (1 << (sew - 1)) - 1]
        v0 = [1, 0, 1, 0, 1, 1, 0, 1]
        mres(
            t,
            "vmadc.vvm {vd}, {vs2}, {vs1}{vm}",
            sew=sew,
            a=a,
            b=bb,
            bmask=True,
            mask=v0,
            fn=lambda x, yc, w=sew: int(x + yc[0] + yc[1] > ones(w)),
            desc=f"vmadc.vvm e{sew}",
        )
        mres(
            t,
            "vmsbc.vvm {vd}, {vs2}, {vs1}{vm}",
            sew=sew,
            a=a,
            b=bb,
            bmask=True,
            mask=v0,
            fn=lambda x, yc: int(x - yc[0] - yc[1] < 0),
            desc=f"vmsbc.vvm e{sew}",
        )
    for sew in (8, 32):
        mx = ones(sew)
        a = [mx, mx - 1, 0, 1, mx, 0]
        v0 = [1, 1, 0, 1, 0, 1]
        mres(
            t,
            "vmadc.vxm {vd}, {vs2}, {rs1}{vm}",
            sew=sew,
            a=a,
            kind="vx",
            b=1,
            bmask=True,
            mask=v0,
            fn=lambda x, yc, w=sew: int(x + 1 + yc[1] > ones(w)),
            desc=f"vmadc.vxm e{sew}, x=1",
        )
        mres(
            t,
            "vmsbc.vxm {vd}, {vs2}, {rs1}{vm}",
            sew=sew,
            a=a,
            kind="vx",
            b=1,
            bmask=True,
            mask=v0,
            fn=lambda x, yc: int(x - 1 - yc[1] < 0),
            desc=f"vmsbc.vxm e{sew}, x=1",
        )
        mres(
            t,
            "vmadc.vim {vd}, {vs2}, -1{vm}",
            sew=sew,
            a=a,
            kind="vi",
            b=-1,
            bmask=True,
            mask=v0,
            fn=lambda x, yc, w=sew: int(x + ones(w) + yc[1] > ones(w)),
            desc=f"vmadc.vim -1 e{sew}",
        )
    out_.append(t)

    t = new(
        "vmadc_vmsbc_op_unmasked",
        "Unmasked (vm=1) vmadc/vmsbc have no carry-in: 0xff + 0 does not carry and 0 - 0 does not borrow even "
        "though v0 is all ones. .vv, .vx, .vi at SEW 8 and 32.",
    )
    for sew in (8, 32):
        mx = ones(sew)
        a = [mx, mx, 0, 0, 1, mx - 1]
        bb = [0, 1, 0, 1, 1, 1]
        cin = 1 if MUT == "vmadc_unmasked_cin" else 0
        t.mload("v0", [1] * 16)
        mres(
            t,
            "vmadc.vv {vd}, {vs2}, {vs1}",
            sew=sew,
            a=a,
            b=bb,
            fn=lambda x, y, w=sew, c=cin: int(x + y + c > ones(w)),
            desc=f"vmadc.vv e{sew} (v0 all ones)",
        )
        t.mload("v0", [1] * 16)
        mres(
            t,
            "vmsbc.vv {vd}, {vs2}, {vs1}",
            sew=sew,
            a=a,
            b=bb,
            fn=lambda x, y, c=cin: int(x - y - c < 0),
            desc=f"vmsbc.vv e{sew} (v0 all ones)",
        )
        t.mload("v0", [1] * 16)
        mres(
            t,
            "vmadc.vx {vd}, {vs2}, {rs1}",
            sew=sew,
            a=a,
            kind="vx",
            b=0,
            fn=lambda x, y, w=sew, c=cin: int(x + c > ones(w)),
            desc=f"vmadc.vx e{sew}, x=0",
        )
        t.mload("v0", [1] * 16)
        mres(
            t,
            "vmsbc.vx {vd}, {vs2}, {rs1}",
            sew=sew,
            a=a,
            kind="vx",
            b=0,
            fn=lambda x, y, c=cin: int(x - c < 0),
            desc=f"vmsbc.vx e{sew}, x=0",
        )
        t.mload("v0", [1] * 16)
        mres(
            t,
            "vmadc.vi {vd}, {vs2}, 1",
            sew=sew,
            a=a,
            kind="vi",
            b=1,
            fn=lambda x, y, w=sew, c=cin: int(x + 1 + c > ones(w)),
            desc=f"vmadc.vi 1 e{sew}",
        )
    out_.append(t)

    t = new(
        "vmadc_vmsbc_masked_write_all_elem",
        "Masked vmadc/vmsbc write every body element: an element whose v0 bit is 0 gets the carry/borrow "
        "computed with carry-in 0, not its old bit, also with vtype.vma = 1. The old destination bits are the "
        "complement of the expected ones.",
    )
    for ma in (False, True):
        a = [0xFF, 0x00, 0xFF, 0x00, 0x80, 0x7F, 0x01, 0xFE]
        bb = [0x01, 0x01, 0x00, 0x00, 0x80, 0x80, 0xFF, 0x01]
        v0 = [0] * 8
        exp_c = [int(a[i] + bb[i] > 0xFF) for i in range(8)]
        exp_b = [int(a[i] - bb[i] < 0) for i in range(8)]
        for mn, ex in (("vmadc", exp_c), ("vmsbc", exp_b)):
            old = [1 - e for e in ex]
            lab = t.op(
                f"{mn}.vvm {VD}, {VS2}, {VS1}, v0",
                sew=8,
                vl=8,
                ma=ma,
                mask=v0,
                srcs={VD: (1, "1", old), VS2: (8, "1", a), VS1: (8, "1", bb)},
            )
            t.check_mask(VD, ex, lab, f"{mn}.vvm e8 with v0 = 0 ({'ma' if ma else 'mu'})")
    out_.append(t)

    t = new(
        "vmadc_vmsbc_tail_agnostic",
        "vmadc/vmsbc always use a tail-agnostic policy: a tail bit may keep its old value, become 1, or take the "
        "value computed for its element, even with vtype.vta = 0. The test sets every old tail bit to 1 and "
        "chooses tail operands whose carry/borrow is 1, so the only illegal outcome is a tail bit cleared to 0 "
        "(e.g. an implementation that zeroes the mask tail). vl = 3 of 16 elements, vta = 0 and 1.",
    )
    for ta in (False, True):
        a = [0xFF] * 16
        bb = [0x01] * 16
        old = [0, 1, 0] + [1] * 13
        exp = [1, 1, 1] + ([0] * 13 if MUT == "mask_tail_zero" else [1] * 13)
        lab = t.op(
            f"vmadc.vv {VD}, {VS2}, {VS1}",
            sew=8,
            vl=3,
            ta=ta,
            srcs={VD: (1, "1", old), VS2: (8, "1", a), VS1: (8, "1", bb)},
        )
        t.check_mask(VD, exp, lab, f"vmadc.vv vl=3 {'ta' if ta else 'tu'}: tail bits stay 1")
        a = [0x00] * 16
        lab = t.op(
            f"vmsbc.vx {VD}, {VS2}, x6", sew=8, vl=3, ta=ta, xs={"x6": 1}, srcs={VD: (1, "1", old), VS2: (8, "1", a)}
        )
        t.check_mask(VD, exp, lab, f"vmsbc.vx vl=3 {'ta' if ta else 'tu'}: tail bits stay 1")
    out_.append(t)

    t = new(
        "vmsbc_borrow_neg",
        "vmsbc's borrow is 1 iff the infinitely precise difference vs2 - vs1 (- borrow-in) is negative, with the "
        "operands taken as unsigned: 0x80 - 0x7f does not borrow although the signed difference overflows, "
        "0 - 0xff borrows, equal operands do not, and 5 - 5 - 1 borrows. SEW 8, 16 and 64.",
    )
    for sew in (8, 16, 64):
        hi = 1 << (sew - 1)
        a = [hi, 0, 5, 5, hi - 1, ones(sew), 0, 1]
        bb = [hi - 1, ones(sew), 5, 6, hi, ones(sew), 0, 0]

        def bor(x: int, y: int, c: int = 0, w: int = sew) -> int:
            if MUT == "vmsbc_unsigned_wrong":
                return int(s(x, w) - s(y, w) - c < 0)
            return int(x - y - c < 0)

        mres(
            t,
            "vmsbc.vv {vd}, {vs2}, {vs1}",
            sew=sew,
            a=a,
            b=bb,
            fn=lambda x, y, f=bor: f(x, y),
            desc=f"vmsbc.vv e{sew}",
        )
        mres(
            t,
            "vmsbc.vvm {vd}, {vs2}, {vs1}{vm}",
            sew=sew,
            a=a,
            b=bb,
            bmask=True,
            mask=[0, 0, 1, 0, 1, 1, 1, 0],
            fn=lambda x, yc, f=bor: f(x, yc[0], yc[1]),
            desc=f"vmsbc.vvm e{sew}",
        )
    out_.append(t)

    # ---- logical
    t = new(
        "vand_vor_vxor_op",
        "vand/vor/vxor in .vv, .vx and .vi forms; the 5-bit immediate is sign-extended to SEW (0x10 -> all ones "
        "above bit 3), and vxor.vi -1 is vnot. SEW 8, 32, 64 with the 0x55../0xaa.. patterns.",
    )
    for sew in (8, 32, 64):
        p5, pa = int("5" * (sew // 4), 16), int("A" * (sew // 4), 16)
        a = [p5, pa, ones(sew), 0x0F]
        bb = [pa, pa, 0x12, p5]
        for mn, f in (("vand", lambda x, y: x & y), ("vor", lambda x, y: x | y), ("vxor", lambda x, y: x ^ y)):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                fn=lambda x, y, o, g=f: g(x, y),
                desc=f"{mn}.vv e{sew}",
            )
            arith(
                t,
                mn + ".vi {vd}, {vs2}, -16{vm}",
                sew=sew,
                a=a,
                kind="vi",
                b=-16,
                fn=lambda x, y, o, g=f, w=sew: g(x, ims(-16, w)),
                desc=f"{mn}.vi -16 e{sew}",
            )
            if sew != 64:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=p5,
                    fn=lambda x, y, o, g=f: g(x, y),
                    desc=f"{mn}.vx e{sew}",
                )
        arith(
            t,
            "vxor.vi {vd}, {vs2}, -1{vm}",
            sew=sew,
            a=a,
            kind="vi",
            b=-1,
            fn=lambda x, y, o, w=sew: x ^ ones(w),
            desc=f"vnot.v e{sew}",
        )
    out_.append(t)

    # ---- shifts
    t = new(
        "vsll_vsrl_vsra_op",
        "vsll shifts left, vsrl shifts right zero-extending and vsra shifts right sign-extending, with the amount "
        "from vs1, x[rs1] or a zero-extended 5-bit immediate (uimm 31 shifts by 31, not -1). Sources with the "
        "top bit set at SEW 8, 32, 64.",
    )
    for sew in (8, 32, 64):
        hi = 1 << (sew - 1)
        a = [hi | 1, ones(sew), 0x5A, hi >> 1]
        sh = [1, sew - 1, 3, 0]
        for mn, f in (
            ("vsll", lambda x, k, w: m(x << k, w)),
            ("vsrl", lambda x, k, w: x >> k),
            ("vsra", lambda x, k, w: m(s(x, w) >> k, w)),
        ):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=sh,
                fn=lambda x, y, o, g=f, w=sew: g(x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            k = min(31, sew - 1)
            arith(
                t,
                mn + f".vi {{vd}}, {{vs2}}, {k}{{vm}}",
                sew=sew,
                a=a,
                kind="vi",
                b=k,
                fn=lambda x, y, o, g=f, w=sew, kk=k: g(x, kk, w),
                desc=f"{mn}.vi {k} e{sew}",
            )
            if sew != 64:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=2,
                    fn=lambda x, y, o, g=f, w=sew: g(x, 2, w),
                    desc=f"{mn}.vx 2 e{sew}",
                )
    out_.append(t)

    t = new(
        "vsll_vsrl_vsra_shamt",
        "Only the low lg2(SEW) bits of the shift amount are used: amounts SEW, SEW+1, 2*SEW-1 and all-ones from "
        "vs1 and x[rs1], and uimm 8/9/31 at SEW 8 and 16 (immediates above lg2(SEW)), for vsll, vsrl and vsra at "
        "every SEW. A design that shifts by the full amount gives 0 (or all sign bits).",
    )

    def shf(mn: str, x: int, k: int, w: int) -> int:
        k = k if MUT == "shamt_unmasked" else k & (w - 1)
        if mn == "vsll":
            return m(x << k, w) if k < w else 0
        if mn == "vsrl":
            return x >> k
        return m(s(x, w) >> min(k, w), w)

    for sew in (8, 16, 32, 64):
        a = [(1 << (sew - 1)) | 0x15, 0x2D, ones(sew) - 2, (1 << (sew - 1)) | 3]
        sh = [sew, sew + 1, 2 * sew - 1, ones(sew)]
        for mn in ("vsll", "vsrl", "vsra"):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=sh,
                fn=lambda x, y, o, g=mn, w=sew: shf(g, x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            if sew <= 32:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=X(sew + 3, sew + 3),
                    fn=lambda x, y, o, g=mn, w=sew: shf(g, x, w + 3, w),
                    desc=f"{mn}.vx {sew + 3} e{sew}",
                )
            else:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=X(65, 65),
                    fn=lambda x, y, o, g=mn, w=sew: shf(g, x, 65, w),
                    desc=f"{mn}.vx 65 e{sew}",
                )
            for k in (8, 9, 31) if sew == 8 else (16, 31) if sew == 16 else ():
                arith(
                    t,
                    mn + f".vi {{vd}}, {{vs2}}, {k}{{vm}}",
                    sew=sew,
                    a=a,
                    kind="vi",
                    b=k,
                    fn=lambda x, y, o, g=mn, w=sew, kk=k: shf(g, x, kk, w),
                    desc=f"{mn}.vi {k} e{sew}",
                )
    out_.append(t)

    t = new(
        "vnsrl_vnsra_op",
        "vnsrl/vnsra take a 2*SEW source and write the SEW-wide field (vs2 >> shamt): vnsrl zero-fills and vnsra "
        "sign-fills from the wide source's top bit. .wv, .wx and .wi (zero-extended uimm) forms at SEW 8, 16 "
        "and 32.",
    )
    for sew in (8, 16, 32):
        W = 2 * sew
        hi = 1 << (W - 1)
        a = [hi | 0x1234 & ones(W), 0xABCD & ones(W), ones(W), hi >> 1]
        sh = [sew, 4, sew - 1, 0]
        for mn, f in (("vnsrl", lambda x, k, w: m(x >> k, w)), ("vnsra", lambda x, k, w: m(s(x, 2 * w) >> k, w))):
            arith(
                t,
                mn + ".wv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                aeew=W,
                b=sh,
                fn=lambda x, y, o, g=f, w=sew: g(x, y, w),
                desc=f"{mn}.wv e{sew}",
            )
            arith(
                t,
                mn + ".wx {vd}, {vs2}, {rs1}{vm}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vx",
                b=X(sew, sew),
                fn=lambda x, y, o, g=f, w=sew: g(x, w, w),
                desc=f"{mn}.wx {sew} e{sew}",
            )
            arith(
                t,
                mn + ".wi {vd}, {vs2}, 31{vm}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vi",
                b=31,
                fn=lambda x, y, o, g=f, w=sew: g(x, 31 & (2 * w - 1), w),
                desc=f"{mn}.wi 31 e{sew}",
            )
    out_.append(t)

    t = new(
        "vnsrl_vnsra_shamt",
        "Narrowing shifts use the low lg2(2*SEW) bits of the shift amount: at SEW 8, amounts 15 (not reduced to "
        "7), 16 -> 0, 17 -> 1; at SEW 32, 63 and 64 -> 0 and 0x7f -> 63; .wi with uimm 15 at SEW 8 and uimm 17 at "
        "SEW 16.",
    )

    def nsh(mn: str, x: int, k: int, w: int) -> int:
        k &= (w - 1) if MUT == "nshamt_sew_bits" else (2 * w - 1)
        return m(x >> k, w) if mn == "vnsrl" else m(s(x, 2 * w) >> k, w)

    for sew, shamts in ((8, [15, 16, 17, 0xFF]), (16, [31, 32, 33, 17]), (32, [63, 64, 0x7F, 33])):
        W = 2 * sew
        a = [(1 << (W - 1)) | 0x5A5A & ones(W), ones(W) >> 1, (1 << (W - 1)) | 1, 0xC3C3C3C3 & ones(W)]
        for mn in ("vnsrl", "vnsra"):
            arith(
                t,
                mn + ".wv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                aeew=W,
                b=[x & ones(sew) for x in shamts],
                fn=lambda x, y, o, g=mn, w=sew: nsh(g, x, y, w),
                desc=f"{mn}.wv e{sew}",
            )
            for k in shamts[:2]:
                arith(
                    t,
                    mn + ".wx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    aeew=W,
                    kind="vx",
                    b=X(k, k),
                    fn=lambda x, y, o, g=mn, w=sew, kk=k: nsh(g, x, kk, w),
                    desc=f"{mn}.wx {k} e{sew}",
                )
        k = {8: 15, 16: 17, 32: 31}[sew]
        for mn in ("vnsrl", "vnsra"):
            arith(
                t,
                mn + f".wi {{vd}}, {{vs2}}, {k}{{vm}}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vi",
                b=k,
                fn=lambda x, y, o, g=mn, w=sew, kk=k: nsh(g, x, kk, w),
                desc=f"{mn}.wi {k} e{sew}",
            )
    out_.append(t)

    # ---- compares
    t = new(
        "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_op",
        "Each compare writes 1 when its relation holds and 0 otherwise into one mask register. Operand pairs "
        "that separate the signed and unsigned orders (0x80.. vs 0x7f..; -1 vs 1) and equal operands, for every "
        "form the ISA provides (.vv, .vx, .vi; vmsgt/vmsgtu only .vx/.vi; vmslt/vmsltu no .vi). The .vi "
        "immediate is sign-extended even for the unsigned compares: vmsleu.vi -1 compares with 2^SEW-1 (always "
        "true) and vmsgtu.vi -16 with 2^SEW-16.",
    )
    rel = {
        "vmseq": lambda x, y, w: x == y,
        "vmsne": lambda x, y, w: x != y,
        "vmsltu": lambda x, y, w: (s(x, w) < s(y, w)) if MUT == "vmsltu_signed" else x < y,
        "vmslt": lambda x, y, w: s(x, w) < s(y, w),
        "vmsleu": lambda x, y, w: x <= y,
        "vmsle": lambda x, y, w: s(x, w) <= s(y, w),
        "vmsgtu": lambda x, y, w: x > y,
        "vmsgt": lambda x, y, w: s(x, w) > s(y, w),
    }
    for sew in (8, 32, 64):
        hi = 1 << (sew - 1)
        a = [hi, hi - 1, ones(sew), 1, 7, 0, hi, ones(sew) - 15]
        bb = [hi - 1, hi, 1, ones(sew), 7, 0, hi, ones(sew) - 15]
        for mn, f in rel.items():
            if mn not in ("vmsgtu", "vmsgt"):
                mres(
                    t,
                    mn + ".vv {vd}, {vs2}, {vs1}",
                    sew=sew,
                    a=a,
                    b=bb,
                    fn=lambda x, y, g=f, w=sew: int(g(x, y, w)),
                    desc=f"{mn}.vv e{sew}",
                )
            if sew != 64:
                mres(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=hi,
                    fn=lambda x, y, g=f, w=sew, h=hi: int(g(x, h, w)),
                    desc=f"{mn}.vx 0x80.. e{sew}",
                )
            if mn not in ("vmsltu", "vmslt"):
                for imm in (-1, -16, 7):
                    iv = ims(imm, sew)
                    if MUT == "vmsleu_vi_zext" and mn == "vmsleu":
                        iv = imm & 0x1F
                    mres(
                        t,
                        mn + f".vi {{vd}}, {{vs2}}, {imm}",
                        sew=sew,
                        a=a,
                        kind="vi",
                        b=imm,
                        fn=lambda x, y, g=f, w=sew, v=iv: int(g(x, v, w)),
                        desc=f"{mn}.vi {imm} e{sew}",
                    )
    out_.append(t)

    t = new(
        "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_vd_v0_legal",
        "A masked compare may write v0, its own mask: vmslt.vv v0, v16, v24, v0.t (and vmseq.vx, vmsgtu.vi) "
        "execute without trapping and write the active elements; inactive elements keep their v0 bit "
        "(mask undisturbed).",
    )
    a = [1, 5, 0x80, 0x7F, 3, 3, 0xFF, 0]
    bb = [2, 4, 0x7F, 0x80, 3, 4, 0, 0xFF]
    v0 = [1, 1, 0, 1, 1, 0, 1, 1]
    mres(
        t,
        "vmslt.vv {vd}, {vs2}, {vs1}{vm}",
        sew=8,
        a=a,
        b=bb,
        mask=v0,
        vd="v0",
        fn=lambda x, y: int(s(x, 8) < s(y, 8)),
        desc="vmslt.vv v0, ..., v0.t",
    )
    mres(
        t,
        "vmseq.vx {vd}, {vs2}, {rs1}{vm}",
        sew=8,
        a=a,
        kind="vx",
        b=3,
        mask=v0,
        vd="v0",
        fn=lambda x, y: int(x == 3),
        desc="vmseq.vx v0, ..., v0.t",
    )
    mres(
        t,
        "vmsgtu.vi {vd}, {vs2}, 4{vm}",
        sew=8,
        a=a,
        kind="vi",
        b=4,
        mask=v0,
        vd="v0",
        fn=lambda x, y: int(x > 4),
        desc="vmsgtu.vi v0, ..., v0.t",
    )
    out_.append(t)

    t = new(
        "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_maskundisturbed",
        "Under mask-undisturbed, a masked compare into v0 ANDs the result into the mask: v0 = v0 & (a < b) "
        "(inactive elements keep 0, active elements take the compare). The example from the spec: "
        "(a < b) && (b < c) in two instructions.",
    )
    a = [1, 2, 3, 4, 5, 6, 7, 8]
    bb = [2, 2, 4, 3, 9, 1, 8, 8]
    c = [3, 1, 5, 9, 9, 7, 9, 2]
    t.vload(VS2, 8, a)
    t.vload(VS1, 8, bb)
    t.vload("v20", 8, c)
    t.vset(8, 8, "1", ma=False)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vmslt.vv v0, {VS2}, {VS1}")
    t.emit(f"vmslt.vv v0, {VS1}, v20, v0.t")
    exp = [int(a[i] < bb[i] and bb[i] < c[i]) for i in range(8)]
    if MUT == "cmp_v0_ignores_mask":
        exp = [int(bb[i] < c[i]) for i in range(8)]
    t.check_mask("v0", exp, lab, "v0 = (a < b) && (b < c), mask undisturbed")
    v0 = [1, 0, 1, 0, 1, 0, 1, 0]
    mres(
        t,
        "vmsne.vv {vd}, {vs2}, {vs1}{vm}",
        sew=8,
        a=a,
        b=bb,
        mask=v0,
        vd="v0",
        fn=lambda x, y: int(x != y),
        desc="vmsne.vv v0, ..., v0.t: inactive elements keep 0",
    )
    out_.append(t)

    t = new(
        "vmseq_vmsne_vmsltu_vmslt_vmsleu_vmsle_vmsgtu_vmsgt_tail_agnostic",
        "Compares write mask registers and always use a tail-agnostic policy: a tail bit may keep its old value, "
        "become 1, or take its element's compare result, even with vtype.vta = 0. With old tail bits 1 and tail "
        "elements that compare true, a tail bit must remain 1; with old tail bit 0 and a false compare, it may be "
        "0 or 1 (not checked). vl = 4 of 16, vta = 0 and 1, vmseq and vmsltu.",
    )
    for ta in (False, True):
        a = [5] * 16
        old = [0, 1, 0, 1] + [1] * 12
        exp = [1, 1, 1, 1] + ([0] * 12 if MUT == "mask_tail_zero" else [1] * 12)
        lab = t.op(
            f"vmseq.vx {VD}, {VS2}, x6", sew=8, vl=4, ta=ta, xs={"x6": 5}, srcs={VD: (1, "1", old), VS2: (8, "1", a)}
        )
        t.check_mask(VD, exp, lab, f"vmseq.vx vl=4 {'ta' if ta else 'tu'}: tail bits stay 1")
        lab = t.op(
            f"vmsleu.vi {VD}, {VS2}, 6", sew=16, vl=4, ta=ta, srcs={VD: (1, "1", old[:8]), VS2: (16, "1", [5] * 8)}
        )
        t.check_mask(VD, exp[:8], lab, f"vmsleu.vi e16 vl=4 {'ta' if ta else 'tu'}: tail bits stay 1")
    out_.append(t)

    t = new(
        "vminu_vmin_vmaxu_vmax_op",
        "vminu/vmaxu compare unsigned and vmin/vmax signed: 0x80.. vs 0x7f.. and -1 vs 1 select different "
        "operands. .vv and .vx forms at SEW 8, 16, 32 and 64 (.vx up to 32).",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        a = [hi, ones(sew), 0, 5]
        bb = [hi - 1, 1, 0, 5]
        for mn, f in (
            ("vminu", lambda x, y, w: min(x, y)),
            ("vmaxu", lambda x, y, w: max(x, y)),
            ("vmin", lambda x, y, w: m(min(s(x, w), s(y, w)), w)),
            ("vmax", lambda x, y, w: m(max(s(x, w), s(y, w)), w)),
        ):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                fn=lambda x, y, o, g=f, w=sew: g(x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            if sew != 64:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=1,
                    fn=lambda x, y, o, g=f, w=sew: g(x, 1, w),
                    desc=f"{mn}.vx 1 e{sew}",
                )
    out_.append(t)

    t = new(
        "vmul_vmulh_vmulhu_vmulhsu_op",
        "vmul returns the low SEW bits of the 2*SEW product; vmulh (signed x signed), vmulhu (unsigned x "
        "unsigned) and vmulhsu (signed vs2 x unsigned vs1) return the high SEW bits. Operands MIN, -1, MAX and "
        "all ones at SEW 8, 16, 32, 64 where the signedness of each operand changes the high half.",
    )

    def mulh(mn: str, x: int, y: int, w: int) -> int:
        if mn == "vmul":
            return m(x * y, w)
        if mn == "vmulh":
            return m((s(x, w) * s(y, w)) >> w, w)
        if mn == "vmulhu":
            return m((x * y) >> w, w)
        if MUT == "vmulhsu_swapped":
            return m((x * s(y, w)) >> w, w)
        return m((s(x, w) * y) >> w, w)

    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        a = [hi, ones(sew), hi - 1, ones(sew), 3]
        bb = [hi, ones(sew), ones(sew), 2, hi + 1]
        for mn in ("vmul", "vmulh", "vmulhu", "vmulhsu"):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                fn=lambda x, y, o, g=mn, w=sew: mulh(g, x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            if sew <= 32:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=ones(sew),
                    fn=lambda x, y, o, g=mn, w=sew: mulh(g, x, ones(w), w),
                    desc=f"{mn}.vx -1 e{sew}",
                )
    out_.append(t)

    t = new(
        "vdivu_vdiv_vremu_vrem_op",
        "Divide and remainder match the scalar M instructions, including the extreme inputs: division by zero "
        "gives all ones (vdivu, vdiv) and the dividend (vremu, vrem); signed overflow MIN / -1 gives MIN with "
        "remainder 0; signed division truncates toward zero (-7 / 2 = -3 r -1, 7 / -2 = -3 r 1). .vv and .vx at "
        "SEW 8, 16, 32, 64.",
    )

    def div(mn: str, x: int, y: int, w: int) -> int:
        if mn == "vdivu":
            return (0 if MUT == "vdiv_zero_0" else ones(w)) if y == 0 else x // y
        if mn == "vremu":
            return x if y == 0 else x % y
        a_, b_ = s(x, w), s(y, w)
        if mn == "vdiv":
            if b_ == 0:
                return 0 if MUT == "vdiv_zero_0" else ones(w)
            if a_ == -(1 << (w - 1)) and b_ == -1:
                return m(a_, w)
            return m(tdiv(a_, b_), w)
        if b_ == 0:
            return x
        if a_ == -(1 << (w - 1)) and b_ == -1:
            return x if MUT == "vrem_overflow_dividend" else 0
        return m(a_ - tdiv(a_, b_) * b_, w)

    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        a = [5, hi, hi, m(-7, sew), 7, ones(sew), 0, hi - 1]
        bb = [0, ones(sew), 0, 2, m(-2, sew), 3, 0, 1]
        for mn in ("vdivu", "vdiv", "vremu", "vrem"):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                fn=lambda x, y, o, g=mn, w=sew: div(g, x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            if sew <= 32:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=0,
                    fn=lambda x, y, o, g=mn, w=sew: div(g, x, 0, w),
                    desc=f"{mn}.vx 0 e{sew}",
                )
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=ones(sew),
                    fn=lambda x, y, o, g=mn, w=sew: div(g, x, ones(w), w),
                    desc=f"{mn}.vx -1 e{sew}",
                )
    out_.append(t)

    t = new(
        "vwmul_vwmulu_vwmulsu_op",
        "Widening multiplies return the full 2*SEW product: vwmul signed x signed, vwmulu unsigned x unsigned, "
        "vwmulsu signed vs2 x unsigned vs1/x[rs1]. MIN*MIN, (-1)*(-1) and MAX*(-1) at SEW 8, 16, 32 (.vv, .vx).",
    )

    def wmul(mn: str, x: int, y: int, w: int) -> int:
        if mn == "vwmul":
            return m(s(x, w) * s(y, w), 2 * w)
        if mn == "vwmulu":
            return x * y
        return m(s(x, w) * y, 2 * w)

    for sew in (8, 16, 32):
        hi = 1 << (sew - 1)
        a = [hi, ones(sew), hi - 1, 2]
        bb = [hi, ones(sew), ones(sew), hi]
        for mn in ("vwmul", "vwmulu", "vwmulsu"):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                deew=2 * sew,
                fn=lambda x, y, o, g=mn, w=sew: wmul(g, x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            arith(
                t,
                mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                sew=sew,
                a=a,
                kind="vx",
                b=ones(sew),
                deew=2 * sew,
                fn=lambda x, y, o, g=mn, w=sew: wmul(g, x, ones(w), w),
                desc=f"{mn}.vx -1 e{sew}",
            )
    out_.append(t)

    t = new(
        "vmacc_vnmsac_vmadd_vnmsub_op",
        "vmacc: vd = vs1*vs2 + vd; vnmsac: vd = -(vs1*vs2) + vd (both overwrite the addend); vmadd: "
        "vd = vs1*vd + vs2; vnmsub: vd = -(vs1*vd) + vs2 (both overwrite the multiplicand). Distinct small "
        "operands so that every role swap gives a different result; .vv and .vx at SEW 8, 32, 64.",
    )

    def mac(mn: str, v1: int, v2: int, d: int, w: int) -> int:
        if mn == "vnmsac" and MUT == "vnmsac_as_vmadd":
            return m(v1 * d + v2, w)
        return m(
            {"vmacc": v1 * v2 + d, "vnmsac": -(v1 * v2) + d, "vmadd": v1 * d + v2, "vnmsub": -(v1 * d) + v2}[mn], w
        )

    for sew in (8, 32, 64):
        a = [3, 5, ones(sew), 7]  # vs2
        bb = [2, 7, 3, 1 << (sew - 1)]  # vs1
        old = [11, 13, 2, 6]
        for mn in ("vmacc", "vnmsac", "vmadd", "vnmsub"):
            arith(
                t,
                mn + ".vv {vd}, {vs1}, {vs2}{vm}",
                sew=sew,
                a=a,
                b=bb,
                old=old,
                fn=lambda x, y, o, g=mn, w=sew: mac(g, y, x, o, w),
                desc=f"{mn}.vv e{sew}",
            )
            if sew != 64:
                arith(
                    t,
                    mn + ".vx {vd}, {rs1}, {vs2}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=9,
                    old=old,
                    fn=lambda x, y, o, g=mn, w=sew: mac(g, 9, x, o, w),
                    desc=f"{mn}.vx 9 e{sew}",
                )
    out_.append(t)

    t = new(
        "vmacc_vnmsac_vmadd_vnmsub_op_lowhalf",
        "Only the low SEW bits of the product are added or subtracted: products that overflow SEW (0x10*0x10 at "
        "e8, MIN*MIN, (-1)*(-1)) so a design using the high half or a saturated product differs.",
    )
    for sew in (8, 16, 64):
        hi = 1 << (sew - 1)
        a = [1 << (sew // 2), hi, ones(sew), 0x55 & ones(sew)]
        bb = [1 << (sew // 2), hi, ones(sew), 0xAB & ones(sew)]
        old = [1, 2, 3, ones(sew)]
        for mn in ("vmacc", "vnmsac", "vmadd", "vnmsub"):
            arith(
                t,
                mn + ".vv {vd}, {vs1}, {vs2}{vm}",
                sew=sew,
                a=a,
                b=bb,
                old=old,
                fn=lambda x, y, o, g=mn, w=sew: mac(g, y, x, o, w),
                desc=f"{mn}.vv e{sew}",
            )
    out_.append(t)

    t = new(
        "vwmaccu_vwmacc_vwmaccsu_vwmaccus_op",
        "Widening multiply-add: vd(2*SEW) += full product. vwmaccu unsigned x unsigned, vwmacc signed x signed, "
        "vwmaccsu signed vs1/x[rs1] x unsigned vs2, vwmaccus (.vx only) unsigned x[rs1] x signed vs2. Operands "
        "with the top bit set and an addend that makes the 2*SEW sum wrap; SEW 8, 16, 32.",
    )

    def wmac(mn: str, v1: int, v2: int, d: int, w: int) -> int:
        if mn == "vwmaccus" and MUT == "vwmaccus_as_su":
            mn = "vwmaccsu"
        p = {"vwmaccu": v1 * v2, "vwmacc": s(v1, w) * s(v2, w), "vwmaccsu": s(v1, w) * v2, "vwmaccus": v1 * s(v2, w)}[
            mn
        ]
        return m(p + d, 2 * w)

    for sew in (8, 16, 32):
        hi = 1 << (sew - 1)
        a = [hi, ones(sew), 3, hi - 1]
        bb = [ones(sew), hi, ones(sew), hi]
        old = [ones(2 * sew), 1, 1 << (2 * sew - 1), 0]
        for mn in ("vwmaccu", "vwmacc", "vwmaccsu"):
            arith(
                t,
                mn + ".vv {vd}, {vs1}, {vs2}{vm}",
                sew=sew,
                a=a,
                b=bb,
                old=old,
                deew=2 * sew,
                fn=lambda x, y, o, g=mn, w=sew: wmac(g, y, x, o, w),
                desc=f"{mn}.vv e{sew}",
            )
        for mn in ("vwmaccu", "vwmacc", "vwmaccsu", "vwmaccus"):
            arith(
                t,
                mn + ".vx {vd}, {rs1}, {vs2}{vm}",
                sew=sew,
                a=a,
                kind="vx",
                b=hi,
                old=old,
                deew=2 * sew,
                fn=lambda x, y, o, g=mn, w=sew, h=hi: wmac(g, h, x, o, w),
                desc=f"{mn}.vx 0x80.. e{sew}",
            )
    out_.append(t)

    # ---- merge / move
    def merge_tests(rule: str, plan: str, which: str) -> VTest:
        t = new(rule, plan)
        for sew in (8, 32, 64):
            a = rnd(t, sew, 8)
            bb = rnd(t, sew, 8)
            v0 = [0, 1, 1, 0, 1, 0, 0, 1]
            for ma in (False, True) if which != "op" else (False,):
                old = rnd(t, sew, 8)
                vl = 6
                lab = t.op(
                    f"vmerge.vvm {VD}, {VS2}, {VS1}, v0",
                    sew=sew,
                    vl=vl,
                    ma=ma,
                    mask=v0,
                    srcs={VD: (sew, "1", old), VS2: (sew, "1", a), VS1: (sew, "1", bb)},
                )
                exp = [(bb[i] if v0[i] else a[i]) if i < vl else old[i] for i in range(8)]
                if MUT == "vmerge_masked_policy" and ma:
                    exp = [ones(sew) if (i < vl and not v0[i]) else exp[i] for i in range(8)]
                t.check_vreg(VD, sew, exp, lab, f"vmerge.vvm e{sew} vl={vl} {'ma' if ma else 'mu'}")
            if sew != 64:
                old = rnd(t, sew, 8)
                lab = t.op(
                    f"vmerge.vxm {VD}, {VS2}, x6, v0",
                    sew=sew,
                    vl=8,
                    mask=v0,
                    xs={"x6": X(-3, -3)},
                    srcs={VD: (sew, "1", old), VS2: (sew, "1", a)},
                )
                t.check_vreg(VD, sew, [m(-3, sew) if v0[i] else a[i] for i in range(8)], lab, f"vmerge.vxm -3 e{sew}")
            old = rnd(t, sew, 8)
            lab = t.op(
                f"vmerge.vim {VD}, {VS2}, -16, v0",
                sew=sew,
                vl=8,
                mask=v0,
                srcs={VD: (sew, "1", old), VS2: (sew, "1", a)},
            )
            t.check_vreg(VD, sew, [ims(-16, sew) if v0[i] else a[i] for i in range(8)], lab, f"vmerge.vim -16 e{sew}")
        return t

    out_.append(
        merge_tests(
            "vmerge_op",
            "vmerge.vvm/.vxm/.vim select vs2 where v0 is 0 and vs1/x[rs1]/imm where "
            "it is 1, at SEW 8, 32, 64; the immediate is sign-extended.",
            "op",
        )
    )
    out_.append(
        merge_tests(
            "vmerge_all_elem",
            "vmerge writes every body element (vstart <= i < vl) whatever the "
            "mask: elements with v0 = 0 get vs2[i] (not the old value, and not ones under vma = 1); "
            "tail elements (vl = 6 of 8, tu) are undisturbed. Also the .vxm/.vim forms.",
            "all",
        )
    )
    out_.append(
        merge_tests(
            "vmerge_op_mask",
            "Mask value 0 copies the first operand vs2 and mask value 1 copies the "
            "second operand (vs1, x[rs1] or the sign-extended 5-bit immediate), for a v0 pattern "
            "that differs per element; with vma = 0 and 1.",
            "mask",
        )
    )

    t = new(
        "vmv_op",
        "vmv.v.v copies a register group and vmv.v.x/vmv.v.i splat a scalar or the sign-extended "
        "immediate to every body element (unmasked); tail elements are undisturbed under tu and old-or-ones under "
        "ta. vmv.v.x uses the low SEW bits of x[rs1] (SEW < XLEN) and sign-extends it (SEW = 64 on RV32). LMUL "
        "2 group copy.",
    )
    for sew in (8, 32, 64):
        for ta in (False, True):
            a = rnd(t, sew, 8)
            old = rnd(t, sew, 8)
            lab = t.op(f"vmv.v.v {VD}, {VS2}", sew=sew, vl=5, ta=ta, srcs={VD: (sew, "1", old), VS2: (sew, "1", a)})
            t.check_vreg(VD, sew, pol(old, a, 5, sew, ta=ta), lab, f"vmv.v.v e{sew} vl=5 {'ta' if ta else 'tu'}")
        old = rnd(t, sew, 8)
        xv = X(0x89ABCDEF, 0x0123456789ABCDEF) if sew == 64 else X(0x7654321F, 0x7654321F)
        lab = t.op(f"vmv.v.x {VD}, x6", sew=sew, vl=8, xs={"x6": xv}, srcs={VD: (sew, "1", old)})
        exp = X(m(sx(0x89ABCDEF, 32), 64), 0x0123456789ABCDEF) if sew == 64 else m(0x7654321F, sew)
        t.check_vreg(VD, sew, [exp] * 8, lab, f"vmv.v.x e{sew}")
        old = rnd(t, sew, 8)
        lab = t.op(f"vmv.v.i {VD}, -16", sew=sew, vl=8, srcs={VD: (sew, "1", old)})
        t.check_vreg(VD, sew, [ims(-16, sew)] * 8, lab, f"vmv.v.i -16 e{sew}")
    a = rnd(t, 32, 8)
    old = rnd(t, 32, 8)
    lab = t.op(f"vmv.v.v {VD}, {VS2}", sew=32, lmul="2", vl=8, srcs={VD: (32, "2", old), VS2: (32, "2", a)})
    t.check_vreg(VD, 32, a, lab, "vmv.v.v e32 m2 vl=8", "2")
    out_.append(t)
    return out_


# ==================================================================== fixed point
VXRM = ("rnu", "rne", "rdn", "rod")


def g_fixed() -> list[VTest]:
    out_: list[VTest] = []

    def sat_add(mn: str, x: int, y: int, w: int) -> tuple[int, int]:
        if mn in ("vsaddu", "vssubu"):
            r = x + y if mn == "vsaddu" else x - y
            lo, hi = 0, ones(w)
        else:
            r = s(x, w) + s(y, w) if mn == "vsadd" else s(x, w) - s(y, w)
            lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
        if MUT == "vsadd_wrap" and mn == "vsadd":
            return m(r, w), 0
        if r > hi:
            return m(hi, w), 1
        if r < lo:
            return m(lo, w), 1
        return m(r, w), 0

    t = new(
        "vsaddu_vsadd_vssubu_vssub_op",
        "vsaddu/vssubu are unsigned and vsadd/vssub signed saturating add/subtract; for results in range they "
        "equal the plain sum or difference and leave vxsat 0. Operand pairs whose result is in range only under "
        "the correct signedness (0x80 + 0x7f, 0xff - 0x01, -1 + 1) at SEW 8, 16, 32, 64, .vv/.vx/.vi forms.",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        cases = {
            "vsaddu": ([hi, 1, 0], [hi - 1, 2, 0]),
            "vsadd": ([ones(sew), hi, 5], [1, hi - 1, m(-7, sew)]),
            "vssubu": ([ones(sew), hi, 7], [1, hi, 7]),
            "vssub": ([ones(sew), hi - 1, hi], [ones(sew), hi - 1, ones(sew)]),
        }
        for mn, (a, bb) in cases.items():
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                vxrm=0,
                sat=0,
                fn=lambda x, y, o, g=mn, w=sew: sat_add(g, x, y, w)[0],
                desc=f"{mn}.vv e{sew} in range",
            )
    arith(
        t,
        "vsadd.vi {vd}, {vs2}, -16{vm}",
        sew=8,
        a=[0x10, 0x7F, 0x00],
        kind="vi",
        b=-16,
        vxrm=0,
        sat=0,
        fn=lambda x, y, o: sat_add("vsadd", x, ims(-16, 8), 8)[0],
        desc="vsadd.vi -16 e8 in range",
    )
    arith(
        t,
        "vsaddu.vi {vd}, {vs2}, 15{vm}",
        sew=16,
        a=[0x10, 0x7FFF, 0xFFF0],
        kind="vi",
        b=15,
        vxrm=0,
        sat=0,
        fn=lambda x, y, o: sat_add("vsaddu", x, 15, 16)[0],
        desc="vsaddu.vi 15 e16 in range",
    )
    arith(
        t,
        "vssub.vx {vd}, {vs2}, {rs1}{vm}",
        sew=32,
        a=[0, 0x7FFFFFFE, 0x80000000],
        kind="vx",
        b=ones(32),
        vxrm=0,
        sat=0,
        fn=lambda x, y, o: sat_add("vssub", x, ones(32), 32)[0],
        desc="vssub.vx -1 e32 in range",
    )
    out_.append(t)

    t = new(
        "vsaddu_vsadd_vssubu_vssub_op_overflow_vxsat_op_vsaddsub",
        "On overflow the result is the closest representable value (unsigned: 0 or 2^SEW-1; signed: MIN or MAX) "
        "and vxsat is set. Each instruction overflows in each direction it can at SEW 8 and 64 (and .vx/.vi at 16, "
        "32); a vector with one saturating element among in-range ones sets vxsat; vxsat already 1 stays 1 "
        "after an instruction that does not saturate (it is only ever set).",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        cases = {
            "vsaddu": ([ones(sew), hi, 1], [1, hi, 1]),
            "vsadd": ([hi - 1, hi, 3], [1, ones(sew), 4]),
            "vssubu": ([0, 5, 9], [1, 6, 3]),
            "vssub": ([hi, hi - 1, 2], [1, ones(sew), 1]),
        }
        for mn, (a, bb) in cases.items():
            sat = [sat_add(mn, a[i], bb[i], sew)[1] for i in range(3)]
            sv = int(any(sat)) if MUT != "vxsat_not_set" else 0
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                vxrm=0,
                sat=sv,
                fn=lambda x, y, o, g=mn, w=sew: sat_add(g, x, y, w)[0],
                desc=f"{mn}.vv e{sew} overflow",
            )
        if sew <= 32:
            arith(
                t,
                "vsaddu.vx {vd}, {vs2}, {rs1}{vm}",
                sew=sew,
                a=[ones(sew), 0],
                kind="vx",
                b=ones(sew),
                vxrm=0,
                sat=1 if MUT != "vxsat_not_set" else 0,
                fn=lambda x, y, o, w=sew: sat_add("vsaddu", x, ones(w), w)[0],
                desc=f"vsaddu.vx -1 e{sew}",
            )
            arith(
                t,
                "vsadd.vi {vd}, {vs2}, -16{vm}",
                sew=sew,
                a=[hi, hi + 15, hi + 16],
                kind="vi",
                b=-16,
                vxrm=0,
                sat=1 if MUT != "vxsat_not_set" else 0,
                fn=lambda x, y, o, w=sew: sat_add("vsadd", x, ims(-16, w), w)[0],
                desc=f"vsadd.vi -16 e{sew}",
            )
    # sticky: vxsat = 1, then a non-saturating vsadd
    t.vload(VS2, 8, [1, 2])
    t.vload(VS1, 8, [3, 4])
    t.emit("csrwi vxsat, 1")
    t.vset(2, 8)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vsadd.vv {VD}, {VS2}, {VS1}")
    t.check_vxsat(0 if MUT == "vxsat_cleared" else 1, lab, "vxsat = 1 before a non-saturating vsadd.vv stays 1")
    t.check_vreg(VD, 8, [4, 6], lab, "vsadd.vv e8 in range")
    out_.append(t)

    def avg(mn: str, x: int, y: int, w: int, rm: int) -> int:
        if MUT == "vaadd_rdn_always":
            rm = 2
        if mn == "vaaddu":
            v = x + y
        elif mn == "vaadd":
            v = s(x, w) + s(y, w)
        elif mn == "vasubu":
            v = (x - y) if MUT != "vasubu_signed" else s(x, w) - s(y, w)
            v = m(v, w + 1)  # roundoff_unsigned of the SEW+1-bit difference
            if MUT == "vasubu_signed":
                v = s(x, w) - s(y, w)
        else:
            v = s(x, w) - s(y, w)
        return m(roundoff(v, 1, rm), w)

    t = new(
        "vaaddu_vaadd_vasubu_vasub_op",
        "Averaging add/subtract: (a +/- b) >> 1, computed in infinite precision and rounded by vxrm "
        "(roundoff_unsigned/roundoff_signed with d = 1). Odd sums under each of rnu, rne, rdn, rod give different "
        "results (3 -> 2,2,1,1; 5 -> 3,2,2,3; -3 -> -1,-2,-2,-1), and MAX + MAX (no overflow in infinite "
        "precision) gives MAX. .vv at SEW 8, 32 and 64, .vx at SEW 16.",
    )
    for rm in range(4):
        for sew in (8, 32, 64):
            hi = 1 << (sew - 1)
            a = [1, 2, ones(sew), hi - 1, ones(sew), hi]
            bb = [2, 3, m(-2, sew), hi - 1, ones(sew), hi]
            for mn in ("vaaddu", "vaadd", "vasubu", "vasub"):
                arith(
                    t,
                    mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                    sew=sew,
                    a=a,
                    b=bb,
                    vxrm=rm,
                    fn=lambda x, y, o, g=mn, w=sew, r=rm: avg(g, x, y, w, r),
                    desc=f"{mn}.vv e{sew} {VXRM[rm]}",
                )
        for mn in ("vaaddu", "vaadd", "vasubu", "vasub"):
            arith(
                t,
                mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                sew=16,
                a=[1, 4, 0xFFFF, 0x8000],
                kind="vx",
                b=X(3, 3),
                vxrm=rm,
                fn=lambda x, y, o, g=mn, r=rm: avg(g, x, 3, 16, r),
                desc=f"{mn}.vx 3 e16 {VXRM[rm]}",
            )
    out_.append(t)

    t = new(
        "vasub_vasubu_op_overflow",
        "For vasub and vasubu the halved difference wraps around: vasub MAX - MIN = (2^SEW - 1)/2 rounds up to "
        "2^(SEW-1) under rnu/rne and wraps to MIN; vasubu 0 - (2^SEW - 1) (difference -(2^SEW - 1), i.e. 0b1..01 "
        "in SEW+1 bits) gives 2^(SEW-1) + 1 under rnu. All four vxrm modes at SEW 8, 16, 64.",
    )
    for rm in range(4):
        for sew in (8, 16, 64):
            hi = 1 << (sew - 1)
            arith(
                t,
                "vasub.vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=[hi - 1, hi, 0],
                b=[hi, hi - 1, hi],
                vxrm=rm,
                fn=lambda x, y, o, w=sew, r=rm: avg("vasub", x, y, w, r),
                desc=f"vasub.vv e{sew} {VXRM[rm]}",
            )
            arith(
                t,
                "vasubu.vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=[0, 0, 1],
                b=[ones(sew), 1, ones(sew)],
                vxrm=rm,
                fn=lambda x, y, o, w=sew, r=rm: avg("vasubu", x, y, w, r),
                desc=f"vasubu.vv e{sew} {VXRM[rm]}",
            )
    out_.append(t)

    def smul(x: int, y: int, w: int, rm: int) -> tuple[int, int]:
        v = roundoff(s(x, w) * s(y, w), w - 1, rm)
        hi, lo = (1 << (w - 1)) - 1, -(1 << (w - 1))
        if MUT == "vsmul_no_sat":
            return m(v, w), 0
        if v > hi:
            return m(hi, w), 1
        if v < lo:
            return m(lo, w), 1
        return m(v, w), 0

    t = new(
        "vsmul_op",
        "vsmul: 2*SEW product shifted right by SEW-1 with vxrm rounding, then saturated. Products whose "
        "discarded bits are exactly half, above half and below half (so rnu, rne, rdn, rod differ), negative "
        "products, and MIN * MIN (the only saturating case) at SEW 8, 16, 32, 64; .vv and .vx.",
    )
    for rm in range(4):
        for sew in (8, 16, 32, 64):
            hi = 1 << (sew - 1)
            a = [hi >> 1, (hi >> 1) + 1, m(-(hi >> 1) - 1, sew), 3, hi, hi - 1]
            bb = [3, (hi >> 1) + 1, 3, 1, hi, hi - 1]
            arith(
                t,
                "vsmul.vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                vxrm=rm,
                fn=lambda x, y, o, w=sew, r=rm: smul(x, y, w, r)[0],
                desc=f"vsmul.vv e{sew} {VXRM[rm]}",
            )
        arith(
            t,
            "vsmul.vx {vd}, {vs2}, {rs1}{vm}",
            sew=16,
            a=[0x4000, 0x8000, 0x0003, 0xFFFD],
            kind="vx",
            b=0xC001,
            vxrm=rm,
            fn=lambda x, y, o, r=rm: smul(x, 0xC001, 16, r)[0],
            desc=f"vsmul.vx e16 {VXRM[rm]}",
        )
    out_.append(t)

    t = new(
        "vxsat_op_vsmul",
        "vsmul sets vxsat when the result saturates (only MIN * MIN, giving MAX), and not otherwise "
        "(MIN * MAX, MAX * MAX, small products). Each SEW, .vv and .vx, with vxsat cleared before.",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        for a, bb in (([hi, 3], [hi, 5]), ([hi, hi - 1, 7], [hi - 1, hi - 1, 9])):
            sv = int(any(smul(a[i], bb[i], sew, 0)[1] for i in range(len(a))))
            arith(
                t,
                "vsmul.vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=bb,
                vxrm=0,
                sat=sv,
                fn=lambda x, y, o, w=sew: smul(x, y, w, 0)[0],
                desc=f"vsmul.vv e{sew} vxsat {sv}",
            )
    arith(
        t,
        "vsmul.vx {vd}, {vs2}, {rs1}{vm}",
        sew=32,
        a=[0x80000000, 1],
        kind="vx",
        b=0x80000000,
        vxrm=0,
        sat=1 if MUT != "vsmul_no_sat" else 0,
        fn=lambda x, y, o: smul(x, 0x80000000, 32, 0)[0],
        desc="vsmul.vx MIN e32",
    )
    out_.append(t)

    def ssr(mn: str, x: int, k: int, w: int, rm: int) -> int:
        k &= w - 1
        if mn == "vssrl" or MUT == "vssra_logical":
            return m(roundoff(x, k, rm), w)
        return m(roundoff(s(x, w), k, rm), w)

    t = new(
        "vssrl_vssra_op",
        "Scaling shifts: vssrl shifts the unsigned and vssra the signed value right, and rounds the shifted-out "
        "bits with vxrm. Sources with the shifted-out bits exactly half / above / below half and odd/even "
        "results, negative sources for vssra, under all four vxrm modes; .vv, .vx and .vi (uimm) at SEW 8, 32, "
        "64.",
    )
    for rm in range(4):
        for sew in (8, 32, 64):
            hi = 1 << (sew - 1)
            a = [0x18, 0x28, 0x19, hi | 0x37, ones(sew), hi]
            sh = [4, 4, 4, 3, 1, sew - 1]
            for mn in ("vssrl", "vssra"):
                arith(
                    t,
                    mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                    sew=sew,
                    a=a,
                    b=sh,
                    vxrm=rm,
                    fn=lambda x, y, o, g=mn, w=sew, r=rm: ssr(g, x, y, w, r),
                    desc=f"{mn}.vv e{sew} {VXRM[rm]}",
                )
                arith(
                    t,
                    mn + ".vi {vd}, {vs2}, 3{vm}",
                    sew=sew,
                    a=a,
                    kind="vi",
                    b=3,
                    vxrm=rm,
                    fn=lambda x, y, o, g=mn, w=sew, r=rm: ssr(g, x, 3, w, r),
                    desc=f"{mn}.vi 3 e{sew} {VXRM[rm]}",
                )
        for mn in ("vssrl", "vssra"):
            arith(
                t,
                mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                sew=16,
                a=[0x8018, 0x0028, 0xFFFF],
                kind="vx",
                b=X(4, 4),
                vxrm=rm,
                fn=lambda x, y, o, g=mn, r=rm: ssr(g, x, 4, 16, r),
                desc=f"{mn}.vx 4 e16 {VXRM[rm]}",
            )
    out_.append(t)

    t = new(
        "vssrl_vssra_shamt",
        "Scaling shifts use only the low lg2(SEW) bits of the shift amount: amounts SEW + 1, 2*SEW - 1 and "
        "all ones from vs1/x[rs1], and uimm 9 and 31 at SEW 8 and 16, with rounding (rnu) visible in the result.",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        a = [hi | 0x6, 0x7 << 2, ones(sew)]
        sh = [sew + 1, 2 * sew - 1, ones(sew)]

        def ssr2(mn: str, x: int, k: int, w: int) -> int:
            if MUT == "shamt_unmasked" and k >= w:
                return 0 if mn == "vssrl" else m(-1 if s(x, w) < 0 else 0, w)
            return ssr(mn, x, k, w, 0)

        for mn in ("vssrl", "vssra"):
            arith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                b=sh,
                vxrm=0,
                fn=lambda x, y, o, g=mn, w=sew: ssr2(g, x, y, w),
                desc=f"{mn}.vv e{sew}",
            )
            if sew <= 32:
                arith(
                    t,
                    mn + ".vx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    kind="vx",
                    b=X(sew + 1, sew + 1),
                    vxrm=0,
                    fn=lambda x, y, o, g=mn, w=sew: ssr2(g, x, w + 1, w),
                    desc=f"{mn}.vx {sew + 1} e{sew}",
                )
            for k in (9, 31) if sew == 8 else (17, 31) if sew == 16 else ():
                arith(
                    t,
                    mn + f".vi {{vd}}, {{vs2}}, {k}{{vm}}",
                    sew=sew,
                    a=a,
                    kind="vi",
                    b=k,
                    vxrm=0,
                    fn=lambda x, y, o, g=mn, w=sew, kk=k: ssr2(g, x, kk, w),
                    desc=f"{mn}.vi {k} e{sew}",
                )
    out_.append(t)

    def clip(mn: str, x: int, k: int, w: int, rm: int) -> tuple[int, int]:
        k &= 2 * w - 1
        if mn == "vnclipu" and MUT != "vnclipu_signed":
            src = x
            lo, hi = 0, ones(w)
        else:
            src = s(x, 2 * w)
            lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
            if mn == "vnclipu":
                lo, hi = 0, ones(w)
        if MUT == "vnclip_sat_after_trunc":
            v = src >> k
            v = max(lo, min(hi, v))
            return m(v, w), 0
        v = roundoff(src, k, rm)
        if v > hi:
            return m(hi, w), 1
        if v < lo:
            return m(lo, w), 1
        return m(v, w), 0

    t = new(
        "vnclipu_vnclip_op",
        "vnclipu/vnclip narrow a 2*SEW source: shift right (vs1, x[rs1] or uimm), round with vxrm, saturate to "
        "SEW (unsigned for vnclipu, signed for vnclip). In-range and saturating elements, .wv/.wx/.wi at SEW 8, "
        "16, 32 under rnu.",
    )
    for sew in (8, 16, 32):
        W = 2 * sew
        a = [0x1234 & ones(W), 0x00F7, ones(W), 1 << (W - 1), (1 << (sew + 2)) - 1, 0x7F]
        sh = [4, 1, 0, sew, 3, 0]
        for mn in ("vnclipu", "vnclip"):
            arith(
                t,
                mn + ".wv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                aeew=W,
                b=sh,
                vxrm=0,
                fn=lambda x, y, o, g=mn, w=sew: clip(g, x, y, w, 0)[0],
                desc=f"{mn}.wv e{sew}",
            )
            arith(
                t,
                mn + ".wx {vd}, {vs2}, {rs1}{vm}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vx",
                b=X(2, 2),
                vxrm=0,
                fn=lambda x, y, o, g=mn, w=sew: clip(g, x, 2, w, 0)[0],
                desc=f"{mn}.wx 2 e{sew}",
            )
            arith(
                t,
                mn + ".wi {vd}, {vs2}, 5{vm}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vi",
                b=5,
                vxrm=0,
                fn=lambda x, y, o, g=mn, w=sew: clip(g, x, 5, w, 0)[0],
                desc=f"{mn}.wi 5 e{sew}",
            )
    out_.append(t)

    t = new(
        "vnclipu_vnclip_shamt",
        "vnclip/vnclipu use the low lg2(2*SEW) bits of the shift amount: at SEW 8 amounts 15 (kept), 16 -> 0, "
        "17 -> 1, 0xff -> 15; at SEW 32 amounts 63, 64 -> 0, 65 -> 1; uimm 15 and 31 at SEW 8 and 16.",
    )
    for sew, shamts in ((8, [15, 16, 17, 0xFF]), (16, [31, 32, 33, 0xFFFF]), (32, [63, 64, 65, 33])):
        W = 2 * sew
        a = [0x8001 & ones(W) | (1 << (W - 1)), 0x7FFF & ones(W), 0x00FF, (1 << (W - 1)) - 1]

        def cl(mn: str, x: int, k: int, w: int) -> int:
            if MUT == "nshamt_sew_bits":
                k &= w - 1
            return clip(mn, x, k, w, 0)[0]

        for mn in ("vnclipu", "vnclip"):
            arith(
                t,
                mn + ".wv {vd}, {vs2}, {vs1}{vm}",
                sew=sew,
                a=a,
                aeew=W,
                b=[x & ones(sew) for x in shamts],
                vxrm=0,
                fn=lambda x, y, o, g=mn, w=sew: cl(g, x, y, w),
                desc=f"{mn}.wv e{sew}",
            )
            for k in shamts[1:3]:
                arith(
                    t,
                    mn + ".wx {vd}, {vs2}, {rs1}{vm}",
                    sew=sew,
                    a=a,
                    aeew=W,
                    kind="vx",
                    b=X(k, k),
                    vxrm=0,
                    fn=lambda x, y, o, g=mn, w=sew, kk=k: cl(g, x, kk, w),
                    desc=f"{mn}.wx {k} e{sew}",
                )
            if sew <= 16:
                for k in (15, 31):
                    arith(
                        t,
                        mn + f".wi {{vd}}, {{vs2}}, {k}{{vm}}",
                        sew=sew,
                        a=a,
                        aeew=W,
                        kind="vi",
                        b=k,
                        vxrm=0,
                        fn=lambda x, y, o, g=mn, w=sew, kk=k: cl(g, x, kk, w),
                        desc=f"{mn}.wi {k} e{sew}",
                    )
    out_.append(t)

    t = new(
        "vnclipu_vnclip_rounding",
        "vnclip/vnclipu round with vxrm around the destination LSB, before saturating: vnclipu.wi 1 of 0x01ff "
        "rounds to 0x100 under rnu/rne and then saturates to 0xff with vxsat = 1, but gives 0xff without "
        "saturation under rdn and rod (rod: v[1] = 1, so no increment); 0x00ff >> 1 gives 0x80 (rnu), 0x80 (rne), 0x7f (rdn), 0x7f (rod). vnclip of "
        "0x00ff >> 1 rounds to 0x80 and saturates to 0x7f only when rounding up. All four modes, SEW 8 and 32.",
    )
    for rm in range(4):
        for sew in (8, 32):
            W = 2 * sew
            hi = 1 << (sew - 1)
            for mn, a in (
                ("vnclipu", [(1 << (sew + 1)) - 1, (1 << sew) - 1, 0x5]),
                ("vnclip", [(hi << 1) - 1, m(-(hi << 1) - 1, W), 0x6]),
            ):
                sv = int(any(clip(mn, x, 1, sew, rm)[1] for x in a))
                if MUT == "vnclip_sat_after_trunc":
                    sv = 0
                arith(
                    t,
                    mn + ".wi {vd}, {vs2}, 1{vm}",
                    sew=sew,
                    a=a,
                    aeew=W,
                    kind="vi",
                    b=1,
                    vxrm=rm,
                    sat=sv,
                    fn=lambda x, y, o, g=mn, w=sew, r=rm: clip(g, x, 1, w, r)[0],
                    desc=f"{mn}.wi 1 e{sew} {VXRM[rm]}",
                )
    out_.append(t)

    t = new(
        "vnclipu_overflow",
        "vnclipu treats the shifted, rounded source as unsigned and saturates to 2^SEW - 1 when it exceeds the "
        "destination: 0xffff (as unsigned, not -1), 0x8000, 0x0100 at SEW 8 with shift 0, and values just in "
        "range (0x00ff); vxsat is set only when an element saturates. SEW 8, 16, 32.",
    )
    for sew in (8, 16, 32):
        W = 2 * sew
        for a in ([ones(W), 1 << (W - 1), 1 << sew], [ones(sew), 0, 1]):
            sv = int(any(clip("vnclipu", x, 0, sew, 0)[1] for x in a))
            arith(
                t,
                "vnclipu.wi {vd}, {vs2}, 0{vm}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vi",
                b=0,
                vxrm=0,
                sat=sv,
                fn=lambda x, y, o, w=sew: clip("vnclipu", x, 0, w, 0)[0],
                desc=f"vnclipu.wi 0 e{sew}",
            )
    out_.append(t)

    t = new(
        "vnclip_overflow",
        "vnclip treats the shifted, rounded source as signed and saturates to MIN or MAX of SEW: 0x0080 -> 0x7f, "
        "0xff7f -> 0x80 (both saturate), 0xff80 -> 0x80 and 0x007f -> 0x7f (in range); vxsat set only when an "
        "element saturates. SEW 8, 16, 32.",
    )
    for sew in (8, 16, 32):
        W = 2 * sew
        hi = 1 << (sew - 1)
        for a in ([hi, m(-hi - 1, W), 1 << (W - 1)], [m(-hi, W), hi - 1, 0]):
            sv = int(any(clip("vnclip", x, 0, sew, 0)[1] for x in a))
            arith(
                t,
                "vnclip.wi {vd}, {vs2}, 0{vm}",
                sew=sew,
                a=a,
                aeew=W,
                kind="vi",
                b=0,
                vxrm=0,
                sat=sv,
                fn=lambda x, y, o, w=sew: clip("vnclip", x, 0, w, 0)[0],
                desc=f"vnclip.wi 0 e{sew}",
            )
    out_.append(t)

    t = new(
        "vxsat_op_vnclip_u",
        "If any destination element of vnclip/vnclipu saturates, vxsat[0] is set: one saturating element in the "
        "last body position of 8 sets it; no saturating element leaves a cleared vxsat 0; a vxsat already 1 is "
        "not cleared by a non-saturating vnclip.",
    )
    for mn in ("vnclipu", "vnclip"):
        a = [0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x7FFF]
        arith(
            t,
            mn + ".wi {vd}, {vs2}, 0{vm}",
            sew=8,
            a=a,
            aeew=16,
            kind="vi",
            b=0,
            vxrm=0,
            sat=0 if MUT == "vxsat_not_set" else 1,
            fn=lambda x, y, o, g=mn: clip(g, x, 0, 8, 0)[0],
            desc=f"{mn}.wi e8, last element saturates",
        )
        arith(
            t,
            mn + ".wi {vd}, {vs2}, 0{vm}",
            sew=8,
            a=a[:7],
            aeew=16,
            kind="vi",
            b=0,
            vxrm=0,
            sat=0,
            fn=lambda x, y, o, g=mn: clip(g, x, 0, 8, 0)[0],
            desc=f"{mn}.wi e8, none saturates",
        )
        t.vload(VS2, 16, [0x10, 0x20])
        t.emit("csrwi vxsat, 1")
        t.vset(2, 8)
        lab = t.label("insn")
        t.emit(f"{lab}:", 0)
        t.emit(f"{mn}.wi {VD}, {VS2}, 0")
        t.check_vxsat(0 if MUT == "vxsat_cleared" else 1, lab, f"{mn}: vxsat = 1 stays 1")
    out_.append(t)
    return out_


# ==================================================================== floating point
def F(x: float | Fr, w: int) -> int:
    return fenc(x, w)


FRM = ("rne", "rtz", "rdn", "rup", "rmm")


def farith(
    t: VTest,
    asm: str,
    *,
    sew: int,
    a: Sequence[int],
    b: object = None,
    kind: str = "vv",
    f: Callable[..., tuple[int, int]],
    frm: int = 0,
    mask: Sequence[int] | None = None,
    vl: int | None = None,
    deew: int | None = None,
    aeew: int | None = None,
    old: Sequence[int] | None = None,
    desc: str = "",
    ma: bool = False,
    ta: bool = False,
    flags: object = "auto",
) -> str:
    """A vector FP instruction: f(a_i, b_i, old_i) -> (bits, flags). fflags must be the OR of the active elements'
    flags (fflags_op_V_fp), unless flags is given."""
    n = len(a)
    deew = deew or sew
    old = list(old) if old is not None else rnd(t, deew, n)
    vlv = vl if vl is not None else n
    bs = list(b) if kind == "vv" else [b if not isinstance(b, tuple) else b[0]] * n  # type: ignore[arg-type]
    if kind == "vf" and isinstance(b, tuple) and b[1] == 64 and sew == 32 and (b[0] >> 32) != 0xFFFFFFFF:
        bs = [CNAN[32]] * n  # not NaN-boxed: the canonical NaN is used
    res = [f(a[i], bs[i], old[i]) for i in range(n)]
    fl = 0
    for i in range(min(vlv, n)):
        if mask is None or mask[i]:
            fl |= res[i][1]
    if flags != "auto":
        fl = flags  # type: ignore[assignment]
    return arith(
        t,
        asm,
        sew=sew,
        a=a,
        b=b,
        kind=kind,
        fn=lambda x, y, o, r=iter(res): next(r)[0],  # noqa: B008  (one iterator per call)
        frm=frm,
        mask=mask,
        vl=vl,
        deew=deew,
        aeew=aeew,
        old=old,
        desc=desc,
        flags=fl,
        ma=ma,
        ta=ta,
    )


def g_fp() -> list[VTest]:
    out_: list[VTest] = []

    t = new(
        "vf_requires_vx",
        "V provides FP elements of 32 and 64 bits, so the hart must also implement scalar F and D: fadd.s, "
        "fadd.d, fmv.x.w and fsqrt.d execute with correct results, and so do vfadd.vf at SEW 32 and 64 using "
        "those f registers.",
        required=REQ,
    )
    t.fload("f1", F(1.5, 32), 32)
    t.fload("f2", F(2.25, 32), 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("fadd.s f3, f1, f2")
    t.check_freg("f3", 32, F(3.75, 32), lab, "fadd.s 1.5 + 2.25")
    t.emit("fmv.x.w x8, f3")
    t.check("x8", sx(F(3.75, 32), 32), lab, "fmv.x.w of 3.75")
    t.fload("f4", F(2.0, 64), 64)
    t.fload("f5", F(0.125, 64), 64)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("fadd.d f6, f4, f5")
    t.emit("fsqrt.d f7, f4")
    t.check_freg("f6", 64, F(2.125, 64), lab, "fadd.d 2 + 0.125")
    t.check_freg("f7", 64, fsqrt(F(2.0, 64), 64, 0)[0], lab, "fsqrt.d 2")
    for w, fr in ((32, "f1"), (64, "f4")):
        a = [F(1.0, w), F(-3.5, w)]
        bv = F(1.5, w) if w == 32 else F(2.0, w)
        farith(
            t,
            f"vfadd.vf {{vd}}, {{vs2}}, {fr}{{vm}}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w, bb=bv: fadd(x, bb, ww, 0),
            desc=f"vfadd.vf e{w} with the scalar register",
        )
    out_.append(t)

    t = new(
        "fflags_op_V_fp",
        "An FP exception at an active element sets its fflags bit; inactive (masked-off) elements do not. "
        "vfdiv.vv with 1/0 (DZ), 0/0 (NV), MAX*2-style overflow via vfmul (OF|NX) and an inexact quotient (NX) "
        "placed alternately in active and masked-off elements at SEW 32 and 64; each flag must appear iff an "
        "active element raised it. Flags accrue: a flag set before the instruction stays set.",
    )
    for w in (32, 64):
        one, zero, three = F(1.0, w), fpzero(w), F(3.0, w)
        a = [one, zero, one, one, zero]
        bb = [zero, zero, three, one, one]
        for mask in ([1, 0, 0, 1, 1], [0, 1, 0, 1, 1], [0, 0, 1, 1, 1], [1, 1, 1, 1, 1]):
            fl = None
            if MUT == "fflags_inactive":
                fl = 0
                for i in range(5):
                    fl |= fdiv(a[i], bb[i], w, 0)[1]
            farith(
                t,
                "vfdiv.vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                mask=mask,
                f=lambda x, y, o, ww=w: fdiv(x, y, ww, 0),
                desc=f"vfdiv.vv e{w} mask {mask}",
                flags="auto" if fl is None else fl,
            )
        mx = fpmax(w)
        a = [mx, one, mx]
        farith(
            t,
            "vfmul.vv {vd}, {vs2}, {vs1}{vm}",
            sew=w,
            a=a,
            b=[F(2.0, w), one, F(2.0, w)],
            mask=[0, 1, 1],
            f=lambda x, y, o, ww=w: fmul(x, y, ww, 0),
            desc=f"vfmul.vv e{w} overflow in the active element",
        )
    # accrual: NX set before an exact vfadd stays set
    t.vload(VS2, 32, [F(1.0, 32)])
    t.vload(VS1, 32, [F(2.0, 32)])
    t.emit("fsflagsi x0, 1")
    t.vset(1, 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vfadd.vv {VD}, {VS2}, {VS1}")
    t.check_fflags(NX, lab, "fflags.NX set before an exact vfadd stays set")
    out_.append(t)

    t = new(
        "vfadd_vfsub_vfrsub_op",
        "vfadd: vs2 + op; vfsub: vs2 - op; vfrsub (.vf only): f[rs1] - vs2, so operands 1 and 3 give -2 for "
        "vfsub and +2 for vfrsub. Exact and inexact sums under each frm (1 + 2^-24 at SEW 32, 1 + 2^-53 at SEW "
        "64), x - x = +0 (but -0 under rdn), inf - inf = canonical NaN with NV, at SEW 32 and 64.",
    )
    for w in (32, 64):
        p = FMT_P[w]
        tiny = F(Fr(1, 2**p), w)
        a = [F(1.0, w), F(3.0, w), F(1.0, w), F(5.0, w), fpinf(w)]
        bb = [F(2.0, w), F(1.0, w), tiny, F(5.0, w), fpinf(w)]
        for rm in range(5):
            farith(
                t,
                "vfadd.vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                frm=rm,
                f=lambda x, y, o, ww=w, r=rm: fadd(x, y, ww, r),
                desc=f"vfadd.vv e{w} {FRM[rm]}",
            )
            farith(
                t,
                "vfsub.vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                frm=rm,
                f=lambda x, y, o, ww=w, r=rm: fadd(x, y, ww, r, sub=True),
                desc=f"vfsub.vv e{w} {FRM[rm]}",
            )
        fv = F(1.0, w)
        farith(
            t,
            "vfadd.vf {vd}, {vs2}, {fs1}{vm}",
            sew=w,
            a=a,
            kind="vf",
            b=fv,
            f=lambda x, y, o, ww=w: fadd(x, y, ww, 0),
            desc=f"vfadd.vf 1.0 e{w}",
        )
        farith(
            t,
            "vfsub.vf {vd}, {vs2}, {fs1}{vm}",
            sew=w,
            a=a,
            kind="vf",
            b=fv,
            f=lambda x, y, o, ww=w: fadd(x, y, ww, 0, sub=True),
            desc=f"vfsub.vf 1.0 e{w}",
        )

        def rsub(x: int, y: int, ww: int = w) -> tuple[int, int]:
            if MUT == "vfrsub_order":
                return fadd(x, y, ww, 0, sub=True)
            return fadd(y, x, ww, 0, sub=True)

        farith(
            t,
            "vfrsub.vf {vd}, {vs2}, {fs1}{vm}",
            sew=w,
            a=a,
            kind="vf",
            b=fv,
            f=lambda x, y, o, g=rsub: g(x, y),
            desc=f"vfrsub.vf 1.0 e{w} (f - vs2)",
        )
    out_.append(t)

    t = new(
        "vfwadd_op",
        "Widening FP add/subtract produce a 2*SEW result from SEW operands (.vv/.vf) or from a 2*SEW vs2 and a "
        "SEW operand (.wv/.wf): the narrow operands are widened exactly, so 2^24 + 1 (not representable in "
        "binary32) and 1 - 2^-30 are exact in the binary64 result. SEW = 32.",
    )

    def wid(x: int) -> int:
        return fcvt_ff(x, 32, 64, 0)[0]

    def wadd(x: int, y: int, sub: bool) -> tuple[int, int]:
        if MUT == "vfwadd_narrow_round":
            r = fadd(x, y, 32, 0, sub)
            return wid(r[0]), r[1]
        return fadd(wid(x), wid(y), 64, 0, sub)

    a = [F(2**24, 32), F(1.0, 32), F(-3.0, 32), fpinf(32)]
    bb = [F(1.0, 32), F(Fr(1, 2**30), 32), F(0.5, 32), F(1.0, 32)]
    for mn, sub in (("vfwadd", False), ("vfwsub", True)):
        farith(
            t,
            mn + ".vv {vd}, {vs2}, {vs1}{vm}",
            sew=32,
            a=a,
            b=bb,
            deew=64,
            f=lambda x, y, o, sb=sub: wadd(x, y, sb),
            desc=f"{mn}.vv e32",
        )
        farith(
            t,
            mn + ".vf {vd}, {vs2}, {fs1}{vm}",
            sew=32,
            a=a,
            kind="vf",
            b=F(1.0, 32),
            deew=64,
            f=lambda x, y, o, sb=sub: wadd(x, y, sb),
            desc=f"{mn}.vf 1.0 e32",
        )
        wa = [F(2**40, 64), F(1.0, 64), F(Fr(1, 2**60), 64), fpinf(64, True)]
        farith(
            t,
            mn + ".wv {vd}, {vs2}, {vs1}{vm}",
            sew=32,
            a=wa,
            aeew=64,
            b=bb,
            deew=64,
            f=lambda x, y, o, sb=sub: fadd(x, wid(y), 64, 0, sb),
            desc=f"{mn}.wv e32",
        )
        farith(
            t,
            mn + ".wf {vd}, {vs2}, {fs1}{vm}",
            sew=32,
            a=wa,
            aeew=64,
            kind="vf",
            b=F(1.0, 32),
            deew=64,
            f=lambda x, y, o, sb=sub: fadd(x, wid(y), 64, 0, sb),
            desc=f"{mn}.wf 1.0 e32",
        )
    out_.append(t)

    t = new(
        "vfmul_vfdiv_vfrdiv_op",
        "vfmul and vfdiv (.vv/.vf) compute vs2 * op and vs2 / op; vfrdiv (.vf only) computes f[rs1] / vs2 "
        "(2 / 4 = 0.5, not 2). Exact and inexact quotients (1/3) under rne and rup, x/0 = inf with DZ, 0/0 and "
        "inf*0 = canonical NaN with NV, at SEW 32 and 64.",
    )
    for w in (32, 64):
        a = [F(4.0, w), F(1.0, w), F(1.0, w), fpzero(w), fpinf(w)]
        bb = [F(2.0, w), F(3.0, w), fpzero(w), fpzero(w), fpzero(w)]
        for rm in (0, 3):
            farith(
                t,
                "vfmul.vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                frm=rm,
                f=lambda x, y, o, ww=w, r=rm: fmul(x, y, ww, r),
                desc=f"vfmul.vv e{w} {FRM[rm]}",
            )
            farith(
                t,
                "vfdiv.vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                frm=rm,
                f=lambda x, y, o, ww=w, r=rm: fdiv(x, y, ww, r),
                desc=f"vfdiv.vv e{w} {FRM[rm]}",
            )
        fv = F(2.0, w)
        farith(
            t,
            "vfmul.vf {vd}, {vs2}, {fs1}{vm}",
            sew=w,
            a=a,
            kind="vf",
            b=fv,
            f=lambda x, y, o, ww=w: fmul(x, y, ww, 0),
            desc=f"vfmul.vf 2 e{w}",
        )
        farith(
            t,
            "vfdiv.vf {vd}, {vs2}, {fs1}{vm}",
            sew=w,
            a=a,
            kind="vf",
            b=fv,
            f=lambda x, y, o, ww=w: fdiv(x, y, ww, 0),
            desc=f"vfdiv.vf 2 e{w}",
        )
        farith(
            t,
            "vfrdiv.vf {vd}, {vs2}, {fs1}{vm}",
            sew=w,
            a=a,
            kind="vf",
            b=fv,
            f=lambda x, y, o, ww=w: fdiv(y, x, ww, 0),
            desc=f"vfrdiv.vf 2 e{w} (f / vs2)",
        )
    out_.append(t)

    t = new(
        "vfwmul_op",
        "vfwmul gives the exact 2*SEW product of SEW operands: (2^12 + 1)^2 = 2^24 + 2^13 + 1 and "
        "(1 + 2^-23)^2 are exact in binary64 but not in binary32; .vv and .vf at SEW 32, and inf * 0 = NaN (NV).",
    )
    a = [F(2**12 + 1, 32), F(1 + Fr(1, 2**23), 32), fpinf(32), F(-3.0, 32)]
    bb = [F(2**12 + 1, 32), F(1 + Fr(1, 2**23), 32), fpzero(32), F(0.5, 32)]
    farith(
        t,
        "vfwmul.vv {vd}, {vs2}, {vs1}{vm}",
        sew=32,
        a=a,
        b=bb,
        deew=64,
        f=lambda x, y, o: fmul(wid(x), wid(y), 64, 0),
        desc="vfwmul.vv e32",
    )
    farith(
        t,
        "vfwmul.vf {vd}, {vs2}, {fs1}{vm}",
        sew=32,
        a=a,
        kind="vf",
        b=F(2**12 + 1, 32),
        deew=64,
        f=lambda x, y, o: fmul(wid(x), wid(y), 64, 0),
        desc="vfwmul.vf e32",
    )
    out_.append(t)

    def vfma(mn: str, v1: int, v2: int, d: int, w: int, rm: int = 0) -> tuple[int, int]:
        # (a, b, c, neg_prod, neg_c) for vd = +/-(a*b) +/- c
        if MUT == "vfma_unfused":
            pr = fmul(v1, v2 if mn in ("vfmacc", "vfnmacc", "vfmsac", "vfnmsac") else d, w, rm)[0]
            c = d if mn in ("vfmacc", "vfnmacc", "vfmsac", "vfnmsac") else v2
            sg = {
                "vfmacc": (0, 0),
                "vfnmacc": (1, 1),
                "vfmsac": (0, 1),
                "vfnmsac": (1, 0),
                "vfmadd": (0, 0),
                "vfnmadd": (1, 1),
                "vfmsub": (0, 1),
                "vfnmsub": (1, 0),
            }[mn]
            return fma(pr, F(1.0, w), c, w, rm, bool(sg[0]), bool(sg[1]))
        if mn in ("vfmacc", "vfnmacc", "vfmsac", "vfnmsac"):
            x, y, c = v1, v2, d
        else:
            x, y, c = v1, d, v2
        np_, nc = {
            "vfmacc": (0, 0),
            "vfnmacc": (1, 1),
            "vfmsac": (0, 1),
            "vfnmsac": (1, 0),
            "vfmadd": (0, 0),
            "vfnmadd": (1, 1),
            "vfmsub": (0, 1),
            "vfnmsub": (1, 0),
        }[mn]
        if MUT == "vfmsac_sign" and mn == "vfmsac":
            np_, nc = 1, 0
        return fma(x, y, c, w, rm, bool(np_), bool(nc))

    t = new(
        "vfmacc_vfnmacc_vfmsac_vfnmsac_vfmadd_vfnmadd_vfmsub_vfnmsub_op",
        "All eight FMAs in both destructive forms: vfmacc +(vs1*vs2)+vd, vfnmacc -(vs1*vs2)-vd, vfmsac "
        "+(vs1*vs2)-vd, vfnmsac -(vs1*vs2)+vd overwrite the addend; vfmadd +(vs1*vd)+vs2, vfnmadd "
        "-(vs1*vd)-vs2, vfmsub +(vs1*vd)-vs2, vfnmsub -(vs1*vd)+vs2 overwrite the multiplicand. Distinct operands "
        "so each sign and role gives a different result; a fused case (1+2^-12)(1-2^-12) - 1 = -2^-24 that a "
        "rounded product would make 0; .vv and .vf at SEW 32 and 64.",
    )
    for w in (32, 64):
        e = Fr(1, 2**12) if w == 32 else Fr(1, 2**27)
        v2 = [F(3.0, w), F(1 + e, w), F(-1.5, w)]
        v1 = [F(2.0, w), F(1 - e, w), F(4.0, w)]
        d = [F(7.0, w), F(1.0, w), F(0.25, w)]
        for mn in ("vfmacc", "vfnmacc", "vfmsac", "vfnmsac", "vfmadd", "vfnmadd", "vfmsub", "vfnmsub"):
            farith(
                t,
                mn + ".vv {vd}, {vs1}, {vs2}{vm}",
                sew=w,
                a=v2,
                b=v1,
                old=d,
                f=lambda x, y, o, g=mn, ww=w: vfma(g, y, x, o, ww),
                desc=f"{mn}.vv e{w}",
            )
            farith(
                t,
                mn + ".vf {vd}, {fs1}, {vs2}{vm}",
                sew=w,
                a=v2,
                kind="vf",
                b=F(0.5, w),
                old=d,
                f=lambda x, y, o, g=mn, ww=w: vfma(g, y, x, o, ww),
                desc=f"{mn}.vf 0.5 e{w}",
            )
    out_.append(t)

    t = new(
        "vfwmacc_vfwnmacc_vfwmsac_vfwnmsac_op",
        "Widening FMAs: SEW multiplier inputs, 2*SEW addend and result (vd). vfwmacc +(vs1*vs2)+vd, vfwnmacc "
        "-(vs1*vs2)-vd, vfwmsac +(vs1*vs2)-vd, vfwnmsac -(vs1*vs2)+vd, with a product (2^12+1)^2 that is exact "
        "only at 2*SEW and a binary64 addend 2^-40; .vv and .vf at SEW 32.",
    )
    v2 = [F(2**12 + 1, 32), F(3.0, 32), F(-0.5, 32)]
    v1 = [F(2**12 + 1, 32), F(2.0, 32), F(8.0, 32)]
    d = [F(Fr(1, 2**40), 64), F(1.0, 64), F(2**33, 64)]
    for mn in ("vfwmacc", "vfwnmacc", "vfwmsac", "vfwnmsac"):
        np_, nc = {"vfwmacc": (0, 0), "vfwnmacc": (1, 1), "vfwmsac": (0, 1), "vfwnmsac": (1, 0)}[mn]
        farith(
            t,
            mn + ".vv {vd}, {vs1}, {vs2}{vm}",
            sew=32,
            a=v2,
            b=v1,
            old=d,
            deew=64,
            f=lambda x, y, o, p=np_, c=nc: fma(wid(y), wid(x), o, 64, 0, bool(p), bool(c)),
            desc=f"{mn}.vv e32",
        )
        farith(
            t,
            mn + ".vf {vd}, {fs1}, {vs2}{vm}",
            sew=32,
            a=v2,
            kind="vf",
            b=F(2**12 + 1, 32),
            old=d,
            deew=64,
            f=lambda x, y, o, p=np_, c=nc: fma(wid(y), wid(x), o, 64, 0, bool(p), bool(c)),
            desc=f"{mn}.vf e32",
        )
    out_.append(t)

    t = new(
        "vfsqrt_op",
        "vfsqrt.v is unary (vs2 only): sqrt(4) = 2, sqrt(2) correctly rounded under each frm, sqrt(-0) = -0, "
        "sqrt(+inf) = +inf, sqrt(-1) = canonical NaN with NV, sNaN -> canonical NaN with NV, the smallest "
        "subnormal, at SEW 32 and 64.",
    )
    for w in (32, 64):
        a = [F(4.0, w), F(2.0, w), fpzero(w, True), fpinf(w), F(-1.0, w), snan(w), 1]
        for rm in range(5):
            farith(
                t,
                "vfsqrt.v {vd}, {vs2}{vm}",
                sew=w,
                a=a,
                kind="none",
                frm=rm,
                f=lambda x, y, o, ww=w, r=rm: fsqrt(x, ww, r),
                desc=f"vfsqrt.v e{w} {FRM[rm]}",
            )
    out_.append(t)

    # ---- reciprocal estimates
    def rs7(x: int, w: int) -> tuple[int, int]:
        tab = RSQRT7
        if MUT == "vfrsqrt7_exp_parity":
            tab = RSQRT7[:64] + RSQRT7[:64]
        return frsqrt7(x, w, tab)

    def rc7(x: int, w: int, rm: int) -> tuple[int, int]:
        b, fl = frec7(x, w, rm, REC7)
        if MUT == "vfrec7_no_denorm":
            _, f_, _, _ = FMTS[w]
            if (b >> f_) & ones(w - 1 - f_) == 0 and b & ones(f_):
                b &= 1 << (w - 1)
        if MUT == "vfrec7_of_rtz_inf" and fl & OF and rm == RTZ:
            b = fpinf(w, bool(b >> (w - 1)))
        return b, fl

    t = new(
        "vfrsqrt7_op",
        "vfrsqrt7.v special cases from the table: -inf and negative normals/subnormals -> canonical NaN with NV; "
        "-0 -> -inf and +0 -> +inf with DZ; +inf -> +0; qNaN -> canonical NaN (no flag); sNaN -> canonical NaN "
        "with NV; a positive normal gives the 7-bit estimate with no flag. The output does not depend on frm "
        "(run under rne and rup). SEW 32 and 64.",
    )
    for w in (32, 64):
        a = [
            fpinf(w, True),
            F(-1.0, w),
            (1 << (w - 1)) | 1,
            fpzero(w, True),
            fpzero(w),
            fpinf(w),
            qnan(w, 5),
            snan(w),
            F(4.0, w),
        ]
        for rm in (0, 3):
            farith(
                t,
                "vfrsqrt7.v {vd}, {vs2}{vm}",
                sew=w,
                a=a,
                kind="none",
                frm=rm,
                f=lambda x, y, o, ww=w: rs7(x, ww),
                desc=f"vfrsqrt7.v e{w} {FRM[rm]}",
            )
    out_.append(t)

    t = new(
        "vfrsqrt7_op_unex",
        "Non-exceptional vfrsqrt7: the exponent LSB and the 6 significand MSBs index the table; the 7 output "
        "MSBs come from the table and the other significand bits are 0. Inputs cover even and odd exponents with "
        "table indices 0, 1, 31, 32, 63 (and random low significand bits that must be ignored), plus subnormal "
        "inputs, which are normalized first. SEW 32 and 64.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        a = []
        for ex in (bias, bias + 1):
            for idx in (0, 1, 31, 32, 63):
                a.append((ex << f_) | (idx << (f_ - 6)) | t.rand(f_ - 6))
        a += [1 << (f_ - 1), (1 << (f_ - 2)) | t.rand(f_ - 3), 3]
        farith(
            t,
            "vfrsqrt7.v {vd}, {vs2}{vm}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w: rs7(x, ww),
            desc=f"vfrsqrt7.v table lookups e{w}",
        )
    out_.append(t)

    t = new(
        "vfrsqrt7_op_precise",
        "vfrsqrt7 exponent: floor((3B - 1 - normalized exponent) / 2), with the normalized exponent of a "
        "subnormal = -(leading zeros). Inputs at the exponent extremes: largest normal, smallest normal, the "
        "spec's examples 0x00718abc -> 0x5f080000 and 0x7f765432 -> 0x1f820000, the smallest subnormal and "
        "subnormals with 1 and 2 leading zeros. The output sign equals the input sign (+). SEW 32 and 64.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        a = [fpmax(w), 1 << f_, 1, 1 << (f_ - 1), 1 << (f_ - 2), (1 << (f_ - 2)) | 1]
        if w == 32:
            a += [0x00718ABC, 0x7F765432]
        farith(
            t,
            "vfrsqrt7.v {vd}, {vs2}{vm}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w: rs7(x, ww),
            desc=f"vfrsqrt7.v exponent edges e{w}",
        )
    out_.append(t)

    t = new(
        "vfrec7_op",
        "vfrec7.v special cases from the table: +/-inf -> +/-0; +/-0 -> +/-inf with DZ; qNaN -> canonical NaN; "
        "sNaN -> canonical NaN with NV; a subnormal with sig = 00... (|x| < 2^-(B+1)) overflows with NX|OF to "
        "+/-inf or the largest finite value depending on frm and sign (rup/rtz for negative give max, rdn/rtz "
        "for positive give max); large normals give subnormal outputs. All five frm values, SEW 32 and 64.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        tiny = 1 << (f_ - 3)
        a = [
            fpinf(w),
            fpinf(w, True),
            fpzero(w),
            fpzero(w, True),
            qnan(w, 3),
            snan(w),
            tiny,
            (1 << (w - 1)) | tiny,
            F(2.0, w),
            (2 * bias) << f_,
        ]
        for rm in range(5):
            farith(
                t,
                "vfrec7.v {vd}, {vs2}{vm}",
                sew=w,
                a=a,
                kind="none",
                frm=rm,
                f=lambda x, y, o, ww=w, r=rm: rc7(x, ww, r),
                desc=f"vfrec7.v e{w} {FRM[rm]}",
            )
    out_.append(t)

    t = new(
        "vfrec7_op_unex",
        "Non-exceptional vfrec7: the 7 significand MSBs index the table, its output is the 7 result MSBs and "
        "the other bits are 0. Table indices 0, 1, 63, 64, 126, 127 with random low bits (ignored), positive "
        "and negative, normal exponents, SEW 32 and 64.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        a = []
        for idx in (0, 1, 63, 64, 126, 127):
            a.append(((bias + 3) << f_) | (idx << (f_ - 7)) | t.rand(f_ - 7))
        a += [(1 << (w - 1)) | ((bias - 5) << f_) | (77 << (f_ - 7)) | t.rand(f_ - 7)]
        farith(
            t,
            "vfrec7.v {vd}, {vs2}{vm}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w: rc7(x, ww, 0),
            desc=f"vfrec7.v table lookups e{w}",
        )
    out_.append(t)

    t = new(
        "vfrec7_op_precise",
        "vfrec7 output exponent 2B - 1 - normalized input exponent; outside [-1, 2B] the result is one of the "
        "exceptional cases. Boundary inputs: subnormal with sig = 01... (normalized exponent -1, output exponent "
        "2B: largest normal binade), sig = 001... (normalized exponent -2: overflow, NX|OF), smallest normal, and "
        "exponent 2B (output exponent -1: subnormal). SEW 32 and 64, rne.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        a = [
            1 << (f_ - 2),
            (1 << (f_ - 2)) | t.rand(f_ - 2),
            1 << (f_ - 3),
            1 << f_,
            (2 * bias) << f_,
            ((2 * bias) << f_) | ones(f_),
            ((2 * bias - 1) << f_) | 1,
        ]
        farith(
            t,
            "vfrec7.v {vd}, {vs2}{vm}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w: rc7(x, ww, 0),
            desc=f"vfrec7.v exponent edges e{w}",
        )
    out_.append(t)

    t = new(
        "vfrec7_op_subnorm",
        "A subnormal vfrec7 input is normalized: its significand is shifted left by 1 - normalized exponent and "
        "the leading 1 dropped before the table lookup. Subnormals with 0 and 1 leading zeros and random low "
        "bits, including the spec's example 0x00718abc -> 0x7e900000. SEW 32 and 64.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        a = [
            (1 << (f_ - 1)) | t.rand(f_ - 1),
            (1 << (f_ - 2)) | t.rand(f_ - 2),
            (1 << (f_ - 1)) | (1 << (w - 1)),
            ones(f_),
        ]
        if w == 32:
            a.append(0x00718ABC)
        farith(
            t,
            "vfrec7.v {vd}, {vs2}{vm}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w: rc7(x, ww, 0),
            desc=f"vfrec7.v subnormal inputs e{w}",
        )
    out_.append(t)

    t = new(
        "vfrec7_op_output",
        "When the normalized output exponent is 0 or -1 the vfrec7 result is subnormal: 1.sig shifted right by "
        "1 - exponent. Inputs with exponent 2B - 1 (output exponent 0) and 2B (output exponent -1) for several "
        "table indices, positive and negative (the sign is kept), and the spec's example 0x7f765432 -> "
        "0x00214000. SEW 32 and 64.",
    )
    for w in (32, 64):
        e, f_, bias, _ = FMTS[w]
        a = []
        for ex in (2 * bias - 1, 2 * bias):
            for idx in (0, 64, 127):
                a.append((ex << f_) | (idx << (f_ - 7)) | t.rand(f_ - 7))
        a.append((1 << (w - 1)) | ((2 * bias) << f_) | (5 << (f_ - 7)))
        if w == 32:
            a.append(0x7F765432)
        farith(
            t,
            "vfrec7.v {vd}, {vs2}{vm}",
            sew=w,
            a=a,
            kind="none",
            f=lambda x, y, o, ww=w: rc7(x, ww, 0),
            desc=f"vfrec7.v subnormal outputs e{w}",
        )
    out_.append(t)

    def fmm(x: int, y: int, w: int, mx: bool) -> tuple[int, int]:
        if MUT == "vfmin_nan_prop" and not mx and (FISNAN(x, w) or FISNAN(y, w)):
            return CNAN[w], fminmax(x, y, w, mx)[1]
        if MUT == "vfmin_zero_order" and not mx and x & ~(1 << (w - 1)) == 0 and y & ~(1 << (w - 1)) == 0:
            return x, 0
        return fminmax(x, y, w, mx)

    t = new(
        "vfmin_vfmax_op",
        "vfmin/vfmax are IEEE 754-2019 minimumNumber/maximumNumber: -0 < +0 (both operand orders), a single "
        "NaN operand gives the other operand, two NaNs give the canonical NaN, an sNaN raises NV, ordinary "
        "values. .vv and .vf at SEW 32 and 64.",
    )
    for w in (32, 64):
        a = [fpzero(w, True), fpzero(w), qnan(w, 7), F(1.0, w), snan(w), qnan(w), F(-2.0, w), fpinf(w, True)]
        bb = [fpzero(w), fpzero(w, True), F(3.0, w), qnan(w, 9), F(5.0, w), snan(w), F(-3.0, w), F(0.0, w)]
        for mn, mx in (("vfmin", False), ("vfmax", True)):
            farith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                f=lambda x, y, o, ww=w, g=mx: fmm(x, y, ww, g),
                desc=f"{mn}.vv e{w}",
            )
            farith(
                t,
                mn + ".vf {vd}, {vs2}, {fs1}{vm}",
                sew=w,
                a=a,
                kind="vf",
                b=fpzero(w),
                f=lambda x, y, o, ww=w, g=mx: fmm(x, y, ww, g),
                desc=f"{mn}.vf +0 e{w}",
            )
    out_.append(t)

    t = new(
        "vfsgnj_vfsgnjn_vfsgnjx_op",
        "Sign injection: all bits but the sign come from vs2; the sign is vs1's (vfsgnj), its complement "
        "(vfsgnjn) or the XOR of both signs (vfsgnjx). NaN and sNaN vs2 operands keep their payload (no "
        "canonicalization, no NV); .vv and .vf at SEW 32 and 64.",
    )
    for w in (32, 64):
        sb = 1 << (w - 1)
        a = [F(1.5, w), F(-1.5, w), snan(w), qnan(w, 0x15) | sb, fpinf(w), fpzero(w, True)]
        bb = [F(-1.0, w), F(-1.0, w), F(-1.0, w), F(2.0, w), qnan(w) | sb, fpzero(w)]
        fs_ = {
            "vfsgnj": lambda x, y, sb=sb: (x & ~sb) | (y & sb),
            "vfsgnjn": lambda x, y, sb=sb: (x & ~sb) | (~y & sb),
            "vfsgnjx": lambda x, y, sb=sb: x ^ (y & sb),
        }
        for mn, f in fs_.items():
            farith(
                t,
                mn + ".vv {vd}, {vs2}, {vs1}{vm}",
                sew=w,
                a=a,
                b=bb,
                f=lambda x, y, o, g=f: (g(x, y), 0),
                desc=f"{mn}.vv e{w}",
            )
            farith(
                t,
                mn + ".vf {vd}, {vs2}, {fs1}{vm}",
                sew=w,
                a=a,
                kind="vf",
                b=F(-0.0, w),
                f=lambda x, y, o, g=f: (g(x, y), 0),
                desc=f"{mn}.vf -0 e{w}",
            )
    out_.append(t)
    out_ += g_fcmp()
    out_ += g_fmisc()
    return out_


def g_fcmp() -> list[VTest]:
    out_: list[VTest] = []

    def cmpf(op: str, x: int, y: int, w: int) -> tuple[int, int]:
        r, fl = fcmp(x, y, w, op)
        nan = FISNAN(x, w) or FISNAN(y, w)
        if MUT == "vmfeq_qnan_nv" and op == "eq" and nan:
            fl = NV
        if MUT == "vmflt_qnan_quiet" and op == "lt" and nan:
            fl = (
                NV
                if (FISNAN(x, w) and not (x >> (FMT[w][1] - 1)) & 1)
                or (FISNAN(y, w) and not (y >> (FMT[w][1] - 1)) & 1)
                else 0
            )
        if MUT == "vmfne_nan_0" and op == "ne" and nan:
            r = 0
        return r, fl

    def fm(
        t: VTest,
        mn: str,
        w: int,
        a: Sequence[int],
        b: int | Sequence[int],
        kind: str,
        desc: str,
        **kw: Unpack[MresOptions],
    ) -> None:
        op = mn[3:]
        bs = list(cast("Sequence[int]", b)) if kind == "vv" else [cast(int, b)] * len(a)
        mask = kw.get("mask")
        vl = kw.get("vl") or len(a)
        fl = 0
        for i in range(vl):
            if mask is None or mask[i]:
                fl |= cmpf(op, a[i], bs[i], w)[1]
        asm = mn + (".vv {vd}, {vs2}, {vs1}{vm}" if kind == "vv" else ".vf {vd}, {vs2}, {fs1}{vm}")
        mres(
            t,
            asm,
            sew=w,
            a=a,
            b=b,
            kind=kind,
            fn=lambda x, y, g=op, ww=w: cmpf(g, x, y, ww)[0],
            flags=fl,
            desc=desc,
            **kw,
        )

    t = new(
        "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_op",
        "Each FP compare writes its relation (eq, ne, lt, le, gt, ge) for each element into a mask register: "
        "ordered pairs below, equal and above, -0 == +0, infinities. .vv for vmfeq/vmfne/vmflt/vmfle and .vf for "
        "all six, SEW 32 and 64.",
    )
    for w in (32, 64):
        a = [F(1.0, w), F(2.0, w), F(3.0, w), fpzero(w, True), fpinf(w, True), fpinf(w), F(-1.0, w), F(2.0, w)]
        bb = [F(2.0, w), F(2.0, w), F(2.0, w), fpzero(w), F(0.0, w), fpinf(w), F(-2.0, w), F(-2.0, w)]
        for mn in ("vmfeq", "vmfne", "vmflt", "vmfle"):
            fm(t, mn, w, a, bb, "vv", f"{mn}.vv e{w}")
        for mn in ("vmfeq", "vmfne", "vmflt", "vmfle", "vmfgt", "vmfge"):
            fm(t, mn, w, a, F(2.0, w), "vf", f"{mn}.vf 2.0 e{w}")
    out_.append(t)

    t = new(
        "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_vd_single_vreg",
        "The FP compare result is a single mask register even for LMUL = 8: vmflt.vv at e32/m8 with vl = 32 "
        "(the VLEN=128 VLMAX) writes bits 0-31 of v8, and v9 (the next register) is unchanged.",
    )
    n = 32
    a = [F(float(i), 32) for i in range(n)]
    bb = [F(float(15 - (i % 16)), 32) for i in range(n)]
    t.vload("v9", 32, [0x13579BDF] * 4)
    old = [t.rand(1) for _ in range(n)]
    lab = t.op(
        f"vmflt.vv {VD}, {VS2}, {VS1}",
        sew=32,
        lmul="8",
        vl=n,
        srcs={VD: (1, "1", old), VS2: (32, "8", a), VS1: (32, "8", bb)},
    )
    t.check_mask(VD, [cmpf("lt", a[i], bb[i], 32)[0] for i in range(n)], lab, "vmflt.vv e32 m8 vl=32 into v8")
    t.check_vreg("v9", 32, [0x13579BDF] * 4, lab, "v9 unchanged")
    out_.append(t)

    t = new(
        "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_vd_eq_v0",
        "A masked FP compare may write v0, its own mask register: vmfle.vv v0, v16, v24, v0.t and vmfgt.vf "
        "v0, v16, f1, v0.t write the active elements and keep the inactive v0 bits (mu).",
    )
    a = [F(1.0, 32), F(2.0, 32), F(3.0, 32), F(4.0, 32), F(5.0, 32), F(6.0, 32)]
    bb = [F(2.0, 32), F(2.0, 32), F(2.0, 32), F(9.0, 32), F(1.0, 32), F(6.0, 32)]
    fm(t, "vmfle", 32, a, bb, "vv", "vmfle.vv v0, v16, v24, v0.t", vd="v0", mask=[1, 0, 1, 1, 0, 1])
    fm(t, "vmfgt", 32, a, F(2.5, 32), "vf", "vmfgt.vf v0, v16, f1, v0.t", vd="v0", mask=[0, 1, 1, 1, 0, 1])
    out_.append(t)

    t = new(
        "vmfeq_vmfne_vmflt_vmfle_vmfgt_vmfge_tail_agnostic",
        "FP compares write mask registers and always use a tail-agnostic policy: with old tail bits 1 and tail "
        "elements whose compare is true, a tail bit must stay 1 (it may keep its old value, become 1, or take its "
        "element's result); vl = 3 of 8, vta = 0 and 1.",
    )
    for ta in (False, True):
        a = [F(1.0, 32)] * 8
        old = [0, 0, 0] + [1] * 5
        exp = [1, 1, 1] + ([0] * 5 if MUT == "mask_tail_zero" else [1] * 5)
        lab = t.op(
            f"vmfeq.vv {VD}, {VS2}, {VS1}",
            sew=32,
            vl=3,
            ta=ta,
            srcs={VD: (1, "1", old), VS2: (32, "2", a), VS1: (32, "2", a)},
        )
        t.check_mask(VD, exp, lab, f"vmfeq.vv vl=3 {'ta' if ta else 'tu'}: tail bits stay 1")
    out_.append(t)

    t = new(
        "vmfeq_vmfne_snan_invalid",
        "vmfeq and vmfne raise NV only for a signaling NaN operand: a quiet NaN in either position sets no flag, "
        "an sNaN in either position sets NV; .vv and .vf, SEW 32 and 64.",
    )
    for w in (32, 64):
        for mn in ("vmfeq", "vmfne"):
            for a, bb in (([qnan(w), F(1.0, w)], [F(1.0, w), qnan(w)]), ([snan(w), F(1.0, w)], [F(1.0, w), snan(w)])):
                fm(t, mn, w, a, bb, "vv", f"{mn}.vv e{w}")
            fm(t, mn, w, [F(1.0, w), qnan(w)], qnan(w), "vf", f"{mn}.vf qNaN e{w}")
            fm(t, mn, w, [F(1.0, w)], snan(w), "vf", f"{mn}.vf sNaN e{w}")
    out_.append(t)

    t = new(
        "vmflt_vmfle_vmfgt_vmfge_sqnan_invalid",
        "vmflt, vmfle, vmfgt and vmfge raise NV for any NaN operand, quiet or signaling, in either position; "
        ".vv (vmflt, vmfle) and .vf (all four), SEW 32 and 64.",
    )
    for w in (32, 64):
        for mn in ("vmflt", "vmfle"):
            for a, bb in (([qnan(w)], [F(1.0, w)]), ([F(1.0, w)], [qnan(w)]), ([snan(w)], [F(1.0, w)])):
                fm(t, mn, w, a, bb, "vv", f"{mn}.vv e{w}")
        for mn in ("vmflt", "vmfle", "vmfgt", "vmfge"):
            fm(t, mn, w, [F(1.0, w)], qnan(w), "vf", f"{mn}.vf qNaN e{w}")
            fm(t, mn, w, [qnan(w)], F(1.0, w), "vf", f"{mn}.vf qNaN vs2 e{w}")
    out_.append(t)

    t = new(
        "vmfne_vdval1_nan",
        "vmfne writes 1 when either operand is NaN (quiet or signaling, either position, both NaN, NaN against "
        "itself), .vv and .vf, SEW 32 and 64.",
    )
    for w in (32, 64):
        a = [qnan(w), F(1.0, w), qnan(w), snan(w), qnan(w, 3)]
        bb = [F(1.0, w), qnan(w), qnan(w), F(1.0, w), qnan(w, 3)]
        fm(t, "vmfne", w, a, bb, "vv", f"vmfne.vv e{w}")
        fm(t, "vmfne", w, [F(1.0, w), qnan(w)], qnan(w), "vf", f"vmfne.vf qNaN e{w}")
    out_.append(t)

    t = new(
        "vmfeq_vmflt_vmfle_vmfgt_vmfge_vdval0_nan",
        "vmfeq, vmflt, vmfle, vmfgt and vmfge write 0 when either operand is NaN (including NaN compared with "
        "itself and NaN against +/-inf), .vv and .vf, SEW 32 and 64. The old destination bits are 1.",
    )
    for w in (32, 64):
        a = [qnan(w), F(1.0, w), qnan(w), snan(w), fpinf(w)]
        bb = [F(1.0, w), qnan(w), qnan(w), fpinf(w, True), qnan(w)]
        for mn in ("vmfeq", "vmflt", "vmfle"):
            fm(t, mn, w, a, bb, "vv", f"{mn}.vv e{w}", old=[1] * 5)
        for mn in ("vmfeq", "vmflt", "vmfle", "vmfgt", "vmfge"):
            fm(t, mn, w, [F(1.0, w), qnan(w)], qnan(w), "vf", f"{mn}.vf qNaN e{w}", old=[1, 1])
    out_.append(t)
    return out_


def g_fmisc() -> list[VTest]:
    out_: list[VTest] = []

    def cls(x: int, w: int) -> int:
        c = fclass(x, w)
        if MUT == "vfclass_snan_qnan" and c in (1 << 8, 1 << 9):
            c ^= 0x300
        return c

    def clsvals(w: int) -> list[int]:
        _e, _f, _bias, _ = FMTS[w]
        sb = 1 << (w - 1)
        return [
            fpinf(w, True),
            sb | F(1.0, w) & ~sb,
            sb | 1,
            fpzero(w, True),
            fpzero(w),
            1,
            F(1.0, w),
            fpinf(w),
            snan(w),
            qnan(w),
        ]

    for rule, plan in (
        (
            "vfclass_op",
            (
                "vfclass.v classifies like the scalar fclass: one input of each of the 10 classes (-inf, "
                "-normal, -subnormal, -0, +0, +subnormal, +normal, +inf, sNaN, qNaN) at SEW 32 and 64, masked and unmasked."
            ),
        ),
        (
            "vfclass_op_result",
            (
                "The 10-bit class mask is in the low bits and the upper SEW-10 bits are 0: every "
                "result element is compared in full (the old destination is all ones), at SEW 32 and 64, for all 10 "
                "classes."
            ),
        ),
        (
            "vfclass_sewge16",
            (
                "vfclass.v is defined for SEW >= 16, so its 10-bit result always fits: at SEW 32 and 64 "
                "(and 16 when Zvfh is implemented) each class bit, including bit 9 (qNaN), appears in the element."
            ),
        ),
    ):
        t = new(rule, plan)
        for w in (32, 64):
            a = clsvals(w)
            farith(
                t,
                "vfclass.v {vd}, {vs2}{vm}",
                sew=w,
                a=a,
                kind="none",
                old=[ones(w)] * 10,
                f=lambda x, y, o, ww=w: (cls(x, ww), 0),
                desc=f"vfclass.v e{w}",
            )
            if rule == "vfclass_op":
                farith(
                    t,
                    "vfclass.v {vd}, {vs2}{vm}",
                    sew=w,
                    a=a,
                    kind="none",
                    mask=[1, 0] * 5,
                    f=lambda x, y, o, ww=w: (cls(x, ww), 0),
                    desc=f"vfclass.v e{w} masked",
                )
        if rule == "vfclass_sewge16":
            with t.only_if("defined(ZVFH_SUPPORTED)"):
                t.emit(".option push", 0)
                t.emit(".option arch, +zvfh", 0)
                a = [0xFC00, 0xBC00, 0x8001, 0x8000, 0x0000, 0x0001, 0x3C00, 0x7C00, 0x7C01, 0x7E00]
                old = [0xFFFF] * 10
                lab = t.op(f"vfclass.v {VD}, {VS2}", sew=16, vl=10, srcs={VD: (16, "2", old), VS2: (16, "2", a)})
                t.check_vreg(VD, 16, [1 << i for i in range(10)], lab, "vfclass.v e16 (Zvfh)", "2")
                t.emit(".option pop", 0)
        out_.append(t)

    def merge_t(rule: str, plan: str, mas: tuple[bool, ...]) -> VTest:
        t = new(rule, plan)
        for w in (32, 64):
            a = [F(float(i + 1), w) for i in range(8)]
            v0 = [1, 0, 0, 1, 1, 0, 1, 0]
            for ma in mas:
                old = rnd(t, w, 8)
                fv = F(-7.5, w)
                exp = [(fv if v0[i] else a[i]) if i < 6 else old[i] for i in range(8)]
                if MUT == "vfmerge_masked_policy" and ma:
                    exp = [ones(w) if i < 6 and not v0[i] else exp[i] for i in range(8)]
                t.fload("f1", fv, w)
                lab = t.op(
                    f"vfmerge.vfm {VD}, {VS2}, f1, v0",
                    sew=w,
                    vl=6,
                    ma=ma,
                    mask=v0,
                    srcs={VD: (w, "1", old), VS2: (w, "1", a)},
                )
                t.check_vreg(VD, w, exp, lab, f"vfmerge.vfm e{w} vl=6 {'ma' if ma else 'mu'}")
        if rule == "vfmerge_op":
            a = [F(1.0, 32)] * 4
            old = rnd(t, 32, 4)
            t.fload("f1", 0x123456783F800000, 64)
            lab = t.op(
                f"vfmerge.vfm {VD}, {VS2}, f1, v0",
                sew=32,
                vl=4,
                mask=[1, 1, 0, 0],
                srcs={VD: (32, "1", old), VS2: (32, "1", a)},
            )
            t.check_vreg(
                VD,
                32,
                [CNAN[32], CNAN[32], a[2], a[3]],
                lab,
                "vfmerge.vfm e32 with a non-NaN-boxed f1: the canonical NaN is merged",
            )
        return t

    out_.append(
        merge_t(
            "vfmerge_op",
            "vfmerge.vfm at SEW 32 and 64: elements with v0 = 1 get f[rs1] and the others "
            "vs2; tail elements (vl = 6 of 8, tu) are undisturbed. An f register that is not NaN-boxed "
            "(SEW 32) supplies the canonical NaN.",
            (False,),
        )
    )
    out_.append(
        merge_t(
            "vfmerge_all_elem",
            "vfmerge writes every body element whatever the mask: elements with v0 = 0 "
            "get vs2[i], not their old value and not ones under vma = 1; tail elements (vl = 6 of 8, tu) "
            "are undisturbed. SEW 32 and 64.",
            (False, True),
        )
    )
    out_.append(
        merge_t(
            "vfmerge_op_mask",
            "Mask 0 copies vs2[i], mask 1 copies f[rs1], for a v0 pattern that differs "
            "per element, SEW 32 and 64, vma = 0 and 1.",
            (False, True),
        )
    )

    t = new(
        "vfmv_op",
        "vfmv.v.f splats f[rs1] to every body element (unmasked); tail elements are undisturbed (tu) or old/ones "
        "(ta). SEW 32 and 64; an f register that is not NaN-boxed (SEW 32) splats the canonical NaN; LMUL 2.",
    )
    for w in (32, 64):
        for ta in (False, True):
            old = rnd(t, w, 4)
            fv = F(-0.0, w) if ta else snan(w)
            t.fload("f1", fv, w)
            lab = t.op(f"vfmv.v.f {VD}, f1", sew=w, vl=3, ta=ta, srcs={VD: (w, "1", old)})
            t.check_vreg(VD, w, pol(old, [fv] * 4, 3, w, ta=ta), lab, f"vfmv.v.f e{w} vl=3 {'ta' if ta else 'tu'}")
    old = rnd(t, 32, 8)
    t.fload("f1", 0x000000003F800000, 64)
    lab = t.op(f"vfmv.v.f {VD}, f1", sew=32, lmul="2", vl=8, srcs={VD: (32, "2", old)})
    t.check_vreg(VD, 32, [CNAN[32]] * 8, lab, "vfmv.v.f e32 m2 with a non-NaN-boxed f1", "2")
    out_.append(t)

    # ---- conversions
    def cvt(mn: str, x: int, w: int, rm: int) -> tuple[int, int]:
        rtz = ".rtz." in mn
        if MUT == "vfcvt_rtz_uses_frm":
            rtz = False
        r = RTZ if rtz else rm
        if mn.endswith("xu.f.v"):
            return f2i(x, w, w, False, r)
        if mn.endswith("x.f.v"):
            res = f2i(x, w, w, True, r)
            if MUT == "vfcvt_nan_min" and FISNAN(x, w):
                return 1 << (w - 1), res[1]
            return res
        if mn.endswith("f.xu.v"):
            return i2f(x, w, False, w, r)
        return i2f(x, w, True, w, r)

    t = new(
        "vfcvt_op",
        "Single-width conversions, SEW to SEW: vfcvt.xu.f.v and vfcvt.x.f.v (float to unsigned/signed integer), "
        "their .rtz forms, vfcvt.f.xu.v and vfcvt.f.x.v (integer to float). Values whose result differs between "
        "signed and unsigned (-1.0, 2^31 at SEW 32, 0xffffffff), at SEW 32 and 64.",
    )
    mns = ("vfcvt.xu.f.v", "vfcvt.x.f.v", "vfcvt.rtz.xu.f.v", "vfcvt.rtz.x.f.v", "vfcvt.f.xu.v", "vfcvt.f.x.v")
    for w in (32, 64):
        fvals = [F(1.0, w), F(-1.0, w), F(2.0 ** (w - 1), w), F(3.75, w), F(-3.75, w)]
        ivals = [1, ones(w), 1 << (w - 1), 7, (1 << (w - 1)) - 1]
        for mn in mns:
            a = ivals if mn.startswith("vfcvt.f.") else fvals
            farith(
                t,
                mn + " {vd}, {vs2}{vm}",
                sew=w,
                a=a,
                kind="none",
                f=lambda x, y, o, g=mn, ww=w: cvt(g, x, ww, 0),
                desc=f"{mn} e{w}",
            )
    out_.append(t)

    t = new(
        "vfcvt_op_exceptions",
        "Conversions follow the scalar rules for exceptional inputs: NaN -> largest integer (2^SEW-1 unsigned, "
        "2^(SEW-1)-1 signed) with NV; +inf/-inf and out-of-range values saturate with NV; a negative value to "
        "unsigned gives 0 with NV unless it rounds to 0 (-0.5 under rne gives 0 with only NX); inexact "
        "conversions raise NX; integer to float conversions that round raise NX. SEW 32 and 64.",
    )
    for w in (32, 64):
        fvals = [
            qnan(w),
            snan(w),
            fpinf(w),
            fpinf(w, True),
            F(2.0**w, w),
            F(-(2.0**w), w),
            F(-0.5, w),
            F(-1.0, w),
            F(0.5, w),
        ]
        ivals = [ones(w), (1 << (w - 1)) + 1, (1 << (w - 1)) - 1]
        for mn in mns:
            a = ivals if mn.startswith("vfcvt.f.") else fvals
            farith(
                t,
                mn + " {vd}, {vs2}{vm}",
                sew=w,
                a=a,
                kind="none",
                f=lambda x, y, o, g=mn, ww=w: cvt(g, x, ww, 0),
                desc=f"{mn} e{w} exceptional inputs",
            )
    out_.append(t)

    t = new(
        "vfcvt_op_frm",
        "Conversions round with frm except the .rtz forms, which truncate: 2.5 and -2.5 (and 2.25) to integer "
        "under each of rne, rtz, rdn, rup, rmm; the .rtz forms under rup and rmm still truncate; integer to float "
        "of 2^24 + 1 (SEW 32) and 2^53 + 1 (SEW 64) rounds by frm.",
    )
    for w in (32, 64):
        fvals = [F(2.5, w), F(-2.5, w), F(2.25, w), F(-3.5, w)]
        ivals = [(1 << FMT_P[w]) + 1, (1 << FMT_P[w]) + 3, m(-((1 << FMT_P[w]) + 1), w)]
        for rm in range(5):
            for mn in mns:
                a = ivals if mn.startswith("vfcvt.f.") else fvals
                farith(
                    t,
                    mn + " {vd}, {vs2}{vm}",
                    sew=w,
                    a=a,
                    kind="none",
                    frm=rm,
                    f=lambda x, y, o, g=mn, ww=w, r=rm: cvt(g, x, ww, r),
                    desc=f"{mn} e{w} {FRM[rm]}",
                )
    out_.append(t)

    t = new(
        "vfwcvt_op",
        "Widening conversions (SEW -> 2*SEW): float to unsigned/signed integer (and .rtz), unsigned/signed "
        "integer to float, and float to float. At SEW 32: 3e9-style values that need 64-bit integers, -1.0 to "
        "unsigned (NV, 0), 0xffffffff as unsigned and signed, 1 + 2^-23 and subnormals widened exactly, sNaN to "
        "canonical NaN with NV, +/-inf.",
    )
    fv = [
        F(2.0**33 + 0.5, 32) if False else F(2.0**33, 32),
        F(-1.0, 32),
        F(3.5, 32),
        F(-2.5, 32),
        qnan(32),
        fpinf(32, True),
    ]
    iv = [ones(32), 1 << 31, 7]
    wmns = {
        "vfwcvt.xu.f.v": lambda x, r: f2i(x, 32, 64, False, r),
        "vfwcvt.x.f.v": lambda x, r: f2i(x, 32, 64, True, r),
        "vfwcvt.rtz.xu.f.v": lambda x, r: f2i(x, 32, 64, False, RTZ if MUT != "vfcvt_rtz_uses_frm" else r),
        "vfwcvt.rtz.x.f.v": lambda x, r: f2i(x, 32, 64, True, RTZ if MUT != "vfcvt_rtz_uses_frm" else r),
        "vfwcvt.f.xu.v": lambda x, r: i2f(x, 32, False, 64, r),
        "vfwcvt.f.x.v": lambda x, r: i2f(x, 32, True, 64, r),
        "vfwcvt.f.f.v": lambda x, r: fcvt_ff(x, 32, 64, r),
    }
    for mn, f in wmns.items():
        if mn == "vfwcvt.f.f.v":
            a = [F(1 + Fr(1, 2**23), 32), 1, snan(32), fpinf(32), fpzero(32, True), qnan(32, 0x123)]
        elif ".f.x" in mn:
            a = iv
        else:
            a = fv
        for rm in (0, 3):
            farith(
                t,
                mn + " {vd}, {vs2}{vm}",
                sew=32,
                a=a,
                kind="none",
                deew=64,
                frm=rm,
                f=lambda x, y, o, g=f, r=rm: g(x, r),
                desc=f"{mn} e32 {FRM[rm]}",
            )
    out_.append(t)

    t = new(
        "vfncvt_op",
        "Narrowing conversions (2*SEW -> SEW): float to unsigned/signed integer (and .rtz) with saturation, "
        "integer to float with rounding, float to float with rounding and overflow, and vfncvt.rod.f.f.w "
        "(round to odd: 1 + 2^-30 becomes 1 + 2^-23 since the result is inexact; values beyond the binary32 "
        "range become the largest finite value with the same sign). At SEW 32 under rne and rup.",
    )

    def rodcvt(x: int, r: int) -> tuple[int, int]:
        if MUT == "vfncvt_rod_rne":
            return fcvt_ff(x, 64, 32, 0)
        return fcvt_ff(x, 64, 32, r, rod=True)

    nmns = {
        "vfncvt.xu.f.w": lambda x, r: f2i(x, 64, 32, False, r),
        "vfncvt.x.f.w": lambda x, r: f2i(x, 64, 32, True, r),
        "vfncvt.rtz.xu.f.w": lambda x, r: f2i(x, 64, 32, False, RTZ if MUT != "vfcvt_rtz_uses_frm" else r),
        "vfncvt.rtz.x.f.w": lambda x, r: f2i(x, 64, 32, True, RTZ if MUT != "vfcvt_rtz_uses_frm" else r),
        "vfncvt.f.xu.w": lambda x, r: i2f(x, 64, False, 32, r),
        "vfncvt.f.x.w": lambda x, r: i2f(x, 64, True, 32, r),
        "vfncvt.f.f.w": lambda x, r: fcvt_ff(x, 64, 32, r),
        "vfncvt.rod.f.f.w": rodcvt,
    }
    for mn, f in nmns.items():
        if ".f.f." in mn:
            a = [
                F(1 + Fr(1, 2**30), 64),
                F(1 + Fr(3, 2**25), 64),
                F(2.0**200, 64),
                F(-(2.0**200), 64),
                F(2.0**-140, 64),
                snan(64),
                fpinf(64, True),
            ]
        elif ".f.x" in mn:
            a = [(1 << 24) + 1, ones(64), 1 << 63, (1 << 40) + 3]
        else:
            a = [F(2.0**32, 64), F(-1.0, 64), F(3.5, 64), F(-(2.0**31), 64), F(2.0**31, 64), qnan(64)]
        for rm in (0, 3):
            farith(
                t,
                mn + " {vd}, {vs2}{vm}",
                sew=32,
                a=a,
                kind="none",
                aeew=64,
                frm=rm,
                f=lambda x, y, o, g=f, r=rm: g(x, r),
                desc=f"{mn} e32 {FRM[rm]}",
            )
    out_.append(t)
    return out_


# ==================================================================== reductions
def red(
    t: VTest,
    mn: str,
    *,
    sew: int,
    a: Sequence[int],
    s0: int,
    fn: Callable[[list[int], int], object],
    mask: Sequence[int] | None = None,
    vl: int | None = None,
    ta: bool = False,
    wide: bool = False,
    frm: int | None = None,
    flags: object = None,
    desc: str = "",
    vd: str = VD,
    vs1: str = VS1,
    lmul: str | None = None,
    nvd: int = 4,
    window: object = None,
) -> str:
    """A reduction mn.vs vd, vs2, vs1[, v0.t]: vs2 = a, vs1[0] = s0. fn(active elements, s0) -> vd[0] legal value(s).
    vd[1..nvd-1] are tail elements (tu: undisturbed, ta: old or ones); with vl = 0 nothing is written."""
    n = len(a)
    vlv = vl if vl is not None else n
    deew = 2 * sew if wide else sew
    lmul = lmul or auto_lmul(n, sew)
    nvd = min(nvd, 128 // deew)  # vd and vs1 are single registers
    old = rnd(t, deew, nvd)
    s1 = [s0] + rnd(t, deew, 1)
    act = [a[i] for i in range(min(vlv, n)) if mask is None or mask[i]]
    r = fn(act, s0)
    if vlv == 0:
        legal: list = [m(o, deew) for o in old]
        if MUT == "red_vl0_writes":
            legal[0] = s0
    else:
        legal = [r] + pol(old[1:], old[1:], 0, deew, ta=ta)
    srcs = {vd: (deew, "1", old), VS2: (sew, lmul, a), vs1: (deew, "1", s1)}
    asm = f"{mn}.vs {vd}, {VS2}, {vs1}" + (", v0.t" if mask is not None else "")
    if window is None:
        lab = t.op(asm, sew=sew, lmul=lmul, vl=vlv, ta=ta, srcs=srcs, mask=mask, frm=frm, clear_flags=flags is not None)
    else:
        if mask is not None:
            t.mload("v0", mask)
        for vr, (eew, emul, vals) in srcs.items():
            t.vload(vr, eew, vals, emul)
        if frm is not None:
            t.set_frm(frm)
            t.clear_fflags()
        t.vset(vlv, sew, lmul, ta)
        lab = t.ill_window([asm], window, desc)
    if flags is not None:
        t.check_fflags(flags, lab, desc)  # type: ignore[arg-type]
    t.check_vreg(vd, deew, legal, lab, desc)
    return lab


def ired(mn: str, w: int) -> Callable[[list[int], int], int]:
    def f(xs: list[int], s0: int) -> int:
        acc = s0
        for x in xs:
            if mn == "vredsum":
                acc = m(acc + x, w)
            elif mn == "vredmaxu":
                acc = max(acc, x) if MUT != "vredmaxu_signed" else m(max(s(acc, w), s(x, w)), w)
            elif mn == "vredmax":
                acc = m(max(s(acc, w), s(x, w)), w)
            elif mn == "vredminu":
                acc = min(acc, x)
            elif mn == "vredmin":
                acc = m(min(s(acc, w), s(x, w)), w)
            elif mn == "vredand":
                acc &= x
            elif mn == "vredor":
                acc |= x
            else:
                acc ^= x
        return acc

    return f


def wred(signed: bool, w: int) -> Callable[[list[int], int], int]:
    def f(xs: list[int], s0: int) -> int:
        sg = signed and MUT != "vwredsum_zext"
        return m(s0 + sum(s(x, w) if sg else x for x in xs), 2 * w)

    return f


def fred_o(w: int, rm: int = 0, wide: bool = False) -> Callable[[list[int], int], tuple[int, int]]:
    def f(xs: list[int], s0: int) -> tuple[int, int]:
        acc, fl = s0, 0
        seq = list(xs)
        if MUT == "vfredosum_unordered" and seq:
            seq = seq[1:] + seq[:1]
        for x in seq:
            xx = fcvt_ff(x, w, 2 * w, 0)[0] if wide else x
            acc, f1 = fadd(acc, xx, 2 * w if wide else w, rm)
            fl |= f1
        return acc, fl

    return f


def fred_mm(w: int, mx: bool) -> Callable[[list[int], int], tuple[int, int]]:
    def f(xs: list[int], s0: int) -> tuple[int, int]:
        acc, fl = s0, 0
        for x in xs:
            if MUT == "vfredmax_nan" and mx and FISNAN(x, w):
                return CNAN[w], NV if (x >> (FMT[w][1] - 1)) & 1 == 0 else 0
            acc, f1 = fminmax(acc, x, w, mx)
            fl |= f1
        return acc, fl

    return f


def g_red() -> list[VTest]:
    out_: list[VTest] = []
    IRED = ("vredsum", "vredmaxu", "vredmax", "vredminu", "vredmin", "vredand", "vredor", "vredxor")

    t = new(
        "vreduction_scalar_def",
        "A reduction combines vs2's active elements with the scalar vs1[0] and writes the scalar result to vd[0]; "
        "vs1's other elements are ignored (vs1[1] is random). vredsum, vredmax and vfredosum at SEW 8, 32 and 64.",
    )
    for sew in (8, 32, 64):
        a = [1, 2, 3, 0x7F]
        red(t, "vredsum", sew=sew, a=a, s0=5, fn=ired("vredsum", sew), desc=f"vredsum.vs e{sew}")
        red(t, "vredmax", sew=sew, a=a, s0=ones(sew), fn=ired("vredmax", sew), desc=f"vredmax.vs e{sew}")
    for w in (32, 64):
        a = [F(1.0, w), F(2.0, w), F(0.5, w)]
        r = fred_o(w)
        red(
            t,
            "vfredosum",
            sew=w,
            a=a,
            s0=F(4.0, w),
            fn=lambda xs, s0, g=r: g(xs, s0)[0],
            flags=0,
            desc=f"vfredosum.vs e{w}",
        )
    out_.append(t)

    t = new(
        "vreduction_scalar_disregard_lmul",
        "The scalar operand and result are element 0 of a single register (EMUL = 1) whatever LMUL is: with "
        "LMUL = 8, vs1 = v25 and vd = v9 (not multiples of 8) are legal and must not trap; only vd[0] is "
        "written (vd[1..3] tail, tu) and v10 (where an LMUL group would extend) is unchanged. vredsum at e32 "
        "with vl = 32 (VLEN=128 VLMAX), vwredsum at e16, vfredmax at e64.",
    )
    for mn, sew, wide, fnr in (
        ("vredsum", 32, False, ired("vredsum", 32)),
        ("vwredsum", 16, True, wred(True, 16)),
        ("vfredmax", 64, False, None),
    ):
        n = 128 * 8 // sew
        a = [F(float(i), 64) for i in range(n)] if mn == "vfredmax" else [t.rand(sew) for _ in range(n)]
        if fnr is None:
            g = fred_mm(64, True)
            fnr = lambda xs, s0, gg=g: gg(xs, s0)[0]
        t.vload("v10", 32, [0x0BADF00D] * 4)
        lab = red(
            t,
            mn,
            sew=sew,
            a=a,
            s0=F(3.5, 64) if mn == "vfredmax" else 7,
            fn=fnr,
            lmul="8",
            wide=wide,
            vd="v9",
            vs1="v25",
            window=2 if MUT == "red_scalar_lmul" else "ok",
            desc=f"{mn}.vs m8 vd=v9 vs1=v25",
        )
        t.check_vreg("v10", 32, [0x0BADF00D] * 4, lab, f"{mn}: v10 unchanged")
    out_.append(t)

    t = new(
        "vreduction_vd_overlap_vs",
        "The reduction destination may overlap its sources, including the mask: vredsum.vs v16, v16, v24 "
        "(vd = vs2), vredor.vs v24, v16, v24 (vd = vs1), vredmaxu.vs v0, v16, v24, v0.t (vd = mask), and "
        "vfredosum.vs v16, v16, v16 (vd = vs1 = vs2). Each executes and writes the reduction of the original "
        "operands to element 0.",
    )
    a = [3, 9, 1, 7]
    t.vload(VS2, 32, a)
    t.vload(VS1, 32, [100, 5])
    t.vset(4, 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vredsum.vs {VS2}, {VS2}, {VS1}")
    t.check_vreg(VS2, 32, [120, 9, 1, 7], lab, "vredsum.vs v16, v16, v24 (tu)")
    t.vload(VS2, 32, a)
    t.vload(VS1, 32, [0x100, 5])
    t.vset(4, 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vredor.vs {VS1}, {VS2}, {VS1}")
    t.check_vreg(VS1, 32, [0x10F, 5], lab, "vredor.vs v24, v16, v24 (tu)")
    t.vload(VS2, 8, [3, 9, 1, 7, 2, 2, 2, 2])
    t.vload(VS1, 8, [4])
    t.mload("v0", [1, 0, 1, 1, 0, 1, 1, 1] + [0] * 8)
    t.vset(8, 8)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vredmaxu.vs v0, {VS2}, {VS1}, v0.t")
    t.check_vreg("v0", 8, [7, 0], lab, "vredmaxu.vs v0, v16, v24, v0.t: v0[0] = 7, v0[1] (tail) unchanged")
    fa = [F(1.0, 32), F(2.0, 32), F(4.0, 32)]
    t.vload(VS2, 32, fa)
    t.vset(3, 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vfredosum.vs {VS2}, {VS2}, {VS2}")
    t.check_vreg(VS2, 32, [F(8.0, 32), fa[1], fa[2]], lab, "vfredosum.vs v16, v16, v16 = 1 + (1 + 2 + 4)")
    out_.append(t)

    t = new(
        "vreduction_scalar_disregard_maskval",
        "Inactive elements are left out of the reduction but the scalar vs1[0] is always included: with every "
        "element masked off the result is vs1[0]; a masked-off element larger (vredmaxu) or smaller (vredminu) "
        "than the rest or a masked-off sNaN (vfredmin) does not affect the result. SEW 8, 32, 64.",
    )
    for sew in (8, 32, 64):
        a = [ones(sew), 1, 2, 3]
        for mn in ("vredsum", "vredmaxu", "vredminu", "vredand"):
            s0 = 0x40
            fnr = ired(mn, sew)
            if MUT == "red_mask_drops_scalar":
                fnr = lambda xs, s0, g=ired(mn, sew): g(xs[1:], xs[0]) if xs else 0  # noqa: B008
            red(t, mn, sew=sew, a=a, s0=s0, fn=fnr, mask=[0, 0, 0, 0], desc=f"{mn}.vs e{sew} all masked off")
            red(t, mn, sew=sew, a=a, s0=s0, fn=fnr, mask=[0, 1, 1, 0], desc=f"{mn}.vs e{sew} mask 0110")
    for w in (32, 64):
        g = fred_mm(w, False)
        red(
            t,
            "vfredmin",
            sew=w,
            a=[snan(w), F(2.0, w), F(-9.0, w)],
            s0=F(1.0, w),
            mask=[0, 1, 0],
            fn=lambda xs, s0, gg=g: gg(xs, s0)[0],
            flags=0,
            desc=f"vfredmin.vs e{w} masked-off sNaN",
        )
        red(
            t,
            "vfredmin",
            sew=w,
            a=[F(-1.0, w), F(2.0, w)],
            s0=qnan(w, 3),
            mask=[0, 0],
            fn=lambda xs, s0, gg=g: gg(xs, s0)[0],
            flags=0,
            desc=f"vfredmin.vs e{w} all masked off (NaN scalar kept)",
        )
    out_.append(t)

    t = new(
        "vreduction_tail_policy",
        "Elements 1..VLEN/SEW-1 of the reduction destination are tail elements: with vta = 0 they keep their "
        "old values, with vta = 1 each keeps its old value or becomes all ones. vredsum, vwredsumu, vfredusum "
        "and vfwredosum at SEW 8/16/32, elements 1-3 checked.",
    )
    for ta in (False, True):
        red(t, "vredsum", sew=8, a=[1, 2, 3, 4], s0=9, fn=ired("vredsum", 8), ta=ta, desc=f"vredsum e8 ta={int(ta)}")
        red(
            t,
            "vwredsumu",
            sew=16,
            a=[1, 2, 3],
            s0=9,
            fn=wred(False, 16),
            wide=True,
            ta=ta,
            desc=f"vwredsumu e16 ta={int(ta)}",
        )
        red(
            t,
            "vfredusum",
            sew=32,
            a=[F(1.0, 32), F(2.0, 32)],
            s0=F(1.0, 32),
            fn=lambda xs, s0: F(4.0, 32),
            ta=ta,
            desc=f"vfredusum e32 ta={int(ta)}",
        )
        red(
            t,
            "vfwredosum",
            sew=32,
            a=[F(1.0, 32), F(2.0, 32)],
            s0=F(1.0, 64),
            fn=lambda xs, s0: F(4.0, 64),
            wide=True,
            ta=ta,
            desc=f"vfwredosum e32 ta={int(ta)}",
        )
    out_.append(t)

    t = new(
        "vreduction_vl_0",
        "With vl = 0 a reduction performs no operation and leaves vd unchanged, even when vd differs from vs1 "
        "(vs1[0] is not copied) and even with vta = 1 (no agnostic update): vredsum, vredmax, vwredsum, "
        "vfredosum, vfredusum, vfredmax, vfwredusum; fflags stays 0 with an sNaN scalar.",
    )
    for ta in (False, True):
        for mn, sew, wide, fn_ in (
            ("vredsum", 32, False, ired("vredsum", 32)),
            ("vredmax", 8, False, ired("vredmax", 8)),
            ("vwredsum", 16, True, wred(True, 16)),
        ):
            red(t, mn, sew=sew, a=[1, 2], s0=0x55, fn=fn_, vl=0, ta=ta, wide=wide, desc=f"{mn}.vs vl=0 ta={int(ta)}")
        for mn, wide in (("vfredosum", False), ("vfredusum", False), ("vfredmax", False), ("vfwredusum", True)):
            red(
                t,
                mn,
                sew=32,
                a=[F(1.0, 32)],
                s0=snan(64 if wide else 32),
                fn=lambda xs, s0: 0,
                vl=0,
                ta=ta,
                wide=wide,
                flags=0,
                desc=f"{mn}.vs vl=0 ta={int(ta)}",
            )
    out_.append(t)

    t = new(
        "vreduction_vstart_n0_ill",
        "Reductions raise illegal-instruction when vstart != 0 (vstart = 1 with vl = 4): vredsum, vredmaxu, "
        "vwredsumu, vfredosum, vfredusum, vfredmin, vfwredosum. xtval is 0 or the instruction bits, and vd is "
        "unchanged.",
    )
    for mn, sew, wide in (
        ("vredsum", 8, False),
        ("vredmaxu", 64, False),
        ("vwredsumu", 16, True),
        ("vfredosum", 32, False),
        ("vfredusum", 64, False),
        ("vfredmin", 32, False),
        ("vfwredosum", 32, True),
    ):
        deew = 2 * sew if wide else sew
        old = rnd(t, deew, 2)
        t.vload(VD, deew, old)
        t.vload(VS2, sew, [1, 2, 3, 4])
        t.vload(VS1, deew, [5])
        t.vset(4, sew)
        t.emit("csrwi vstart, 1")
        lab = t.ill_window(
            [f"{mn}.vs {VD}, {VS2}, {VS1}"], "ok" if MUT == "red_vstart_ok" else 2, f"{mn}.vs with vstart = 1"
        )
        t.emit("csrwi vstart, 0")
        t.check_vreg(VD, deew, old, lab, f"{mn}: vd unchanged")
    out_.append(t)

    t = new(
        "vredsum_vredmaxu_vredmax_vredminu_vredmin_vredand_vredor_vredxor_op",
        "The eight single-width integer reductions, all operands SEW wide: sum, unsigned/signed max and min "
        "(operands with the top bit set so signedness matters), and, or, xor. SEW 8, 16, 32, 64, masked once.",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        a = [hi, 3, hi - 1, ones(sew), 0x55 & ones(sew)]
        for mn in IRED:
            red(t, mn, sew=sew, a=a, s0=hi + 1, fn=ired(mn, sew), desc=f"{mn}.vs e{sew}")
        red(
            t,
            "vredmin",
            sew=sew,
            a=a,
            s0=5,
            fn=ired("vredmin", sew),
            mask=[0, 1, 1, 0, 1],
            desc=f"vredmin.vs e{sew} masked",
        )
    out_.append(t)

    t = new(
        "vredsum_vredmaxu_vredmax_vredminu_vredmin_vredand_vredor_vredxor_overflow",
        "vredsum wraps around on overflow: 0x80 + 0x80 = 0 at SEW 8, MAX + 1 = MIN, all-ones elements summed "
        "with 1, at SEW 8, 16, 32, 64.",
    )
    for sew in (8, 16, 32, 64):
        hi = 1 << (sew - 1)
        red(t, "vredsum", sew=sew, a=[hi, hi], s0=0, fn=ired("vredsum", sew), desc=f"vredsum e{sew} MIN + MIN")
        red(t, "vredsum", sew=sew, a=[hi - 1], s0=1, fn=ired("vredsum", sew), desc=f"vredsum e{sew} MAX + 1")
        red(t, "vredsum", sew=sew, a=[ones(sew)] * 3, s0=1, fn=ired("vredsum", sew), desc=f"vredsum e{sew} -3 + 1")
    out_.append(t)

    t = new(
        "vwredsumu_op",
        "vwredsumu zero-extends each SEW element, sums, and adds the 2*SEW scalar into a 2*SEW result: four "
        "all-ones elements give 4*(2^SEW-1) + scalar (not -4). SEW 8, 16, 32, masked once.",
    )
    for sew in (8, 16, 32):
        red(t, "vwredsumu", sew=sew, a=[ones(sew)] * 4, s0=1, fn=wred(False, sew), wide=True, desc=f"vwredsumu e{sew}")
        red(
            t,
            "vwredsumu",
            sew=sew,
            a=[ones(sew), 1 << (sew - 1), 2],
            s0=1 << sew,
            fn=wred(False, sew),
            wide=True,
            mask=[1, 1, 0],
            desc=f"vwredsumu e{sew} masked",
        )
    out_.append(t)

    t = new(
        "vwredsum_op",
        "vwredsum sign-extends each SEW element before summing into the 2*SEW scalar: four all-ones elements "
        "give scalar - 4, MIN elements give negative 2*SEW sums. SEW 8, 16, 32.",
    )
    for sew in (8, 16, 32):
        red(t, "vwredsum", sew=sew, a=[ones(sew)] * 4, s0=1, fn=wred(True, sew), wide=True, desc=f"vwredsum e{sew}")
        red(
            t,
            "vwredsum",
            sew=sew,
            a=[1 << (sew - 1), 1 << (sew - 1), 5],
            s0=0,
            fn=wred(True, sew),
            wide=True,
            desc=f"vwredsum e{sew} MIN + MIN + 5",
        )
    out_.append(t)

    t = new(
        "vwredsumu_vwredsum_op_overflow",
        "Widening sums wrap around at 2*SEW: vwredsumu with scalar 2^(2*SEW)-1 plus 1 gives 0; vwredsum with "
        "scalar MAX(2*SEW) plus 1 gives MIN(2*SEW); vwredsum with scalar MIN(2*SEW) plus -1 gives MAX. SEW 8, "
        "16, 32.",
    )
    for sew in (8, 16, 32):
        W = 2 * sew
        red(t, "vwredsumu", sew=sew, a=[1], s0=ones(W), fn=wred(False, sew), wide=True, desc=f"vwredsumu e{sew}")
        red(
            t,
            "vwredsum",
            sew=sew,
            a=[1],
            s0=(1 << (W - 1)) - 1,
            fn=wred(True, sew),
            wide=True,
            desc=f"vwredsum e{sew} MAX + 1",
        )
        red(
            t,
            "vwredsum",
            sew=sew,
            a=[ones(sew)],
            s0=1 << (W - 1),
            fn=wred(True, sew),
            wide=True,
            desc=f"vwredsum e{sew} MIN - 1",
        )
    out_.append(t)

    t = new(
        "vfredosum_op",
        "vfredosum adds in element order starting from vs1[0]: (((s + a0) + a1) + a2) + a3 with s = 1, "
        "a = [2^24, -2^24, 1, 1] at SEW 32 gives 2 (1 + 2^24 rounds to 2^24); any other order gives 1, 3 or 4 "
        "(and similarly with 2^53 at SEW 64). Under rne and rup.",
    )
    for w in (32, 64):
        P = FMT_P[w]
        a = [F(2**P, w), F(-(2**P), w), F(1.0, w), F(1.0, w)]
        for rm in (0, 3):
            r = fred_o(w, rm)
            red(
                t,
                "vfredosum",
                sew=w,
                a=a,
                s0=F(1.0, w),
                fn=lambda xs, s0, g=r: g(xs, s0)[0],
                frm=rm,
                flags=r([x for x in a], F(1.0, w))[1],
                desc=f"vfredosum e{w} {FRM[rm]}",
            )
    out_.append(t)

    t = new(
        "vfredosum_op_exceptions",
        "Each addition of vfredosum behaves like the scalar fadd for flags and special values: +inf + -inf -> "
        "canonical NaN with NV, an sNaN element -> canonical NaN with NV, MAX + MAX -> +inf with OF|NX, an inexact "
        "sum -> NX, a qNaN scalar propagates as the canonical NaN without NV. SEW 32 and 64.",
    )
    for w in (32, 64):
        r = fred_o(w)
        for a, s0 in (
            ([fpinf(w), fpinf(w, True)], F(1.0, w)),
            ([F(1.0, w), snan(w)], F(1.0, w)),
            ([fpmax(w)], fpmax(w)),
            ([F(Fr(1, 2**30), w) if w == 32 else F(Fr(1, 2**60), w)], F(1.0, w)),
            ([F(1.0, w)], qnan(w, 9)),
        ):
            res, fl = r(a, s0)
            red(t, "vfredosum", sew=w, a=a, s0=s0, fn=lambda xs, s0, v=res: v, flags=fl, desc=f"vfredosum e{w}")
    out_.append(t)

    t = new(
        "vfredosum_maskoff",
        "Masked-off elements of vfredosum change neither the result nor fflags: a masked-off sNaN (no NV), a "
        "masked-off +inf, a masked-off 2^-30 that would make the SEW-32 sum inexact. With every element masked off, "
        "vs1[0] is copied as is (an sNaN scalar keeps its payload, no NV). SEW 32 and 64; also vfwredosum.",
    )
    for w in (32, 64):
        r = fred_o(w)
        a = [F(1.0, w), snan(w), fpinf(w), F(Fr(1, 2**30), w), F(2.0, w)]
        mask = [1, 0, 0, 0, 1]
        fl = r([a[0], a[4]], F(4.0, w))[1]
        if MUT == "vfredosum_maskoff_flags":
            fl = NV | NX
        red(
            t,
            "vfredosum",
            sew=w,
            a=a,
            s0=F(4.0, w),
            fn=lambda xs, s0, w=w: F(7.0, w),
            mask=mask,
            flags=fl,
            desc=f"vfredosum e{w} masked",
        )
        red(
            t,
            "vfredosum",
            sew=w,
            a=a,
            s0=snan(w),
            fn=lambda xs, s0: s0,
            mask=[0] * 5,
            flags=NV if MUT == "vfredosum_maskoff_flags" else 0,
            desc=f"vfredosum e{w} all masked off, sNaN scalar",
        )
    red(
        t,
        "vfwredosum",
        sew=32,
        a=[snan(32), F(1.0, 32)],
        s0=F(2.0, 64),
        fn=lambda xs, s0: F(3.0, 64),
        mask=[0, 1],
        wide=True,
        flags=0,
        desc="vfwredosum e32 masked-off sNaN",
    )
    out_.append(t)

    t = new(
        "vfredusum_op",
        "vfredusum is any deterministic binary tree of exact-sum-then-round nodes over vs1[0] and the active "
        "elements. Cases whose value every tree gives: small integers (exact in every order), a pair +inf and "
        "-inf among finite elements (NaN with NV whatever the order), one sNaN element (canonical NaN, NV), "
        "masked-off elements (identity or copied, so no effect). SEW 32 and 64. A result that depends on the "
        "order is not checked.",
    )
    for w in (32, 64):
        red(
            t,
            "vfredusum",
            sew=w,
            a=[F(float(i), w) for i in (1, 2, 3, 4, 5)],
            s0=F(10.0, w),
            fn=lambda xs, s0, w=w: F(25.0, w),
            flags=0,
            desc=f"vfredusum e{w} exact integers",
        )
        red(
            t,
            "vfredusum",
            sew=w,
            a=[F(1.0, w), fpinf(w), F(2.0, w), fpinf(w, True)],
            s0=F(1.0, w),
            fn=lambda xs, s0, w=w: CNAN[w],
            flags=NV,
            desc=f"vfredusum e{w} +inf and -inf",
        )
        red(
            t,
            "vfredusum",
            sew=w,
            a=[F(1.0, w), snan(w), F(2.0, w)],
            s0=F(1.0, w),
            fn=lambda xs, s0, w=w: CNAN[w],
            flags=NV,
            desc=f"vfredusum e{w} sNaN element",
        )
        red(
            t,
            "vfredusum",
            sew=w,
            a=[F(1.0, w), fpinf(w), F(2.0, w), snan(w)],
            s0=F(1.0, w),
            mask=[1, 0, 1, 0],
            fn=lambda xs, s0, w=w: F(4.0, w),
            flags=0,
            desc=f"vfredusum e{w} masked-off inf and sNaN",
        )
    out_.append(t)

    t = new(
        "vfredusum_additive_impl",
        "The additive identity for masked-off or past-vl inputs is +0 under rdn and -0 otherwise. Under rne a "
        "scalar -0 with active elements -0 must give -0 (a +0 identity would give +0); under rdn a scalar +0 with "
        "active +0 elements must give +0 (a -0 identity would give -0). Masked-off elements and vl below the "
        "loaded elements; SEW 32 and 64; also vfwredusum.",
    )
    for w in (32, 64):
        for rm, z in ((0, True), (2, False), (3, True), (1, True), (4, True)):
            exp = fpzero(w, z)
            if MUT == "vfredusum_identity_pos" and rm != 2:
                exp = fpzero(w, False)
            red(
                t,
                "vfredusum",
                sew=w,
                a=[fpzero(w, z), F(5.0, w), fpzero(w, z), F(-3.0, w)],
                s0=fpzero(w, z),
                mask=[1, 0, 1, 0],
                frm=rm,
                fn=lambda xs, s0, e=exp: e,
                flags=0,
                desc=f"vfredusum e{w} {FRM[rm]} signed zeros",
            )
            red(
                t,
                "vfredusum",
                sew=w,
                a=[fpzero(w, z), F(5.0, w), fpzero(w, z)],
                s0=fpzero(w, z),
                vl=1,
                frm=rm,
                fn=lambda xs, s0, e=exp: e,
                flags=0,
                desc=f"vfredusum e{w} {FRM[rm]} vl=1",
            )
    exp = fpzero(64, True) if MUT != "vfredusum_identity_pos" else fpzero(64)
    red(
        t,
        "vfwredusum",
        sew=32,
        a=[fpzero(32, True), F(5.0, 32)],
        s0=fpzero(64, True),
        mask=[1, 0],
        frm=0,
        fn=lambda xs, s0: exp,
        flags=0,
        wide=True,
        desc="vfwredusum e32 rne signed zeros",
    )
    out_.append(t)

    t = new(
        "vfredusum_redtree",
        "The vfredusum tree is deterministic for a given vtype and vl: the same order-dependent reduction "
        "(elements 2^24, -2^24, 1, 1, 2^-10 and scalar 1 at SEW 32, whose result depends on the tree) run twice, "
        "and once more after an unrelated vsetvli, gives identical bits and identical fflags.",
    )
    for w in (32, 64):
        P = FMT_P[w]
        a = [F(2**P, w), F(-(2**P), w), F(1.0, w), F(1.0, w), F(Fr(1, 1024), w), F(3.0, w)]
        t.vload(VS2, w, a)
        t.vload(VS1, w, [F(1.0, w)])
        for k in range(3):
            t.clear_fflags()
            t.vset(6, w)
            if k == 2:
                t.emit("vsetivli x0, 3, e8, m1, ta, ma")
                t.vset(6, w)
            lab = t.label("insn")
            t.emit(f"{lab}:", 0)
            t.emit(f"vfredusum.vs {'v8' if k == 0 else 'v12'}, {VS2}, {VS1}")
            t.emit(f"frflags x{6 + k}" if k < 2 else "frflags x9")
            if k > 0:
                t.vset(1, w)
                t.emit("vmv.x.s x8, v8")
                t.emit("vmv.x.s x1, v12")
                t.emit("xor x8, x8, x1")
                if w == 64:
                    with t.rv32_only():
                        t.emit("vsetivli x0, 1, e64, m1, tu, mu")
                        t.emit("vsrl.vx v13, v8, x0")
                        t.li("x1", 32)
                        t.emit("vsrl.vx v13, v8, x1")
                        t.emit("vsrl.vx v14, v12, x1")
                        t.emit("vmv.x.s x1, v13")
                        t.emit("vmv.x.s x5, v14")
                        t.emit("xor x1, x1, x5")
                        t.emit("or x8, x8, x1")
                t.emit("seqz x8, x8")
                t.check_bool("x8", lab, f"vfredusum e{w} run {k + 1} gives the same bits as run 1")
                t.emit(f"xor x1, x6, {'x7' if k == 1 else 'x9'}")
                t.emit("seqz x1, x1")
                t.check_bool("x1", lab, f"vfredusum e{w} run {k + 1} gives the same fflags as run 1")
    out_.append(t)

    t = new(
        "vfredmin_vfredmax_op",
        "vfredmin/vfredmax reduce vs1[0] and the active elements with minimumNumber/maximumNumber: -0 < +0, "
        "qNaN elements are ignored, an sNaN element raises NV and is ignored, all-NaN inputs give the canonical "
        "NaN, the scalar takes part (it can be the result). SEW 32 and 64.",
    )
    for w in (32, 64):
        for mx, mn in ((False, "vfredmin"), (True, "vfredmax")):
            g = fred_mm(w, mx)
            for a, s0 in (
                ([fpzero(w), fpzero(w, True), F(1.0, w)], F(0.5, w)),
                ([qnan(w), F(-3.0, w), snan(w)], F(2.0, w)),
                ([qnan(w), snan(w)], qnan(w, 5)),
                ([F(1.0, w), F(2.0, w)], F(-7.0, w) if not mx else F(7.0, w)),
            ):
                res, fl = g(a, s0)
                red(t, mn, sew=w, a=a, s0=s0, fn=lambda xs, s0, v=res: v, flags=fl, desc=f"{mn}.vs e{w}")
    out_.append(t)

    t = new(
        "vfwredosum_vfwredusum_op",
        "vfwredosum/vfwredusum read SEW elements and a 2*SEW scalar and write a 2*SEW result: at SEW 32, "
        "2^24 + 1 + 1 (scalar 2^24) is exact in binary64 although not in binary32; the result is checked as a "
        "64-bit element.",
    )
    for mn in ("vfwredosum", "vfwredusum"):
        red(
            t,
            mn,
            sew=32,
            a=[F(1.0, 32), F(1.0, 32)],
            s0=F(2**24, 64),
            fn=lambda xs, s0: F(2**24 + 2, 64),
            wide=True,
            flags=0,
            desc=f"{mn} e32",
        )
        red(
            t,
            mn,
            sew=32,
            a=[F(2**30, 32), F(2**30, 32), F(2**30, 32)],
            s0=F(3.0, 64),
            fn=lambda xs, s0: F(3 * 2**30 + 3, 64),
            wide=True,
            flags=0,
            desc=f"{mn} e32 3*2^30 + 3",
        )
    out_.append(t)

    t = new(
        "vfwredosum_vfwredusum_op_reduction",
        "The SEW elements are promoted to 2*SEW before being added to the 2*SEW accumulator: an element "
        "1 + 2^-23 plus scalar 2^20 is exact in binary64 (a binary32 sum would round), an sNaN element still "
        "raises NV (promotion of an sNaN signals), and a binary32 subnormal is promoted exactly. SEW 32, ordered "
        "and unordered.",
    )
    for mn in ("vfwredosum", "vfwredusum"):
        e = F(1 + Fr(1, 2**23), 32)
        red(
            t,
            mn,
            sew=32,
            a=[e],
            s0=F(2**20, 64),
            fn=lambda xs, s0: F(2**20 + 1 + Fr(1, 2**23), 64),
            wide=True,
            flags=0,
            desc=f"{mn} e32 promote 1 + 2^-23",
        )
        red(
            t,
            mn,
            sew=32,
            a=[snan(32)],
            s0=F(1.0, 64),
            fn=lambda xs, s0: CNAN[64],
            wide=True,
            flags=NV,
            desc=f"{mn} e32 sNaN element",
        )
        red(
            t,
            mn,
            sew=32,
            a=[1],
            s0=fpzero(64),
            fn=lambda xs, s0: F(Fr(1, 2**149), 64),
            wide=True,
            flags=0,
            desc=f"{mn} e32 smallest subnormal",
        )
    out_.append(t)
    return out_


# ==================================================================== mask instructions
MLOG = {
    "vmand": lambda a, b: a & b,
    "vmnand": lambda a, b: 1 - (a & b),
    "vmandn": lambda a, b: a & (1 - b),
    "vmxor": lambda a, b: a ^ b,
    "vmor": lambda a, b: a | b,
    "vmnor": lambda a, b: 1 - (a | b),
    "vmorn": lambda a, b: a | (1 - b),
    "vmxnor": lambda a, b: 1 - (a ^ b),
}


def mlog(mn: str, a: int, b: int) -> int:
    if mn == "vmandn" and MUT == "vmandn_swapped":
        return (1 - a) & b
    return MLOG[mn](a, b)


def bits(t: VTest, n: int) -> list[int]:
    return [t.rand(1) for _ in range(n)]


def sbf(kind: str, src: Sequence[int], vl: int, mask: Sequence[int] | None) -> list[int | None]:
    """vmsbf/vmsif/vmsof result for each active element i < vl (None for inactive)."""
    out: list[int | None] = []
    found = False
    for i in range(vl):
        if mask is not None and not mask[i]:
            out.append(None)
            continue
        b = src[i]
        if kind == "sbf":
            v = (
                0
                if (found or b)
                else (
                    0 if MUT == "vmsbf_none_0" and not any(src[j] for j in range(vl) if mask is None or mask[j]) else 1
                )
            )
        elif kind == "sif":
            v = 0 if found else (1 if not (MUT == "vmsif_as_vmsbf" and b) else 0)
        else:
            v = 1 if (b and not found) or (MUT == "vmsof_all_after" and found) else 0
        if b:
            found = True
        out.append(v)
    return out


def g_mask() -> list[VTest]:
    out_: list[VTest] = []

    def mm(
        t: VTest,
        mn: str,
        a: Sequence[int],
        b: Sequence[int],
        vl: int,
        *,
        old: Sequence[int] | None = None,
        vstart: int = 0,
        desc: str = "",
        lmul: str | None = None,
        sew: int = 8,
        vd: str = VD,
        s2: str = VS2,
        s1: str = VS1,
    ) -> str:
        n = len(a)
        old = list(old) if old is not None else bits(t, n)
        calc = [mlog(mn, a[i], b[i]) for i in range(n)]
        legal = mpol(old, calc, vl, vstart=0 if MUT == "mask_vstart_ignored" else vstart, tailcalc=calc)
        srcs: dict = {}
        if vd not in (s2, s1):
            srcs[vd] = (1, "1", old)
        srcs[s2] = (1, "1", a)
        if s1 != s2:
            srcs[s1] = (1, "1", b)
        lab = t.op(f"{mn}.mm {vd}, {s2}, {s1}", sew=sew, lmul=lmul, vl=vl, srcs=srcs, vstart=vstart)
        t.check_mask(vd, legal, lab, desc)
        return lab

    t = new(
        "vmand_vmnand_vmandn_vmxor_vmor_vmnor_vmorn_vmxnor_op",
        "The eight mask-logical operations on bit patterns that contain all four input combinations (vs2, vs1) "
        "in 32 elements, vl = 32: vmand, vmnand, vmandn (vs2 & !vs1), vmxor, vmor, vmnor, vmorn (vs2 | !vs1), "
        "vmxnor; plus the pseudo-instructions vmmv/vmclr/vmset/vmnot as their expansions.",
    )
    a = [(i >> 0) & 1 for i in range(4)] * 8
    b = [(i >> 1) & 1 for i in range(4)] * 8
    for mn in MLOG:
        mm(t, mn, a, b, 32, desc=f"{mn}.mm vl=32")
    mm(t, "vmand", a, a, 32, desc="vmmv.m (vmand vd, vs, vs)", s1=VS2)
    mm(t, "vmnand", b, b, 32, desc="vmnot.m (vmnand vd, vs, vs)", s1=VS2)
    out_.append(t)

    t = new(
        "vmask_maskreg_def",
        "Mask registers hold one bit per element in the mask layout (element i is bit i): vmxor.mm of single-bit "
        "patterns at elements 0, 7, 8, 31, 63, 64 and 127 with vl = 128 (the VLEN=128 VLMAX at e8/m8) sets exactly "
        "those bits; vmor of disjoint byte patterns checks byte boundaries.",
    )
    n = 128
    a = [1 if i in (0, 8, 63, 127) else 0 for i in range(n)]
    b = [1 if i in (7, 31, 64, 127) else 0 for i in range(n)]
    mm(t, "vmxor", a, b, n, desc="vmxor.mm vl=128 single bits", lmul="8")
    a = [1 if i % 16 < 8 else 0 for i in range(n)]
    b = [1 if i % 16 == 15 else 0 for i in range(n)]
    mm(t, "vmor", a, b, n, desc="vmor.mm vl=128 byte patterns", lmul="8")
    out_.append(t)

    t = new(
        "instrgrp_vmask_disregard_vlmul",
        "Mask-logical instructions operate on single registers whatever LMUL is and leave vlmul unchanged: at "
        "e8/m8 with vl = VLMAX (= VLEN bits), vmxnor.mm v9, v17, v25 (registers not aligned to 8) executes, sets "
        "v9's bits, and leaves v10 (the next register) unchanged; vtype reads back the same e8/m8 value.",
    )
    t.vload("v10", 32, [0x0F1E2D3C] * 4)
    t.vset("max", 8, "8", rd="x7")
    t.emit("csrr x6, vtype")
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("vmxnor.mm v9, v9, v9")
    t.emit("csrr x8, vtype")
    t.emit("sub x8, x8, x6")
    t.emit("seqz x8, x8")
    t.check_bool("x8", lab, "vtype unchanged by vmxnor.mm at m8")
    t.check_mask("v9", [1] * 128, lab, "vmset.m v9 at m8: v9 all ones")
    exp_v10 = [0x0F1E2D3C] * 4 if MUT != "mask_lmul_group" else [ones(32)] * 4
    t.check_vreg("v10", 32, exp_v10, lab, "v10 unchanged")
    out_.append(t)

    t = new(
        "vmask_vd_overlap_vs",
        "The mask-logical destination may equal either source: vmand.mm v8, v8, v16, vmor.mm v16, v8, v16, "
        "vmxor.mm v8, v8, v8 (vmclr) and vmxnor.mm v16, v16, v16 (vmset), each computed from the original "
        "operands; vl = 16.",
    )
    a = bits(t, 16)
    b = bits(t, 16)
    mm(t, "vmand", a, b, 16, vd=VD, s2=VD, s1=VS2, old=a, desc="vmand.mm v8, v8, v16")
    a = bits(t, 16)
    b = bits(t, 16)
    mm(t, "vmor", a, b, 16, vd=VS2, s2=VD, s1=VS2, old=b, desc="vmor.mm v16, v8, v16")
    a = bits(t, 16)
    mm(t, "vmxor", a, a, 16, vd=VD, s2=VD, s1=VD, old=a, desc="vmclr.m v8")
    mm(t, "vmxnor", a, a, 16, vd=VS2, s2=VS2, s1=VS2, old=a, desc="vmset.m v16")
    out_.append(t)

    t = new(
        "vmask_vstart",
        "Mask-logical elements below vstart are unchanged and vstart is 0 afterwards: vmor.mm with vstart = 5 "
        "and 9 (vl = 16) on all-ones sources leaves bits 0..vstart-1 at their old 0. A hart may raise "
        "illegal-instruction for a nonzero vstart it never produces (vstart_vtype_dep), so a trap is also "
        "accepted; then vd must be unchanged.",
    )
    for vs in (5, 9):
        old = [0] * 16
        t.vload(VD, 8, [0, 0])
        t.vload(VS2, 8, [0xFF, 0xFF])
        t.vload(VS1, 8, [0xFF, 0xFF])
        t.vset(16, 8)
        t.set_vstart(vs)
        lab = t.ill_window([f"vmor.mm {VD}, {VS2}, {VS1}"], ["ok", 2], f"vmor.mm with vstart = {vs}")
        t.emit("addi x6, x14, 1")
        t.emit("csrr x9, vstart")
        t.emit("csrwi vstart, 0")
        exp = [0 if (i < vs and MUT != "mask_vstart_ignored") else 1 for i in range(16)]

        def ok_path(e: list = exp, lb: str = lab, v: int = vs) -> None:
            t.check("x9", 0, lb, "vstart is 0 after the instruction")
            t.check_mask(VD, e, lb, f"vmor.mm vstart={v}: bits below vstart unchanged")

        def trap_path(lb: str = lab, o: list = old) -> None:
            t.check_mask(VD, o, lb, "vmor.mm trapped: vd unchanged")

        t.either("x6", trap_path, ok_path)
    out_.append(t)

    t = new(
        "vmasklogical_unmasked",
        "Mask-logical instructions are always unmasked: with v0 = 0 every body bit is computed (no inactive "
        "elements, also under vma = 1); vmand.mm and vmorn.mm, vl = 16.",
    )
    for ma in (False, True):
        t.mload("v0", [0] * 16)
        a = bits(t, 16)
        b = bits(t, 16)
        old = [1 - mlog("vmand", a[i], b[i]) for i in range(16)]
        lab = t.op(
            f"vmand.mm {VD}, {VS2}, {VS1}",
            sew=8,
            vl=16,
            ma=ma,
            srcs={VD: (1, "1", old), VS2: (1, "1", a), VS1: (1, "1", b)},
        )
        t.check_mask(VD, [mlog("vmand", a[i], b[i]) for i in range(16)], lab, f"vmand.mm v0=0 ma={int(ma)}")
        lab = t.op(
            f"vmorn.mm {VD}, {VS2}, {VS1}",
            sew=8,
            vl=16,
            ma=ma,
            srcs={VD: (1, "1", old), VS2: (1, "1", a), VS1: (1, "1", b)},
        )
        t.check_mask(VD, [mlog("vmorn", a[i], b[i]) for i in range(16)], lab, f"vmorn.mm v0=0 ma={int(ma)}")
    out_.append(t)

    t = new(
        "vmasklogical_tail_agnostic",
        "Mask-logical tail bits are always agnostic: each may keep its old value, become 1, or take the value "
        "computed for it (the whole register may be written). Old tail bits 1 whose computed value is 1 must stay "
        "1, under vta = 0 and 1; vl = 5 of 32.",
    )
    for ta in (False, True):
        for mn in ("vmand", "vmor", "vmxnor"):
            a = [1] * 32
            b = [1] * 32
            old = [0] * 5 + [1] * 27
            calc = [mlog(mn, 1, 1)] * 32
            exp = mpol(old, calc, 5, tailcalc=calc)
            if MUT == "mask_tail_zero":
                exp = calc[:5] + [0] * 27
            lab = t.op(
                f"{mn}.mm {VD}, {VS2}, {VS1}",
                sew=8,
                vl=5,
                ta=ta,
                srcs={VD: (1, "1", old), VS2: (1, "1", a), VS1: (1, "1", b)},
            )
            t.check_mask(VD, exp, lab, f"{mn}.mm vl=5 ta={int(ta)}")
    out_.append(t)

    # ---- vcpop / vfirst
    def scal(
        t: VTest,
        asm: str,
        src: Sequence[int],
        vl: int,
        expect: object,
        desc: str,
        mask: Sequence[int] | None = None,
        lmul: str = "1",
        sew: int = 8,
    ) -> str:
        t.load("x8", X(0x5A5A5A5A, 0x5A5A5A5A5A5A5A5A))
        lab = t.op(
            asm + (", v0.t" if mask is not None else ""),
            sew=sew,
            lmul=lmul,
            vl=vl,
            mask=mask,
            srcs={VS2: (1, "1", src)},
        )
        t.check("x8", expect, lab, desc)  # type: ignore[arg-type]
        return lab

    def cpop(src: Sequence[int], vl: int, mask: Sequence[int] | None = None) -> int:
        return sum(src[i] for i in range(vl) if mask is None or mask[i])

    def first(src: Sequence[int], vl: int, mask: Sequence[int] | None = None) -> X:
        for i in range(vl):
            if src[i] and (mask is None or mask[i] or MUT == "vfirst_ignores_mask"):
                return X(i, i)
        return X(0, 0) if MUT == "vfirst_none_0" else X(ones(32), ones(64))

    t = new(
        "vcpop_vs_single_vreg",
        "vcpop.m reads a single mask register whatever LMUL is: at e8/m8 with vl = 128 (the VLEN=128 VLMAX), the "
        "source v17 (not 8-aligned) is counted over bits 0-127 and v18 (all ones) is not read; also vs2 = v9 at "
        "e32/m4 with vl = 16.",
    )
    src = [1 if i % 3 == 0 else 0 for i in range(128)]
    t.vload("v18", 8, [0xFF] * 16)
    t.load("x8", 0x5A5A)
    lab = t.op("vcpop.m x8, v17", sew=8, lmul="8", vl=128, srcs={"v17": (1, "1", src)})
    t.check("x8", cpop(src, 128), lab, "vcpop.m e8 m8 vl=128 of v17")
    src = bits(t, 16)
    t.load("x8", 0x5A5A)
    lab = t.op("vcpop.m x8, v9", sew=32, lmul="4", vl=16, srcs={"v9": (1, "1", src)})
    t.check("x8", cpop(src, 16), lab, "vcpop.m e32 m4 vl=16 of v9")
    out_.append(t)

    t = new(
        "vcpop_op",
        "vcpop.m counts the 1 bits among the active elements: all zeros, all ones, a single bit at element vl-1, "
        "bits past vl (not counted), vl = 1, 16, 31 and 64 at SEW 8 and 64 (LMUL chosen so vl fits).",
    )
    for vl, sew in ((1, 8), (16, 8), (31, 8), (64, 8), (16, 64)):
        for src in ([0] * 64, [1] * 64, [0] * (vl - 1) + [1] + [1] * (64 - vl), bits(t, 64)):
            scal(
                t,
                "vcpop.m x8, v16",
                src,
                vl,
                cpop(src, vl),
                f"vcpop.m vl={vl} e{sew}",
                sew=sew,
                lmul="8" if sew == 64 or vl > 16 else "1",
            )
    out_.append(t)

    t = new(
        "vcpop_op_mask",
        "Masked vcpop.m counts only elements whose v0 bit is 1 (vs2 & v0): disjoint masks give 0, equal masks "
        "the full count, and a mask with vs2 = v0 counts v0's bits; vl = 16 and 32.",
    )
    for vl in (16, 32):
        src = bits(t, 32)
        for mask in ([1 - b for b in src], src, bits(t, 32), [1] * 32):
            scal(
                t,
                "vcpop.m x8, v16",
                src,
                vl,
                cpop(src, vl, mask),
                f"vcpop.m vl={vl} masked",
                mask=mask,
                lmul="2" if vl > 16 else "1",
            )
    t.mload("v0", [1, 0, 1, 1] * 4)
    t.vset(16, 8)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("vcpop.m x8, v0, v0.t")
    t.check("x8", 12, lab, "vcpop.m x8, v0, v0.t")
    out_.append(t)

    t = new(
        "vcpop_vl0",
        "vcpop.m with vl = 0 writes 0 to rd (rd held 0x5a.. before), also masked and with a source of all ones.",
    )
    for mask in (None, [1] * 16):
        scal(
            t,
            "vcpop.m x8, v16",
            [1] * 16,
            0,
            0x5A5A5A5A if MUT == "vcpop_vl0_nowrite" else 0,
            "vcpop.m vl=0",
            mask=mask,
        )
    out_.append(t)

    t = new(
        "vcpop_vstart_n0_ill",
        "vcpop.m raises illegal-instruction when vstart != 0 (vstart = 1 and 3, vl = 16); rd is unchanged and "
        "xtval is 0 or the instruction bits.",
    )
    for vs in (1, 3):
        t.vload(VS2, 8, [0xFF, 0xFF])
        t.load("x8", 0x77)
        t.vset(16, 8)
        t.set_vstart(vs)
        lab = t.ill_window(["vcpop.m x8, v16"], 2, f"vcpop.m vstart={vs}")
        t.emit("csrwi vstart, 0")
        t.check("x8", 0x77, lab, "rd unchanged")
    out_.append(t)

    t = new(
        "vfirst_op",
        "vfirst.m writes the index of the lowest active element whose bit is 1, or -1 when there is none: bit 0, "
        "bit vl-1, bits only past vl (-1), no bits (-1), a masked case where the first set bit is inactive "
        "(the next active set bit is found), and a mask with no active set bits (-1); vl = 16 and 64.",
    )
    for vl, lm in ((16, "1"), (64, "8")):
        for src in ([1] + [0] * 63, [0] * (vl - 1) + [1] + [0] * (64 - vl), [0] * vl + [1] * (64 - vl), [0] * 64):
            scal(t, "vfirst.m x8, v16", src, vl, first(src, vl), f"vfirst.m vl={vl}", lmul=lm)
        src = [0, 1, 0, 1] + [0] * 60
        mask = [1, 0, 1, 1] + [1] * 60
        scal(t, "vfirst.m x8, v16", src, vl, first(src, vl, mask), f"vfirst.m vl={vl} masked", mask=mask, lmul=lm)
        mask = [1 - b for b in src]
        scal(
            t,
            "vfirst.m x8, v16",
            src,
            vl,
            first(src, vl, mask),
            f"vfirst.m vl={vl} no active set bit",
            mask=mask,
            lmul=lm,
        )
    out_.append(t)

    t = new(
        "vfirst_vl0",
        "vfirst.m with vl = 0 writes -1 to rd (rd held 0x5a.. before), unmasked and masked, with a source of all ones.",
    )
    for mask in (None, [1] * 16):
        scal(t, "vfirst.m x8, v16", [1] * 16, 0, first([1] * 16, 0), "vfirst.m vl=0", mask=mask)
    out_.append(t)

    t = new(
        "vfirst_vstart_n0_ill",
        "vfirst.m raises illegal-instruction when vstart != 0 (vstart = 1 and 2, vl = 16); rd is unchanged and "
        "xtval is 0 or the instruction bits.",
    )
    for vs in (1, 2):
        t.vload(VS2, 8, [0xFF, 0xFF])
        t.load("x8", 0x77)
        t.vset(16, 8)
        t.set_vstart(vs)
        lab = t.ill_window(["vfirst.m x8, v16"], 2, f"vfirst.m vstart={vs}")
        t.emit("csrwi vstart, 0")
        t.check("x8", 0x77, lab, "rd unchanged")
    out_.append(t)

    # ---- vmsbf / vmsif / vmsof
    EX = [  # (src bits 0..7, mask or None), from the spec's examples (element 0 first)
        ([0, 0, 1, 0, 1, 0, 0, 1], None),
        ([1, 0, 1, 0, 1, 0, 0, 1], None),
        ([0] * 8, None),
        ([0, 0, 1, 0, 1, 0, 0, 1], [1, 1, 0, 0, 0, 0, 1, 1]),
        ([0, 0, 1, 0, 1, 0, 1, 1], [1, 1, 0, 0, 0, 0, 1, 1]),
    ]

    def setfirst(
        t: VTest,
        kind: str,
        src: Sequence[int],
        vl: int,
        mask: Sequence[int] | None,
        ma: bool,
        desc: str,
        ta: bool = False,
    ) -> None:
        n = len(src)
        old = bits(t, n)
        res = sbf(kind, src, vl, mask)
        fullcalc = sbf(kind, src, n, mask)
        tailcalc = [fullcalc[i] if fullcalc[i] is not None else old[i] for i in range(n)]
        new_ = [r if r is not None else 0 for r in res] + [0] * (n - vl)
        legal = mpol(old, new_, vl, mask=mask, ma=ma, tailcalc=tailcalc)
        lab = t.op(
            f"vm{kind}.m {VD}, {VS2}" + (", v0.t" if mask is not None else ""),
            sew=8,
            vl=vl,
            ma=ma,
            ta=ta,
            mask=mask,
            srcs={VD: (1, "1", old), VS2: (1, "1", src)},
        )
        t.check_mask(VD, legal, lab, desc)

    for kind, name in (("bf", "vmsbf"), ("if", "vmsif"), ("of", "vmsof")):
        k = {"bf": "sbf", "if": "sif", "of": "sof"}[kind]
        t = new(
            f"{name}_op",
            f"{name}.m on the spec's examples (set bits at 2, 4, 7; a set bit at 0; no set bits; masked with v0 = "
            "1 at 0, 1, 6, 7 under mu and ma) and on 32-element patterns with the first set bit at 0, 15, 31 or "
            "none, vl = 8 and 32. Inactive elements keep their old bit (mu) or may become 1 (ma).",
        )
        for src, mask in EX:
            for ma in (False, True) if mask else (False,):
                setfirst(t, k, src, 8, mask, ma, f"{name}.m {src} mask {mask} ma={int(ma)}")
        for p in (0, 15, 31, None):
            src = [0] * 32
            if p is not None:
                src[p] = 1
                if p < 31:
                    src[31] = 1
            setfirst(t, k, src, 32, None, False, f"{name}.m vl=32 first set bit {p}")
        out_.append(t)

        t = new(
            f"{name}_tail_agnostic",
            f"{name}.m tail bits are agnostic: each may keep its old value, become 1, or take the value the "
            "instruction computes for it over the whole register. The only source bit is element 6 (in the tail, "
            "vl = 4 of 32) and every old tail bit is 1, so a tail bit whose computed value is 1 (elements 4-5 "
            "for vmsbf, 4-6 for vmsif, 6 for vmsof) must stay 1, under vta = 0 and 1.",
        )
        for ta in (False, True):
            src = [0] * 32
            src[6] = 1
            old = [0, 1, 0, 1] + [1] * 28
            full = sbf(k, src, 32, None)
            res = sbf(k, src, 4, None)
            legal = mpol(old, list(res) + [0] * 28, 4, tailcalc=full)  # type: ignore[arg-type]
            if MUT == "mask_tail_zero":
                legal = list(res) + [0] * 28  # type: ignore[assignment]
            lab = t.op(f"{name}.m {VD}, {VS2}", sew=8, vl=4, ta=ta, srcs={VD: (1, "1", old), VS2: (1, "1", src)})
            t.check_mask(VD, legal, lab, f"{name}.m vl=4 ta={int(ta)}")
        out_.append(t)

        t = new(
            f"{name}_vstart_n0_ill",
            f"{name}.m raises illegal-instruction when vstart != 0 (vstart = 1 and 4, vl = 16); vd is unchanged "
            "and xtval is 0 or the instruction bits.",
        )
        for vs in (1, 4):
            old = bits(t, 16)
            t.vload(VS2, 8, [0x10, 0x01])
            t.mload(VD, old)
            t.vset(16, 8)
            t.set_vstart(vs)
            lab = t.ill_window([f"{name}.m {VD}, {VS2}"], 2, f"{name}.m vstart={vs}")
            t.emit("csrwi vstart, 0")
            t.check_mask(VD, old, lab, "vd unchanged")
        out_.append(t)

    # ---- viota / vid
    def iota(src: Sequence[int], vl: int, mask: Sequence[int] | None, w: int) -> list[int | None]:
        out: list[int | None] = []
        c = 0
        for i in range(vl):
            act = mask is None or mask[i]
            if act:
                out.append(m(c + (src[i] if MUT == "viota_inclusive" else 0), w))
            else:
                out.append(None)
            if act or MUT == "viota_masked_counts_all":
                c += src[i]
        return out

    t = new(
        "viota_op",
        "viota.m writes to element i the number of set source bits below i (exclusive prefix sum): the spec's "
        "example (bits 0, 4, 7 -> 0 1 1 1 1 2 2 2), all ones (0, 1, 2, ...), all zeros, at SEW 8, 16, 32, 64 "
        "with vl = 8 (and 16 at SEW 8).",
    )
    for sew in (8, 16, 32, 64):
        for src in ([1, 0, 0, 0, 1, 0, 0, 1], [1] * 8, [0] * 8, bits(t, 8)):
            old = rnd(t, sew, 8)
            res = iota(src, 8, None, sew)
            lab = t.op(f"viota.m {VD}, {VS2}", sew=sew, vl=8, srcs={VD: (sew, "1", old), VS2: (1, "1", src)})
            t.check_vreg(VD, sew, res, lab, f"viota.m e{sew} {src}")
    src = bits(t, 16)
    old = rnd(t, 8, 16)
    lab = t.op(f"viota.m {VD}, {VS2}", sew=8, vl=16, srcs={VD: (8, "1", old), VS2: (1, "1", src)})
    t.check_vreg(VD, 8, iota(src, 16, None, 8), lab, "viota.m e8 vl=16")
    out_.append(t)

    t = new(
        "viota_op_masked",
        "Masked viota.m: only active elements contribute to the count and are written; inactive elements keep "
        "their old value (mu) or may become all ones (ma). The spec's example (v0 = 1 1 0 1 0 1 1 1 from element "
        "0, v2 bits at 0, 4, 7, old 9 8 7 6 5 4 3 2 -> 0 1 7 1 5 1 1 1) and a random case, SEW 8 and 32.",
    )
    for sew in (8, 32):
        for src, mask, old in (
            ([1, 0, 0, 0, 1, 0, 0, 1], [1, 1, 0, 1, 0, 1, 1, 1], [9, 8, 7, 6, 5, 4, 3, 2]),
            (bits(t, 8), bits(t, 8), rnd(t, sew, 8)),
        ):
            for ma in (False, True):
                res = iota(src, 8, mask, sew)
                legal = pol(old, [r if r is not None else 0 for r in res], 8, sew, mask=mask, ma=ma)
                lab = t.op(
                    f"viota.m {VD}, {VS2}, v0.t",
                    sew=sew,
                    vl=8,
                    ma=ma,
                    mask=mask,
                    srcs={VD: (sew, "1", old), VS2: (1, "1", src)},
                )
                t.check_vreg(VD, sew, legal, lab, f"viota.m e{sew} masked ma={int(ma)}")
    out_.append(t)

    t = new(
        "viota_op_zext",
        "The viota.m count is zero-extended to SEW: with all source bits set and an old destination of all ones, "
        "element i must be exactly i (upper bits 0) at SEW 16, 32 and 64.",
    )
    for sew in (16, 32, 64):
        n = 8
        lab = t.op(
            f"viota.m {VD}, {VS2}", sew=sew, vl=n, srcs={VD: (sew, "1", [ones(sew)] * n), VS2: (1, "1", [1] * n)}
        )
        t.check_vreg(VD, sew, iota([1] * n, n, None, sew), lab, f"viota.m e{sew} all ones")
    out_.append(t)

    def overflow_case(t: VTest, insn: str, desc: str) -> None:
        """At e8/m8 with vl = VLMAX = VLEN: when VLEN > 256, element 256 holds 0 and element 257 holds 1 (the low 8
        bits of the index/count). Skipped (nothing to check) at VLEN <= 256."""
        t.emit("csrr x6, vlenb")
        t.emit("sltiu x6, x6, 33")
        t.emit("xori x6, x6, 1")

        def big() -> None:
            t.vset("max", 8, "8")
            t.emit("vmset.m v0")
            lab = t.label("insn")
            t.emit(f"{lab}:", 0)
            t.emit(insn)
            for k in (256, 257, 511):
                t.li("x7", k)
                t.emit("vslidedown.vx v16, v8, x7")
                t.emit("vmv.x.s x8, v16")
                t.emit("andi x8, x8, 0xff")
                exp = k & 0xFF
                t.check("x8", exp, lab, f"{desc}: element {k}")

        t.either("x6", big, lambda: None)

    t = new(
        "viota_op_overflow",
        "If the viota.m count overflows SEW, its low SEW bits are kept: at e8/m8 with vl = VLMAX and every "
        "source bit set, element i is i mod 256, so elements 256 and 257 are 0 and 1. Only harts with VLEN > 256 "
        "have such elements (VLEN >= 512, so element 511 = 255 is checked too); at smaller VLEN the case is "
        "skipped (VLEN is read from vlenb).",
    )
    t.vload(VD, 8, [0x5A] * 16)
    overflow_case(t, f"viota.m {VD}, v0", "viota.m e8 overflow")
    out_.append(t)

    t = new(
        "vid_op",
        "vid.v writes each element's index 0..vl-1 (unmasked), tail undisturbed (tu) or old/ones (ta); vl = 8 at "
        "SEW 8, 16, 32, 64 and vl = 32 at e8.",
    )
    for sew in (8, 16, 32, 64):
        for ta in (False, True):
            old = rnd(t, sew, 8)
            lab = t.op(f"vid.v {VD}", sew=sew, vl=6, ta=ta, srcs={VD: (sew, "1", old)})
            t.check_vreg(VD, sew, pol(old, list(range(8)), 6, sew, ta=ta), lab, f"vid.v e{sew} vl=6 ta={int(ta)}")
    old = rnd(t, 8, 32)
    lab = t.op(f"vid.v {VD}", sew=8, vl=32, srcs={VD: (8, "2", old)})
    t.check_vreg(VD, 8, list(range(32)), lab, "vid.v e8 vl=32")
    out_.append(t)

    t = new(
        "vid_op_mask",
        "Masked vid.v writes the element's own index to active elements (masking does not compact the indices); "
        "inactive elements keep their value (mu) or may become ones (ma). SEW 8 and 32.",
    )
    for sew in (8, 32):
        mask = [0, 1, 1, 0, 1, 0, 0, 1]
        for ma in (False, True):
            old = rnd(t, sew, 8)
            idx = list(range(8))
            if MUT == "vid_masked_compact":
                c = 0
                idx = []
                for i in range(8):
                    idx.append(c)
                    c += mask[i]
            lab = t.op(f"vid.v {VD}, v0.t", sew=sew, vl=8, ma=ma, mask=mask, srcs={VD: (sew, "1", old)})
            t.check_vreg(VD, sew, pol(old, idx, 8, sew, mask=mask, ma=ma), lab, f"vid.v e{sew} masked ma={int(ma)}")
    out_.append(t)

    t = new(
        "vid_op_zext",
        "vid.v zero-extends the index to SEW: with an old destination of all ones, element i is "
        "exactly i at SEW 16, 32 and 64.",
    )
    for sew in (16, 32, 64):
        lab = t.op(f"vid.v {VD}", sew=sew, vl=8, srcs={VD: (sew, "1", [ones(sew)] * 8)})
        t.check_vreg(VD, sew, list(range(8)), lab, f"vid.v e{sew}")
    out_.append(t)

    t = new(
        "vid_op_overflow",
        "vid.v keeps the low SEW bits of an index that overflows SEW: at e8/m8 with vl = VLMAX elements 256 and "
        "257 are 0 and 1 (checked only when VLEN > 256, read from vlenb).",
    )
    t.vload(VD, 8, [0x5A] * 16)
    overflow_case(t, f"vid.v {VD}", "vid.v e8 overflow")
    out_.append(t)

    t = new(
        "viota_vstart_n0_ill",
        "viota.m raises illegal-instruction when vstart != 0 (vstart = 1 and 3, vl = 8); vd is unchanged and "
        "xtval is 0 or the instruction bits.",
    )
    for vs in (1, 3):
        old = rnd(t, 16, 8)
        t.vload(VD, 16, old)
        t.vload(VS2, 8, [0xFF])
        t.vset(8, 16)
        t.set_vstart(vs)
        lab = t.ill_window([f"viota.m {VD}, {VS2}"], 2, f"viota.m vstart={vs}")
        t.emit("csrwi vstart, 0")
        t.check_vreg(VD, 16, old, lab, "vd unchanged")
    out_.append(t)
    return out_


# ==================================================================== permutation
def xval(v: int, sew: int) -> X:
    """x[rs1] holding v: the low SEW bits for SEW < XLEN, the sign-extended 32-bit value on RV32 for SEW = 64."""
    return X(m(v, 32), m(v, 64))


def scal_in(v: X, sew: int) -> X:
    """The SEW-bit element written from x = v: truncated when SEW < XLEN, sign-extended when SEW > XLEN."""
    if MUT == "vslide1up_zext":
        return X(m(v.num(32), min(sew, 32)), m(v.num(64), sew))
    return X(m(sx(v.num(32), 32), sew), m(v.num(64), sew))


def g_perm() -> list[VTest]:
    out_: list[VTest] = []

    t = new(
        "vmv-x-s_vmv-s-x_ignorelmul",
        "vmv.x.s and vmv.s.x ignore LMUL (EMUL = 1): at e32/m8, vmv.x.s x8, v9 and vmv.s.x v9, x6 use register "
        "v9 (not a multiple of 8) without trapping; vmv.s.x writes only v9[0] (v9[1..3] are tail, tu) and leaves "
        "v10 unchanged.",
    )
    a = [0x89ABCDEF, 2, 3, 4]
    t.vload("v9", 32, a)
    t.vload("v10", 32, [0x0F0F0F0F] * 4)
    t.vset(8, 32, "8")
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("vmv.x.s x8, v9")
    t.check("x8", sx(0x89ABCDEF, 32), lab, "vmv.x.s x8, v9 at m8")
    t.load("x6", 0x13572468)
    t.vset(8, 32, "8")
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("vmv.s.x v9, x6")
    t.check_vreg("v9", 32, [0x13572468, 2, 3, 4], lab, "vmv.s.x v9, x6 at m8 (tu)")
    t.check_vreg("v10", 32, [0x0F0F0F0F] * 4, lab, "v10 unchanged")
    out_.append(t)

    t = new(
        "vmv-x-s_op",
        "vmv.x.s copies element 0 to x[rd], sign-extended when SEW < XLEN (0x80 -> -128, 0x8001, 0x80000000 on "
        "RV64) and truncated to the low XLEN bits when SEW > XLEN (SEW 64 on RV32); positive values are not "
        "extended with ones. It also writes x[rd] with vl = 0.",
    )
    for sew, v in (
        (8, 0x80),
        (8, 0x7F),
        (16, 0x8001),
        (32, 0x80000000),
        (32, 0x7FFFFFFF),
        (64, 0x8000000189ABCDEF),
        (64, 0x7FFFFFFF00000000),
    ):
        for vl in (1, 0):
            t.load("x8", 0x5A5A)
            lab = t.op("vmv.x.s x8, v16", sew=sew, vl=vl, srcs={VS2: (sew, "1", [v, 0x11])})
            exp = X(m(v, 32), m(v, 64)) if MUT == "vmvxs_zext" else X(m(sx(v, sew), 32), m(sx(v, sew), 64))
            t.check("x8", exp, lab, f"vmv.x.s e{sew} of 0x{v:x} vl={vl}")
    out_.append(t)

    t = new(
        "vmv-s-x_op",
        "vmv.s.x writes x[rs1] to element 0 (the low SEW bits when SEW < XLEN; sign-extended to 64 bits on RV32); "
        "elements 1.. of that register are tail elements: undisturbed under tu, old or ones under ta. At m4 the "
        "next register of the group (v17) is not written.",
    )
    for sew, v in (
        (8, X(0x123456F8, 0x123456F8)),
        (16, X(0xFFFF8001, 0xFFFF8001)),
        (32, X(0x89ABCDEF, 0x89ABCDEF)),
        (64, X(0x80000001, 0xFEDCBA9880000001)),
    ):
        for ta in (False, True):
            old = rnd(t, sew, 128 // sew)
            exp = X(m(sx(v.num(32), 32), sew), m(v.num(64), sew))
            lab = t.op("vmv.s.x v16, x6", sew=sew, vl=4, ta=ta, xs={"x6": v}, srcs={VS2: (sew, "1", old)})
            legal: list = [exp] + pol(old[1:], old[1:], 0, sew, ta=ta)
            t.check_vreg(VS2, sew, legal, lab, f"vmv.s.x e{sew} ta={int(ta)}")
    t.vload("v17", 32, [0x0BADC0DE] * 4)
    lab = t.op("vmv.s.x v16, x6", sew=32, lmul="4", vl=16, xs={"x6": X(7, 7)}, srcs={VS2: (32, "1", [1, 2, 3, 4])})
    t.check_vreg(VS2, 32, [7, 2, 3, 4], lab, "vmv.s.x e32 m4 (tu)")
    t.check_vreg("v17", 32, [0x0BADC0DE] * 4, lab, "v17 unchanged")
    out_.append(t)

    t = new(
        "vmv-s-x_vstart_ge_vl",
        "vmv.s.x with vstart >= vl does nothing: vl = 0 (vta = 0 and 1) leaves the whole register unchanged; "
        "vstart = 1 with vl = 1 also leaves it unchanged, or may raise illegal-instruction (a nonzero vstart the "
        "hart never produces, vstart_vtype_dep).",
    )
    for ta in (False, True):
        old = rnd(t, 32, 4)
        lab = t.op("vmv.s.x v16, x6", sew=32, vl=0, ta=ta, xs={"x6": X(9, 9)}, srcs={VS2: (32, "1", old)})
        exp = old if MUT != "vmvsx_vl0_writes" else [9] + old[1:]
        t.check_vreg(VS2, 32, exp, lab, f"vmv.s.x vl=0 ta={int(ta)}")
    old = rnd(t, 32, 4)
    t.vload(VS2, 32, old)
    t.load("x6", 9)
    t.vset(1, 32)
    t.set_vstart(1)
    lab = t.ill_window(["vmv.s.x v16, x6"], ["ok", 2], "vmv.s.x vstart=1 vl=1")
    t.emit("csrwi vstart, 0")
    t.check_vreg(VS2, 32, old, lab, "vmv.s.x vstart=1 vl=1: unchanged")
    out_.append(t)

    # ---- slides
    def slide(
        kind: str,
        src: Sequence[int],
        old: Sequence[int],
        vl: int,
        off: int,
        sew: int,
        x: X | None = None,
        mask: Sequence[int] | None = None,
        ma: bool = False,
        ta: bool = False,
        vlmax: int | None = None,
        vstart: int = 0,
    ) -> list:
        n = len(old)
        if vstart >= vl:
            return [m(o, sew) for o in old]
        new_: list = []
        for i in range(n):
            if kind == "up":
                off_ = off & ones(sew) if MUT == "vslideup_offset_trunc" else off
                v = src[i - off_] if i >= off_ else None
            elif kind == "down":
                j = i + off
                if vlmax is not None and j >= vlmax and MUT != "vslidedown_past_vlmax_keep":
                    v = 0
                else:
                    assert j < len(src) or i >= vl, f"vslidedown source {j} not loaded"
                    v = src[j] if j < len(src) else None
            elif kind == "1up":
                v = scal_in(x, sew) if i == 0 else src[i - 1]  # type: ignore[arg-type]
            else:
                if i == vl - 1:
                    v = src[vl] if MUT == "vslide1down_reads_vl" and vl < len(src) else scal_in(x, sew)  # type: ignore[arg-type]
                else:
                    v = src[i + 1] if i + 1 < len(src) else None
            new_.append(v)
        out = pol(old, new_, vl, sew, mask=mask, vstart=vstart, ta=ta, ma=ma)
        if kind == "up":
            for i in range(min(vl, n)):
                if i < max(vstart, off if MUT != "vslideup_offset_trunc" else off & ones(sew)):
                    out[i] = m(old[i], sew)
        return out

    def sl(
        t: VTest,
        asm: str,
        kind: str,
        *,
        sew: int,
        src: Sequence[int],
        vl: int,
        off: int = 0,
        x: X | None = None,
        f: tuple[int, int] | None = None,
        mask: Sequence[int] | None = None,
        ma: bool = False,
        ta: bool = False,
        desc: str = "",
        n: int | None = None,
    ) -> str:
        n = n or len(src)
        old = rnd(t, sew, n)
        xs = {"x6": x} if x is not None and f is None else {}
        fs = {"f1": f} if f is not None else {}
        xx = x
        if f is not None:
            fb, fw = f
            if sew == 32 and fw == 64 and (fb >> 32) != 0xFFFFFFFF:
                xx = X(CNAN[32], CNAN[32])
            else:
                xx = X(m(fb, sew), m(fb, sew))
        legal = slide(kind, src, old, vl, off, sew, xx, mask=mask, ma=ma, ta=ta)
        if f is not None and kind in ("1up", "1down"):
            pos = 0 if kind == "1up" else vl - 1
            if vl > 0 and (mask is None or mask[pos]):
                legal[pos] = xx
        lm = auto_lmul(max(n, len(src)), sew)
        lab = t.op(
            asm + (", v0.t" if mask is not None else ""),
            sew=sew,
            lmul=lm,
            vl=vl,
            ma=ma,
            ta=ta,
            mask=mask,
            xs=xs,
            fs=fs,
            srcs={VD: (sew, lm, old), VS2: (sew, lm, src)},
        )
        t.check_vreg(VD, sew, legal, lab, desc, lm)
        return lab

    t = new(
        "vslide_vstart_ge_vl",
        "vslideup, vslidedown, vslide1up, vfslide1up, vslide1down and vfslide1down with vstart >= vl leave vd "
        "unchanged: vl = 0 with vta = 1 (no agnostic tail update) for each; vstart = 2 with vl = 2 for "
        "vslideup/vslide1down, which may also raise illegal-instruction (vstart_vtype_dep).",
    )
    insns = [
        ("vslideup.vi {vd}, {vs2}, 1", "up"),
        ("vslidedown.vi {vd}, {vs2}, 1", "down"),
        ("vslide1up.vx {vd}, {vs2}, x6", "1up"),
        ("vfslide1up.vf {vd}, {vs2}, f1", "1up"),
        ("vslide1down.vx {vd}, {vs2}, x6", "1down"),
        ("vfslide1down.vf {vd}, {vs2}, f1", "1down"),
    ]
    for asm, kind in insns:
        src = rnd(t, 32, 4)
        old = rnd(t, 32, 4)
        xs = {"x6": X(5, 5)} if "x6" in asm else {}
        fs = {"f1": (F(1.0, 32), 32)} if "f1" in asm else {}
        a2 = asm.format(vd=VD, vs2=VS2)
        lab = t.op(a2, sew=32, vl=0, ta=True, xs=xs, fs=fs, srcs={VD: (32, "1", old), VS2: (32, "1", src)})
        exp = old if MUT != "vslide_vl0_tail" else [ones(32)] * 4
        t.check_vreg(VD, 32, exp, lab, f"{a2.split()[0]} vl=0 ta")
    for asm in ("vslideup.vi {vd}, {vs2}, 1", "vslide1down.vx {vd}, {vs2}, x6"):
        old = rnd(t, 32, 4)
        t.vload(VD, 32, old)
        t.vload(VS2, 32, rnd(t, 32, 4))
        t.load("x6", 5)
        t.vset(2, 32)
        t.set_vstart(2)
        a2 = asm.format(vd=VD, vs2=VS2)
        lab = t.ill_window([a2], ["ok", 2], f"{a2.split()[0]} vstart=2 vl=2")
        t.emit("csrwi vstart, 0")
        t.check_vreg(VD, 32, old, lab, f"{a2.split()[0]} vstart=2 vl=2: unchanged")
    out_.append(t)

    t = new(
        "vslide_mask",
        "Masked slides: mask element i controls whether destination element i is written; inactive elements "
        "keep their value (mu) or may become ones (ma). vslideup.vi 1, vslidedown.vx 2, vslide1up.vx, "
        "vslide1down.vx and vfslide1down.vf with masks that make destination 0 and vl-1 inactive, SEW 16 and 64.",
    )
    for sew in (16, 64):
        src = rnd(t, sew, 8)
        for ma in (False, True):
            mask = [0, 1, 1, 0, 1, 1, 0, 0]
            sl(
                t,
                f"vslideup.vi {VD}, {VS2}, 1",
                "up",
                sew=sew,
                src=src,
                vl=8,
                off=1,
                mask=mask,
                ma=ma,
                desc=f"vslideup.vi 1 e{sew} ma={int(ma)}",
            )
            sl(
                t,
                f"vslidedown.vx {VD}, {VS2}, x6",
                "down",
                sew=sew,
                src=src,
                vl=6,
                off=2,
                x=X(2, 2),
                mask=mask,
                ma=ma,
                desc=f"vslidedown.vx 2 e{sew} ma={int(ma)}",
            )
            sl(
                t,
                f"vslide1up.vx {VD}, {VS2}, x6",
                "1up",
                sew=sew,
                src=src,
                vl=8,
                x=X(0x77, 0x77),
                mask=mask,
                ma=ma,
                desc=f"vslide1up.vx e{sew} ma={int(ma)}",
            )
            sl(
                t,
                f"vslide1down.vx {VD}, {VS2}, x6",
                "1down",
                sew=sew,
                src=src,
                vl=7,
                x=X(0x66, 0x66),
                mask=mask,
                ma=ma,
                desc=f"vslide1down.vx vl=7 e{sew} ma={int(ma)}",
            )
        if sew == 64:
            sl(
                t,
                f"vfslide1down.vf {VD}, {VS2}, f1",
                "1down",
                sew=64,
                src=src,
                vl=7,
                f=(F(2.5, 64), 64),
                mask=[1, 1, 1, 1, 1, 1, 0, 0],
                desc="vfslide1down.vf vl=7 e64, element vl-1 inactive",
            )
    out_.append(t)

    t = new(
        "vslideup_op",
        "vslideup writes vd[i] = vs2[i - OFFSET] for OFFSET <= i < vl; elements below OFFSET are unchanged; "
        "nothing is written when OFFSET >= vl. OFFSET 0, 1, 3 and 4 (= vl) from x[rs1] and uimm 2 and 31 at "
        "e32; at e8 x[rs1] = 0x101 is not truncated to SEW bits (OFFSET 257 >= vl: vd unchanged); OFFSET = "
        "all ones (x = -1) writes nothing. vl = 4 of 6, tail undisturbed.",
    )
    src = rnd(t, 32, 6)
    for off in (0, 1, 3, 4):
        sl(
            t,
            f"vslideup.vx {VD}, {VS2}, x6",
            "up",
            sew=32,
            src=src,
            vl=4,
            off=off,
            x=X(off, off),
            n=6,
            desc=f"vslideup.vx {off} e32 vl=4",
        )
    for off in (2, 31):
        sl(
            t,
            f"vslideup.vi {VD}, {VS2}, {off}",
            "up",
            sew=32,
            src=src,
            vl=4,
            off=off,
            n=6,
            desc=f"vslideup.vi {off} e32 vl=4",
        )
    src = rnd(t, 8, 8)
    sl(
        t,
        f"vslideup.vx {VD}, {VS2}, x6",
        "up",
        sew=8,
        src=src,
        vl=8,
        off=0x101,
        x=X(0x101, 0x101),
        desc="vslideup.vx 0x101 e8",
    )
    old = rnd(t, 8, 8)
    lab = t.op(
        f"vslideup.vx {VD}, {VS2}, x6",
        sew=8,
        vl=8,
        xs={"x6": X(ones(32), ones(64))},
        srcs={VD: (8, "1", old), VS2: (8, "1", src)},
    )
    t.check_vreg(VD, 8, old, lab, "vslideup.vx -1 e8: unchanged")
    out_.append(t)

    t = new(
        "vslidedown_op",
        "vslidedown writes vd[i] = vs2[i + OFFSET] for i < vl, reading source elements past vl (but below "
        "VLMAX); tail elements are undisturbed (tu) or old/ones (ta). OFFSET 1, 2 (.vx) and 5 (.vi) at e16 with "
        "vl = 4 of 8 loaded source elements; e64 with vl = 2.",
    )
    for ta in (False, True):
        src = rnd(t, 16, 8)
        for off in (1, 2):
            sl(
                t,
                f"vslidedown.vx {VD}, {VS2}, x6",
                "down",
                sew=16,
                src=src,
                vl=4,
                off=off,
                x=X(off, off),
                ta=ta,
                desc=f"vslidedown.vx {off} e16 vl=4 ta={int(ta)}",
            )
        sl(
            t,
            f"vslidedown.vi {VD}, {VS2}, 3",
            "down",
            sew=16,
            src=src,
            vl=4,
            off=3,
            ta=ta,
            desc=f"vslidedown.vi 3 e16 vl=4 ta={int(ta)}",
        )
        src = rnd(t, 64, 4)
        sl(
            t,
            f"vslidedown.vi {VD}, {VS2}, 1",
            "down",
            sew=64,
            src=src,
            vl=2,
            off=1,
            ta=ta,
            desc=f"vslidedown.vi 1 e64 vl=2 ta={int(ta)}",
        )
    out_.append(t)

    t = new(
        "vslidedown_op_src",
        "vslidedown reads 0 for source indices i + OFFSET >= VLMAX, with OFFSET unsigned and not truncated to "
        "SEW: at e32/m1 with vs2 = vid + 100 over the whole register and OFFSET = VLMAX - 2 (VLMAX from vsetvli), "
        "vd[0..1] = VLMAX + 98, VLMAX + 99 and vd[2..3] = 0; OFFSET = all ones gives 0 everywhere; at e8 OFFSET "
        "0x10001 (>= any VLMAX) gives 0 although its low 8 bits are 1.",
    )
    t.vset("max", 32, "1", rd="x7")
    t.emit(f"vid.v {VS2}")
    t.emit(f"vadd.vi {VS2}, {VS2}, 15")
    t.li("x6", 85)
    t.emit(f"vadd.vx {VS2}, {VS2}, x6")
    t.emit("addi x6, x7, -2")
    t.vload(VD, 32, [1, 2, 3, 4])
    t.vset(4, 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vslidedown.vx {VD}, {VS2}, x6")
    exp_hi = [0, 0] if MUT != "vslidedown_past_vlmax_keep" else [5, 6]
    for k in (0, 1):
        t.vset(4, 32)
        t.emit(f"vslidedown.vi v12, {VD}, {k}" if k else f"vmv.v.v v12, {VD}")
        t.emit("vmv.x.s x8, v12")
        t.emit(f"addi x8, x8, -{98 + k}")
        t.emit("sub x8, x8, x7")
        t.emit("seqz x8, x8")
        t.check_bool("x8", lab, f"vslidedown.vx VLMAX-2: vd[{k}] = VLMAX + {98 + k}")
    t.vstore(VD, 32, 4)
    t.check_elems(32, [None, None] + exp_hi, lab, "vslidedown.vx VLMAX-2: elements past VLMAX read 0")
    lab = t.op(
        f"vslidedown.vx {VD}, {VS2}, x6",
        sew=32,
        vl=4,
        xs={"x6": X(ones(32), ones(64))},
        srcs={VD: (32, "1", [1, 2, 3, 4])},
    )
    t.check_vreg(VD, 32, [0, 0, 0, 0], lab, "vslidedown.vx all-ones offset")
    src = rnd(t, 8, 8)
    lab = t.op(
        f"vslidedown.vx {VD}, {VS2}, x6",
        sew=8,
        vl=4,
        xs={"x6": X(0x10001, 0x10001)},
        srcs={VD: (8, "1", [1, 2, 3, 4]), VS2: (8, "1", src)},
    )
    t.check_vreg(VD, 8, [0] * 4 if MUT != "vslideup_offset_trunc" else src[1:5], lab, "vslidedown.vx 0x10001 e8")
    out_.append(t)

    for rule, plan, kind, vf in (
        (
            "vslide1up-vx_op",
            (
                "vslide1up.vx writes x[rs1] to element 0 when it is active (inactive: mu keeps it, ma old "
                "or ones); x is truncated to SEW when SEW < XLEN (0x1234567f at e8 -> 0x7f) and sign-extended when SEW > XLEN "
                "(RV32 at e64: 0x80000001 -> 0xffffffff80000001)."
            ),
            "1up",
            False,
        ),
        (
            "vslide1up-vx_op_rem_elem",
            (
                "vslide1up copies vs2[i] to vd[i+1] for the remaining active elements below vl "
                "(vs2[vl-1] is not copied); masked-off destination elements keep their values (mu). SEW 8, 32, 64."
            ),
            "1up",
            False,
        ),
        (
            "vslide1up-vx_op_vl",
            (
                "vslide1up writes at most vl elements; elements past vl follow the tail policy "
                "(tu: unchanged, ta: old or ones), vl = 3 of 6, SEW 16 and 64."
            ),
            "1up",
            False,
        ),
        (
            "vslide1down-vx_op",
            (
                "vslide1down copies vs2[i+1] to vd[i] for i < vl-1; vs2[vl] (past vl, below VLMAX) is "
                "not used, element vl-1 gets x[rs1]. SEW 8, 32, 64, vl = 5 of 8."
            ),
            "1down",
            False,
        ),
        (
            "vslide1down-vx_op_vl",
            (
                "vslide1down writes at most vl elements; elements past vl follow the tail policy "
                "(tu: unchanged, ta: old or ones), vl = 3 of 6, SEW 16 and 64."
            ),
            "1down",
            False,
        ),
        (
            "vslide1down-vx_op_details",
            (
                "vslide1down writes x[rs1] to element vl-1 when it is active (inactive: mu keeps "
                "it, ma old or ones); x truncated to SEW (e8) or sign-extended (RV32 at e64)."
            ),
            "1down",
            False,
        ),
        (
            "vslide1up-vf_op",
            (
                "vfslide1up.vf is vslide1up with the scalar from f[rs1]: f at element 0, vs2[i] at "
                "i+1, mask and tail as for vslide1up; SEW 32 (a non-NaN-boxed f register gives the canonical NaN) and 64."
            ),
            "1up",
            True,
        ),
        (
            "vslide1down-vf_op",
            (
                "vfslide1down.vf is vslide1down with the scalar from f[rs1]: vs2[i+1] at i, f at vl-1, "
                "mask and tail as for vslide1down; SEW 32 (a non-NaN-boxed f register gives the canonical NaN) and 64."
            ),
            "1down",
            True,
        ),
    ):
        t = new(rule, plan)
        mn = ("vfslide" if vf else "vslide") + kind + (".vf" if vf else ".vx")
        opnd = "f1" if vf else "x6"
        for sew in (32, 64) if vf else (8, 32, 64) if not rule.endswith("_vl") else (16, 64):
            src = rnd(t, sew, 8 if sew != 64 else 6)
            xv = X(0x1234567F, 0x1234567F) if sew == 8 else X(0x80000001, 0xFEDCBA9880000001)
            fv = (F(-1.25, sew), sew) if vf else None
            vls = [5, 8] if not rule.endswith("_vl") else [3]
            for vl in vls:
                vl = min(vl, len(src))
                for ta in (False, True) if rule.endswith("_vl") else (False,):
                    sl(
                        t,
                        f"{mn} {VD}, {VS2}, {opnd}",
                        kind,
                        sew=sew,
                        src=src,
                        vl=vl,
                        x=None if vf else xv,
                        f=fv if vf else None,
                        ta=ta,
                        desc=f"{mn} e{sew} vl={vl} ta={int(ta)}",
                    )
            if not rule.endswith("_vl"):
                pos = 0 if kind == "1up" else len(src) - 1
                mask = [1] * len(src)
                mask[pos] = 0
                mask[2] = 0
                for ma in (False, True):
                    sl(
                        t,
                        f"{mn} {VD}, {VS2}, {opnd}",
                        kind,
                        sew=sew,
                        src=src,
                        vl=len(src),
                        x=None if vf else xv,
                        f=fv if vf else None,
                        mask=mask,
                        ma=ma,
                        desc=f"{mn} e{sew} masked ma={int(ma)}",
                    )
        if vf:
            src = rnd(t, 32, 4)
            sl(
                t,
                f"{mn} {VD}, {VS2}, f1",
                kind,
                sew=32,
                src=src,
                vl=4,
                f=(0x000000003F800000, 64),
                desc=f"{mn} e32 non-NaN-boxed f1",
            )
        out_.append(t)

    # ---- gather
    def gat(
        t: VTest,
        asm: str,
        *,
        sew: int,
        src: Sequence[int],
        idx: object,
        vl: int,
        ieew: int | None = None,
        kind: str = "vv",
        mask: Sequence[int] | None = None,
        ma: bool = False,
        ta: bool = False,
        n: int | None = None,
        vlmax: int,
        desc: str = "",
        lmul: str | None = None,
    ) -> str:
        n = n or (len(idx) if isinstance(idx, list) else 4)  # type: ignore[arg-type]
        lmul = lmul or auto_lmul(max(n, len(src)), sew)
        old = rnd(t, sew, n)
        ieew = ieew or sew
        ids = idx if isinstance(idx, list) else [idx.num(32) if isinstance(idx, X) else idx] * n

        vlmax_max = int(65536 * lmul_val(lmul) / sew)  # VLEN <= 65536

        def pick(j: int) -> int:
            if MUT == "vrgather_signed_index" and j == ones(ieew if kind == "vv" else 32):
                return src[0]
            if MUT == "vrgather_index_vl" and j >= vl:
                return 0
            if j < len(src):
                return src[j]
            assert j >= vlmax_max, f"index {j} may be below VLMAX"
            return 0

        new_ = [pick(j) for j in ids]  # type: ignore[union-attr]
        legal = pol(old, new_, vl, sew, mask=mask, ma=ma, ta=ta)
        srcs = {VD: (sew, lmul, old), VS2: (sew, lmul, src)}
        xs = {}
        if kind == "vv":
            srcs[VS1] = (ieew, emul_s(lmul, ieew, sew), ids)
        elif kind == "vx":
            xs = {"x6": idx if isinstance(idx, X) else X(idx, idx)}  # type: ignore[arg-type]
        lab = t.op(
            asm + (", v0.t" if mask is not None else ""),
            sew=sew,
            lmul=lmul,
            vl=vl,
            ma=ma,
            ta=ta,
            mask=mask,
            xs=xs,
            srcs=srcs,
        )
        t.check_vreg(VD, sew, legal, lab, desc, lmul)
        return lab

    G = f"vrgather.vv {VD}, {VS2}, {VS1}"
    t = new(
        "vrgather_vrgatherei16_vs2_uint",
        "Gather indices are unsigned: an all-ones index (0xffff at e16, 0xffffffff at e32, and the vrgatherei16 "
        "index 0xffff at e8) is >= VLMAX and gives 0, not element -1 (or a wrapped element); 0x8000/0x80000000 "
        "likewise; vrgather.vx with x = -1 gives 0.",
    )
    for sew in (16, 32):
        src = [t.rand(sew) | 1 for _ in range(4)]
        gat(
            t,
            G,
            sew=sew,
            src=src,
            idx=[ones(sew), 1 << (sew - 1), 2, 0],
            vl=4,
            vlmax=1 << 30,
            desc=f"vrgather.vv e{sew}",
        )
        gat(
            t,
            f"vrgather.vx {VD}, {VS2}, x6",
            sew=sew,
            src=src,
            idx=X(ones(32), ones(64)),
            kind="vx",
            vl=4,
            vlmax=1 << 30,
            desc=f"vrgather.vx -1 e{sew}",
        )
    src = [t.rand(8) | 1 for _ in range(4)]
    gat(
        t,
        f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
        sew=8,
        src=src,
        idx=[0xFFFF, 0x8000, 1, 3],
        ieew=16,
        vl=4,
        vlmax=1 << 30,
        desc="vrgatherei16.vv e8",
    )
    out_.append(t)

    t = new(
        "vrgather_vrgatherei16_vs_ignore_vl",
        "Gathers read any source index below VLMAX whatever vl is: with vl = 2 at e32/m1 (VLMAX >= 4), indices 3 "
        "and 2 select vs2[3] and vs2[2]; vrgather.vi 3 and vrgatherei16 likewise.",
    )
    src = rnd(t, 32, 4)
    gat(t, G, sew=32, src=src, idx=[3, 2, 0, 1], vl=2, vlmax=4, desc="vrgather.vv vl=2 indices 3, 2")
    gat(t, f"vrgather.vi {VD}, {VS2}, 3", sew=32, src=src, idx=3, kind="vi", vl=2, vlmax=4, desc="vrgather.vi 3 vl=2")
    gat(
        t,
        f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
        sew=32,
        src=src,
        idx=[2, 3, 1, 0],
        ieew=16,
        vl=2,
        vlmax=4,
        desc="vrgatherei16.vv vl=2",
    )
    out_.append(t)

    for rule, plan, ta in (
        (
            "vrgather_vrgatherei16_vl",
            (
                "Gathers write at most vl elements: with vl = 3 of 6 (tu) elements 3-5 keep "
                "their values; vrgather.vv/.vx/.vi and vrgatherei16 at SEW 8 and 64."
            ),
            False,
        ),
        (
            "vrgather_vrgatherei16_tail",
            (
                "Elements past vl follow the tail policy: with vta = 1 each tail element keeps "
                "its value or becomes all ones (vl = 3 of 6); vrgather.vv/.vx/.vi and vrgatherei16 at SEW 8 and 64."
            ),
            True,
        ),
    ):
        t = new(rule, plan)
        for sew in (8, 64):
            n = 6 if sew == 8 else 4
            src = rnd(t, sew, n)
            vlx = 3
            gat(
                t,
                G,
                sew=sew,
                src=src,
                idx=[n - 1 - i for i in range(n)],
                vl=vlx,
                ta=ta,
                vlmax=n,
                desc=f"vrgather.vv e{sew} vl=3",
            )
            gat(
                t,
                f"vrgather.vx {VD}, {VS2}, x6",
                sew=sew,
                src=src,
                idx=1,
                kind="vx",
                vl=vlx,
                ta=ta,
                vlmax=n,
                n=n,
                desc=f"vrgather.vx 1 e{sew} vl=3",
            )
            gat(
                t,
                f"vrgather.vi {VD}, {VS2}, 2",
                sew=sew,
                src=src,
                idx=2,
                kind="vi",
                vl=vlx,
                ta=ta,
                vlmax=n,
                n=n,
                desc=f"vrgather.vi 2 e{sew} vl=3",
            )
            gat(
                t,
                f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
                sew=sew,
                src=src,
                idx=[(i + 1) % n for i in range(n)],
                ieew=16,
                vl=vlx,
                ta=ta,
                vlmax=n,
                desc=f"vrgatherei16.vv e{sew} vl=3",
            )
        out_.append(t)

    t = new(
        "vrgather_vrgatherei16_mask",
        "Masked gathers write only active elements; inactive ones keep their value (mu) or may become ones (ma). "
        "vrgather.vv, vrgather.vx and vrgatherei16 at SEW 16 and 32.",
    )
    for sew in (16, 32):
        src = rnd(t, sew, 4)
        for ma in (False, True):
            mask = [1, 0, 0, 1]
            gat(
                t,
                G,
                sew=sew,
                src=src,
                idx=[3, 2, 1, 0],
                vl=4,
                mask=mask,
                ma=ma,
                vlmax=4,
                desc=f"vrgather.vv e{sew} ma={int(ma)}",
            )
            gat(
                t,
                f"vrgather.vx {VD}, {VS2}, x6",
                sew=sew,
                src=src,
                idx=2,
                kind="vx",
                vl=4,
                mask=[0, 1, 1, 0],
                ma=ma,
                vlmax=4,
                desc=f"vrgather.vx 2 e{sew} ma={int(ma)}",
            )
            gat(
                t,
                f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
                sew=sew,
                src=src,
                idx=[1, 1, 3, 3],
                ieew=16,
                vl=4,
                mask=mask,
                ma=ma,
                vlmax=4,
                desc=f"vrgatherei16.vv e{sew} ma={int(ma)}",
            )
    out_.append(t)

    t = new(
        "vrgather-vv_op_vrgatherei16-vv_op",
        "vrgather.vv and vrgatherei16.vv write vd[i] = vs2[vs1[i]] (0 when vs1[i] >= VLMAX): a reversal, a "
        "duplication and an identity permutation at SEW 8, 16, 32, 64, plus one index past VLMAX (2^16-1).",
    )
    for sew in (8, 16, 32, 64):
        n = min(8, 128 // sew * 2)
        lm = "1" if n * sew <= 128 else "2"
        src = rnd(t, sew, n)
        for idx in ([n - 1 - i for i in range(n)], [1] * n, list(range(n))):
            gat(t, G, sew=sew, src=src, idx=idx, vl=n, vlmax=n, lmul=lm, desc=f"vrgather.vv e{sew} {idx}")
            gat(
                t,
                f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
                sew=sew,
                src=src,
                idx=idx,
                ieew=16,
                vl=n,
                vlmax=n,
                lmul=lm,
                desc=f"vrgatherei16.vv e{sew} {idx}",
            )
        gat(
            t,
            f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
            sew=sew,
            src=src,
            idx=[0xFFFF] + list(range(1, n)),
            ieew=16,
            vl=n,
            vlmax=1 << 20,
            lmul=lm,
            desc=f"vrgatherei16.vv e{sew} index 0xffff",
        )
    out_.append(t)

    t = new(
        "vrgather-vv_sew_lmul",
        "vrgather.vv uses SEW/LMUL for both data and indices: at e16/m2 with vl = 16 (two registers at "
        "VLEN=128) the index group v24-v25 and the data group v16-v17 are both read as 16-bit elements, so "
        "indices 8..15 select elements in v17; and an e8 permutation with byte indices.",
    )
    src = rnd(t, 16, 16)
    idx = [15 - i for i in range(16)]
    gat(t, G, sew=16, src=src, idx=idx, vl=16, vlmax=16, lmul="2", desc="vrgather.vv e16 m2 reversed")
    src = rnd(t, 8, 8)
    gat(t, G, sew=8, src=src, idx=[5, 1, 3, 7, 0, 2, 4, 6], vl=8, vlmax=8, desc="vrgather.vv e8")
    out_.append(t)

    t = new(
        "vrgatherei16-vv_sew_lmul",
        "vrgatherei16.vv reads 16-bit indices with EMUL = (16/SEW)*LMUL while the data use SEW/LMUL: at e8/m1, "
        "16 indices fill v24-v25 (EMUL 2); at e32/m2 the 8 indices fit v24 alone (EMUL 1) and v25 holds other "
        "values; index 0x8003 (>= VLMAX) gives 0, not element 3 as an 8-bit index would.",
    )
    src = rnd(t, 8, 16)
    idx = [(i * 5) % 16 for i in range(15)] + [0x8003]
    idx_eff = [j & 255 for j in idx] if MUT == "vrgatherei16_sew_index" else idx
    old = rnd(t, 8, 16)
    t.vload("v25", 16, [0x8003] * 8)
    lab = t.op(
        f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
        sew=8,
        vl=16,
        srcs={VD: (8, "1", old), VS2: (8, "1", src), VS1: (16, "2", idx)},
    )
    t.check_vreg(VD, 8, [src[j] if j < 16 else 0 for j in idx_eff], lab, "vrgatherei16.vv e8 m1, indices in v24-v25")
    src = rnd(t, 32, 8)
    idx = [7, 6, 5, 4, 3, 2, 1, 0]
    t.vload("v25", 16, [0x8003] * 8)
    old = rnd(t, 32, 8)
    lab = t.op(
        f"vrgatherei16.vv {VD}, {VS2}, {VS1}",
        sew=32,
        lmul="2",
        vl=8,
        srcs={VD: (32, "2", old), VS2: (32, "2", src), VS1: (16, "1", idx)},
    )
    t.check_vreg(VD, 32, [src[j] for j in idx], lab, "vrgatherei16.vv e32 m2, indices in v24 only", "2")
    out_.append(t)

    t = new(
        "vrgather_vrgatherei16_id_ge_vlmax",
        "An index >= VLMAX returns 0: at e16/m1 with vs2 = vid + 1 (vs2[i] = i + 1 over the whole register) and "
        "indices VLMAX-1, VLMAX, VLMAX+1, VLMAX+2 (VLMAX read from vsetvli), vd = VLMAX, 0, 0, 0; vrgather.vx with "
        "x = VLMAX gives 0; vrgatherei16 at e32 with index VLMAX gives 0.",
    )
    t.vset("max", 16, "1", rd="x7")
    t.emit(f"vid.v {VS2}")
    t.emit(f"vadd.vi {VS2}, {VS2}, 1")
    t.emit(f"vid.v {VS1}")
    t.emit("addi x6, x7, -1")
    t.emit(f"vadd.vx {VS1}, {VS1}, x6")
    t.vload(VD, 16, [5, 5, 5, 5])
    t.vset(4, 16)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(G)
    t.emit("vmv.x.s x8, v8")
    t.emit("sub x8, x8, x7")
    t.emit("seqz x8, x8")
    t.check_bool("x8", lab, "vrgather.vv index VLMAX-1 gives vs2[VLMAX-1] = VLMAX")
    t.vstore(VD, 16, 4)
    zero = [0, 0, 0] if MUT != "vrgather_vlmax_wrap" else [1, 2, 3]
    t.check_elems(16, [None] + zero, lab, "vrgather.vv indices VLMAX.. give 0")
    t.vload(VD, 16, [5, 5, 5, 5])
    t.vset(4, 16)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vrgather.vx {VD}, {VS2}, x7")
    t.check_vreg(VD, 16, [0] * 4 if MUT != "vrgather_vlmax_wrap" else [1] * 4, lab, "vrgather.vx x = VLMAX")
    t.vset("max", 32, "1", rd="x7")
    t.emit(f"vid.v {VS2}")
    t.emit(f"vadd.vi {VS2}, {VS2}, 1")
    t.vset("max", 16, "f2")
    t.emit(f"vmv.v.x {VS1}, x7")
    t.vload(VD, 32, [5, 5, 5, 5])
    t.vset(4, 32)
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit(f"vrgatherei16.vv {VD}, {VS2}, {VS1}")
    t.check_vreg(VD, 32, [0] * 4 if MUT != "vrgather_vlmax_wrap" else [1] * 4, lab, "vrgatherei16.vv e32 index VLMAX")
    out_.append(t)

    t = new(
        "vrgather-vx_vrgather-vi_op",
        "vrgather.vx/.vi splat vs2[index] to the active elements; the index (x[rs1] or the zero-extended uimm) is "
        "unsigned and not truncated to SEW: at e8, x = 2^31 + 1 is >= VLMAX and gives 0 (not vs2[1]); uimm 3 "
        "selects vs2[3]; x = 1 selects vs2[1]. SEW 8, 32, 64; masked once.",
    )
    for sew in (8, 32, 64):
        src = [t.rand(sew) | 1 for _ in range(4)]
        gat(
            t,
            f"vrgather.vx {VD}, {VS2}, x6",
            sew=sew,
            src=src,
            idx=1,
            kind="vx",
            vl=4,
            vlmax=4,
            desc=f"vrgather.vx 1 e{sew}",
        )
        gat(
            t,
            f"vrgather.vi {VD}, {VS2}, 3",
            sew=sew,
            src=src,
            idx=3,
            kind="vi",
            vl=4,
            vlmax=4,
            desc=f"vrgather.vi 3 e{sew}",
        )
        gat(
            t,
            f"vrgather.vi {VD}, {VS2}, 0",
            sew=sew,
            src=src,
            idx=0,
            kind="vi",
            vl=4,
            vlmax=4,
            mask=[0, 1, 0, 1],
            desc=f"vrgather.vi 0 e{sew} masked",
        )
    src = [t.rand(8) | 1 for _ in range(4)]
    big = X(0x80000001, 0x80000001)
    old = rnd(t, 8, 4)
    lab = t.op(
        f"vrgather.vx {VD}, {VS2}, x6", sew=8, vl=4, xs={"x6": big}, srcs={VD: (8, "1", old), VS2: (8, "1", src)}
    )
    t.check_vreg(VD, 8, [0] * 4 if MUT != "vslideup_offset_trunc" else [src[1]] * 4, lab, "vrgather.vx 2^31+1 e8")
    out_.append(t)

    # ---- compress
    def comp(src: Sequence[int], sel: Sequence[int], vl: int) -> list[int]:
        return [src[i] for i in range(vl) if sel[i]]

    t = new(
        "vcompress_op",
        "vcompress.vm packs the elements of vs2 whose vs1 mask bit is set (among the first vl) into vd's first "
        "elements; the remaining elements are tail: undisturbed under tu (including those below vl), old or ones "
        "under ta. The spec's example (e8, vl = 9, tu): v0 = 1 0 1 0 0 1 0 1 1 from element 0, v1 = 0..8, "
        "v2 = 9..1 -> 0 2 5 7 8 4 3 2 1. Also all and none selected, SEW 16, 32, 64.",
    )
    sel = [1, 0, 1, 0, 0, 1, 0, 1, 1]
    src = list(range(9))
    old = [9, 8, 7, 6, 5, 4, 3, 2, 1]
    for ta in (False, True):
        c = comp(src, sel, 9)
        newv = c + [0] * (9 - len(c))
        legal = pol(old, newv, len(c), 8, ta=ta)
        if MUT == "vcompress_tail_ones":
            legal = c + [0] * (9 - len(c))
        lab = t.op(
            f"vcompress.vm {VD}, {VS2}, v24",
            sew=8,
            vl=9,
            ta=ta,
            srcs={VD: (8, "1", old), VS2: (8, "1", src), "v24": (1, "1", sel)},
        )
        t.check_vreg(VD, 8, legal, lab, f"vcompress.vm spec example ta={int(ta)}")
    for sew in (16, 32, 64):
        n = 4
        src = rnd(t, sew, n)
        for sel in ([1] * n, [0] * n, [0, 1, 1, 0]):
            old = rnd(t, sew, n)
            c = comp(src, sel, n)
            lab = t.op(
                f"vcompress.vm {VD}, {VS2}, v24",
                sew=sew,
                vl=n,
                srcs={VD: (sew, "1", old), VS2: (sew, "1", src), "v24": (1, "1", sel)},
            )
            t.check_vreg(VD, sew, pol(old, c + [0] * (n - len(c)), len(c), sew), lab, f"vcompress.vm e{sew} {sel}")
    out_.append(t)

    t = new(
        "vcompress_enc",
        "vcompress is encoded unmasked (vm=1): the selection comes from vs1, not v0. With v0 = 0 (and v0 = all "
        "ones) the result is the same compression of vs2 by vs1.",
    )
    for v0 in ([0] * 16, [1] * 16):
        t.mload("v0", v0)
        src = rnd(t, 16, 8)
        sel = [1, 1, 0, 0, 1, 0, 1, 0]
        old = rnd(t, 16, 8)
        c = comp(src, sel, 8)
        lab = t.op(
            f"vcompress.vm {VD}, {VS2}, v24",
            sew=16,
            vl=8,
            srcs={VD: (16, "1", old), VS2: (16, "1", src), "v24": (1, "1", sel)},
        )
        t.check_vreg(VD, 16, pol(old, c + [0] * 4, len(c), 16), lab, f"vcompress.vm with v0 = {v0[0]}s")
    out_.append(t)

    t = new(
        "vcompress_vstart_n0_ill",
        "vcompress.vm raises illegal-instruction when vstart != 0 (vstart = 1 and 2, vl = 8); vd is unchanged and "
        "xtval is 0 or the instruction bits.",
    )
    for vs in (1, 2):
        old = rnd(t, 16, 8)
        t.vload(VD, 16, old)
        t.vload(VS2, 16, rnd(t, 16, 8))
        t.mload("v24", [1] * 8)
        t.vset(8, 16)
        t.set_vstart(vs)
        lab = t.ill_window(
            [f"vcompress.vm {VD}, {VS2}, v24"], "ok" if MUT == "vcompress_vstart_ok" else 2, f"vcompress.vm vstart={vs}"
        )
        t.emit("csrwi vstart, 0")
        t.check_vreg(VD, 16, old, lab, "vd unchanged")
    out_.append(t)

    # ---- whole-register moves
    def full_eq(t: VTest, a: str, b: str, nreg: int, lab: str, desc: str, ok: bool = True) -> None:
        """Compare the nreg registers from a and b at e8 over all VLEN bits (vmsne + vcpop): the count of different
        bytes must be 0 (ok) or nonzero (not ok)."""
        lm = str(nreg)
        t.vset("max", 8, lm)
        t.emit(f"vmsne.vv v0, {a}, {b}")
        t.emit("vcpop.m x8, v0")
        if ok:
            t.check("x8", 0, lab, desc)
        else:
            t.emit("snez x8, x8")
            t.check_bool("x8", lab, desc)

    t = new(
        "vmv-nr-r_op",
        "vmv<nr>r.v copies whole registers (all VLEN bits) whatever vl and vtype are: with vtype e32/m1 and vl = 1, "
        "vmv1r/2r/4r/8r copy every byte of the source group (filled with vid at e8 over VLMAX) and leave the "
        "register after the destination group unchanged (compared over all VLEN bits with vmsne/vcpop). With "
        "vstart = 1 at e32 they leave element 0 unchanged and copy the rest, or may raise illegal-instruction "
        "(vstart_vtype_dep); with vtype.vill = 1 they raise illegal-instruction (EEW depends on SEW).",
        issues="Imperas: vmv<nr>r.v did not trap with vtype.vill = 1 (Solvnet case, config/imperas/ci.yaml); "
        "the engineering build fixes it.",
    )
    for nr in (1, 2, 4, 8):
        dst = "v8" if nr < 8 else "v0"
        srcr = "v16"
        t.vset("max", 8, "8")
        t.emit("vid.v v16")
        t.emit("vmv.v.i v24, 0")
        t.emit("vmv.v.i v8, 0" if nr < 8 else "vmv.v.i v0, 0")
        t.vset(1, 32, "1")
        lab = t.label("insn")
        t.emit(f"{lab}:", 0)
        t.emit(f"vmv{nr}r.v {dst}, {srcr}")
        cnt = nr if MUT != "vmvnr_count" or nr != 2 else 1
        if nr < 8:
            full_eq(
                t,
                dst,
                srcr,
                nr if cnt == nr else 1,
                lab,
                f"vmv{nr}r.v: the {nr} destination registers equal the source",
                ok=MUT != "vmvnr_vl",
            )
            if MUT == "vmvnr_count" and nr == 2:
                full_eq(t, "v9", "v17", 1, lab, "vmv2r.v copies one register (mutant): v9 differs from v17", ok=False)
            nxt = f"v{8 + nr}"
            t.vset("max", 8, "1")
            t.emit(f"vmsne.vi v0, {nxt}, 0")
            t.emit("vcpop.m x8, v0")
            t.check("x8", 0, lab, f"vmv{nr}r.v: {nxt} (after the destination group) unchanged")
        else:
            t.vset("max", 8, "8")
            t.emit("vmsne.vv v24, v0, v16")
            t.emit("vcpop.m x8, v24")
            t.check("x8", 0, lab, "vmv8r.v v0, v16: v0-v7 equal v16-v23")
    # vstart
    t.vload(VD, 32, [1, 2, 3, 4])
    t.vload(VS2, 32, [5, 6, 7, 8])
    t.vset(4, 32, "1")
    t.set_vstart(1)
    lab = t.ill_window([f"vmv1r.v {VD}, {VS2}"], ["ok", 2], "vmv1r.v vstart=1")
    t.emit("addi x6, x14, 1")
    t.emit("csrwi vstart, 0")
    t.either(
        "x6",
        lambda: t.check_vreg(VD, 32, [1, 2, 3, 4], lab, "vmv1r.v trapped: vd unchanged"),
        lambda: t.check_vreg(VD, 32, [1, 6, 7, 8], lab, "vmv1r.v vstart=1: element 0 unchanged"),
    )
    # vill
    t.li("x6", 0x38)  # vsew = 7 (reserved): vill
    t.emit("vsetvl x7, x0, x6")
    lab = t.ill_window([f"vmv1r.v {VD}, {VS2}"], 2, "vmv1r.v with vtype.vill = 1")
    t.vset(1, 32)
    out_.append(t)

    t = new(
        "vmv-nr-r_enc",
        "vmv<nr>r.v is OPIVI with imm[2:0] = NREG-1: the encodings with simm5 = 0, 1, 3, 7 (emitted as .word, "
        "vd = v8, vs2 = v16) copy exactly 1, 2, 4 and 8 registers: the destination group equals the source and "
        "the register after it (v9, v10, v12; v16-v23 for NREG 8 into v8 overlaps no further group) is unchanged.",
    )
    for nr in (1, 2, 4, 8):
        enc = (0x27 << 26) | (1 << 25) | (16 << 20) | ((nr - 1) << 15) | (3 << 12) | (8 << 7) | 0x57
        t.vset("max", 8, "8")
        t.emit("vid.v v16")
        t.emit("vmv.v.i v8, 0")
        t.emit("vmv.v.i v24, 0")
        t.vset(1, 64, "1")
        lab = t.label("insn")
        t.emit(f"{lab}:", 0)
        t.emit(f".word 0x{enc:08x}  // vmv{nr}r.v v8, v16")
        full_eq(
            t,
            "v8",
            "v16",
            nr if not (MUT == "vmvnr_count" and nr == 2) else 1,
            lab,
            f"simm5 {nr - 1}: v8.. equals v16.. over {nr} registers",
        )
        if MUT == "vmvnr_count" and nr == 2:
            full_eq(t, "v9", "v17", 1, lab, "simm5 1 copies one register (mutant): v9 differs from v17", ok=False)
        if nr < 8:
            t.vset("max", 8, "1")
            t.emit(f"vmsne.vi v0, v{8 + nr}, 0")
            t.emit("vcpop.m x8, v0")
            t.check("x8", 0, lab, f"simm5 {nr - 1}: v{8 + nr} unchanged")
    out_.append(t)

    # ---- FP scalar moves
    t = new(
        "vfmv-f-s_vfmv-s-f_ignorelmul",
        "vfmv.f.s and vfmv.s.f ignore LMUL (EMUL = 1): at e64/m8 they use v9 (not a multiple of 8) without "
        "trapping; vfmv.s.f writes only v9[0] (v9[1] tail, tu) and v10 is unchanged.",
    )
    t.vload("v9", 64, [F(3.5, 64), 0x1111])
    t.vload("v10", 64, [0x2222, 0x3333])
    t.vset(8, 64, "8")
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("vfmv.f.s f2, v9")
    t.check_freg("f2", 64, F(3.5, 64), lab, "vfmv.f.s f2, v9 at m8")
    t.fload("f1", F(-0.75, 64), 64)
    t.vset(8, 64, "8")
    lab = t.label("insn")
    t.emit(f"{lab}:", 0)
    t.emit("vfmv.s.f v9, f1")
    t.check_vreg("v9", 64, [F(-0.75, 64), 0x1111], lab, "vfmv.s.f v9 at m8")
    t.check_vreg("v10", 64, [0x2222, 0x3333], lab, "v10 unchanged")
    out_.append(t)

    t = new(
        "vfmv-f-s_op",
        "vfmv.f.s copies element 0 to f[rd]: at SEW 64 all 64 bits; at SEW 32 the value is NaN-boxed in the "
        "64-bit f register (upper 32 bits all ones). NaN payloads (sNaN, qNaN with payload) are copied as is, "
        "with no flag. It also writes f[rd] with vl = 0.",
    )
    for w, v in ((32, F(1.5, 32)), (32, snan(32)), (64, qnan(64, 0x1234)), (64, F(-2.0, 64))):
        for vl in (1, 0):
            t.fload("f2", 0x0123456789ABCDEF, 64)
            lab = t.op("vfmv.f.s f2, v16", sew=w, vl=vl, srcs={VS2: (w, "1", [v, 0])}, clear_flags=True)
            exp = v if w == 64 else (v | (0xFFFFFFFF << 32) if MUT != "vfmvfs_no_box" else v)
            t.check_fflags(0, lab, "vfmv.f.s")
            t.check_freg("f2", 64, exp, lab, f"vfmv.f.s e{w} 0x{v:x} vl={vl}")
    out_.append(t)

    t = new(
        "vfmv-s-f_op",
        "vfmv.s.f writes f[rs1] to element 0; elements 1.. of that register are tail (tu: unchanged; ta: old or "
        "ones). At SEW 32 a NaN-boxed f register gives its low 32 bits and one that is not NaN-boxed gives the "
        "canonical NaN; NaN payloads otherwise pass unchanged. SEW 32 and 64.",
    )
    for w, fb, fw in ((32, F(2.5, 32), 32), (32, snan(32), 32), (32, 0x0000000040200000, 64), (64, qnan(64, 7), 64)):
        for ta in (False, True):
            old = rnd(t, w, 128 // w)
            t.fload("f1", fb, fw)
            exp = fb if fw == w else (CNAN[32] if MUT != "vfmvsf_unboxed_used" else fb & 0xFFFFFFFF)
            lab = t.op("vfmv.s.f v16, f1", sew=w, vl=2, ta=ta, srcs={VS2: (w, "1", old)})
            t.check_vreg(VS2, w, [exp] + pol(old[1:], old[1:], 0, w, ta=ta), lab, f"vfmv.s.f e{w} ta={int(ta)}")
    out_.append(t)

    t = new(
        "vfmv-s-f_vstart_ge_vl",
        "vfmv.s.f with vstart >= vl does nothing: vl = 0 (vta = 0 and 1) leaves the register unchanged; vstart = 1 "
        "with vl = 1 also leaves it unchanged or may raise illegal-instruction (vstart_vtype_dep).",
    )
    for ta in (False, True):
        old = rnd(t, 64, 2)
        t.fload("f1", F(1.0, 64), 64)
        lab = t.op("vfmv.s.f v16, f1", sew=64, vl=0, ta=ta, srcs={VS2: (64, "1", old)})
        t.check_vreg(
            VS2, 64, old if MUT != "vmvsx_vl0_writes" else [F(1.0, 64), old[1]], lab, f"vfmv.s.f vl=0 ta={int(ta)}"
        )
    old = rnd(t, 32, 4)
    t.vload(VS2, 32, old)
    t.fload("f1", F(1.0, 32), 32)
    t.vset(1, 32)
    t.set_vstart(1)
    lab = t.ill_window(["vfmv.s.f v16, f1"], ["ok", 2], "vfmv.s.f vstart=1 vl=1")
    t.emit("csrwi vstart, 0")
    t.check_vreg(VS2, 32, old, lab, "vfmv.s.f vstart=1 vl=1: unchanged")
    out_.append(t)
    return out_


# ==================================================================== FP state (mstatus.FS / vsstatus.FS)
FS_INSNS = [  # (instruction, what it modifies)
    (f"vfadd.vv {VD}, {VS2}, {VS1}", "fflags"),
    ("vfmv.f.s f2, v16", "f2"),
    (f"vfmv.s.f {VD}, f1", "nothing"),
    (f"vmfeq.vv {VD}, {VS2}, {VS1}", "fflags"),
    (f"vfredosum.vs {VD}, {VS2}, {VS1}", "fflags"),
    (f"vfcvt.x.f.v {VD}, {VS2}", "fflags"),
    (f"vfmv.v.f {VD}, f1", "nothing"),
    (f"vfwcvt.f.f.v {VD}, {VS2}", "fflags"),
    (f"vfsgnj.vv {VD}, {VS2}, {VS1}", "nothing"),
]


def fs_setup(t: VTest) -> None:
    """Operands that make every FS_INSNS entry raise a flag where it can: vs2 = [1 + 2^-23 * 3, sNaN] (inexact
    conversions and sums, NV on compares)."""
    t.vload(VS2, 32, [F(1 + Fr(3, 2**23), 32), snan(32)])
    t.vload(VS1, 32, [F(Fr(1, 2**30), 32), F(1.0, 32)])
    t.fload("f1", F(2.0, 32), 32)
    t.vset(2, 32)


def g_fs() -> list[VTest]:
    out_: list[VTest] = []
    FS = 0x6000

    for suffix, csr, boot, req in (("", "sstatus", "S", ["I", "V", "S"]), ("_Sm", "mstatus", "M", ["I", "V", "Sm"])):
        t = new(
            "mstatus_fs_off_V_fp_ill",
            f"With {csr}.FS = Off every vector FP instruction raises illegal-instruction (xtval 0 or the "
            "instruction bits): vfadd, vfmv.f.s, vfmv.s.f, vmfeq, vfredosum, vfcvt, vfmv.v.f, vfwcvt.f.f, "
            "vfsgnj; the destination is not written. Integer vector instructions (vadd.vv) still execute. "
            f"Runs in {'S' if boot == 'S' else 'M'}-mode{' (sstatus.FS is mstatus.FS)' if boot == 'S' else ''}.",
            required=req,
            boot=boot,
            suffix=suffix,
        )
        fs_setup(t)
        old = rnd(t, 32, 2)
        t.vload(VD, 32, old)
        t.vset(2, 32)
        t.li("x6", FS)
        t.emit(f"csrc {csr}, x6")
        for insn, _ in FS_INSNS:
            t.ill_window([insn], "ok" if MUT == "fs_off_ok" else 2, f"{insn.split()[0]} with FS = Off")
        lab = t.ill_window([f"vadd.vv v12, {VS2}, {VS1}"], "ok", "vadd.vv with FS = Off")
        t.li("x6", FS)
        t.emit(f"csrs {csr}, x6")
        t.check_vreg(VD, 32, old, lab, "vd unchanged by the trapping FP instructions")
        out_.append(t)

        t = new(
            "mstatus_fs_dirty_V_fp",
            f"A vector FP instruction that modifies FP state sets {csr}.FS to Dirty: from FS = Clean, vfadd.vv "
            "raising NX, vmfeq.vv raising NV (sNaN), vfredosum and vfcvt.x.f.v and vfwcvt.f.f.v raising flags, and "
            "vfmv.f.s (writes an f register) each leave FS = Dirty (fflags is cleared first, so each flag is a change). Instructions that change no FP state "
            "(vfmv.s.f, vfmv.v.f, vfsgnj) may leave FS Clean or Dirty, so they are not checked. Runs in "
            f"{boot}-mode.",
            required=req,
            boot=boot,
            suffix=suffix,
        )
        for insn, what in FS_INSNS:
            if what == "nothing":
                continue
            fs_setup(t)
            t.clear_fflags()  # so the instruction changes fflags (this write dirties FS before it is set Clean)
            t.li("x6", FS)
            t.emit(f"csrc {csr}, x6")
            t.li("x6", 0x4000)
            t.emit(f"csrs {csr}, x6")  # Clean
            lab = t.label("insn")
            t.emit(f"{lab}:", 0)
            t.emit(insn)
            t.emit(f"csrr x8, {csr}")
            t.check_masked(
                "x8",
                FS,
                FS if MUT != "fs_not_dirty" else 0x4000,
                lab,
                f"{insn.split()[0]} ({what}) from FS = Clean: FS = Dirty",
            )
        out_.append(t)

    VSF = ["I", "V", "S", "H"]
    t = new(
        "vsstatus_mstatus_fs_off_hypervisor_V_fp_ill",
        "With V = 1, vsstatus.FS also gates vector FP: in VS-mode, vfadd.vv and vfmv.f.s raise illegal-instruction "
        "when vsstatus.FS = Off (sstatus.FS Dirty) and when sstatus.FS (= mstatus.FS) = Off (vsstatus.FS Dirty); "
        "with both Dirty they execute; vadd.vv executes with vsstatus.FS = Off. Also in VU-mode with "
        "vsstatus.FS = Off.",
        required=VSF,
        boot="S",
    )
    fs_setup(t)
    t.li("x6", 0x600)
    t.emit("csrs vsstatus, x6")  # vsstatus.VS = Dirty
    for vsfs, sfs, exp in ((0, 3, 2), (3, 0, 2), (3, 3, "ok")):
        t.li("x6", FS)
        t.emit("csrc vsstatus, x6")
        t.emit("csrc sstatus, x6")
        if vsfs:
            t.emit("csrs vsstatus, x6")
        if sfs:
            t.emit("csrs sstatus, x6")
        e = "ok" if MUT == "fs_off_ok" else exp
        for insn in (FS_INSNS[0][0], FS_INSNS[1][0]):
            t.window("VS", [insn], e, f"{insn.split()[0]} vsstatus.FS={vsfs} sstatus.FS={sfs}")
        t.li("x6", FS)
        t.emit("csrs sstatus, x6")
    t.li("x6", FS)
    t.emit("csrc vsstatus, x6")
    t.window("VS", [f"vadd.vv v12, {VS2}, {VS1}"], "ok", "vadd.vv vsstatus.FS=0")
    t.window("VU", [FS_INSNS[0][0]], "ok" if MUT == "fs_off_ok" else 2, "vfadd.vv vsstatus.FS=0")
    t.li("x6", FS)
    t.emit("csrs vsstatus, x6")
    out_.append(t)

    t = new(
        "vsstatus_mstatus_fs_dirty_hypervisor_V_fp",
        "With V = 1, a vector FP instruction that modifies FP state sets both mstatus.FS (sstatus.FS in HS-mode) "
        "and vsstatus.FS to Dirty: from both Clean, vfadd.vv raising NX and vfmv.f.s in VS-mode leave both "
        "Dirty.",
        required=VSF,
        boot="S",
    )
    t.li("x6", 0x600)
    t.emit("csrs vsstatus, x6")
    for insn, what in (FS_INSNS[0], FS_INSNS[1]):
        fs_setup(t)
        t.clear_fflags()
        for c in ("vsstatus", "sstatus"):
            t.li("x6", FS)
            t.emit(f"csrc {c}, x6")
            t.li("x6", 0x4000)
            t.emit(f"csrs {c}, x6")
        lab = t.window("VS", [insn], "ok", f"{insn.split()[0]} in VS-mode")
        for c in ("sstatus", "vsstatus"):
            t.emit(f"csrr x8, {c}")
            t.check_masked(
                "x8",
                FS,
                FS if MUT != "fs_not_dirty" else 0x4000,
                lab,
                f"{insn.split()[0]} ({what}) in VS-mode: {c}.FS = Dirty",
            )
    out_.append(t)
    return out_


def gen() -> list[VTest]:
    tests: list[VTest] = []
    tests += g_int()
    tests += g_fixed()
    tests += g_fp()
    tests += g_red()
    tests += g_mask()
    tests += g_perm()
    tests += g_fs()
    names = [t.rule + t.suffix for t in tests]
    dup = {r for r in names if names.count(r) > 1}
    assert not dup, f"duplicate rules: {dup}"
    return tests


def main() -> None:
    only = set(sys.argv[1:])
    for t in gen():
        if only and t.rule not in only:
            continue
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
