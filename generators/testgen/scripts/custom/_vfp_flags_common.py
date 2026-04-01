# SPDX-License-Identifier: BSD-3-Clause
"""Shared constants and helpers for all cp_custom_vfp_flags_* scripts.

This module is imported by each per-coverpoint script. It contains:
- Instruction classification sets (NO_FLAG, DZ, OF, UF, wide-source, etc.)
- FP trigger values per SEW
- Test generation helpers (_gen_test, _gen_test_two_operands)
- The gen_spacer / gen_nv / gen_nx / gen_dz / gen_of / gen_uf / gen_inactive
  building blocks that each variant script calls selectively.
"""

import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    registerCustomData,
    vfloattypes,
)

# Instructions that do NOT set fflags — skip these for flag coverage
NO_FLAG_INSTRUCTIONS = {
    "vfmerge.vfm",      # merge — no arithmetic
    "vfmv.v.f",         # move — no arithmetic
    "vfmv.f.s",         # move — no arithmetic
    "vfmv.s.f",         # move — no arithmetic
    "vfsgnj.vv",        # sign injection — no arithmetic
    "vfsgnj.vf",
    "vfsgnjn.vv",
    "vfsgnjn.vf",
    "vfsgnjx.vv",
    "vfsgnjx.vf",
    "vfslide1up.vf",    # slide — no arithmetic
    "vfslide1down.vf",
    "vfclass.v",        # classify — no arithmetic
}

# Instructions that can raise DZ (divide by zero)
# vfrec7.v: vfrec7(0) = +Inf, raises DZ
DZ_INSTRUCTIONS = {"vfdiv.vv", "vfdiv.vf", "vfrdiv.vf", "vfrsqrt7.v", "vfrec7.v"}

# Instructions good for triggering OF (overflow via large values added together)
OF_INSTRUCTIONS = {"vfadd.vv", "vfadd.vf", "vfmul.vv", "vfmul.vf"}

# Instructions good for triggering UF (underflow via tiny value * tiny value)
UF_INSTRUCTIONS = {"vfmul.vv", "vfmul.vf"}

# Narrowing int→float: source register has 2*sew-wide INTEGER elements.
NARROWING_INT_TO_FLOAT = {"vfncvt.f.x.w", "vfncvt.f.xu.w"}

# ALL instructions whose vs2 source has 2*sew-wide elements.
WIDE_SOURCE_INSTRUCTIONS = {
    # Narrowing float→float
    "vfncvt.f.f.w", "vfncvt.rod.f.f.w",
    # Narrowing float→int
    "vfncvt.x.f.w", "vfncvt.xu.f.w", "vfncvt.rtz.x.f.w", "vfncvt.rtz.xu.f.w",
    # Narrowing int→float
    "vfncvt.f.x.w", "vfncvt.f.xu.w",
    # Widening with wide first operand (.wv/.wf)
    "vfwadd.wv", "vfwadd.wf", "vfwsub.wv", "vfwsub.wf",
}

# Widening .vv/.vf where NX is structurally uncoverable.
WIDENING_NX_IMPOSSIBLE = {
    "vfwadd.vv", "vfwadd.vf", "vfwsub.vv", "vfwsub.vf",
    "vfwmul.vv", "vfwmul.vf",
}

# Per-instruction NX trigger overrides.
NX_TRIGGERS_OVERRIDE = {
    "vfrsqrt7.v": {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000},  # 3.0
    "vfrec7.v":   {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000},  # 3.0
    "vfsqrt.v":   {16: 0x4000, 32: 0x40000000, 64: 0x4000000000000000},  # 2.0
    "vfncvt.f.x.w":  {16: 0x00000801, 32: 0x0000000001000001},
    "vfncvt.f.xu.w": {16: 0x00000801, 32: 0x0000000001000001},
}

