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
Generate ASCIIDoc tables from parameter YAML files.

Usage:
  generate_param_table.py --yaml DIR --out DIR

The script generates:
  - One .adoc file per YAML in coverpoints/param with parameter tables
  - A summary.adoc with used and unused parameter tables

UDB parameters are loaded via the `udb list parameters` CLI command (from the udb gem).
"""

import argparse
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def _ensure_udb_installed() -> Path:
    """Ensure the UDB gem is installed via bundler, installing if necessary."""
    gemfile = Path(__file__).resolve().parent.parent.parent / "framework" / "src" / "act" / "data" / "Gemfile"
    if not gemfile.exists():
        print(
            "Error: 'udb' command not found and Gemfile not found. Install the udb gem (see README).", file=sys.stderr
        )
        sys.exit(2)

    try:
        subprocess.run(["bundle", "check"], check=True, cwd=gemfile.parent, capture_output=True, text=True)
    except FileNotFoundError:
        print(
            "Error: 'udb' and 'bundle' commands not found. See the README for installation instructions.",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.CalledProcessError:
        print("UDB gem missing or out of date; running 'bundle install'...")
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                subprocess.run(["bundle", "install"], check=True, cwd=gemfile.parent)
                break
            except subprocess.CalledProcessError:
                if attempt == max_attempts:
                    print("Error: 'bundle install' failed. Check Ruby and bundler installation.", file=sys.stderr)
                    sys.exit(2)
                backoff = attempt * 10
                print(f"'bundle install' attempt {attempt} failed. Retrying in {backoff}s...")
                time.sleep(backoff)

    return gemfile


def load_udb_params() -> dict[str, dict[str, Any]]:
    """Load all UDB parameter definitions via the `udb list parameters` CLI command."""
    gemfile = _ensure_udb_installed()
    try:
        result = subprocess.run(
            ["bundle", "exec", "udb", "list", "parameters", "-f", "json"],
            check=True,
            capture_output=True,
            text=True,
            cwd=gemfile.parent,
        )
    except FileNotFoundError:
        print("Error: 'udb' command not found. Install the udb gem (see README).", file=sys.stderr)
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print(f"Error: 'udb list parameters' failed: {e.stderr}", file=sys.stderr)
        sys.exit(2)

    params = {}
    for entry in json.loads(result.stdout):
        name = entry.get("name")
        if name:
            params[name] = {
                "description": entry.get("description", "").strip(),
                "exts": entry.get("exts", ""),
            }
    return params


def extract_extensions(exts_str: str) -> list[str]:
    """Extract extension names from a UDB exts expression string.

    Examples:
        "S>=0" -> ["S"]
        "(Zicbom>=0 || Zicbop>=0 || Zicboz>=0)" -> ["Zicbom", "Zicbop", "Zicboz"]
        "(Sm>=0 && (MARCHID_IMPLEMENTED==true))" -> ["Sm"]
    """
    # Match extension names: sequences of word characters that start with an uppercase letter,
    # followed by a version comparison operator (>=, <=, ==, >, <)
    extensions = re.findall(r"\b([A-Z][A-Za-z0-9]*)\s*(?:>=|<=|==|>|<)", exts_str)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for ext in extensions:
        if ext not in seen:
            seen.add(ext)
            unique.append(ext)
    return unique


def parse_input_yaml(yaml_path: Path) -> list[dict[str, Any]]:
    """Parameter entries of a coverpoints/param YAML file."""
    data = YAML(typ="safe", pure=True).load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"parameter_definitions"}:
        sys.exit(f"Error: {yaml_path}: expected a single 'parameter_definitions' key")
    entries = []
    for i, item in enumerate(data["parameter_definitions"] or []):
        where = f"{yaml_path}: entry {i + 1}"
        if not isinstance(item, dict) or set(item) != {"name", "coverpoint", "effect"}:
            sys.exit(f"Error: {where}: expected 'name', 'coverpoint' and 'effect'")
        if not isinstance(item["name"], str) or not item["name"].strip():
            sys.exit(f"Error: {where}: 'name' must be a non-empty string")
        for key in ("coverpoint", "effect"):
            if not isinstance(item[key], list) or not all(isinstance(x, str) for x in item[key]):
                sys.exit(f"Error: {where} ({item['name']}): '{key}' must be a list of strings")
        entries.append({"name": item["name"].strip(), "coverpoint": item["coverpoint"], "effect": item["effect"]})
    if not entries:
        sys.exit(f"Error: {yaml_path}: no parameter entries")
    return entries


def make_param_table(
    entries: list[dict[str, Any]], udb_params: dict[str, dict[str, Any]], outpath: Path, base: str
) -> None:
    """Generate AsciiDoc table for parameters."""
    lines = []

    # Add auto-generation header
    argv_abs = [str(Path(arg).resolve()) if Path(arg).exists() else arg for arg in sys.argv]
    command_line = " ".join(argv_abs)
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines.extend(
        [
            "// WARNING: This file was automatically generated.",
            "// Do not modify by hand.",
            f"// Generation command: {command_line}",
            f"// Generation date: {gen_date}",
            "",
        ]
    )

    # Add table header
    lines.extend(
        [
            f"[[t-{base}-parameters]]",
            f".{base} UDB Parameters",
            '[cols="1,3,2,2", options="header"]',
            "|===",
            "|Parameter |Description |Coverpoint |Effect",
            "",
        ]
    )

    # Add rows
    for entry in entries:
        param_name = entry["name"]

        description = udb_params[param_name]["description"]

        # Format coverpoint list
        coverpoint_str = ", ".join(entry["coverpoint"]) if entry["coverpoint"] else ""

        # Format effect list
        effect_str = ", ".join(entry["effect"]) if entry["effect"] else ""

        # Escape pipe characters
        param_name = param_name.replace("|", "&#124;")
        description = description.replace("|", "&#124;")
        coverpoint_str = coverpoint_str.replace("|", "&#124;")
        effect_str = effect_str.replace("|", "&#124;")

        lines.append(f"|{param_name} |{description} |{coverpoint_str} |{effect_str}")
        lines.append("")

    lines.extend(["|===", ""])

    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(lines), encoding="utf-8")


def make_summary_tables(all_input_files: list[Path], udb_params: dict[str, dict[str, Any]], outpath: Path) -> None:
    """Generate summary tables for used and unused parameters."""
    # Build mapping of parameter -> list of (covergroup, coverpoints)
    param_usage: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)

    for input_file in all_input_files:
        entries = parse_input_yaml(input_file)
        base = input_file.stem
        covergroup = f"{base}_cg"

        for entry in entries:
            param_name = entry["name"]
            coverpoints = entry["coverpoint"]
            param_usage[param_name].append((covergroup, coverpoints))

    # Separate used and unused parameters
    used_params = set(param_usage.keys())
    all_params = set(udb_params.keys())
    unused_params = all_params - used_params

    lines = []

    # Add auto-generation header
    argv_abs = [str(Path(arg).resolve()) if Path(arg).exists() else arg for arg in sys.argv]
    command_line = " ".join(argv_abs)
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines.extend(
        [
            "// WARNING: This file was automatically generated.",
            "// Do not modify by hand.",
            f"// Generation command: {command_line}",
            f"// Generation date: {gen_date}",
            "",
        ]
    )

    # Used parameters table
    lines.extend(
        [
            "[[t-used-parameters]]",
            ".Used UDB Parameters",
            '[cols="1,3,2,3", options="header"]',
            "|===",
            "|Parameter |Dependent Coverpoints |Defined By |Description",
            "",
        ]
    )

    for param_name in sorted(used_params):
        # Collect all coverpoints with their covergroup names
        all_coverpoints = []
        for covergroup, coverpoints in param_usage[param_name]:
            all_coverpoints.extend(f"{covergroup}/{cp}" for cp in coverpoints)

        # Remove duplicates while preserving order
        seen = set()
        unique_coverpoints = []
        for cp in all_coverpoints:
            if cp not in seen:
                seen.add(cp)
                unique_coverpoints.append(cp)

        coverpoints_str = ", ".join(unique_coverpoints)

        # Get UDB info
        udb_info = udb_params.get(param_name, {})
        description = udb_info.get("description", "")
        extensions = extract_extensions(udb_info.get("exts", ""))
        defined_by_str = ", ".join(extensions)

        # Escape pipes
        param_name_esc = param_name.replace("|", "&#124;")
        coverpoints_esc = coverpoints_str.replace("|", "&#124;")
        defined_by_esc = defined_by_str.replace("|", "&#124;")
        description_esc = description.replace("|", "&#124;")

        lines.append(f"|{param_name_esc} |{coverpoints_esc} |{defined_by_esc} |{description_esc}")
        lines.append("")

    lines.extend(["|===", "", ""])

    # Unused parameters table
    lines.extend(
        [
            "[[t-unused-parameters]]",
            ".Unused UDB Parameters",
            '[cols="1,2,3", options="header"]',
            "|===",
            "|Parameter |Defined By |Description",
            "",
        ]
    )

    for param_name in sorted(unused_params):
        # Skip MOCK parameters
        if param_name.startswith("MOCK"):
            continue

        udb_info = udb_params.get(param_name, {})
        description = udb_info.get("description", "")
        extensions = extract_extensions(udb_info.get("exts", ""))
        defined_by_str = ", ".join(extensions)

        # Escape pipes
        param_name_esc = param_name.replace("|", "&#124;")
        defined_by_esc = defined_by_str.replace("|", "&#124;")
        description_esc = description.replace("|", "&#124;")

        lines.append(f"|{param_name_esc} |{defined_by_esc} |{description_esc}")
        lines.append("")

    lines.extend(["|===", ""])

    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate ASCIIDoc tables from parameter YAML files")
    p.add_argument("--yaml", required=True, type=Path, help="directory of parameter YAML files")
    p.add_argument("--out", required=True, type=Path, help="output directory for the AsciiDoc tables")
    args = p.parse_args()

    yaml_files = sorted(args.yaml.glob("*.yaml"))
    if not yaml_files:
        sys.exit(f"Error: no YAML files in {args.yaml}")

    print("Loading UDB parameters via 'udb list parameters'...")
    udb_params = load_udb_params()
    print(f"Loaded {len(udb_params)} UDB parameters")

    entries_by_file = {f: parse_input_yaml(f) for f in yaml_files}
    unknown = [
        f"{f}: {e['name']}" for f, entries in entries_by_file.items() for e in entries if e["name"] not in udb_params
    ]
    if unknown:
        sys.exit("Error: parameters not defined in UDB:\n  " + "\n  ".join(unknown))

    for yaml_file, entries in entries_by_file.items():
        make_param_table(entries, udb_params, args.out / f"{yaml_file.stem}_parameters.adoc", yaml_file.stem)

    summary_path = args.out / "summary.adoc"
    make_summary_tables(yaml_files, udb_params, summary_path)
    print(f"Generated summary: {summary_path}")


if __name__ == "__main__":
    main()
