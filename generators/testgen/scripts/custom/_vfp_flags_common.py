# SPDX-License-Identifier: BSD-3-Clause
"""Unified VFP flags test generator.

Registers ``cp_custom_vfp_flags_<variant>`` for each variant listed in
VARIANTS below.  The Vf.csv column ``cp_custom_vfp_flags`` holds the
variant suffix (e.g. ``nv_nx_dz``); the framework appends it automatically.

Also registers ``cp_custom_vfp_flags_inactive_not_set`` (separate CSV column).

Variant suffixes and the flags they test::

    nv            -> NV
    nv_nx         -> NV, NX
    nv_nx_dz      -> NV, NX, DZ
    nv_nx_of      -> NV, NX, OF
    nv_nx_of_uf   -> NV, NX, OF, UF
    nx            -> NX
    nv_dz         -> NV, DZ
"""

from __future__ import annotations

from collections.abc import Callable

import vector_testgen_common as common
from coverpoint_registry import register
from vector_testgen_common import (
    getBaseSuiteTestCount,
    incrementBasetestCount,
    randomizeVectorInstructionData,
    registerCustomData,
    vfloattypes,
    vsAddressCount,
    writeTest,
)

# -- Instruction classification -----------------------------------------------

NO_FLAG = {
    "vfmerge.vfm",
    "vfmv.v.f",
    "vfmv.f.s",
    "vfmv.s.f",
    "vfsgnj.vv",
    "vfsgnj.vf",
    "vfsgnjn.vv",
    "vfsgnjn.vf",
    "vfsgnjx.vv",
    "vfsgnjx.vf",
    "vfslide1up.vf",
    "vfslide1down.vf",
    "vfclass.v",
}

WIDE_SRC = {
    "vfncvt.f.f.w",
    "vfncvt.rod.f.f.w",
    "vfncvt.x.f.w",
    "vfncvt.xu.f.w",
    "vfncvt.rtz.x.f.w",
    "vfncvt.rtz.xu.f.w",
    "vfncvt.f.x.w",
    "vfncvt.f.xu.w",
    "vfwadd.wv",
    "vfwadd.wf",
    "vfwsub.wv",
    "vfwsub.wf",
}

NARROW_I2F = {"vfncvt.f.x.w", "vfncvt.f.xu.w"}

WIDENING_NX_IMPOSSIBLE = {
    "vfwadd.vv",
    "vfwadd.vf",
    "vfwsub.vv",
    "vfwsub.vf",
    "vfwmul.vv",
    "vfwmul.vf",
}

# -- Trigger values per SEW ---------------------------------------------------

TV: dict[int, dict[str, int]] = {
    16: {
        "NV": 0x7D01,
        "DZ": 0x0000,
        "OF": 0x7BFF,
        "UF": 0x0080,
        "NX": 0x3C01,
        "NX2": 0x3C02,
        "ONE": 0x3C00,
        "THREE": 0x4200,
    },
    32: {
        "NV": 0x7F800001,
        "DZ": 0x00000000,
        "OF": 0x7F7FFFFF,
        "UF": 0x00800001,
        "NX": 0x3F800001,
        "NX2": 0x3F800002,
        "ONE": 0x3F800000,
        "THREE": 0x40400000,
    },
    64: {
        "NV": 0x7FF0000000000001,
        "DZ": 0x0000000000000000,
        "OF": 0x7FEFFFFFFFFFFFFF,
        "UF": 0x0010000000000001,
        "NX": 0x3FF0000000000001,
        "NX2": 0x3FF0000000000002,
        "ONE": 0x3FF0000000000000,
        "THREE": 0x4008000000000000,
    },
}

NX_OVERRIDE: dict[str, dict[int, int]] = {
    "vfrsqrt7.v": {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000},
    "vfrec7.v": {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000},
    "vfsqrt.v": {16: 0x4000, 32: 0x40000000, 64: 0x4000000000000000},
    "vfncvt.f.x.w": {16: 0x00000801, 32: 0x0000000001000001},
    "vfncvt.f.xu.w": {16: 0x00000801, 32: 0x0000000001000001},
}

# -- Per-instruction NX/DZ strategies ----------------------------------------
# (vs2_key, vs1_key): looked up in TV[sew].  For .vf, vs1_key -> fs1_val.

