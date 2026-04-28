#!/usr/bin/env python3
##################################
# scripts/sspmp_coverage_reachability.py
#
# Static coverage reachability checker for the SspmpSm coverage suite.
#
# Parses `coverpoints/priv/SspmpSm_coverage.svh` for every (covergroup,
# coverpoint) pair and cross-checks against labels emitted by the testgen
# into `tests/priv/Sspmp/*.S`.  A coverpoint is considered reachable if at
# least one .S file contains a label that starts with `<covergroup>_<coverpoint>_`.
#
# Also reports per-bin reachability where the test label contains the bin
# name as a substring, but the primary metric is coverpoint-level because
# testgen naming conventions do not map 1:1 to SVH bin names.
#
# Output format mirrors framework/src/act/coverreport.py so the report
# reads the same way as the Questa/VCS functional-coverage report does
# in CI.
#
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COVERAGE_SVH = REPO_ROOT / "coverpoints" / "priv" / "SspmpSm_coverage.svh"
TEST_DIR = REPO_ROOT / "tests" / "priv" / "Sspmp"

# Covergroup names to scan; bins are emitted as <cg>_<cp>_<bin>:
COVERGROUPS = [
    "SspmpSm_csr_cg",
    "SspmpSm_perm_cg",
    "SspmpSm_addr_cg",
    "SspmpSm_paging_cg",
    "SspmpSm_spmpen_cg",
]


@dataclass(frozen=True)
class Bin:
    covergroup: str
    coverpoint: str
    bin_name: str

    @property
    def label(self) -> str:
        return f"{self.covergroup}_{self.coverpoint}_{self.bin_name}"


@dataclass(frozen=True)
class Coverpoint:
    covergroup: str
    name: str
    bins: tuple[Bin, ...]


_RE_CG = re.compile(r"^\s*covergroup\s+(\w+)\s+with", re.M)
_RE_ENDGROUP = re.compile(r"^\s*endgroup\b", re.M)
_RE_CP_OPEN = re.compile(r"^\s*(cp_\w+)\s*:\s*(?:coverpoint|cross)\b")
_RE_BIN = re.compile(r"^\s*(?:wildcard\s+)?bins\s+(\w+)(?:\s*\[[^\]]*\])?\s*=")


def _segment(src: str, cg_name: str) -> str | None:
    start = None
    for m in _RE_CG.finditer(src):
        if m.group(1) == cg_name:
            start = m.end()
            break
    if start is None:
        return None
    end_m = _RE_ENDGROUP.search(src, pos=start)
    return src[start : end_m.start()] if end_m else None


def extract_coverpoints(svh_src: str) -> list[Coverpoint]:
    cps: list[Coverpoint] = []
    for cg in COVERGROUPS:
        seg = _segment(svh_src, cg)
        if seg is None:
            continue
        # For each cp_* block inside the segment, collect bins up to the
        # closing `}` of its coverpoint/cross body.
        current_cp: str | None = None
        current_bins: list[Bin] = []
        brace_depth = 0
        for line in seg.splitlines():
            cp_m = _RE_CP_OPEN.match(line)
            if cp_m:
                if current_cp is not None:
                    cps.append(Coverpoint(cg, current_cp, tuple(current_bins)))
                current_cp = cp_m.group(1)
                current_bins = []
                brace_depth = line.count("{") - line.count("}")
                continue
            if current_cp is None:
                continue
            # Track braces within the cp_* body.
            brace_depth += line.count("{") - line.count("}")
            bin_m = _RE_BIN.match(line)
            if bin_m:
                current_bins.append(Bin(cg, current_cp, bin_m.group(1)))
            if brace_depth <= 0:
                if current_cp is not None:
                    cps.append(Coverpoint(cg, current_cp, tuple(current_bins)))
                current_cp = None
                current_bins = []
                brace_depth = 0
        # Handle case where coverpoint ends at segment end without explicit close
        if current_cp is not None:
            cps.append(Coverpoint(cg, current_cp, current_bins))
    return cps


def load_test_corpus(test_dir: Path) -> str:
    parts: list[str] = []
    for s in sorted(test_dir.glob("SspmpSm*.S")):
        parts.append(s.read_text())
    # Sspmp-00.S is the combined test and must also count.
    combined = test_dir / "Sspmp-00.S"
    if combined.exists():
        parts.append(combined.read_text())
    return "\n".join(parts)


def classify_coverpoints(cps: list[Coverpoint], corpus: str) -> dict[Coverpoint, bool]:
    hits: dict[Coverpoint, bool] = {}
    for cp in cps:
        prefix = re.escape(f"{cp.covergroup}_{cp.name}_")
        hits[cp] = bool(re.search(rf"\b{prefix}\w+", corpus))
    return hits


