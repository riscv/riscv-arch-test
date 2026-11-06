#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Mutation check: regenerate a suite from deliberately wrong reference semantics.

Each mutant models a plausible implementation bug. Its tests are written to tests_ai/Mut/ and run
on a correct DUT or reference simulator; every mutant must make at least one test fail,
otherwise the suite cannot see that bug.

Usage: mutate.py <mutant> (writes tests_ai/Mut/*.S) ; mutate.py --list
  AI_MUT_SUITE=<dir> writes to tests_ai/<dir>/ instead (for concurrent runs).
  H mutants are named <area>:<mutant> (e.g. h_csr:hgeip_write_virtual); each h_*.py has a MUTANTS dict.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import aigen
import gen_M
import gen_Sstc

orig_op = gen_M.op


def m_op(mut: Callable[[str, int, int, int], int | None]) -> Callable[[str, int, int, int], int]:
    def op(insn: str, a: int, b: int, xlen: int) -> int:
        r = mut(insn, a, b, xlen)
        return orig_op(insn, a, b, xlen) if r is None else r

    return op


def sx(v: int, n: int) -> int:
    return aigen.sext(v, n)


M_MUTANTS = {
    # MULHSU treats rs2 as signed (behaves like MULH)
    "mulhsu_rs2_signed": lambda i, a, b, x: orig_op("mulh", a, b, x) if i == "mulhsu" else None,
    # MULHSU with the signed and unsigned operands swapped
    "mulhsu_swapped": lambda i, a, b, x: orig_op("mulhsu", b, a, x) if i == "mulhsu" else None,
    # MULW zero-extends its 32-bit result
    "mulw_zext": lambda i, a, b, x: (orig_op("mulw", a, b, x) & 0xFFFFFFFF) if i == "mulw" else None,
    # DIVUW zero-extends its quotient
    "divuw_zext": lambda i, a, b, x: (orig_op("divuw", a, b, x) & 0xFFFFFFFF) if i == "divuw" else None,
    # DIVW divides the full 64-bit registers, then sign-extends
    "divw_full_width": lambda i, a, b, x: aigen.mask(sx(orig_op("div", a, b, x), 32), x) if i == "divw" else None,
    # REM takes the sign of the divisor (floored division)
    "rem_floored": lambda i, a, b, x: (
        aigen.mask(sx(a, x) % sx(b, x), x)
        if i == "rem" and sx(b, x) != 0 and not (a == 1 << (x - 1) and sx(b, x) == -1)
        else None
    ),
    # Division by zero returns zero
    "div_by_zero_returns_0": lambda i, a, b, x: 0 if i in ("div", "divu") and b == 0 else None,
    # REMUW by zero returns the zero-extended dividend
    "remuw_by_zero_zext": lambda i, a, b, x: (a & 0xFFFFFFFF) if i == "remuw" and b & 0xFFFFFFFF == 0 else None,
    # Signed overflow quotient is zero
    "overflow_quotient_0": lambda i, a, b, x: 0 if i == "div" and a == 1 << (x - 1) and b == (1 << x) - 1 else None,
    # DIVU of the signed-overflow bit pattern returns the dividend (signed special case applied)
    "unsigned_divu_overflow": lambda i, a, b, x: a if i == "divu" and a == 1 << (x - 1) and b == (1 << x) - 1 else None,
}


# Sstc mutants are expectation switches read by gen_Sstc.py (AI_MUTANT); each models a design bug.
SSTC_MUTANTS = {
    "signed_compare": "time >= stimecmp compared as signed (2^63 pends)",
    "compare_32bit": "only the low 32 bits of time and stimecmp compared",
    "u_access_leak": "U-mode may access stimecmp when STCE, TM and scounteren.TM are set",
    "u_needs_sie": "STI in U-mode is gated by sstatus.SIE",
    "tm_ignored": "mcounteren.TM does not gate S-mode stimecmp access",
    "mip_stip_writable": "M-mode can set mip.STIP while STCE=1",
    "vs_virtual_stce0": "VS-mode access with menvcfg.STCE=0 raises virtual-instruction",
    "vu_virtual_stce0": "VU-mode access to stimecmp with menvcfg.STCE=0 raises virtual-instruction",
    "vstimecmp_virtual_stce0": "V=1 access to vstimecmp by its own address with menvcfg.STCE=0 raises "
    "virtual-instruction",
    "sticky_stip": "a software-set STIP survives setting STCE",
    "spp_wrong": "a trap from U-mode records sstatus.SPP = S",
    "vs_direct_vstimecmp_ok": "VS-mode may access vstimecmp by its own address",
    "vs_compare_32bit": "only the low 32 bits of time + htimedelta and vstimecmp compared",
    "vs_signed_compare": "time + htimedelta >= vstimecmp compared as signed",
    "vs_ignore_htimedelta": "the vstimecmp comparison uses time without htimedelta",
    "vs_no_truncate": "time + htimedelta is not truncated to 64 bits",
    "vs_carry_dropped": "the carry from the low half of time + htimedelta is lost",
    "vu_access_leak": "VU-mode may access stimecmp when every gate is set",
    "vstip_timer_with_henvcfg_stce0": "vstimecmp still drives hip.VSTIP with henvcfg.STCE=0",
    "henvcfg_stce_illegal": "henvcfg.STCE=0 makes VS-mode access illegal- instead of virtual-instruction",
    "hcounteren_ignored": "hcounteren.TM does not gate VS-mode stimecmp access",
    "mcounteren_tm_virtual": "mcounteren.TM=0 makes VS-mode access virtual- instead of illegal-instruction",
    "vstip_only_on_write": "hip.VSTIP is re-evaluated only when vstimecmp is written",
    "vsti_ignores_vs_sie": "a delegated VS timer interrupt ignores vsstatus.SIE in VS-mode",
    "vstip_hvip_ignored": "hip.VSTIP ignores hvip.VSTIP when Sstc drives it",
    "hip_vstip_writable": "hip.VSTIP is writable",
    "vstip_not_reverted": "vstimecmp still drives hip.VSTIP with menvcfg.STCE=0",
}


GENERIC_SKIP = {"gen_M", "gen_Sstc", "gen_H"}


def suite_mutants() -> dict[str, str]:
    """Mutants of other suites: any gen_<Suite>.py with a MUTANTS dict, named <Suite>:<mutant>. Its gen() must
    read AI_MUTANT at import time and use the module-level SUITE when it creates tests."""
    import importlib

    out = {}
    for p in sorted(Path(__file__).parent.glob("gen_*.py")):
        if p.stem in GENERIC_SKIP:
            continue
        try:
            mod = importlib.import_module(p.stem)
        except Exception:  # noqa: BLE001, S112  # a generator under construction must not break the others
            continue
        for k, v in getattr(mod, "MUTANTS", {}).items():
            out[f"{p.stem[4:]}:{k}"] = v
    return out


def h_mutants() -> dict[str, str]:
    import gen_H

    out = {}
    for area in gen_H.areas():
        mod = __import__(area)
        for k, v in getattr(mod, "MUTANTS", {}).items():
            out[f"{area}:{k}"] = v
    return out


def run(name: str) -> None:
    import os

    suite = os.environ.get("AI_MUT_SUITE", "Mut")
    out = aigen.ROOT / suite
    shutil.rmtree(out, ignore_errors=True)
    if name in M_MUTANTS:
        gen_M.op = m_op(M_MUTANTS[name])
        gen_M.SUITE = suite
        tests = gen_M.gen()
    elif name in SSTC_MUTANTS:
        import importlib
        import os

        os.environ["AI_MUTANT"] = name
        importlib.reload(gen_Sstc)
        gen_Sstc.SUITE = suite
        tests = gen_Sstc.gen()
    elif ":" in name and name in h_mutants():
        import os

        import gen_H

        area, mut = name.split(":")
        os.environ["AI_MUTANT"] = mut
        tests = gen_H.gen([area], suite=suite)
    elif ":" in name and name in suite_mutants():
        import importlib
        import os

        sname, mut = name.split(":", 1)
        os.environ["AI_MUTANT"] = mut
        mod = importlib.reload(importlib.import_module(f"gen_{sname}"))
        vars(mod)["SUITE"] = suite  # a module found by name: its globals are set through its namespace
        tests = mod.gen()
    else:
        raise SystemExit(f"unknown mutant {name}")
    for t in tests:
        t.write()
    print(f"wrote {len(tests)} tests for mutant {name} to {out}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--list"]:
        print("\n".join([*M_MUTANTS, *SSTC_MUTANTS, *h_mutants(), *suite_mutants()]))
    else:
        run(sys.argv[1])