# FP values that trigger each flag type per SEW
FLAG_TRIGGERS = {
    16: {
        "NV": 0x7D01,      # sNaN
        "DZ": 0x0000,      # +0.0
        "OF": 0x7BFF,      # max normal
        "UF": 0x0080,      # very small normal
        "NX": 0x3C01,      # 1.0 + ulp
        "NX2": 0x3C02,     # 1.0 + 2*ulp
        "ONE": 0x3C00,     # 1.0
    },
    32: {
        "NV": 0x7F800001,
        "DZ": 0x00000000,
        "OF": 0x7F7FFFFF,
        "UF": 0x00800001,
        "NX": 0x3F800001,
        "NX2": 0x3F800002,
        "ONE": 0x3F800000,
    },
    64: {
        "NV": 0x7FF0000000000001,
        "DZ": 0x0000000000000000,
        "OF": 0x7FEFFFFFFFFFFFFF,
        "UF": 0x0010000000000001,
        "NX": 0x3FF0000000000001,
        "NX2": 0x3FF0000000000002,
        "ONE": 0x3FF0000000000000,
    },
}


def _gen_test(test, sew, label_name, value, description, **extra_kwargs):
    """Generate a single flag-triggering test case."""
    esize = sew * 2 if test in WIDE_SOURCE_INSTRUCTIONS else sew
    registerCustomData(label_name, [value], element_size=esize)
    kwargs = {"lmul": 1, "vs2_val_pointer": label_name}
    kwargs.update(extra_kwargs)
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(), **kwargs,
    )
    writeTest(description, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


def _gen_test_two_operands(test, sew, label1, val1, label2, val2, description):
    """Generate test with both vs2 and vs1 (or vs2 and rs1 for .vf) set."""
    registerCustomData(label1, [val1], element_size=sew)
    registerCustomData(label2, [val2], element_size=sew)
    if test.endswith(".vv") or test.endswith(".vs"):
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label1, vs1_val_pointer=label2,
            additional_no_overlap=[['vs2', 'vs1']],
        )
    else:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(),
            lmul=1, vs2_val_pointer=label1,
        )
    writeTest(description, test, data, sew=sew, lmul=1, vl=1)
    incrementBasetestCount()
    vsAddressCount()


def should_skip(test, sew):
    """Return True if this instruction/sew combo should be skipped for flags."""
    if sew > common.flen:
        return True
    if test not in vfloattypes:
        return True
    if test in NO_FLAG_INSTRUCTIONS:
        return True
    if not FLAG_TRIGGERS.get(sew, {}):
        return True
    return False


def gen_spacer(test, sew):
    """Generate a clean spacer test (fflags=0) so first real flag gets 0→1."""
    triggers = FLAG_TRIGGERS[sew]
    if test in WIDE_SOURCE_INSTRUCTIONS:
        wide_sew = sew * 2
        wide_triggers = FLAG_TRIGGERS.get(wide_sew, {})
        if test in NARROWING_INT_TO_FLOAT:
            spacer_one = 1
        else:
            spacer_one = wide_triggers.get("ONE", triggers["ONE"])
        spacer_label = f"custom_flag_wide_one_sew{sew}"
    else:
        spacer_one = triggers["ONE"]
        spacer_label = f"custom_flag_one_sew{sew}"
    spacer_label2 = f"custom_flag_spacer_one2_sew{sew}"
    if test.endswith(".vv") or test.endswith(".vs"):
        _gen_test_two_operands(test, sew,
                               spacer_label, spacer_one,
                               spacer_label2, spacer_one,
                               f"cp_custom_vfp_flags_set (clean spacer, {test})")
    elif test.endswith(".vf") or test.endswith(".wf"):
        _gen_test(test, sew,
                  spacer_label, spacer_one,
                  f"cp_custom_vfp_flags_set (clean spacer, {test})",
                  fs1_val=spacer_one)
    else:
        _gen_test(test, sew,
                  spacer_label, spacer_one,
                  f"cp_custom_vfp_flags_set (clean spacer, {test})")


