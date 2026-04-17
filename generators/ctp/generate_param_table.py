#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "ruamel-yaml>=0.18.16",
# ]
# ///

"""
Generate ASCIIDoc tables from parameter YAML files.

Usage:
  generate_param_table.py [--yaml PATH] [--out PATH]

Defaults:
    yaml: coverpoints/param
    out:  docs/ctp/build/generated/param/

The script generates:
  - One .adoc file per YAML in coverpoints/param with parameter tables
  - A summary.adoc with used and unused parameter tables

UDB parameters are loaded via the `udb list parameters` CLI command (from the udb gem).
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError


def parse_malformed_yaml(text: str) -> dict[str, Any]:
    """Parse malformed YAML with -name: instead of - name:."""
    result = {"parameter_definitions": []}

    lines = text.splitlines()
    current_param: dict[str, Any] = {}

    for line in lines:
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        # Check for parameter_definitions start
        if "parameter_definitions:" in stripped:
            continue

        # Check for new parameter (-name:)
        if stripped.startswith(("-name:", "- name:")):
            # Save previous parameter
            if current_param:
                result["parameter_definitions"].append(current_param)

            # Start new parameter
            name_part = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            current_param = {"name": name_part}

        # Check for other fields
        elif stripped.startswith("coverpoint:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            try:
                yaml_parser = YAML(typ="safe", pure=True)
                current_param["coverpoint"] = yaml_parser.load(value) if value else []
            except YAMLError:
                current_param["coverpoint"] = [value] if value else []

        elif stripped.startswith("effect:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            try:
                yaml_parser = YAML(typ="safe", pure=True)
                current_param["effect"] = yaml_parser.load(value) if value else []
            except YAMLError:
                current_param["effect"] = [value] if value else []

    # Save last parameter
    if current_param:
        result["parameter_definitions"].append(current_param)

    return result


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file with fallback for malformed files."""
    text = path.read_text(encoding="utf-8")
    yaml_parser = YAML(typ="safe", pure=True)
    try:
        return yaml_parser.load(text)
    except YAMLError:
        # Try to parse malformed YAML by fixing common issues
        return parse_malformed_yaml(text)


def _ensure_udb_installed() -> None:
    """Ensure the UDB gem is installed via bundler, installing if necessary."""
    if shutil.which("udb") is not None:
        return

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
        try:
            subprocess.run(["bundle", "install"], check=True, cwd=gemfile.parent)
        except subprocess.CalledProcessError:
            print("Error: 'bundle install' failed. Check Ruby and bundler installation.", file=sys.stderr)
            sys.exit(2)

    if shutil.which("udb") is None:
        print("Error: 'udb' command still not found after 'bundle install'.", file=sys.stderr)
        sys.exit(2)