NX_PAIR: dict[str, tuple[str, str]] = {
    "vfsub.vv": ("OF", "ONE"),  # max - 1 -> inexact
    "vfsub.vf": ("OF", "ONE"),
    "vfrsub.vf": ("ONE", "OF"),  # reversed: fs1 - vs2
    "vfdiv.vv": ("ONE", "THREE"),  # 1 / 3 -> inexact
    "vfdiv.vf": ("ONE", "THREE"),
    "vfrdiv.vf": ("THREE", "ONE"),  # reversed: fs1 / vs2
    "vfnmadd.vv": ("OF", "OF"),  # overflow -> NX
}

DZ_PAIR: dict[str, tuple[str, ...]] = {
    "vfdiv.vv": ("ONE", "DZ"),  # vs2=1, vs1=0
    "vfdiv.vf": ("ONE", "DZ"),  # vs2=1, fs1=0
    "vfrdiv.vf": ("DZ",),  # vs2=0 (divisor in reversed div)
    "vfrsqrt7.v": ("DZ",),  # rsqrt(0) -> DZ
    "vfrec7.v": ("DZ",),  # rec(0) -> DZ
}

OF_SET = {"vfadd.vv", "vfadd.vf", "vfmul.vv", "vfmul.vf"}
UF_SET = {"vfmul.vv", "vfmul.vf"}

# -- Variant -> flag list mapping ---------------------------------------------

VARIANTS: dict[str, list[str]] = {
    "set": ["NV"],
    "nv": ["NV"],
    "nv_nx": ["NV", "NX"],
    "nv_nx_dz": ["NV", "NX", "DZ"],
    "nv_nx_of": ["NV", "NX", "OF"],
    "nv_nx_of_uf": ["NV", "NX", "OF", "UF"],
    "nx": ["NX"],
    "nv_dz": ["NV", "DZ"],
}

# -- Low-level test helpers ---------------------------------------------------