def gen_nv(test, sew):
    """Generate NV (Invalid) transition bin tests: spacer→NV (0→1) and NV→NV (1→1)."""
    triggers = FLAG_TRIGGERS[sew]
    if "NV" not in triggers:
        return
    if test in WIDE_SOURCE_INSTRUCTIONS and test not in NARROWING_INT_TO_FLOAT:
        nv_val = FLAG_TRIGGERS.get(sew * 2, {}).get("NV", triggers["NV"])
        nv_label = f"custom_flag_wide_nv_sew{sew}"
        nv_label2 = f"custom_flag_wide_nv2_sew{sew}"
    else:
        nv_val = triggers["NV"]
        nv_label = f"custom_flag_nv_sew{sew}"
        nv_label2 = f"custom_flag_nv2_sew{sew}"
    if test.endswith(".vv") or test.endswith(".vs"):
        _gen_test_two_operands(test, sew,
                               nv_label, nv_val, nv_label2, nv_val,
                               f"cp_custom_vfp_flags_set (NV via sNaN, {test})")
        _gen_test_two_operands(test, sew,
                               nv_label, nv_val, nv_label2, nv_val,
                               f"cp_custom_vfp_flags_set (NV1 via sNaN again, {test})")
    elif test.endswith(".vf") or test.endswith(".wf"):
        _gen_test(test, sew,
                  nv_label, nv_val,
                  f"cp_custom_vfp_flags_set (NV via sNaN, {test})",
                  fs1_val=nv_val)
        _gen_test(test, sew,
                  nv_label, nv_val,
                  f"cp_custom_vfp_flags_set (NV1 via sNaN again, {test})",
                  fs1_val=nv_val)
    else:
        _gen_test(test, sew,
                  nv_label, nv_val,
                  f"cp_custom_vfp_flags_set (NV via sNaN, {test})")
        _gen_test(test, sew,
                  nv_label, nv_val,
                  f"cp_custom_vfp_flags_set (NV1 via sNaN again, {test})")


