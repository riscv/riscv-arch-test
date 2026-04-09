#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Quick coverage summary for planning.

Usage (run from repo root):
  # All-instruction table across SEWs for the active category
  python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py

  # Show which bins are missing for a specific instruction (across all SEWs)
  python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --bins vfadd.vv

  # Only show 0% and partial instructions (skip 100%)
  python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --uncovered

Output is intentionally compact — designed to be read whole without scrolling.
"""

from __future__ import annotations
import re
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
REPORT_DIRS = {
    "rv64": REPO_ROOT / "work/sail-rv64-max/reports",
    "rv32": REPO_ROOT / "work/sail-rv32-max/reports",
}
CATEGORIES = ["VfCustom", "VlsCustom"]
SEWS = {
    "VfCustom":  ["16", "32", "64"],
    "VlsCustom": ["8", "16", "32", "64"],
}


def _parse_instances(report_file: Path) -> dict[str, float | None]:
    """Return {instruction_name: pct} from an uncovered.txt file.
    pct is None if the line is truncated (no % shown).
    """
    result: dict[str, float | None] = {}
    pat = re.compile(r"obj_\w+?_(\S+?)\s+([\d.]+)%|obj_\w+?_(\S+?)\s*$")
    for line in report_file.read_text().splitlines():
        m = pat.search(line)
        if not m:
            continue
        if m.group(1):
            inst = m.group(1).replace("_", ".")
            result[inst] = float(m.group(2))
        elif m.group(3):
            inst = m.group(3).replace("_", ".")
            result[inst] = None  # truncated line — no % shown
    return result


def _parse_missing_bins(report_file: Path, instruction: str) -> dict[str, list[str]]:
    """Return {coverpoint_name: [missing_bin, ...]} for one instruction."""
    inst_key = instruction.replace(".", "_")
    content = report_file.read_text()

    # Find the instance block for this instruction
    blocks = re.split(r"(?= Covergroup instance obj_)", content)
    target_block = None
    for block in blocks:
        if f"obj_" in block and f"_{inst_key}" in block:
            # confirm it ends with the right instruction name
            m = re.search(r"obj_\S+?_([^_\s][^\s]*)", block)
            if m and m.group(1).replace("_", ".") == instruction:
                target_block = block
                break

    if not target_block:
        return {}

    result: dict[str, list[str]] = {}
    current_cp = None
    for line in target_block.splitlines():
        # Coverpoint/Cross header
        cp_m = re.match(r"\s+(?:Coverpoint|Cross)\s+(\S+)", line)
        if cp_m:
            current_cp = cp_m.group(1)
            continue
        # ZERO bin lines
        if current_cp and "ZERO" in line:
            bin_m = re.search(r"bin\s+(\S+)", line)
            if bin_m:
                result.setdefault(current_cp, []).append(bin_m.group(1))

    return result


def cmd_overview(args):
    """Print per-instruction % table across SEWs."""
    for arch, report_dir in REPORT_DIRS.items():
        if not report_dir.exists():
            continue
        for cat in CATEGORIES:
            sews = SEWS[cat]
            # Gather all instruction names
            all_insts: set[str] = set()
            data: dict[str, dict[str, float | None]] = {}  # sew -> {inst -> pct}
            for sew in sews:
                f = report_dir / f"{cat}{sew}_uncovered.txt"
                if not f.exists():
                    data[sew] = {}
                    continue
                data[sew] = _parse_instances(f)
                all_insts |= data[sew].keys()

            if not all_insts:
                continue

            # Filter if requested
            if args.uncovered:
                all_insts = {
                    i for i in all_insts
                    if any(data[s].get(i) != 100.0 for s in sews if i in data[s])
                }

            if not all_insts:
                print(f"\n{arch}/{cat}: all instructions at 100%")
                continue

            # Sort: 0% first, then by lowest %, then alpha
            def sort_key(inst):
                vals = [data[s].get(inst) for s in sews if inst in data[s]]
                vals = [v if v is not None else 0 for v in vals]
                return (min(vals) if vals else 0, inst)

            sorted_insts = sorted(all_insts, key=sort_key)

            # Print table
            sew_header = "  ".join(f"SEW{s:>3}" for s in sews)
            print(f"\n{'='*60}")
            print(f"{arch}/{cat}   [{sew_header}]")
            print(f"{'='*60}")
            for inst in sorted_insts:
                cols = []
                for sew in sews:
                    pct = data[sew].get(inst)
                    if pct is None and inst not in data[sew]:
                        cols.append("  n/a")
                    elif pct is None:
                        cols.append("  ???")
                    else:
                        cols.append(f"{pct:5.0f}%")
                status = "  ".join(cols)
                # Mark 0% instructions
                flag = " !" if any(data[s].get(inst) == 0.0 for s in sews if inst in data[s]) else "  "
                print(f"{flag}{inst:<32} {status}")


def cmd_bins(args):
    """Print missing bins for a specific instruction across all SEWs."""
    instruction = args.bins
    for arch, report_dir in REPORT_DIRS.items():
        if not report_dir.exists():
            continue
        for cat in CATEGORIES:
            for sew in SEWS[cat]:
                f = report_dir / f"{cat}{sew}_uncovered.txt"
                if not f.exists():
                    continue
                missing = _parse_missing_bins(f, instruction)
                if not missing:
                    continue
                print(f"\n{arch}/{cat}{sew} — {instruction}:")
                for cp, bins in missing.items():
                    print(f"  {cp}:")
                    for b in bins:
                        print(f"    ZERO  {b}")


def main():
    parser = argparse.ArgumentParser(description="Coverage summary for planning")
    parser.add_argument("--uncovered", action="store_true",
                        help="Only show instructions that are not at 100%")
    parser.add_argument("--bins", metavar="INSTRUCTION",
                        help="Show missing bins for a specific instruction (e.g. vfadd.vv)")
    args = parser.parse_args()

    if args.bins:
        cmd_bins(args)
    else:
        cmd_overview(args)


if __name__ == "__main__":
    main()
