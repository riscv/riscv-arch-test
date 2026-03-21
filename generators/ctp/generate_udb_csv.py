#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
#
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""
Generate a CSV spreadsheet of UDB parameters via the `udb list parameters` CLI command.

Creates a CSV with columns:
- name: Parameter name
- ext: Comma-separated list of extensions that define this parameter
- description: Parameter description

UDB parameters are loaded via the `udb list parameters` CLI command (from the udb gem).
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path


def extract_extensions(exts_str: str) -> list[str]:
    """Extract extension names from a UDB exts expression string.

    Examples:
        "S>=0" -> ["S"]
        "(Zicbom>=0 || Zicbop>=0 || Zicboz>=0)" -> ["Zicbom", "Zicbop", "Zicboz"]
    """
    extensions = re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*(?:>=|<=|==|>|<)", exts_str)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for ext in extensions:
        if ext not in seen:
            seen.add(ext)
            unique.append(ext)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CSV of RISC-V UDB parameters")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("udb_parameters.csv"),
        help="Output CSV file path",
    )

    args = parser.parse_args()
    output_csv = args.output

    # Load parameters via udb gem CLI
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

    # Parse and collect data
    rows = []
    for entry in json.loads(result.stdout):
        name = entry.get("name", "")
        if not name:
            continue

        description = entry.get("description", "").strip()
        exts_str = entry.get("exts", "")
        extensions = extract_extensions(exts_str)
        ext = ", ".join(extensions)

        # Skip Xmock entries
        if ext != "Xmock":
            rows.append({"name": name, "ext": ext, "description": description})

    # Sort by ext column
    rows.sort(key=lambda x: x["ext"])

    # Write to CSV
    try:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "ext", "description"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"CSV file created: {output_csv}")
        print(f"Total parameters: {len(rows)}")
    except OSError as e:
        print(f"Error writing CSV: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
