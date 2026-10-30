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
Generate AsciiDoc tables of normative rules and their coverpoints.

Each coverpoints/norm/<suite>.yaml maps normative rules to coverpoints.  This script writes
<suite>_norm_rules.adoc with one row per entry: the rule names, their text from the ISA manual's
norm-rules.json, and the coverpoints.  Every rule name must exist in norm-rules.json, except in a
suite whose rules are not yet tagged in the ISA manual.  Such a file says where the tags are pending
with a top-level 'untagged_upstream' key, and its unknown names are warnings instead of errors.

Usage:
  generate_norm_table.py --json norm-rules.json --yaml DIR --param DIR --out DIR [--report FILE]
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import quote

from ruamel.yaml import YAML

# The ISA manual publishes the unprivileged and privileged volumes as a single document.
SPEC_URL = "https://riscv.github.io/riscv-isa-manual/snapshot/spec/index.html"


class NormYamlError(Exception):
    pass


class NormYaml(NamedTuple):
    groups: list[tuple[list[str], list[str]]]  # (rule names, coverpoints) for each entry
    untagged_upstream: str | None  # where the suite's rule tags are pending, if not yet in the ISA manual


def load_norm_yaml(path: Path) -> NormYaml:
    """Read and check a coverpoints/norm YAML file."""
    data = YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not set(data) <= {"untagged_upstream", "normative_rule_definitions"}:
        raise NormYamlError(f"{path}: expected 'normative_rule_definitions' and optionally 'untagged_upstream'")
    untagged = data.get("untagged_upstream")
    if "untagged_upstream" in data and (not isinstance(untagged, str) or not untagged.strip()):
        raise NormYamlError(f"{path}: 'untagged_upstream' must say where the rule tags are pending")
    groups = []
    for i, item in enumerate(data["normative_rule_definitions"] or []):
        where = f"{path}: entry {i + 1}"
        if not isinstance(item, dict) or set(item) not in ({"name", "coverpoint"}, {"names", "coverpoint"}):
            raise NormYamlError(f"{where}: expected 'name' or 'names', and 'coverpoint'")
        names = item.get("names", [item.get("name")])
        coverpoints = item["coverpoint"]
        if not isinstance(names, list) or not names or not all(isinstance(n, str) and n for n in names):
            raise NormYamlError(f"{where}: rule names must be non-empty strings")
        if not isinstance(coverpoints, list) or not coverpoints or not all(isinstance(c, str) for c in coverpoints):
            raise NormYamlError(f"{where} ({', '.join(names)}): 'coverpoint' must be a non-empty list of strings")
        if len(set(names)) != len(names):
            raise NormYamlError(f"{where}: repeated rule name in {names}")
        groups.append((names, coverpoints))
    repeated = sorted(n for n, k in Counter(n for names, _ in groups for n in names).items() if k > 1)
    if repeated:
        raise NormYamlError(f"{path}: rules listed in more than one entry: {', '.join(repeated)}")
    return NormYaml(groups, untagged)


def load_norm_rules(path: Path) -> dict[str, dict[str, Any]]:
    """Rule name -> norm-rules.json entry."""
    return {entry["name"]: entry for entry in json.loads(path.read_text(encoding="utf-8"))["normative_rules"]}


# Inline macros defined by riscv-isa-manual's src/lib/macros.rb.  The normative rule text is
# extracted from the manual's sources with these macros unexpanded, and the CTP build does not load
# that extension, so expand them here the way the manual renders them:
#   insn:foo[]         FOO           insn:foo[bar,baz]   FOO bar, baz
#   ext:zoo[]          `Zoo`         csr:foo[]           `foo`
#   csr:foo[bar]       `foo.BAR`     csr::[bar]          `BAR`
#   qty:16[KiB]        16 KiB (non-breaking space)
# The *link forms are cross-references inside the manual; the rule text is already one link to the
# manual, and links cannot nest, so they render like their plain forms.
_ENTITY_SPLIT_RE = re.compile(r"(&#?\w+;)")
_ISA_MANUAL_MACRO_RE = re.compile(r"\b(insn|insnlink|ext|extlink|csr|csrlink|qty|xref):([^\[\s]*)\[([^\]]*)\]")


def expand_isa_manual_macros(text: str) -> str:
    """Expand the riscv-isa-manual inline macros in rule text into plain AsciiDoc."""

    def expand(m: re.Match[str]) -> str:
        kind, name, arg = m.group(1), m.group(2), m.group(3)
        args = [a.strip() for a in arg.split(",")] if arg.strip() else []
        if kind in ("insn", "insnlink"):
            # Uppercase the mnemonic but not any HTML entities in it, e.g. the angle brackets of
            # vmv<nr>r.v, which the manual's JSON carries double-escaped as &amp;#60; and &amp;#62;
            name = name.replace("&amp;", "&")
            mnemonic = "".join(t if t.startswith("&") else t.upper() for t in _ENTITY_SPLIT_RE.split(name))
            return mnemonic + (" " + ", ".join(args) if args else "")
        if kind in ("ext", "extlink"):
            return f"`{name.capitalize()}`"
        if kind in ("csr", "csrlink"):
            parts = ([] if name in ("", ":") else [name.lower()]) + ([args[0].upper()] if args else [])
            return "`" + ".⁠".join(parts) + "`"
        if kind == "qty":
            return name + " " + (args[0] if args else "")
        # xref
        return name

    return _ISA_MANUAL_MACRO_RE.sub(expand, text)


