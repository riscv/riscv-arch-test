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
from pathlib import Path

HEADER_LINE = "Covergroup                                             Metric       Goal       Bins    Status"
TYPE_LINE_PATTERN = re.compile(r"^\s*TYPE\s+(.+?)\s*$")
COVERGROUP_PREFIX = "/RISCV_coverage_pkg/RISCV_coverage__1/"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate coverage reports from a UCDB file.")
    parser.add_argument("ucdb", help="Input UCDB file", type=Path)
    parser.add_argument("report_prefix", help="Output report prefix", type=Path)
    args = parser.parse_args()

    report_dir = args.report_prefix.parent
    report_name = args.report_prefix.name
    full_report = report_dir / f"{report_name}_report.txt"
    uncovered_report = report_dir / f"{report_name}_uncovered.txt"
    summary_report = report_dir / f"{report_name}_summary.txt"

    report_dir.mkdir(parents=True, exist_ok=True)

    vcover_cmd = ["vcover", "report", "-details", str(args.ucdb)]

    subprocess.run([*vcover_cmd, "-output", str(full_report)], check=True)
    remove_duplicates_after_second_header(full_report)

    uncovered_report_cmd = [*vcover_cmd, "-below", "100", "-output", str(uncovered_report)]
    subprocess.run(uncovered_report_cmd, check=True)
    remove_duplicates_after_second_header(uncovered_report)

    report_to_summary(full_report, summary_report)
