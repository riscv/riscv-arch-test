##################################
# cp_custom_vfredusum.py
#
# Range-checked tests for the unordered floating-point sum reductions vfredusum.vs and vfwredusum.vs.
# david_harris@hmc.edu Oct 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Tests for vfredusum.vs and vfwredusum.vs that accept every legal reduction tree.

The result of an unordered reduction depends on the tree and on the format of each node, so these tests do not
compare vd[0] with the reference model's value. For each testcase, _redusum_model computes every legal outcome at
generation time, and the assembly checks that vd[0] is one of them and that fflags holds every flag that must be
raised and no flag that cannot be. A passing check records 0 in the signature; a failing one records the result
(never 0) and fflags | 0x100, so the failure report shows what the DUT produced; its expected value 0 is the pass
code, and the legal range is in the comments after the testcase label in the generated test.

The reductions use LMUL=8 so that vl can reach VLMAX = 8*VLEN/SEW. The preprocessor removes testcases whose vl
exceeds VLMAX for the configuration. vl = 1 is left to the regular edge-value tests: one element and the scalar
have a single legal result.
"""

import random
from dataclasses import dataclass, fields

from testgen.asm.helpers import write_sigupd
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector import _redusum_model as model
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# 7 is the largest vl below every possible VLMAX at LMUL=8; 8, 16, ... 512 reach VLMAX
_VL_SWEEP = (2, 3, 4, 7, 8, 16, 32, 64, 128, 256, 512)
_DETERMINISM_VLS = (3, 7)
_NOACTIVE_VL = 7
_LMUL = 8
_MASK_BITS = 8 * VLEN_MAX // 16  # VLMAX at SEW=16, LMUL=8 and the largest VLEN ACT supports
_REPORT_FLAGS = 0x100  # set in a failing fflags report so that fflags = 0 still reads as a failure


@dataclass
class _IntRegs:
    """Integer registers of one testcase."""

    addr: int  # data addresses
    vl: int  # requested vl
    tmp: int  # vsetvli result and short-lived values
    flags: int  # fflags after the reduction
    legal: int  # 1 if vd[0] is legal or matches
    result: int  # signature value for vd[0]
    scratch: int
    flags_first: int  # fflags of the first determinism result
    flags_rdn: int  # fflags of the RDN determinism result


@dataclass
class _VecRegs:
    """Vector registers of one testcase; v0 is always the mask."""

    vs2: int  # LMUL=8 element group
    vs2_repeat: int  # LMUL=8 element group for the repeated determinism run
    vs1: int
    vs1_repeat: int
    vd: int
    vd_repeat: int
    first: int  # first determinism result
    first_rdn: int  # RDN determinism result
    key: int  # order key of vd[0]
    sign: int  # sign bit
    ref: int  # reference value or lower bound
    ref_hi: int  # upper bound or shifted copy
    match: int  # comparison mask
    match_hi: int  # second comparison mask


class _Ctx:
    """Per-call state: instruction, element and accumulator formats, and the testcases built so far."""

    def __init__(self, instr_name: str, coverpoint: str, test_data: TestData) -> None:
        assert test_data.config.sew is not None, "SEW must be provided for vector tests"
        self.instr = instr_name
        self.coverpoint = coverpoint
        self.td = test_data
        self.sew = test_data.config.sew
        self.widening = instr_name.startswith("vfw")
        self.efmt = model.FORMATS[self.sew]
        self.acc = model.FORMATS[2 * self.sew] if self.widening else self.efmt
        self.w = self.acc.width
        self.vlmax = _LMUL * VLEN_MAX // self.sew
        self.prefix = f"redusum_{'w' if self.widening else ''}e{self.sew}"
        self.chunks: list[TestChunk] = []
        self.labels: list[str] = []
        self.x = _IntRegs(*(0,) * len(fields(_IntRegs)))
        self.v = _VecRegs(*(0,) * len(fields(_VecRegs)))

    def skip(self) -> bool:
        return self.sew > self.td.config.flen

    def data(self, name: str, elems: list[int], width: int) -> str:
        """Register a data label used by the current testcase."""
        label = f"{self.prefix}_{name}"
        self.td.register_vector_data(label, width, elements=elems)
        self.labels.append(label)
        return label

    def acc_const(self, name: str, value: int) -> str:
        return self.data(f"{name}_{value:x}", [value], self.w)

    def begin(self) -> list[str]:
        """Start a testcase chunk with fresh registers; return its (empty) list of lines."""
        self.td.begin_test_chunk()
        self.labels = []
        self.x = _IntRegs(*self.td.int_regs.get_registers(len(fields(_IntRegs)), exclude_regs=[0]))
        vec_regs = self.td.vec_regs
        vec_regs.consume_registers([0])
        groups = vec_regs.get_registers(2, lmul=_LMUL)
        singles = vec_regs.get_registers(len(fields(_VecRegs)) - 2)
        self.v = _VecRegs(*groups, *singles)
        return []

    def end(self, lines: list[str]) -> None:
        tc = self.td.test_chunk
        assert tc is not None
        tc.code.extend(lines)
        for label in dict.fromkeys(self.labels):
            elems, width = self.td.vector_labels[label]
            tc.vector_labels.append((label, elems, width))
        self.td.int_regs.return_registers(list(vars(self.x).values()))
        self.td.vec_regs.return_registers([0, *vars(self.v).values()])
        self.chunks.append(self.td.end_test_chunk())


# ---------------------------------------------------------------------------------------------------------------
# Operand values
# ---------------------------------------------------------------------------------------------------------------


def _fval(fmt: model.Fmt, mant: int, exp: int) -> int:
    """Encode mant * 2^exp, which must be exactly representable in fmt."""
    shift = exp + fmt.q
    mag = abs(mant)
    if shift >= 0:
        scaled = mag << shift
    else:
        assert mag & ((1 << -shift) - 1) == 0, "value below the smallest subnormal"
        scaled = mag >> -shift
    return model.encode(-scaled if mant < 0 else scaled, mant < 0, fmt)


def _edge_values(fmt: model.Fmt) -> dict[str, int]:
    """Edge values by class name."""
    return {
        "pos0": 0,
        "neg0": fmt.sign_bit,
        "posinf": fmt.pos_inf,
        "neginf": fmt.pos_inf | fmt.sign_bit,
        "qnan": fmt.canonical_nan,
        "negqnanpayload": fmt.canonical_nan | fmt.sign_bit | 1,
        "snan": fmt.pos_inf | 1,
        "posmax": model.encode(fmt.max_norm, False, fmt),
        "negmax": model.encode(-fmt.max_norm, False, fmt),
        "minsub": 1,
        "neg1": _fval(fmt, -1, 0),
        "onepulp": _fval(fmt, (1 << (fmt.prec - 1)) + 1, 1 - fmt.prec),
    }


def _mild_family(ctx: _Ctx, scale: int = 0, negate: bool = False) -> tuple[int, list[int]]:
    """
    Somewhat order-dependent data: scalar 2^t and every element c = 0.75 ulp(2^t) in the accumulator format.
    Adding the elements to the scalar one at a time rounds each one to 0 or 1 ulp, while adding them together
    first keeps their sum, so the legal results spread by about one ulp per four elements.
    """
    exp = (1 if ctx.widening and ctx.sew == 16 else 0) + scale
    sign = -1 if negate else 1
    elem = _fval(ctx.efmt, 3 * sign, exp - ctx.acc.prec - 1)
    return _fval(ctx.acc, sign, exp), [elem] * ctx.vlmax


def _cancel_family(ctx: _Ctx, vl: int, scale: int = 0, negate: bool = False) -> tuple[int, list[int]]:
    """
    Maximally order-dependent data: element 0 is +B, element n-1 is -B, up to eight copies of t = 3/8 ulp(B) lie
    evenly between them, and the other elements are alternating signed zeros. The scalar is also t. Absorbing each
    t into +-B before they cancel loses it or rounds it up to a whole ulp(B), while adding the ts together first
    keeps them, so the legal results range from 0 to well above the exact sum.
    """
    exp_big = ctx.efmt.emax if ctx.widening else ctx.acc.prec + 1
    exp_small = exp_big - ctx.acc.prec + 1 - 3
    sign = -1 if negate else 1
    small = _fval(ctx.efmt, 3 * sign, exp_small + scale)
    elems = [ctx.efmt.sign_bit if i % 2 else 0 for i in range(vl)]
    elems[0] = _fval(ctx.efmt, sign, exp_big + scale)
    if vl >= 3:
        elems[vl - 1] = _fval(ctx.efmt, -sign, exp_big + scale)
    elif vl == 2:
        elems[1] = small
    inner = list(range(1, vl - 1))
    num_small = min(len(inner), 8)
    for j in range(num_small):
        elems[inner[(j * len(inner)) // num_small]] = small
    return _fval(ctx.acc, 3 * sign, exp_small + scale), elems


def _random_mask() -> list[int]:
    """Pseudo-random mask bytes covering _MASK_BITS elements (about half active), reproducible because the
    coverpoint registry seeds the generator per instruction and coverpoint.

    Elements 0 and 2 are active and element 1 is not, so every vl in the sweep has active and inactive elements.
    """
    mask = [random.randrange(256) for _ in range(_MASK_BITS // 8)]
    mask[0] = (mask[0] & ~0b111) | 0b101
    return mask


def _active(elems: list[int], mask: list[int] | None, vl: int) -> list[int]:
    if mask is None:
        return elems[:vl]
    return [elems[i] for i in range(vl) if mask[i // 8] >> (i % 8) & 1]


def _outcomes(ctx: _Ctx, scalar: int, active: list[int], mode: int) -> model.Result:
    res = model.exact_bits(scalar, active, mode, ctx.sew, ctx.widening)
    if res is None:
        res = model.reduce_bits(scalar, active, mode, ctx.sew, ctx.widening)
    return res


def _same(first: model.Result, second: model.Result) -> bool:
    names = ("lo_bits", "hi_bits", "pos_inf", "neg_inf", "nan", "may", "must", "passthrough")
    return all(getattr(first, name) == getattr(second, name) for name in names)


# ---------------------------------------------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------------------------------------------


def _vlmax_expr(ctx: _Ctx) -> str:
    return f"(UDB_VLEN * {_LMUL} / {ctx.sew})"


def _guard(ctx: _Ctx, vl: int, at_vlmax: bool = False) -> list[str]:
    """Compile a testcase only if vl fits (or, if at_vlmax, only if vl is VLMAX). VLMAX >= 8 at LMUL=8."""
    if at_vlmax:
        return [f"#if {_vlmax_expr(ctx)} == {vl}"]
    return [f"#if {_vlmax_expr(ctx)} >= {vl}"] if vl > _LMUL else []


def _endguard(ctx: _Ctx, vl: int, at_vlmax: bool = False) -> list[str]:
    return ["#endif"] if _guard(ctx, vl, at_vlmax) else []


def _load(
    ctx: _Ctx,
    vl: int,
    elems: str,
    scalar: str,
    mask: str | None = None,
    vd_init: str | None = None,
    repeat: bool = False,
) -> list[str]:
    """Set vl at LMUL=8 and load vs2, the mask, vs1[0] and optionally vd[0] (the repeat registers if repeat)."""
    x = ctx.x
    vs2, vs1, vd = _operands(ctx, repeat)
    lines = [
        f"LI(x{x.vl}, {vl}) # vl",
        f"vsetvli x{x.tmp}, x{x.vl}, e{ctx.sew}, m{_LMUL}, tu, mu",
        f"LA(x{x.addr}, {elems})",
        f"vle{ctx.sew}.v v{vs2}, (x{x.addr}) # vs2 elements",
    ]
    if mask is not None:
        lines += [f"LA(x{x.addr}, {mask})", f"vlm.v v0, (x{x.addr}) # mask"]
    lines += [
        f"vsetivli x0, 1, e{ctx.w}, m1, tu, mu",
        f"LA(x{x.addr}, {scalar})",
        f"vle{ctx.w}.v v{vs1}, (x{x.addr}) # vs1[0]",
    ]
    if vd_init is not None:
        lines += [f"LA(x{x.addr}, {vd_init})", f"vle{ctx.w}.v v{vd}, (x{x.addr}) # vd sentinel"]
    lines.append(f"vsetvli x{x.tmp}, x{x.vl}, e{ctx.sew}, m{_LMUL}, tu, mu")
    return lines


def _operands(ctx: _Ctx, repeat: bool) -> tuple[int, int, int]:
    """vs2, vs1 and vd of the main run, or of the repeated determinism run."""
    v = ctx.v
    return (v.vs2_repeat, v.vs1_repeat, v.vd_repeat) if repeat else (v.vs2, v.vs1, v.vd)


def _reduce(ctx: _Ctx, mode: int, label_line: str, masked: bool = False, repeat: bool = False) -> list[str]:
    vs2, vs1, vd = _operands(ctx, repeat)
    return [
        f"fsrmi {mode} # frm = {model.MODE_NAMES[mode].upper()}",
        "fsflagsi 0 # clear fflags",
        label_line,
        f"{ctx.instr} v{vd}, v{vs2}, v{vs1}{', v0.t' if masked else ''}",
        f"csrr x{ctx.x.flags}, fflags",
        "fsrmi 0",
        f"vsetivli x0, 1, e{ctx.w}, m1, tu, mu",
    ]


def _sign_lines(ctx: _Ctx) -> list[str]:
    """v{sign} = sign bit; x{tmp} = width - 1."""
    tmp, sign = ctx.x.tmp, ctx.v.sign
    return [f"LI(x{tmp}, {ctx.w - 1})", f"vmv.v.i v{sign}, 1", f"vsll.vx v{sign}, v{sign}, x{tmp} # sign bit"]


def _report(ctx: _Ctx, value_ok: int, flags_ok: int, src: int) -> list[str]:
    """Record 0 for a pass; otherwise the result (never 0) and fflags | 0x100."""
    result, scratch, flags = ctx.x.result, ctx.x.scratch, ctx.x.flags
    return [
        f"vmv.x.s x{result}, v{src} # result for the failure report",
        f"seqz x{scratch}, x{result}",
        f"or x{result}, x{result}, x{scratch} # never 0",
        f"addi x{scratch}, x{value_ok}, -1 # 0 if vd[0] is legal",
        f"and x{result}, x{result}, x{scratch}",
        write_sigupd(result, ctx.td),
        f"ori x{scratch}, x{flags}, {_REPORT_FLAGS}",
        f"addi x{flags_ok}, x{flags_ok}, -1 # 0 if fflags are legal",
        f"and x{scratch}, x{scratch}, x{flags_ok}",
        write_sigupd(scratch, ctx.td),
    ]


def _check(ctx: _Ctx, res: model.Result) -> list[str]:
    """Check vd[0] and fflags against every legal outcome in res."""
    x, v = ctx.x, ctx.v
    lines: list[str] = []
    if res.passthrough is not None:
        # No active elements and a NaN scalar: vs1[0] unchanged with no flags, or canonicalized
        canon = ctx.acc_const("canon_nan", ctx.acc.canonical_nan)
        lines += [
            f"vmseq.vv v{v.match}, v{v.vd}, v{v.vs1} # vs1[0] unchanged",
            f"vcpop.m x{x.legal}, v{v.match}",
            f"seqz x{x.tmp}, x{x.flags} # with no flags",
            f"and x{x.legal}, x{x.legal}, x{x.tmp}",
            f"LA(x{x.addr}, {canon})",
            f"vle{ctx.w}.v v{v.ref}, (x{x.addr})",
            f"vmseq.vv v{v.match}, v{v.vd}, v{v.ref} # or the canonical NaN",
            f"vcpop.m x{x.scratch}, v{v.match}",
            f"xori x{x.tmp}, x{x.flags}, {res.passthrough_canon_flags:#x}",
            f"seqz x{x.tmp}, x{x.tmp} # with NV exactly when vs1[0] is a signaling NaN",
            f"and x{x.scratch}, x{x.scratch}, x{x.tmp}",
            f"or x{x.legal}, x{x.legal}, x{x.scratch}",
            f"mv x{x.tmp}, x{x.legal}",
        ]
        return lines + _report(ctx, x.legal, x.tmp, v.vd)
    if res.lo_bits is not None:
        assert res.hi_bits is not None
        lo = ctx.acc_const("key", model.key_of_bits(res.lo_bits, ctx.w))
        hi = ctx.acc_const("key", model.key_of_bits(res.hi_bits, ctx.w))
        lines += _sign_lines(ctx)
        lines += [
            f"vsra.vx v{v.key}, v{v.vd}, x{x.tmp} # all ones if negative",
            f"vor.vv v{v.key}, v{v.key}, v{v.sign}",
            f"vxor.vv v{v.key}, v{v.key}, v{v.vd} # order key of vd[0]",
            f"LA(x{x.addr}, {lo})",
            f"vle{ctx.w}.v v{v.ref}, (x{x.addr}) # key of the lowest legal value {res.lo_bits:#x}",
            f"LA(x{x.addr}, {hi})",
            f"vle{ctx.w}.v v{v.ref_hi}, (x{x.addr}) # key of the highest legal value {res.hi_bits:#x}",
            f"vmsleu.vv v{v.match}, v{v.key}, v{v.ref_hi} # key <= highest",
            f"vmsleu.vv v{v.match_hi}, v{v.ref}, v{v.key} # lowest <= key",
            f"vmand.mm v{v.match}, v{v.match}, v{v.match_hi}",
        ]
    else:
        lines.append(f"vmclr.m v{v.match} # no finite result is legal")
    for allowed, name, value in (
        (res.pos_inf, "pos_inf", ctx.acc.pos_inf),
        (res.neg_inf, "neg_inf", ctx.acc.pos_inf | ctx.acc.sign_bit),
        (res.nan, "canon_nan", ctx.acc.canonical_nan),
    ):
        if allowed:
            label = ctx.acc_const(name, value)
            lines += [
                f"LA(x{x.addr}, {label})",
                f"vle{ctx.w}.v v{v.ref}, (x{x.addr})",
                f"vmseq.vv v{v.match_hi}, v{v.vd}, v{v.ref} # or {name}",
                f"vmor.mm v{v.match}, v{v.match}, v{v.match_hi}",
            ]
    lines += [
        f"vcpop.m x{x.legal}, v{v.match} # 1 if vd[0] is legal",
        f"andi x{x.tmp}, x{x.flags}, {~res.may & 0x1F:#x} # flags that cannot be raised",
        f"andi x{x.scratch}, x{x.flags}, {res.must:#x}",
        f"xori x{x.scratch}, x{x.scratch}, {res.must:#x} # required flags that are missing",
        f"or x{x.tmp}, x{x.tmp}, x{x.scratch}",
        f"seqz x{x.tmp}, x{x.tmp} # 1 if fflags are legal",
    ]
    return lines + _report(ctx, x.legal, x.tmp, v.vd)


# ---------------------------------------------------------------------------------------------------------------
# Coverpoint generators
# ---------------------------------------------------------------------------------------------------------------


@add_coverpoint_generator("cp_custom_vfredusum_sweep")
def cp_custom_vfredusum_sweep(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    vl = 2, 3, 4, 7, 8, 16, ... VLMAX at every rounding mode, unmasked, with a pseudo-random mask and with no
    active elements, for data whose sum differs by a few ulps by tree (mild) or ranges from 0 to well above the
    exact sum by tree (cancel).
    """
    del instr_type
    ctx = _Ctx(instr_name, coverpoint, test_data)
    if ctx.skip():
        return []
    sweep = [vl for vl in _VL_SWEEP if vl <= ctx.vlmax]
    mild_scalar, mild_elems = _mild_family(ctx)
    data = [("mild", mild_scalar, mild_elems, vl) for vl in sweep]
    data += [("cancel", *_cancel_family(ctx, vl), vl) for vl in sweep]

    masks = {
        "unmasked": None,
        "masked": (f"{ctx.prefix}_mask_random", _random_mask()),
        "noactive": (f"{ctx.prefix}_mask_zero", [0] * (_MASK_BITS // 8)),
    }
    for family, scalar, elems, vl in data:
        for mask_tag, mask in masks.items():
            for mode in model.MODES:
                active = elems[:vl] if mask is None else _active(elems, mask[1], vl)
                res = (
                    _outcomes(ctx, scalar, active, mode)
                    if active
                    else model.reduce_bits(scalar, [], mode, ctx.sew, ctx.widening)
                )
                scalar_label = f"{ctx.prefix}_{family}_scalar"
                elems_label = f"{ctx.prefix}_{family}_elems" + (f"_n{vl}" if family == "cancel" else "")
                _data_case(
                    ctx,
                    f"{family}_vl{vl}_{mask_tag}_{model.MODE_NAMES[mode]}",
                    f"{family} data, vl={vl}, {mask_tag}, frm={model.MODE_NAMES[mode]}",
                    vl,
                    mode,
                    (scalar_label, [scalar], ctx.w),
                    (elems_label, elems, ctx.sew),
                    None if mask is None else (mask[0], mask[1], 8),
                    res,
                )
    return ctx.chunks


def _data_case(
    ctx: _Ctx,
    bin_name: str,
    desc: str,
    vl: int,
    mode: int,
    scalar: tuple[str, list[int], int],
    elems: tuple[str, list[int], int],
    mask: tuple[str, list[int], int] | None,
    res: model.Result,
    vd_init: tuple[str, list[int], int] | None = None,
) -> None:
    """Register the operand data (by full label) and emit one testcase."""
    labels = []
    for item in (scalar, elems, mask, vd_init):
        if item is None:
            labels.append(None)
            continue
        label, values, width = item
        ctx.td.register_vector_data(label, width, elements=values)
        labels.append(label)
    scalar_label, elems_label, mask_label, vd_label = labels
    assert scalar_label is not None and elems_label is not None

    lines = ctx.begin()
    ctx.labels = [label for label in labels if label is not None]
    lines.append(f"# Testcase {desc}")
    lines += _guard(ctx, vl)
    lines += _load(ctx, vl, elems_label, scalar_label, mask_label, vd_label)
    lines += _reduce(ctx, mode, ctx.td.add_testcase(bin_name, ctx.coverpoint), masked=mask_label is not None)
    lines += _check(ctx, res)
    lines += _endguard(ctx, vl)
    ctx.end(lines)


def _class_data(ctx: _Ctx, cls: str, fmt: model.Fmt, values: dict[str, int]) -> tuple[str, list[int], int]:
    return (f"{ctx.prefix}_{'acc' if fmt is ctx.acc else 'elem'}_{cls}", [values[cls]], fmt.width)


_SPECIAL_LISTS = (
    ("posinf", "neginf"),
    ("posinf", "posinf"),
    ("posmax", "posmax"),
    ("posmax", "negmax"),
    ("negmax", "neginf"),
    ("qnan", "posinf", "neginf"),
    ("snan", "neginf"),
    ("neg0", "neg0"),
    ("pos0", "neg0"),
    ("minsub", "minsub"),
    ("onepulp", "neg1"),
    ("posmax", "posmax", "negmax", "negmax"),
)
_SPECIAL_SCALARS = ("pos0", "neg0", "posinf", "qnan", "snan", "posmax", "negmax", "minsub")


@add_coverpoint_generator("cp_custom_vfredusum_specials")
def cp_custom_vfredusum_specials(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Signed zeros, infinities, NaNs, the largest finite values and subnormals as vs1[0], each with element lists
    (vl = 2 to 4) that produce +inf + -inf, overflow, overflow that a wider intermediate format avoids, and
    signed-zero sums. Each case runs at RNE and at every other rounding mode whose legal outcomes differ.
    """
    del instr_type
    ctx = _Ctx(instr_name, coverpoint, test_data)
    if ctx.skip():
        return []
    acc_values = _edge_values(ctx.acc)
    elem_values = _edge_values(ctx.efmt)
    cases = [(scalar_cls, elem_list) for elem_list in _SPECIAL_LISTS for scalar_cls in _SPECIAL_SCALARS]
    for scalar_cls, elem_cls in cases:
        scalar = acc_values[scalar_cls]
        elems = [elem_values[cls] for cls in elem_cls]
        name = f"{scalar_cls}_{'_'.join(elem_cls)}"
        elems_data = (f"{ctx.prefix}_elems_{'_'.join(elem_cls)}", elems, ctx.sew)
        base = _outcomes(ctx, scalar, elems, model.RNE)
        for mode in model.MODES:
            res = base if mode == model.RNE else _outcomes(ctx, scalar, elems, mode)
            if mode != model.RNE and _same(res, base):
                continue
            _data_case(
                ctx,
                f"{name}_{model.MODE_NAMES[mode]}",
                f"vs1[0]={scalar_cls}, vs2={list(elem_cls)}, frm={model.MODE_NAMES[mode]}",
                len(elems),
                mode,
                _class_data(ctx, scalar_cls, ctx.acc, acc_values),
                elems_data,
                None,
                res,
            )
    return ctx.chunks


@add_coverpoint_generator("cp_custom_vfredusum_noactive")
def cp_custom_vfredusum_noactive(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    No active elements: vl = 7 with an all-zero mask and signaling-NaN elements, for every vs1[0] class, at
    RNE and RDN (whose additive identities differ). vd[0] must be vs1[0]; a NaN scalar may instead become the
    canonical NaN, with NV only if it was signaling. Also vl = 0, which must leave vd and fflags unchanged.
    """
    del instr_type
    ctx = _Ctx(instr_name, coverpoint, test_data)
    if ctx.skip():
        return []
    acc_values = _edge_values(ctx.acc)
    snans = [_edge_values(ctx.efmt)["snan"]] * 8
    zero_mask = (f"{ctx.prefix}_mask_zero", [0] * (_MASK_BITS // 8), 8)
    elems_data = (f"{ctx.prefix}_elems_snan8", snans, ctx.sew)
    for cls, scalar in acc_values.items():
        for mode in (model.RNE, model.RDN):
            res = model.reduce_bits(scalar, [], mode, ctx.sew, ctx.widening)
            _data_case(
                ctx,
                f"{cls}_vl{_NOACTIVE_VL}_{model.MODE_NAMES[mode]}",
                f"no active elements, vs1[0]={cls}, vl={_NOACTIVE_VL}, frm={model.MODE_NAMES[mode]}",
                _NOACTIVE_VL,
                mode,
                _class_data(ctx, cls, ctx.acc, acc_values),
                elems_data,
                zero_mask,
                res,
            )
    sentinel = _fval(ctx.acc, 5, -1)
    keep = model.Result(sentinel, sentinel, False, False, False, False, 0, 0)
    for masked in (False, True):
        mask_tag = "masked" if masked else "unmasked"
        _data_case(
            ctx,
            f"vl0_{mask_tag}",
            f"vl=0, {mask_tag}: vd and fflags unchanged",
            0,
            model.RNE,
            _class_data(ctx, "neg1", ctx.acc, acc_values),
            elems_data,
            zero_mask if masked else None,
            keep,
            (f"{ctx.prefix}_sentinel", [sentinel], ctx.w),
        )
    return ctx.chunks


@add_coverpoint_generator("cp_custom_vfredusum_determinism")
def cp_custom_vfredusum_determinism(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    The reduction tree is fixed for a given vtype and vl, so for order-dependent data D the result must satisfy
    identities that hold for any one tree: repeating D (in other registers) gives the same bits; 2^k * D gives
    2^k times the result; -D gives the negated result at RNE; and -D at RUP gives the negation of D at RDN. The
    flags must also match. The first results are also range-checked.
    """
    del instr_type
    ctx = _Ctx(instr_name, coverpoint, test_data)
    if ctx.skip():
        return []
    vlmaxes = [vl for vl in _VL_SWEEP if _LMUL <= vl <= ctx.vlmax]
    for vl, at_vlmax in [(vl, False) for vl in _DETERMINISM_VLS] + [(vl, True) for vl in vlmaxes]:
        for family in ("cancel", "mild"):
            if family == "cancel":
                scale_exp = -3 if ctx.widening else 3
                data = _cancel_family(ctx, vl)
                scaled = _cancel_family(ctx, vl, scale_exp)
                negated = _cancel_family(ctx, vl, 0, True)
            else:
                scale_exp = 3
                data, scaled, negated = _mild_family(ctx), _mild_family(ctx, scale_exp), _mild_family(ctx, 0, True)
            _determinism_case(ctx, family, vl, scale_exp, data, scaled, negated, at_vlmax)
    return ctx.chunks


def _determinism_case(
    ctx: _Ctx,
    family: str,
    vl: int,
    scale_exp: int,
    data: tuple[int, list[int]],
    scaled: tuple[int, list[int]],
    negated: tuple[int, list[int]],
    at_vlmax: bool,
) -> None:
    """Determinism checks at vl; if at_vlmax, only in configurations where vl is VLMAX."""
    lines = ctx.begin()
    labels = {}
    for tag, (scalar, elems) in (("d", data), ("s", scaled), ("n", negated)):
        suffix = f"_n{vl}" if family == "cancel" else ""
        labels[tag] = (
            ctx.data(f"det_{family}_{tag}_scalar", [scalar], ctx.w),
            ctx.data(
                f"det_{family}_{tag}_elems{suffix}", elems[: max(vl, 1)] if family == "cancel" else elems, ctx.sew
            ),
        )
    x, v = ctx.x, ctx.v
    lines.append(f"# Testcase determinism, {family} data, vl={vl}{' = VLMAX' if at_vlmax else ''}")
    lines += _guard(ctx, vl, at_vlmax)

    def run(tag: str, mode: int, bin_name: str, repeat: bool = False) -> list[str]:
        scalar_label, elems_label = labels[tag]
        return _load(ctx, vl, elems_label, scalar_label, repeat=repeat) + _reduce(
            ctx, mode, ctx.td.add_testcase(bin_name, ctx.coverpoint), repeat=repeat
        )

    def compare(expected: int, actual: int, flags_ref: int) -> list[str]:
        return [
            f"vmseq.vv v{v.match}, v{actual}, v{expected}",
            f"vcpop.m x{x.legal}, v{v.match} # 1 if the result matches",
            f"xor x{x.tmp}, x{x.flags}, x{flags_ref}",
            f"seqz x{x.tmp}, x{x.tmp} # 1 if fflags match",
            *_report(ctx, x.legal, x.tmp, actual),
        ]

    zero_keep = [
        f"vsll.vi v{v.ref_hi}, v{v.first}, 1",
        f"vmseq.vi v0, v{v.ref_hi}, 0 # first result is a zero",
        f"vmerge.vvm v{v.ref}, v{v.ref}, v{v.first}, v0 # zeros keep their bits",
    ]
    # D at RNE, range-checked, then kept with its flags
    res = _outcomes(ctx, data[0], data[1][:vl], model.RNE)
    lines += run("d", model.RNE, f"{family}_vl{vl}_first")
    lines += _check(ctx, res)
    lines += [f"vmv1r.v v{v.first}, v{v.vd}", f"mv x{x.flags_first}, x{x.flags}"]
    # D again, from other registers
    lines += run("d", model.RNE, f"{family}_vl{vl}_repeat", repeat=True)
    lines += compare(v.first, v.vd_repeat, x.flags_first)
    # 2^k * D
    lines += run("s", model.RNE, f"{family}_vl{vl}_scaled")
    lines += [
        f"LI(x{x.tmp}, {scale_exp})",
        f"vmv.v.x v{v.ref}, x{x.tmp}",
        f"LI(x{x.tmp}, {ctx.acc.frac_bits})",
        f"vsll.vx v{v.ref}, v{v.ref}, x{x.tmp}",
        f"vadd.vv v{v.ref}, v{v.ref}, v{v.first} # first result times 2^{scale_exp}",
        *zero_keep,
        *compare(v.ref, v.vd, x.flags_first),
    ]
    # -D at RNE
    lines += run("n", model.RNE, f"{family}_vl{vl}_negated")
    lines += [*_sign_lines(ctx), f"vxor.vv v{v.ref}, v{v.first}, v{v.sign} # negated first result", *zero_keep]
    lines += compare(v.ref, v.vd, x.flags_first)
    # D at RDN, range-checked and kept; -D at RUP must be its negation
    res = _outcomes(ctx, data[0], data[1][:vl], model.RDN)
    lines += run("d", model.RDN, f"{family}_vl{vl}_rdn")
    lines += _check(ctx, res)
    lines += [f"vmv1r.v v{v.first_rdn}, v{v.vd}", f"mv x{x.flags_rdn}, x{x.flags}"]
    lines += run("n", model.RUP, f"{family}_vl{vl}_rup_negated")
    lines += [*_sign_lines(ctx), f"vxor.vv v{v.ref}, v{v.first_rdn}, v{v.sign} # negated RDN result"]
    lines += compare(v.ref, v.vd, x.flags_rdn)
    lines += _endguard(ctx, vl, at_vlmax)
    ctx.end(lines)