def gen_nx(test, sew):
    """Generate NX (Inexact) transition bin tests."""
    triggers = FLAG_TRIGGERS[sew]
    if "NX" not in triggers:
        return

    if test in NX_TRIGGERS_OVERRIDE:
        nx_val = NX_TRIGGERS_OVERRIDE[test].get(sew, triggers["NX"])
    elif test in WIDE_SOURCE_INSTRUCTIONS:
        wide_triggers = FLAG_TRIGGERS.get(sew * 2, {})
        nx_val = wide_triggers.get("NX", triggers["NX"])
    else:
        nx_val = triggers["NX"]

    three = {16: 0x4200, 32: 0x40400000, 64: 0x4008000000000000}
    if test == "vfsub.vv":
        _gen_test_two_operands(test, sew,
                              f"custom_flag_of_sew{sew}", triggers["OF"],
                              f"custom_flag_one_sew{sew}", triggers["ONE"],
                              f"cp_custom_vfp_flags_set (NX via max-1, {test})")
        _gen_test_two_operands(test, sew,
                              f"custom_flag_of_sew{sew}", triggers["OF"],
                              f"custom_flag_three_sew{sew}", three[sew],
                              f"cp_custom_vfp_flags_set (NX1 via max-3, {test})")
    elif test == "vfdiv.vv":
        _gen_test_two_operands(test, sew,
                              f"custom_flag_one_sew{sew}", triggers["ONE"],
                              f"custom_flag_three_sew{sew}", three[sew],
                              f"cp_custom_vfp_flags_set (NX via 1/3, {test})")
        _gen_test_two_operands(test, sew,
                              f"custom_flag_one_sew{sew}", triggers["ONE"],
                              f"custom_flag_three_sew{sew}", three[sew],
                              f"cp_custom_vfp_flags_set (NX1 via 1/3 again, {test})")
    elif test == "vfrdiv.vf":
        # vfrdiv.vf: vd = f[rs1] / vs2[i]. With vs2=3 and fs1=1, we get 1/3 (NX).
        _gen_test(test, sew,
                  f"custom_flag_three_sew{sew}", three[sew],
                  f"cp_custom_vfp_flags_set (NX via 1/3, {test})",
                  fs1_val=triggers["ONE"])
        _gen_test(test, sew,
                  f"custom_flag_three_sew{sew}", three[sew],
                  f"cp_custom_vfp_flags_set (NX1 via 1/3 again, {test})",
                  fs1_val=triggers["ONE"])
    elif test == "vfdiv.vf":
        # vfdiv.vf: vd = vs2[i] / f[rs1]. With vs2=1 and fs1=3, we get 1/3 (NX).
        _gen_test(test, sew,
                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                  f"cp_custom_vfp_flags_set (NX via 1/3, {test})",
                  fs1_val=three[sew])
        _gen_test(test, sew,
                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                  f"cp_custom_vfp_flags_set (NX1 via 1/3 again, {test})",
                  fs1_val=three[sew])
    elif test == "vfsub.vf":
        # vfsub.vf: vd = vs2[i] - f[rs1]. Use vs2=MAX, fs1=1.0 → MAX-1 is inexact → NX.
        _gen_test(test, sew,
                  f"custom_flag_of_sew{sew}", triggers["OF"],
                  f"cp_custom_vfp_flags_set (NX via max-1, {test})",
                  fs1_val=triggers["ONE"])
        _gen_test(test, sew,
                  f"custom_flag_of_sew{sew}", triggers["OF"],
                  f"cp_custom_vfp_flags_set (NX1 via max-1 again, {test})",
                  fs1_val=triggers["ONE"])
    elif test == "vfrsub.vf":
        # vfrsub.vf: vd = f[rs1] - vs2[i]. Use vs2=1.0, fs1=MAX → MAX-1 is inexact → NX.
        _gen_test(test, sew,
                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                  f"cp_custom_vfp_flags_set (NX via max-1, {test})",
                  fs1_val=triggers["OF"])
        _gen_test(test, sew,
                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                  f"cp_custom_vfp_flags_set (NX1 via max-1 again, {test})",
                  fs1_val=triggers["OF"])
    elif test in {"vfwadd.wv", "vfwsub.wv"}:
        wide_triggers = FLAG_TRIGGERS.get(sew * 2, {})
        vs2_label = f"custom_flag_wide_of_sew{sew}"
        vs1_label = f"custom_flag_one_sew{sew}"
        registerCustomData(vs2_label, [wide_triggers.get("OF", nx_val)], element_size=sew * 2)
        registerCustomData(vs1_label, [triggers["ONE"]], element_size=sew)
        for i in range(2):
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(),
                lmul=1, vs2_val_pointer=vs2_label, vs1_val_pointer=vs1_label,
                additional_no_overlap=[["vs2", "vs1"]],
            )
            writeTest(
                f"cp_custom_vfp_flags_set (NX forced {i + 1}, {test})",
                test, data, sew=sew, lmul=1, vl=1,
            )
            incrementBasetestCount()
            vsAddressCount()
    elif test == "vfwsub.wf":
        wide_triggers = FLAG_TRIGGERS.get(sew * 2, {})
        vs2_label = f"custom_flag_wide_of_sew{sew}"
        registerCustomData(vs2_label, [wide_triggers.get("OF", nx_val)], element_size=sew * 2)
        fs1_val = triggers["ONE"]
        for i in range(2):
            _gen_test(test, sew,
                      vs2_label, wide_triggers.get("OF", nx_val),
                      f"cp_custom_vfp_flags_set (NX forced {i + 1}, {test})",
                      fs1_val=fs1_val)
    elif test == "vfnmadd.vv":
        _gen_test_two_operands(
            test, sew,
            f"custom_flag_of_sew{sew}", triggers["OF"],
            f"custom_flag_of2_sew{sew}", triggers["OF"],
            f"cp_custom_vfp_flags_set (NX forced 1, {test})")
        _gen_test_two_operands(
            test, sew,
            f"custom_flag_of_sew{sew}", triggers["OF"],
            f"custom_flag_of2_sew{sew}", triggers["OF"],
            f"cp_custom_vfp_flags_set (NX forced 2, {test})")
    elif test.endswith(".vs"):
        # Reductions: vs1[0] is accumulator, vs2 is vector. MAX+MAX → +Inf (OF+NX)
        _gen_test_two_operands(test, sew,
                               f"custom_flag_of_sew{sew}", triggers["OF"],
                               f"custom_flag_of2_sew{sew}", triggers["OF"],
                               f"cp_custom_vfp_flags_set (NX via overflow sum, {test})")
        _gen_test_two_operands(test, sew,
                               f"custom_flag_of_sew{sew}", triggers["OF"],
                               f"custom_flag_of2_sew{sew}", triggers["OF"],
                               f"cp_custom_vfp_flags_set (NX1 via overflow sum again, {test})")
    else:
        if test in NARROWING_INT_TO_FLOAT:
            nx_label = f"custom_flag_int_nx_sew{sew}"
        elif test in WIDE_SOURCE_INSTRUCTIONS:
            nx_label = f"custom_flag_wide_nx_sew{sew}"
        else:
            nx_label = f"custom_flag_nx_sew{sew}"
        if test in NARROWING_INT_TO_FLOAT:
            nx2_val = nx_val + 2
            nx2_label = f"custom_flag_int_nx2_sew{sew}"
        elif test in WIDE_SOURCE_INSTRUCTIONS:
            nx2_val = FLAG_TRIGGERS.get(sew * 2, {}).get("NX2", nx_val)
            nx2_label = f"custom_flag_wide_nx2_sew{sew}"
        else:
            nx2_val = triggers.get("NX2", nx_val)
            nx2_label = f"custom_flag_nx2_sew{sew}"
        nx_tries = 8 if test in WIDE_SOURCE_INSTRUCTIONS else 4
        vf_extra: dict[str, int] = {}
        if test.endswith(".vf") or test.endswith(".wf"):
            vf_extra = {"fs1_val": nx_val}
        for i in range(nx_tries):
            if i % 2 == 0:
                _gen_test(test, sew,
                          nx_label, nx_val,
                          f"cp_custom_vfp_flags_set (NX try {i+1}, {test})",
                          **vf_extra)
            else:
                _gen_test(test, sew,
                          nx2_label, nx2_val,
                          f"cp_custom_vfp_flags_set (NX try {i+1}, {test})",
                          **vf_extra)


