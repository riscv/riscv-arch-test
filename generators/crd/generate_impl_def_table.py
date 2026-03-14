#!/usr/bin/env -S uv run
"""
Generate an AsciiDoc table of implementation-defined behaviors sorted by extension.
Reads norm-rules.json and writes an AsciiDoc table with:
- Extension name (from instances property)
- Implementation-defined behavior name
- Associated text from tags array
"""

import argparse
import json
import sys
from itertools import groupby
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AsciiDoc table of implementation-defined behaviors")
    parser.add_argument(
        "--norm-rules-path",
        default="norm-rules.json",
        help="Path to norm-rules.json (default: %(default)s)",
    )
    parser.add_argument(
        "--include-warl-wlrl",
        action="store_true",
        help="Include WARL and WLRL implementation-defined behaviors (excluded by default)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to output AsciiDoc file",
    )
    args = parser.parse_args()

    # Read the norm-rules.json file
    json_file = Path(args.norm_rules_path)
    if not json_file.exists():
        print(f"Error: {json_file} not found", file=sys.stderr)
        sys.exit(1)

    with json_file.open() as f:
        data = json.load(f)

    # Collect rows for the table
    rows = []

    for entry in data.get("normative_rules", []):
        if not entry.get("impl-def-behavior"):
            continue

        # Filter out WARL and WLRL by default (unless explicitly included)
        if not args.include_warl_wlrl:
            category = entry.get("impl-def-category", "").upper()
            if category in ("WARL", "WLRL"):
                continue

        behavior_name = entry.get("name", "")
        instances = entry.get("instances", [])
        tags = entry.get("tags", [])

        # Extract text from first tag (if available)
        tag_text = ""
        if tags:
            tag_text = tags[0].get("text", "").strip()
            # Normalize whitespace
            tag_text = " ".join(tag_text.split())

        # If instances is empty or not present, still add a row
        if not instances:
            instances = [""]

        # Create a row for each instance
        rows.extend({"extension": instance, "name": behavior_name, "text": tag_text} for instance in instances)

    # Sort by extension name, then by behavior name
    rows.sort(key=lambda x: (x["extension"].lower(), x["name"].lower()))

    extension_groups = []
    # Group extensions case-insensitively to be consistent with the sort key.
    # Use the original-cased extension from the first row in each group for display.
    for _ext_key, extension_rows_iter in groupby(rows, key=lambda x: x["extension"].lower()):
        extension_rows = list(extension_rows_iter)
        display_extension = extension_rows[0]["extension"] if extension_rows[0]["extension"] else "(none)"
        extension_groups.append((display_extension, extension_rows))

    # Generate summary table (extension + count).
    output = []
    output.append("[%autowidth]")
    output.append("|===")
    output.append("| Base/Ext | Impl-Defined Behaviors")
    output.append("")

    for extension, extension_rows in extension_groups:
        row_count = len(extension_rows)
        output.append(f"| {extension}")
        output.append(f"| {row_count}")
        output.append("")

    output.append("|===")
    output.append("")

    # Generate detailed table.
    output.append('[cols="10%,35%,55%"]')
    output.append("|===")
    output.append("| Base/Ext | Impl-Defined Behavior | Description")
    output.append("")

    for extension, extension_rows in extension_groups:
        for row in extension_rows:
            name = row["name"]
            text = row["text"]

            # Escape pipe characters in text
            text = text.replace("|", "\\|")

            # Use cell continuation for better formatting if text is long
            output.append(f"| {extension}")
            output.append(f"| `{name}`")
            output.append(f"| {text}")
            output.append("")

    output.append("|===")

    output_file = Path(args.out)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(output) + "\n")


if __name__ == "__main__":
    main()
