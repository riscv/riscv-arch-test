#!/usr/bin/env -S uv run
# ruff: noqa: ANN401
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyyaml",
# ]
# ///

"""
Generate ASCIIDoc tables from parameter YAML files.

Usage:
  generate_param_table.py [--yaml PATH] [--udb PATH] [--out PATH]

Defaults:
    yaml: coverpoints/param
    udb:  external/riscv-unified-db/spec/std/isa/param
    out:  docs/ctp/src/param/

The script generates:
  - One .adoc file per YAML in coverpoints/param with parameter tables
  - A summary.adoc with used and unused parameter tables
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


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
        if stripped.startswith("-name:") or stripped.startswith("- name:"):
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
                current_param["coverpoint"] = yaml.safe_load(value) if value else []
            except:
                current_param["coverpoint"] = [value] if value else []

        elif stripped.startswith("effect:"):
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            try:
                current_param["effect"] = yaml.safe_load(value) if value else []
            except:
                current_param["effect"] = [value] if value else []

    # Save last parameter
    if current_param:
        result["parameter_definitions"].append(current_param)

    return result


def load_yaml(path: Path) -> Any:
    """Load YAML file with fallback for malformed files."""
    text = path.read_text(encoding="utf-8")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        # Try to parse malformed YAML by fixing common issues
        return parse_malformed_yaml(text)


def load_udb_params(udb_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all UDB parameter definitions into a dict keyed by parameter name."""
    params = {}
    for yaml_file in sorted(udb_dir.glob("*.yaml")):
        try:
            data = load_yaml(yaml_file)
            if isinstance(data, dict) and data.get("kind") == "parameter":
                name = data.get("name")
                if name:
                    params[name] = {
                        "description": data.get("description", ""),
                        "definedBy": data.get("definedBy", {}),
                        "file": yaml_file.name,
                    }
        except Exception as e:
            print(f"Warning: Failed to load {yaml_file}: {e}", file=sys.stderr)
    return params


def extract_extensions(defined_by: dict[str, Any]) -> list[str]:
    """Extract extension names from definedBy field, handling allOf/anyOf."""
    extensions = []

    def extract_from_obj(obj: Any) -> None:
        """Recursively extract extensions from nested structures."""
        if isinstance(obj, dict):
            # Direct name field - this is an extension
            if "name" in obj and isinstance(obj.get("name"), str):
                # Only add if this looks like an extension (has name at top level or in extension context)
                extensions.append(obj["name"])
                return

            # Check for direct extension field
            if "extension" in obj:
                ext = obj["extension"]
                if isinstance(ext, dict):
                    # Handle nested allOf/anyOf inside extension
                    if "allOf" in ext:
                        for item in ext.get("allOf", []):
                            extract_from_obj(item)
                    elif "anyOf" in ext:
                        for item in ext.get("anyOf", []):
                            extract_from_obj(item)
                    elif "name" in ext:
                        # Direct name in extension dict
                        extensions.append(ext["name"])
                elif isinstance(ext, str):
                    extensions.append(ext)

            # Check for extensions (plural) field
            if "extensions" in obj:
                exts = obj["extensions"]
                if isinstance(exts, list):
                    for ext in exts:
                        if isinstance(ext, dict) and "name" in ext:
                            extensions.append(ext["name"])
                        elif isinstance(ext, str):
                            extensions.append(ext)

            # Handle allOf - list of conditions (not inside extension)
            if "allOf" in obj and "extension" not in obj:
                for item in obj.get("allOf", []):
                    extract_from_obj(item)

            # Handle anyOf - list of alternatives (not inside extension)
            if "anyOf" in obj and "extension" not in obj:
                for item in obj.get("anyOf", []):
                    extract_from_obj(item)

        elif isinstance(obj, list):
            for item in obj:
                extract_from_obj(item)

    extract_from_obj(defined_by)

    # Remove duplicates while preserving order
    seen = set()
    unique_extensions = []
    for ext in extensions:
        if ext not in seen:
            seen.add(ext)
            unique_extensions.append(ext)

    return unique_extensions


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
            for cp in coverpoints:
                all_coverpoints.append(f"{covergroup}/{cp}")

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
        extensions = extract_extensions(udb_info.get("definedBy", {}))
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
        extensions = extract_extensions(udb_info.get("definedBy", {}))
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
    p.add_argument(
        "--udb", default="external/riscv-unified-db/spec/std/isa/param", help="Path to UDB parameter directory"
    )
    p.add_argument("--out", default="docs/ctp/src/param/", help="Output directory for ASCIIDoc files")
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

    udb_path = Path(args.udb)
    if not udb_path.exists():
        alt = script_dir.parent / args.udb
        if alt.exists():
            udb_path = alt
        else:
            print(f"Error: UDB directory not found: {args.udb} or {alt}", file=sys.stderr)
            sys.exit(2)

    out_path = Path(args.out)

    # Load UDB parameters
    print(f"Loading UDB parameters from: {udb_path}")
    udb_params = load_udb_params(udb_path)
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
    # We treat files named "<base>_norm_rules.adoc" in docs/ctp/src/norm as extensions.

    # Resolve norm directory relative to repository layout
    script_dir = Path(__file__).resolve().parent
    # Prefer top-level docs/ctp/src/norm relative to the repo (sibling of generators)
    repo_root_candidate = script_dir.parent.parent  # .../riscv-arch-test-dh
    norm_dir_candidates = [
        repo_root_candidate / "docs" / "ctp" / "src" / "norm",
        (Path.cwd() / "src" / "norm"),
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
