#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/H: one test per normative rule of the hypervisor extension.

The rules are in src/priv/hypervisor.adoc. The generator is split by area (h_*.py, each with gen() and a
MUTANTS dict); shared helpers are in hlib.py. Tests boot to HS-mode, enter VS, VU and U with sret or T-SBI,
reach M-level state through T-SBI (or boot to M in _Sm files), and check traps and interrupts in the
framework trap log.

Usage: gen_H.py [--area h_x ...] [rule ...]   (default: every area, every rule)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hlib

HERE = Path(__file__).parent


def areas() -> list[str]:
    return sorted(p.stem for p in HERE.glob("h_*.py"))


def gen(only_areas: list[str] | None = None, suite: str | None = None) -> list:
    importlib.reload(hlib)
    if suite:
        hlib.SUITE = suite
    tests = []
    for name in only_areas or areas():
        mod = importlib.import_module(name)
        mod = importlib.reload(mod)
        tests += mod.gen()
    rules = [t.rule + t.suffix for t in tests]
    dup = {r for r in rules if rules.count(r) > 1}
    assert not dup, f"duplicate rules: {dup}"
    return tests


def main() -> None:
    args = sys.argv[1:]
    only_areas = []
    while "--area" in args:
        i = args.index("--area")
        only_areas.append(args[i + 1])
        del args[i : i + 2]
    only = set(args)
    for t in gen(only_areas or None):
        if only and t.rule not in only:
            continue
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
