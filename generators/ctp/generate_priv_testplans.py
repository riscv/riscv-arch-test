#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ruamel-yaml>=0.18.16",
# ]
# ///

"""
Generate AsciiDoc coverpoint tables for the privileged test plans from testplans/priv/*.yaml.

Each YAML file describes one suite.  The Normative Rule column is derived from the
rule -> coverpoint mappings in coverpoints/norm/*.yaml (union with the plan's own `rules`).

Usage:
  generate_priv_testplans.py [--plans DIR] [--norm DIR] [--out DIR] [--coverage DIR]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

FIELDS = (
    ("goal", "Goal"),
    ("description", "Feature Description"),
    ("expectation", "Expectation"),
    ("bins", "Bins"),
    ("id", "ID"),
    ("rules", "Normative Rule"),
    ("check", "Pass/Fail Criteria"),
    ("status", "Status"),
    ("coverage", "Coverage"),
    ("notes", "Notes"),
)


def load_yaml(path: Path) -> dict[str, Any] | list[Any]:
    return YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))


def esc(text: str | float) -> str:
    lines = [ln.strip() for ln in str(text).replace("|", "\\|").replace("<<", "&#60;&#60;").split("\n")]
    return " +\n".join(ln for ln in lines if ln)


def rule_map(norm_dir: Path) -> dict[str, dict[str, list[str]]]:
    """suite -> coverpoint -> [rule names], inverted from every coverpoints/norm/*.yaml."""
    out: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    ref = re.compile(r"(\w+)_cg/(cp_\w+)")
    for f in sorted(norm_dir.glob("*.yaml")):
        data = load_yaml(f)
        entries = data if isinstance(data, list) else (data or {}).get("normative_rule_definitions") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            names = entry.get("names") or ([entry["name"]] if entry.get("name") else [])
            for cp in entry.get("coverpoint") or []:
                for suite, cpname in ref.findall(str(cp)):
                    for n in names:
                        if n not in out[suite][cpname]:
                            out[suite][cpname].append(n)
    return out


def coverage_names(coverage_dir: Path | None, suite: str) -> set[str] | None:
    """Coverpoint names declared in the suite's covergroup, or None if no coverage file exists."""
    if coverage_dir is None:
        return None
    files = list(coverage_dir.glob(f"{suite}_coverage.svh"))
    if not files:
        return None
    names: set[str] = set()
    for f in files:
        names |= set(re.findall(r"^\s*(cp_\w+)\s*:", f.read_text(encoding="utf-8"), re.MULTILINE))
    return names


def widths(header: list[str], rows: list[list[str]]) -> str:
    longest = [max([len(r[k]) for r in rows] + [len(header[k])]) for k in range(len(header))]
    w = [max(1, min(8, round(min(x, 3000) ** 0.5 / 5))) for x in longest]
    w[0] = max(w[0], 2)
    return ",".join(str(x) for x in w)


def render(
    plan: dict[str, Any], rules: dict[str, list[str]], known_rules: set[str], cov: set[str] | None, src: Path
) -> tuple[str, list[str]]:
    suite = plan["suite"]
    title = plan.get("title") or f"{suite} Coverpoints"
    warnings: list[str] = []
    out = [
        "// WARNING: This file was automatically generated.",
        f"// Do not modify by hand; edit {src} instead.",
        "",
    ]
    entries = plan.get("coverpoints") or []
    if not any("heading" not in e for e in entries):
        # prose-only plan: the anchor goes on the text, and an empty plan says so
        out.append(f"[[t-{suite}-coverpoints]]")
        if not plan.get("description") and not plan.get("notes"):
            out += [f"No {title.lower()} have been defined yet.", ""]
    if plan.get("description"):
        out += [esc(plan["description"]).replace(" +\n", "\n"), ""]
    setup = plan.get("setup")
    if setup:
        cols = setup["columns"]
        out += [
            f".{suite} Test Setup",
            f'[cols="{",".join(["2"] + ["3"] * len(cols))}", options=header]',
            "|===",
            "| Step | " + " | ".join(cols),
            "",
        ]
        for step in setup["steps"]:
            out.append("| " + esc(step["step"]))
            out += [("| " + esc(step[c])) if step.get(c) else "|" for c in cols]
            out.append("")
        out += ["|===", ""]
    if plan.get("notes"):
        out += [esc(plan["notes"]).replace(" +\n", "\n"), ""]

    if not any("heading" not in e for e in entries):
        return "\n".join(out), warnings
    used = [k for k, _ in FIELDS if any(e.get(k) for e in entries if "heading" not in e)]
    if rules and "rules" not in used:
        used.insert(min(len(used), 4), "rules")
    header = ["Coverpoint"] + [dict(FIELDS)[k] for k in used]
    rows: list[list[str]] = []
    body: list[str] = []
    for e in entries:
        if "heading" in e:
            body += [f"{len(header)}+| {esc(e['heading'])}", ""]
            continue
        name = str(e.get("name") or "")
        if cov is not None and name and name not in cov:
            warnings.append(f"{suite}: {name} is not a coverpoint in {suite}_coverage.svh")
        cells = [esc(name)]
        for k in used:
            if k == "rules":
                names = list(rules.get(name, []))
                for r in e.get("rules") or []:
                    if r not in names:
                        names.append(r)
                for r in names:
                    if known_rules and r not in known_rules:
                        warnings.append(f"{suite}/{name}: normative rule {r} is not in norm-rules.json")
                cells.append(esc("\n".join(names)))
            else:
                cells.append(esc(e[k]) if e.get(k) else "")
        rows.append(cells)
        body += ["\n".join(("| " + c) if c else "|" for c in cells), ""]
    out += [
        f"[[t-{suite}-coverpoints]]",
        f".{title}",
        f'[cols="{widths(header, rows)}", options=header]',
        "|===",
        "| " + " | ".join(header),
        "",
    ]
    out += body
    out += ["|===", ""]
    return "\n".join(out), warnings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plans", default="testplans/priv", type=Path)
    ap.add_argument("--norm", default="coverpoints/norm", type=Path)
    ap.add_argument(
        "--coverage",
        default="coverpoints/priv",
        type=Path,
        help="directory of <Suite>_coverage.svh files (checks coverpoint names when present)",
    )
    ap.add_argument("--out", default="docs/ctp/build/generated/testplans/priv", type=Path)
    a = ap.parse_args()

    rules = rule_map(a.norm)
    known: set[str] = set()
    cache = a.norm / "norm-rules.json"
    if cache.exists():
        known = {
            r["name"] for r in json.loads(cache.read_text(encoding="utf-8")).get("normative_rules", []) if r.get("name")
        }
    a.out.mkdir(parents=True, exist_ok=True)
    all_warnings: list[str] = []
    for f in sorted(a.plans.glob("*.yaml")):
        plan = load_yaml(f)
        if not isinstance(plan, dict):
            sys.exit(f"{f}: expected a mapping")
        suite = plan["suite"]
        text, warnings = render(plan, rules.get(suite, {}), known, coverage_names(a.coverage, suite), f)
        (a.out / f"{suite}.adoc").write_text(text, encoding="utf-8")
        all_warnings += warnings
    # one line per suite and kind, so the build log stays readable
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for w in all_warnings:
        suite, _, rest = w.partition(":")
        kind = "coverpoints not in" if "is not a coverpoint" in rest else "normative rules not in"
        item = rest.split(" ")[1] if kind.startswith("coverpoints") else rest.split("normative rule ")[1].split(" ")[0]
        grouped[(suite.split("/")[0], kind)].append(item)
    for (suite, kind), items in sorted(grouped.items()):
        target = f"{suite}_coverage.svh" if kind.startswith("coverpoints") else "norm-rules.json"
        print(f"warning: {suite}: {len(items)} {kind} {target}: {', '.join(sorted(set(items)))}", file=sys.stderr)


if __name__ == "__main__":
    main()