def load_udb_params() -> dict[str, dict[str, Any]]:
    """Load all UDB parameter definitions via the `udb list parameters` CLI command."""
    _ensure_udb_installed()
    try:
        result = subprocess.run(
            ["udb", "list", "parameters", "-f", "json"],
            check=True,
            capture_output=True,
            text=True,
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
    """Parse input YAML and extract parameter entries."""
    data = load_yaml(yaml_path)
    entries = []

    if not isinstance(data, dict):
        return entries

    param_defs = data.get("parameter_definitions", [])
    if not isinstance(param_defs, list):
        return entries

    for item in param_defs:
        if not isinstance(item, dict):
            continue

        # Handle both "name" and "-name" (malformed YAML)
        name = item.get("name") or item.get("-name")
        if not name:
            continue

        # Extract coverpoint - can be list or string
        coverpoint = item.get("coverpoint", [])
        if isinstance(coverpoint, str):
            coverpoint = [coverpoint]
        elif not isinstance(coverpoint, list):
            coverpoint = []

        # Extract effect - can be list or string
        effect = item.get("effect", [])
        if isinstance(effect, str):
            effect = [effect]
        elif not isinstance(effect, list):
            effect = []

        entries.append({"name": name.strip(), "coverpoint": coverpoint, "effect": effect})

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

        # Get description from UDB
        description = ""
        if param_name in udb_params:
            description = udb_params[param_name].get("description", "")

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
    p.add_argument("--yaml", default="coverpoints/param", help="Path to directory containing input YAML files")
    p.add_argument("--out", default="docs/ctp/build/generated/param/", help="Output directory for ASCIIDoc files")
    p.add_argument("--norm-dir", default=None, help="Path to norm rules directory (for placeholder generation)")
    args = p.parse_args()

    # Resolve paths relative to script directory if needed
    script_dir = Path(__file__).resolve().parent

    yaml_path = Path(args.yaml)
    if not yaml_path.exists():
        alt = script_dir.parent.parent / args.yaml
        if alt.exists():
            yaml_path = alt
        else:
            print(f"Error: YAML directory not found: {args.yaml} or {alt}", file=sys.stderr)
            sys.exit(2)

    out_path = Path(args.out)

    # Load UDB parameters via the udb gem CLI
    print("Loading UDB parameters via 'udb list parameters'...")
    udb_params = load_udb_params()
    print(f"Loaded {len(udb_params)} UDB parameters")

    # Find all input YAML files
    if yaml_path.is_dir():
        yaml_files = sorted(list(yaml_path.glob("*.yaml")) + list(yaml_path.glob("*.yml")))
    else:
        yaml_files = [yaml_path]

    if not yaml_files:
        print(f"No YAML files found in: {yaml_path}", file=sys.stderr)
        sys.exit(2)

    print(f"Processing {len(yaml_files)} input YAML files")

    # Process each input YAML file
    for yaml_file in yaml_files:
        entries = parse_input_yaml(yaml_file)

        if not entries:
            print(f"  Warning: No parameter entries found in {yaml_file.name}", file=sys.stderr)
            continue

        base = yaml_file.stem
        outpath = out_path / f"{base}_parameters.adoc"
        make_param_table(entries, udb_params, outpath, base)

    # Also produce a placeholder .adoc for any extension that has a norm adoc
    # but lacks a corresponding input YAML in the provided yaml source directory.
    # We treat files named "<base>_norm_rules.adoc" in the norm directory as extensions.

    # Resolve norm directory
    if args.norm_dir:
        norm_dir = Path(args.norm_dir)
        if not norm_dir.exists():
            print(f"Error: specified norm directory does not exist: {norm_dir}", file=sys.stderr)
            sys.exit(2)
    else:
        script_dir = Path(__file__).resolve().parent
        repo_root_candidate = script_dir.parent.parent
        norm_dir_candidates = [
            repo_root_candidate / "docs" / "ctp" / "build" / "generated" / "norm",
            (Path.cwd() / "build" / "generated" / "norm"),
        ]
        norm_dir = None
        for cand in norm_dir_candidates:
            if cand.exists():
                norm_dir = cand
                break

    if norm_dir is None:
        print("Warning: norm directory not found; skipping placeholder generation", file=sys.stderr)
    else:
        # Collect base names from norm files
        norm_bases: set[str] = set()
        for f in norm_dir.glob("*_norm_rules.adoc"):
            name = f.name
            if name.endswith("_norm_rules.adoc"):
                base = name[: -len("_norm_rules.adoc")]
                if base:
                    norm_bases.add(base)

        # Collect bases that already have YAML inputs
        yaml_bases: set[str] = set()
        for yf in yaml_files:
            yaml_bases.add(yf.stem)

        # Determine which bases are missing YAML
        missing_bases = sorted(b for b in norm_bases if b not in yaml_bases)

        # Common header
        argv_abs = [str(Path(arg).resolve()) if Path(arg).exists() else arg for arg in sys.argv]
        command_line = " ".join(argv_abs)
        gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        for base in missing_bases:
            outpath = out_path / f"{base}_parameters.adoc"
            lines = [
                "// WARNING: This file was automatically generated.",
                "// Do not modify by hand.",
                f"// Generation command: {command_line}",
                f"// Generation date: {gen_date}",
                f'// Note: No corresponding input YAML found in "{yaml_path}"; generating placeholder.',
                "",
                "*UDB Parameters:* None.",
                "",
            ]
            outpath.parent.mkdir(parents=True, exist_ok=True)
            outpath.write_text("\n".join(lines), encoding="utf-8")

    # Generate summary
    summary_path = out_path / "summary.adoc"
    make_summary_tables(yaml_files, udb_params, summary_path)
    print(f"Generated summary: {summary_path}")


if __name__ == "__main__":
    main()