def classify_bins(cps: list[Coverpoint], corpus: str) -> dict[Bin, bool]:
    hits: dict[Bin, bool] = {}
    for cp in cps:
        prefix = re.escape(f"{cp.covergroup}_{cp.name}_")
        for b in cp.bins:
            # Best-effort bin-level match: label starts with <cg>_<cp>_ and
            # contains bin_name as a substring.
            pattern = rf"\b{prefix}\w*{re.escape(b.bin_name)}\w*(?:_str)?\s*:"
            hits[b] = bool(re.search(pattern, corpus))
    return hits


def _fmt_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    out = [fmt.format(*headers), fmt.format(*("-" * w for w in widths))]
    out.extend(fmt.format(*r) for r in rows)
    return "\n".join(out)


def render(
    cps: list[Coverpoint],
    cp_hits: dict[Coverpoint, bool],
    bin_hits: dict[Bin, bool],
) -> tuple[str, bool]:
    per_cg_cp: dict[str, tuple[int, int]] = {}
    for cp in cps:
        reached = cp_hits[cp]
        covered, total = per_cg_cp.get(cp.covergroup, (0, 0))
        per_cg_cp[cp.covergroup] = (covered + (1 if reached else 0), total + 1)

    per_cg_bin: dict[str, tuple[int, int]] = {}
    for b, reached in bin_hits.items():
        covered, total = per_cg_bin.get(b.covergroup, (0, 0))
        per_cg_bin[b.covergroup] = (covered + (1 if reached else 0), total + 1)

    all_cp_reached = all(c == t for c, t in per_cg_cp.values())

    # Summary table: coverpoint-level
    summary_rows: list[list[str]] = []
    for cg in COVERGROUPS:
        cp_covered, cp_total = per_cg_cp.get(cg, (0, 0))
        bin_covered, bin_total = per_cg_bin.get(cg, (0, 0))
        cp_pct = "0.00%" if cp_total == 0 else f"{100 * cp_covered / cp_total:.2f}%"
        bin_pct = "0.00%" if bin_total == 0 else f"{100 * bin_covered / bin_total:.2f}%"
        summary_rows.append(
            [
                cg,
                cp_pct,
                bin_pct,
                str(cp_total),
                str(bin_total),
                "Reachable" if cp_covered == cp_total and cp_total > 0 else "Incomplete",
            ]
        )
    summary = _fmt_table(
        ["Covergroup", "CP%", "Bin%", "Coverpoints", "Bins", "Status"],
        summary_rows,
    )

    # Detail table: coverpoint-level
    detail_rows = [
        [cp.covergroup, cp.name, "HIT" if cp_hits[cp] else "MISS", str(len(cp.bins))]
        for cp in cps
    ]
    detail = _fmt_table(
        ["Covergroup", "Coverpoint", "Status", "Bins"],
        detail_rows,
    )

    total_cp = len(cps)
    total_cp_reached = sum(1 for v in cp_hits.values() if v)
    total_bins = len(bin_hits)
    total_bins_reached = sum(1 for v in bin_hits.values() if v)

    banner = (
        "RVCP COVERAGE COMPLETE: SspmpSm_reachability"
        if all_cp_reached
        else "RVCP COVERAGE INCOMPLETE: SspmpSm_reachability"
    )
    footer = (
        f"{banner}\n"
        f"  {len(COVERGROUPS)} covergroups, {total_cp} coverpoints ({total_cp_reached} reached), "
        f"{total_bins} bins ({total_bins_reached} reached)\n"
    )
    if not all_cp_reached:
        miss_cp = [cp for cp in cps if not cp_hits[cp]]
        footer += "\n  Unreached coverpoints:\n"
        for cp in miss_cp:
            footer += f"    {cp.covergroup}.{cp.name}\n"

    header = (
        "SPMP coverage reachability report (static; companion to Questa/VCS "
        "functional coverage run in CI)\n"
        "\n"
        "Primary metric is COVERPOINT-LEVEL: every cp_* must have at least one "
        "test label starting with <covergroup>_<coverpoint>_.\n"
        "Bin-level matching is best-effort because testgen label conventions "
        "(e.g. entry0_addr_write) do not map 1:1 to SVH bin names (e.g. addr_nonzero).\n"
    )
    return (
        header + "\n" + summary + "\n\n" + detail + "\n\n" + footer,
        all_cp_reached,
    )


def main() -> int:
    if not COVERAGE_SVH.exists():
        print(f"ERROR: missing {COVERAGE_SVH}", file=sys.stderr)
        return 2
    if not TEST_DIR.exists():
        print(f"ERROR: missing {TEST_DIR}", file=sys.stderr)
        return 2

    cps = extract_coverpoints(COVERAGE_SVH.read_text())
    if not cps:
        print("ERROR: no coverpoints extracted from SVH -- regex drift?", file=sys.stderr)
        return 2

    corpus = load_test_corpus(TEST_DIR)
    cp_hits = classify_coverpoints(cps, corpus)
    bin_hits = classify_bins(cps, corpus)
    report, ok = render(cps, cp_hits, bin_hits)
    print(report)

    # Also write a copy so the Make target can refer to a file path.
    out_dir = REPO_ROOT / "work" / "spike-rv64-max" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SspmpSm_reachability.txt").write_text(report)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