# Cross-references inside rule text point at ISA-manual anchors that do not exist in the CTP, and
# asciidoctor resolves even the entity-escaped form, so render them as their link text (or the anchor name).
_XREF_RE = re.compile(r"(?:&lt;|<){2}([^,&<>]+?)(?:,([^&<>]+?))?(?:&gt;|>){2}")


def plain_xrefs(text: str) -> str:
    return _XREF_RE.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)


def rule_link(name: str, text: str) -> str:
    """The rule's text as one AsciiDoc link to its tag in the ISA manual."""
    disp = plain_xrefs(expand_isa_manual_macros(" ".join(text.split())))
    # Math is pre-rendered to images in the ISA manual build; those images do not exist here.
    disp = re.sub(r"image:[^\[]*\[[^\]]*\]", "[math expression]", disp)
    if not disp:
        return ""
    # Escape the link text; commas would otherwise separate link attributes and '|' table cells.
    disp = (
        disp.replace("\\", "\\\\").replace('"', '\\"').replace("]", "\\]").replace(",", "&#44;").replace("|", "&#124;")
    )
    return f"link:{SPEC_URL}#{quote('norm:' + name, safe='')}[{disp}]"


def generation_header() -> list[str]:
    argv_abs = [str(Path(arg).resolve()) if Path(arg).exists() else arg for arg in sys.argv]
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return [
        "// WARNING: This file was automatically generated.",
        "// Do not modify by hand.",
        "// Generation command: " + " ".join(argv_abs),
        "// Generation date: " + gen_date,
        "",
    ]


def make_adoc_table(
    base: str, groups: list[tuple[list[str], list[str]]], texts: dict[str, str], has_params: bool
) -> str:
    lines = [*generation_header(), f"[[t-{base}-normative-rules]]", f".{base} Normative Rules"]
    if groups:
        lines += ['[cols="1,4,3", options="header"]', "|===", "|Normative Rule |Rule Text |Coverpoints", ""]
        for names, coverpoints in groups:
            parts = [(n, texts[n]) for n in names if texts[n]]
            parts = [p for i, p in enumerate(parts) if p[1] not in [q[1] for q in parts[:i]]]
            text = parts[0][1] if len(parts) == 1 else " ".join(f"{n}: {t}" for n, t in parts)
            cell = ", ".join(coverpoints).replace("|", "&#124;")
            lines += [f"|{', '.join(names)} |{text} |{cell}", ""]
        lines += ["|===", ""]
    else:
        lines += ["No normative rules found for this section.", ""]
    # Generated files live in src/norm and src/param, so use ../param
    lines += [f"include::../param/{base}_parameters.adoc[]" if has_params else "*UDB Parameters:* None.", ""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", required=True, type=Path, help="the ISA manual's norm-rules.json")
    p.add_argument("--yaml", required=True, type=Path, help="directory of normative rule to coverpoint YAML files")
    p.add_argument("--param", required=True, type=Path, help="directory of parameter YAML files")
    p.add_argument("--out", required=True, type=Path, help="output directory for the AsciiDoc tables")
    p.add_argument("--report", type=Path, help="write the rules that no YAML file maps here, by chapter")
    args = p.parse_args()

    rules = load_norm_rules(args.json)
    texts: dict[str, str] = defaultdict(str, {name: rule_link(name, entry["text"]) for name, entry in rules.items()})

    yaml_files = sorted(args.yaml.glob("*.yaml"))
    if not yaml_files:
        sys.exit(f"Error: no YAML files in {args.yaml}")

    args.out.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    mapped: set[str] = set()
    for yfile in yaml_files:
        try:
            groups, untagged = load_norm_yaml(yfile)
        except NormYamlError as e:
            errors.append(str(e))
            continue
        names = {n for ns, _ in groups for n in ns}
        mapped |= names
        unknown = sorted(names - rules.keys())
        if untagged is None and unknown:
            errors.append(f"{yfile}: {len(unknown)} rules not in {args.json.name}: {', '.join(unknown)}")
            continue
        if untagged is not None:
            if unknown:
                print(f"warning: {yfile.name}: {len(unknown)} rules not yet tagged in the ISA manual ({untagged})")
            else:
                print(f"warning: {yfile.name}: every rule is now in {args.json.name}; remove 'untagged_upstream'")
        base = yfile.stem
        adoc = make_adoc_table(base, groups, texts, (args.param / f"{base}.yaml").exists())
        (args.out / f"{base}_norm_rules.adoc").write_text(adoc, encoding="utf-8")

    if errors:
        sys.exit("\n".join(f"Error: {e}" for e in errors))

    unmapped = sorted(rules.keys() - mapped)
    print(f"{len(rules) - len(unmapped)} of {len(rules)} normative rules are mapped to coverpoints")
    if args.report:
        by_chapter: dict[str, list[str]] = {}
        for name in unmapped:
            by_chapter.setdefault(rules[name]["chapter_name"], []).append(name)
        report = ["Normative rules that no coverpoints/norm YAML file maps, by chapter", ""]
        for chapter, names in sorted(by_chapter.items()):
            report += [f"{chapter}:", *(f"  {n}" for n in names), ""]
        args.report.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
