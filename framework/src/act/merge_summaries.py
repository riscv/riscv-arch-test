##################################
# merge_summaries.py
#
# jcarlin@hmc.edu 4 Nov 2025
# SPDX-License-Identifier: Apache-2.0
#
# Merge multiple coverage summary files into a single formatted file
##################################

import argparse
import sys
from pathlib import Path


def parse_summary_file(file_path: Path) -> list[tuple[str, str, str, str, str]]:
    """Parse a summary file and return list of entries (excluding header)."""
    entries = []
    with file_path.open() as f:
        lines = f.readlines()
        # Skip header line (first line)
        for line in lines[1:]:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            # Split by whitespace
            parts = line.split()
            if len(parts) >= 5:
                covergroup = parts[0]
                metric = parts[1]
                goal = parts[2]
                bins = parts[3]
                status = " ".join(parts[4:])
                entries.append((covergroup, metric, goal, bins, status))
    return entries


def merge_summaries(input_files: list[Path], output_file: Path) -> None:
    """Merge multiple summary files into one with consistent formatting."""
    all_entries = []

    # Parse all input files
    for file_path in input_files:
        if not file_path.exists():
            print(f"Warning: File {file_path} does not exist, skipping.", file=sys.stderr)
            continue
        entries = parse_summary_file(file_path)
        all_entries.extend(entries)

    if not all_entries:
        print("Error: Failed to merge coverage summaries. All input summary files are empty.", file=sys.stderr)
        sys.exit(1)

    # Calculate column widths based on all entries
    padding = 5
    headers = ["Covergroup", "Metric", "Goal", "Bins", "Status"]
    widths = [
        max(len(header) + padding, max(len(entry[idx]) for entry in all_entries) + padding)
        for idx, header in enumerate(headers)
    ]

    # Generate formatted output
    header_line = "".join(f"{header:<{widths[idx]}}" for idx, header in enumerate(headers))
    formatted_rows = ["".join(f"{entry[idx]:<{widths[idx]}}" for idx in range(len(headers))) for entry in all_entries]

    # Write output file
    with output_file.open("w", encoding="utf-8") as f:
        f.write(header_line + "\n")
        f.write("\n".join(formatted_rows) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge multiple coverage summary files into one.")
    parser.add_argument("output", help="Output file path", type=Path)
    parser.add_argument("inputs", nargs="+", help="Input summary files", type=Path)
    args = parser.parse_args()

    merge_summaries(args.inputs, args.output)