def gen_dz(test, sew):
    """Generate DZ (Divide by Zero) transition bin tests."""
    triggers = FLAG_TRIGGERS[sew]
    if test not in DZ_INSTRUCTIONS or "DZ" not in triggers:
        return
    if test in {"vfrsqrt7.v", "vfrec7.v"}:
        _gen_test(test, sew,
                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                  f"cp_custom_vfp_flags_set (DZ via zero, {test})")
        _gen_test(test, sew,
                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                  f"cp_custom_vfp_flags_set (DZ1 via zero again, {test})")
    elif test == "vfdiv.vv":
        _gen_test_two_operands(test, sew,
                              f"custom_flag_one_sew{sew}", triggers["ONE"],
                              f"custom_flag_dz_sew{sew}", triggers["DZ"],
                              f"cp_custom_vfp_flags_set (DZ via zero divisor, {test})")
        _gen_test_two_operands(test, sew,
                              f"custom_flag_one_sew{sew}", triggers["ONE"],
                              f"custom_flag_dz_sew{sew}", triggers["DZ"],
                              f"cp_custom_vfp_flags_set (DZ1 via zero divisor again, {test})")
    elif test == "vfrdiv.vf":
        _gen_test(test, sew,
                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                  f"cp_custom_vfp_flags_set (DZ via zero vs2, {test})")
        _gen_test(test, sew,
                  f"custom_flag_dz_sew{sew}", triggers["DZ"],
                  f"cp_custom_vfp_flags_set (DZ1 via zero vs2 again, {test})")
    elif test == "vfdiv.vf":
        # vfdiv.vf: vd = vs2 / f[rs1], DZ when f[rs1] = 0
        _gen_test(test, sew,
                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                  f"cp_custom_vfp_flags_set (DZ via zero scalar divisor, {test})",
                  fs1_val=triggers["DZ"])
        _gen_test(test, sew,
                  f"custom_flag_one_sew{sew}", triggers["ONE"],
                  f"cp_custom_vfp_flags_set (DZ1 via zero scalar divisor again, {test})",
                  fs1_val=triggers["DZ"])


