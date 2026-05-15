#!/usr/bin/env python3
"""Scan *_uncovered.txt coverage reports under work/ and print unique
uncovered coverpoints as Extension_cp<name>.

Extension = leading token of the covergroup TYPE line
            (e.g. ExceptionsVx from ExceptionsVx_vmv1r_v_cg).
Coverpoint = name from `Coverpoint cp_*` lines with status != Covered.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"

TYPE_RE = re.compile(r"TYPE\s+/RISCV_coverage_pkg/[^/]+/([A-Za-z0-9]+)_")
CP_RE = re.compile(r"^\s*Coverpoint\s+(cp_\S+)\s.*\s(\S+)\s*$")


def scan(path: Path) -> set[str]:
    found: set[str] = set()
    ext: str | None = None
    for line in path.read_text(errors="replace").splitlines():
        m = TYPE_RE.search(line)
        if m:
            ext = m.group(1)
            continue
        m = CP_RE.match(line)
        if m and ext:
            cp, status = m.group(1), m.group(2)
            if status != "Covered":
                found.add(f"{ext}_{cp}")
    return found


def main() -> int:
    if not WORK.is_dir():
        print(f"no work dir: {WORK}", file=sys.stderr)
        return 1
    reports = sorted(WORK.glob("*/reports/*_uncovered.txt"))
    if not reports:
        print("no *_uncovered.txt reports found", file=sys.stderr)
        return 1
    all_cps: set[str] = set()
    for r in reports:
        all_cps |= scan(r)
    for name in sorted(all_cps):
        print(name)
    print(f"\n# {len(all_cps)} unique uncovered coverpoints from {len(reports)} report(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
