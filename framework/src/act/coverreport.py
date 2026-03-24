##################################
# coverreport.py
#
# jcarlin@hmc.edu 9 May 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate txt coverage reports from UCDB file
##################################

import argparse
import re
import subprocess
import sys
from pathlib import Path

HEADER_LINE = "Covergroup                                             Metric       Goal       Bins    Status"
TYPE_LINE_PATTERN = re.compile(r"^\s*TYPE\s+(.+?)\s*$")
COVERGROUP_PREFIX = "/RISCV_coverage_pkg/RISCV_coverage__1/"


def _ansi(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def _red(text: str) -> str:
    return _ansi("1;31", text)


def _green(text: str) -> str:
    return _ansi("1;32", text)


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


def print_coverage_summary(overall_summary: Path, config_name: str) -> None:
    """Print a human-readable coverage summary from an _overall_summary.txt file."""
    lines = overall_summary.read_text().splitlines()
    data_lines = [l for l in lines[1:] if l.strip()]

    num_covergroups = len(data_lines)
    percentages: list[float] = []
    partial_lines: list[str] = []

    for line in data_lines:
        parts = line.split()
        if not parts:
            continue
        try:
            pct = float(parts[1].rstrip("%"))
        except (IndexError, ValueError):
            continue
        percentages.append(pct)
        if pct < 100.0:
            partial_lines.append(line)

    avg_coverage = sum(percentages) / len(percentages) if percentages else 0.0

    if partial_lines:
        print(_red(f" RVCP: {config_name} Coverage FAIL"))
        print(f"  {num_covergroups} covergroups, average coverage {avg_coverage:.2f}%")
        print(f"  Partially covered covergroups: {len(partial_lines)}")
        for line in partial_lines:
            print(f"    {line}")
    else:
        print(_green(f" RVCP: {config_name} Coverage PASS"))
        print(f"  {num_covergroups} covergroups all with 100% coverage")


def remove_duplicates_after_second_header(file_path: Path) -> None:
    """Remove duplicates that appear after the second summary header."""
    unique_lines_before_header: set[str] = set()
    header_count = 0
    output_lines: list[str] = []

    for line in file_path.read_text().splitlines(keepends=True):
        stripped_line = line.strip()
        if stripped_line == HEADER_LINE:
            header_count += 1
            if header_count == 2:
                continue

        if header_count == 2 and stripped_line in unique_lines_before_header:
            continue

        output_lines.append(line)
        if header_count < 2:
            unique_lines_before_header.add(stripped_line)

    file_path.write_text("".join(output_lines))


def report_to_summary(report_path: Path, summary_path: Path) -> None:
    """Convert a detailed coverage report into a condensed summary."""
    lines = report_path.read_text().splitlines()
    entries: list[tuple[str, str, str, str, str]] = []

    for idx, line in enumerate(lines):
        match = TYPE_LINE_PATTERN.match(line)
        if not match:
            continue

        full_path = match.group(1).strip()
        name = (
            full_path.split(COVERGROUP_PREFIX, 1)[1].strip()
            if COVERGROUP_PREFIX in full_path
            else full_path.split("/")[-1].strip()
        )

        metrics_line = next((candidate.strip() for candidate in lines[idx + 1 :] if candidate.strip()), "")
        if not metrics_line:
            continue

        parts = metrics_line.split()
        if len(parts) < 4:
            raise ValueError(f"Unexpected metric line format: '{metrics_line}'")

        metric_value, goal_value, bins_value = parts[0], parts[1], parts[2]
        status_value = " ".join(parts[3:])

        entries.append((name, metric_value, goal_value, bins_value, status_value))

    if not entries:
        raise ValueError("No coverage entries found in report.")

    padding = 5
    headers = ["Covergroup", "Metric", "Goal", "Bins", "Status"]
    widths = [
        max(len(header) + padding, max(len(entry[idx]) for entry in entries) + padding)
        for idx, header in enumerate(headers)
    ]

    header = "".join(f"{header:<{widths[idx]}}" for idx, header in enumerate(headers))

    formatted_rows = ["".join(f"{entry[idx]:<{widths[idx]}}" for idx in range(len(headers))) for entry in entries]

    with summary_path.open("w", encoding="utf-8") as summary_file:
        summary_file.write(header + "\n")
        summary_file.write("\n".join(formatted_rows) + "\n")


def generate_report(ucdb: Path, report_prefix: Path) -> None:
    """Generate coverage reports from a UCDB file."""
    report_dir = report_prefix.parent
    report_name = report_prefix.name
    full_report = report_dir / f"{report_name}_report.txt"
    uncovered_report = report_dir / f"{report_name}_uncovered.txt"
    summary_report = report_dir / f"{report_name}_summary.txt"

    report_dir.mkdir(parents=True, exist_ok=True)

    vcover_cmd = ["vcover", "report", "-details", str(ucdb)]
    subprocess.run([*vcover_cmd, "-output", str(full_report)], check=True, capture_output=True)
    remove_duplicates_after_second_header(full_report)

    # Only generate uncovered report if coverage is not 100%
    if "TOTAL COVERGROUP COVERAGE: 100.00%" not in full_report.read_text():
        uncovered_report_cmd = [*vcover_cmd, "-below", "100", "-output", str(uncovered_report)]
        subprocess.run(uncovered_report_cmd, check=True, capture_output=True)
        remove_duplicates_after_second_header(uncovered_report)

    report_to_summary(full_report, summary_report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate coverage reports from a UCDB file.")
    parser.add_argument("ucdb", help="Input UCDB file", type=Path)
    parser.add_argument("report_prefix", help="Output report prefix", type=Path)
    args = parser.parse_args()
    generate_report(args.ucdb, args.report_prefix)