def gen_of(test, sew):
    """Generate OF (Overflow) transition bin tests."""
    triggers = FLAG_TRIGGERS[sew]
    if test not in OF_INSTRUCTIONS or "OF" not in triggers:
        return
    if test.endswith(".vv"):
        _gen_test_two_operands(test, sew,
                              f"custom_flag_of_sew{sew}", triggers["OF"],
                              f"custom_flag_of2_sew{sew}", triggers["OF"],
                              f"cp_custom_vfp_flags_set (OF via max+max, {test})")
        _gen_test_two_operands(test, sew,
                              f"custom_flag_of_sew{sew}", triggers["OF"],
                              f"custom_flag_of2_sew{sew}", triggers["OF"],
                              f"cp_custom_vfp_flags_set (OF1 via max+max again, {test})")
    else:
        _gen_test(test, sew,
                  f"custom_flag_of_sew{sew}", triggers["OF"],
                  f"cp_custom_vfp_flags_set (OF via max normal, {test})",
                  fs1_val=triggers["OF"])
        _gen_test(test, sew,
                  f"custom_flag_of_sew{sew}", triggers["OF"],
                  f"cp_custom_vfp_flags_set (OF1 via max normal again, {test})",
                  fs1_val=triggers["OF"])


def gen_uf(test, sew):
    """Generate UF (Underflow) transition bin tests."""
    triggers = FLAG_TRIGGERS[sew]
    if test not in UF_INSTRUCTIONS or "UF" not in triggers:
        return
    if test.endswith(".vv"):
        _gen_test_two_operands(test, sew,
                              f"custom_flag_uf_sew{sew}", triggers["UF"],
                              f"custom_flag_uf2_sew{sew}", triggers["UF"],
                              f"cp_custom_vfp_flags_set (UF via tiny*tiny, {test})")
        _gen_test_two_operands(test, sew,
                              f"custom_flag_uf_sew{sew}", triggers["UF"],
                              f"custom_flag_uf2_sew{sew}", triggers["UF"],
                              f"cp_custom_vfp_flags_set (UF1 via tiny*tiny again, {test})")
    else:
        _gen_test(test, sew,
                  f"custom_flag_uf_sew{sew}", triggers["UF"],
                  f"cp_custom_vfp_flags_set (UF via tiny, {test})",
                  fs1_val=triggers["UF"])
        _gen_test(test, sew,
                  f"custom_flag_uf_sew{sew}", triggers["UF"],
                  f"cp_custom_vfp_flags_set (UF1 via tiny again, {test})",
                  fs1_val=triggers["UF"])


def gen_inactive(test, sew):
    """Generate inactive-not-set test (only for vfrsqrt7.v)."""
    if test != "vfrsqrt7.v":
        return
    triggers = FLAG_TRIGGERS[sew]
    # RVVI fsflagsi CSR alias bug workaround: insert spacer to clear stale fcsr
    spacer_label = f"custom_flag_one_sew{sew}"
    registerCustomData(spacer_label, [triggers["ONE"]], element_size=sew)
    _gen_test(test, sew,
              spacer_label, triggers["ONE"],
              f"cp_custom_vfp_flags spacer (clears stale fcsr, {test})")

    label = f"custom_flag_zero_sew{sew}"
    registerCustomData(label, [0], element_size=sew)
    description = "cp_custom_vfp_flags_inactive_not_set (vfrsqrt7.v vs2=0, masked)"
    data = randomizeVectorInstructionData(
        test, sew, getBaseSuiteTestCount(),
        lmul=1, vs2_val_pointer=label,
        additional_no_overlap=[['vs2', 'v0'], ['vd', 'v0']],
    )
    writeTest(description, test, data,
              sew=sew, lmul=1, vl=1, maskval="zeroes")
    incrementBasetestCount()
    vsAddressCount()