def _gen1(test: str, sew: int, label: str, val: int, desc: str, **kw: int) -> None:
    """Single-operand test (unary or .vf with fs1_val in kw)."""
    esize = sew * 2 if test in WIDE_SRC else sew
    registerCustomData(label, [val], element_size=esize)
    data = randomizeVectorInstructionData(
        test,
        sew,
        getBaseSuiteTestCount(),
        lmul=1,
        vs2_val_pointer=label,
        **kw,
    )
    writeTest(desc, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


def _gen2(test: str, sew: int, l1: str, v1: int, l2: str, v2: int, desc: str) -> None:
    """Two-operand test (.vv / .vs)."""
    registerCustomData(l1, [v1], element_size=sew)
    registerCustomData(l2, [v2], element_size=sew)
    if test.endswith((".vv", ".vs")):
        data = randomizeVectorInstructionData(
            test,
            sew,
            getBaseSuiteTestCount(),
            lmul=1,
            vs2_val_pointer=l1,
            vs1_val_pointer=l2,
            additional_no_overlap=[["vs2", "vs1"]],
        )
    else:
        data = randomizeVectorInstructionData(
            test,
            sew,
            getBaseSuiteTestCount(),
            lmul=1,
            vs2_val_pointer=l1,
        )
    writeTest(desc, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


def _emit(test: str, sew: int, vs2: int, vs1: int | None, desc: str, vs2_lbl: str, vs1_lbl: str = "") -> None:
    """Emit one test, auto-dispatching on instruction suffix."""
    if test.endswith((".vv", ".vs")):
        _gen2(test, sew, vs2_lbl, vs2, vs1_lbl, vs1 if vs1 is not None else vs2, desc)
    elif test.endswith((".vf", ".wf")):
        kw: dict[str, int] = {"fs1_val": vs1} if vs1 is not None else {}
        _gen1(test, sew, vs2_lbl, vs2, desc, **kw)
    else:
        _gen1(test, sew, vs2_lbl, vs2, desc)


def _pair(test: str, sew: int, vs2: int, vs1: int | None, flag: str, detail: str) -> None:
    """Emit two tests for 0->1 and 1->1 flag transitions."""
    base = f"custom_flag_{flag.lower()}"
    for i in range(2):
        sfx = "" if i == 0 else "1"
        _emit(
            test,
            sew,
            vs2,
            vs1,
            f"cp_custom_vfp_flags ({flag}{sfx} via {detail}, {test})",
            f"{base}_sew{sew}",
            f"{base}2_sew{sew}",
        )


# -- Skip logic ---------------------------------------------------------------


def _should_skip(test: str, sew: int) -> bool:
    if sew > common.flen:
        return True
    if test not in vfloattypes:
        return True
    if test in NO_FLAG:
        return True
    return sew not in TV


# -- Per-flag generators -------------------------------------------------------


def _gen_spacer(test: str, sew: int) -> None:
    """Clean spacer (fflags=0) so first flag test gets 0->1 transition."""
    t = TV[sew]
    if test in WIDE_SRC:
        one = 1 if test in NARROW_I2F else TV.get(sew * 2, {}).get("ONE", t["ONE"])
        lbl = f"custom_flag_wide_one_sew{sew}"
    else:
        one = t["ONE"]
        lbl = f"custom_flag_one_sew{sew}"
    _emit(test, sew, one, one, f"cp_custom_vfp_flags (clean spacer, {test})", lbl, f"custom_flag_spacer_one2_sew{sew}")


def _gen_nv(test: str, sew: int) -> None:
    """NV (Invalid Operation) via sNaN input."""
    t = TV[sew]
    nv = TV.get(sew * 2, {}).get("NV", t["NV"]) if test in WIDE_SRC and test not in NARROW_I2F else t["NV"]
    _pair(test, sew, nv, nv, "NV", "sNaN")


def _gen_dz(test: str, sew: int) -> None:
    """DZ (Divide by Zero) -- only for instructions in DZ_PAIR."""
    if test not in DZ_PAIR:
        return
    t = TV[sew]
    keys = DZ_PAIR[test]
    vs2 = t[keys[0]]
    vs1 = t[keys[1]] if len(keys) > 1 else None
    _pair(test, sew, vs2, vs1, "DZ", "zero")


def _gen_of(test: str, sew: int) -> None:
    """OF (Overflow) via max + max or max * max."""
    if test not in OF_SET:
        return
    of_val = TV[sew]["OF"]
    _pair(test, sew, of_val, of_val, "OF", "max normal")


def _gen_uf(test: str, sew: int) -> None:
    """UF (Underflow) via tiny * tiny."""
    if test not in UF_SET:
        return
    uf = TV[sew]["UF"]
    _pair(test, sew, uf, uf, "UF", "tiny*tiny")


def _gen_nx(test: str, sew: int) -> None:
    """NX (Inexact) -- strategy depends on instruction."""
    t = TV[sew]

    if test in WIDENING_NX_IMPOSSIBLE:
        return

    # -- Table-driven two-operand strategies --
    if test in NX_PAIR:
        k2, k1 = NX_PAIR[test]
        _pair(test, sew, t[k2], t[k1], "NX", f"{k2.lower()}/{k1.lower()}")
        return

    # -- Reductions: overflow sum causes NX --
    if test.endswith(".vs"):
        of_val = t["OF"]
        _pair(test, sew, of_val, of_val, "NX", "overflow sum")
        return

    # -- Wide .wv: vs2 at sew*2, vs1 at sew --
    if test in {"vfwadd.wv", "vfwsub.wv"}:
        wt = TV.get(sew * 2, {})
        vs2_lbl = f"custom_flag_wide_of_sew{sew}"
        vs1_lbl = f"custom_flag_one_sew{sew}"
        vs2_val = wt.get("OF", t["NX"])
        vs1_val = t["ONE"]
        registerCustomData(vs2_lbl, [vs2_val], element_size=sew * 2)
        registerCustomData(vs1_lbl, [vs1_val], element_size=sew)
        for i in range(2):
            sfx = "" if i == 0 else "1"
            data = randomizeVectorInstructionData(
                test,
                sew,
                getBaseSuiteTestCount(),
                lmul=1,
                vs2_val_pointer=vs2_lbl,
                vs1_val_pointer=vs1_lbl,
                additional_no_overlap=[["vs2", "vs1"]],
            )
            writeTest(
                f"cp_custom_vfp_flags (NX{sfx} forced, {test})",
                test,
                data,
                sew=sew,
                lmul=1,
                vl=1,
            )
            incrementBasetestCount()
            vsAddressCount()
        return

    # -- Wide .wf: vs2 at sew*2, fs1 at sew --
    if test in {"vfwadd.wf", "vfwsub.wf"}:
        wt = TV.get(sew * 2, {})
        vs2_val = wt.get("OF", t["NX"])
        vs2_lbl = f"custom_flag_wide_of_sew{sew}"
        registerCustomData(vs2_lbl, [vs2_val], element_size=sew * 2)
        for i in range(2):
            sfx = "" if i == 0 else "1"
            _gen1(test, sew, vs2_lbl, vs2_val, f"cp_custom_vfp_flags (NX{sfx} forced, {test})", fs1_val=t["ONE"])
        return

    # -- Default: NX trigger values with alternating NX/NX2 --
    nx_val = _resolve_nx(test, sew)
    if test in NARROW_I2F:
        nx2_val = nx_val + 2
        nx_lbl = f"custom_flag_int_nx_sew{sew}"
        nx2_lbl = f"custom_flag_int_nx2_sew{sew}"
    elif test in WIDE_SRC:
        nx2_val = TV.get(sew * 2, {}).get("NX2", nx_val)
        nx_lbl = f"custom_flag_wide_nx_sew{sew}"
        nx2_lbl = f"custom_flag_wide_nx2_sew{sew}"
    else:
        nx2_val = t.get("NX2", nx_val)
        nx_lbl = f"custom_flag_nx_sew{sew}"
        nx2_lbl = f"custom_flag_nx2_sew{sew}"

    tries = 8 if test in WIDE_SRC else 4
    vf_kw: dict[str, int] = {}
    if test.endswith((".vf", ".wf")):
        vf_kw = {"fs1_val": nx_val}
    for i in range(tries):
        if i % 2 == 0:
            _gen1(test, sew, nx_lbl, nx_val, f"cp_custom_vfp_flags (NX try {i + 1}, {test})", **vf_kw)
        else:
            _gen1(test, sew, nx2_lbl, nx2_val, f"cp_custom_vfp_flags (NX try {i + 1}, {test})", **vf_kw)


def _resolve_nx(test: str, sew: int) -> int:
    """Resolve the NX trigger value for the default path."""
    t = TV[sew]
    if test in NX_OVERRIDE:
        return NX_OVERRIDE[test].get(sew, t["NX"])
    if test in WIDE_SRC:
        return TV.get(sew * 2, {}).get("NX", t["NX"])
    return t["NX"]


# -- Flag dispatch table -------------------------------------------------------

_FLAG_GEN: dict[str, Callable[[str, int], None]] = {
    "NV": _gen_nv,
    "NX": _gen_nx,
    "DZ": _gen_dz,
    "OF": _gen_of,
    "UF": _gen_uf,
}


# -- Register all variants ----------------------------------------------------


def _make_handler(flags: list[str]) -> Callable[[str, int], None]:
    """Create a handler that generates spacer + per-flag tests."""

    def handler(test: str, sew: int) -> None:
        if _should_skip(test, sew):
            return
        _gen_spacer(test, sew)
        for flag in flags:
            _FLAG_GEN[flag](test, sew)

    return handler


for _variant, _flags in VARIANTS.items():
    register(f"cp_custom_vfp_flags_{_variant}")(_make_handler(_flags))


# -- Inactive-not-set (separate CSV column, special logic) ---------------------


@register("cp_custom_vfp_flags_inactive_not_set")
def _make_inactive(test: str, sew: int) -> None:
    if _should_skip(test, sew):
        return
    if test != "vfrsqrt7.v":
        return
    t = TV[sew]
    spacer_lbl = f"custom_flag_one_sew{sew}"
    registerCustomData(spacer_lbl, [t["ONE"]], element_size=sew)
    _gen1(test, sew, spacer_lbl, t["ONE"], f"cp_custom_vfp_flags spacer (clears stale fcsr, {test})")
    label = f"custom_flag_zero_sew{sew}"
    registerCustomData(label, [0], element_size=sew)
    data = randomizeVectorInstructionData(
        test,
        sew,
        getBaseSuiteTestCount(),
        lmul=1,
        vs2_val_pointer=label,
        additional_no_overlap=[["vs2", "v0"], ["vd", "v0"]],
    )
    writeTest(
        "cp_custom_vfp_flags_inactive_not_set (vfrsqrt7.v vs2=0, masked)",
        test,
        data,
        sew=sew,
        lmul=1,
        vl=1,
        maskval="zeroes",
    )
    incrementBasetestCount()
    vsAddressCount()
