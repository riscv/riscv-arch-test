#!/usr/bin/env python3
"""CSV line editor for testplan files. Read/update specific lines by line number."""

import argparse
import csv
import pathlib
import sys

# Column indices
COL_NAME = 0
COL_GOAL = 3
COL_DESC = 4
COL_EXPECT = 5
COL_BINS = 6
COL_SPEC_START = 11


def read_line(filepath: str, line_num: int) -> None:
    """Read and display a specific line from CSV."""
    with pathlib.Path(filepath).open(newline="") as f:
        reader = list(csv.reader(f))

    if line_num < 1 or line_num > len(reader):
        print(f"Error: Line {line_num} out of range (1-{len(reader)})")
        sys.exit(1)

    row = reader[line_num - 1]

    # Pad row if needed
    while len(row) <= COL_SPEC_START:
        row.append("")

    spec_parts = [s for s in row[COL_SPEC_START:] if s.strip()]
    spec = " ".join(spec_parts)

    print(f"Line {line_num}:")
    print(f"  name:        {row[COL_NAME]}")
    print(f"  goal:        {row[COL_GOAL]}")
    print(f"  description: {row[COL_DESC]}")
    print(f"  expectation: {row[COL_EXPECT]}")
    print(f"  bins:        {row[COL_BINS]}")
    print(f"  spec:        {spec}")


def update_line(
    filepath: str,
    line_num: int,
    name: str = None,
    goal: str = None,
    desc: str = None,
    expect: str = None,
    bins: str = None,
    spec: str = None,
) -> None:
    """Update specific fields in a CSV line."""
    with pathlib.Path(filepath).open(newline="") as f:
        reader = list(csv.reader(f))

    if line_num < 1 or line_num > len(reader):
        print(f"Error: Line {line_num} out of range (1-{len(reader)})")
        sys.exit(1)

    row = reader[line_num - 1]

    # Ensure row has enough columns
    while len(row) <= COL_SPEC_START:
        row.append("")

    if name is not None:
        row[COL_NAME] = name
    if goal is not None:
        row[COL_GOAL] = goal
    if desc is not None:
        row[COL_DESC] = desc
    if expect is not None:
        row[COL_EXPECT] = expect
    if bins is not None:
        row[COL_BINS] = bins
    if spec is not None:
        # Clear old spec columns and set new
        row = row[:COL_SPEC_START] + [spec]

    reader[line_num - 1] = row

    with pathlib.Path(filepath).open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(reader)

    print(f"Updated line {line_num}")
    read_line(filepath, line_num)


def list_lines(filepath: str) -> None:
    """List all lines with line numbers and coverpoint names."""
    with pathlib.Path(filepath).open(newline="") as f:
        reader = list(csv.reader(f))

    for i, row in enumerate(reader, 1):
        name = row[COL_NAME] if len(row) > COL_NAME else ""
        print(f"{i:4d}: {name}")


def main():
    parser = argparse.ArgumentParser(description="CSV line editor for testplan files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # read command
    read_parser = subparsers.add_parser("read", help="Read a specific line")
    read_parser.add_argument("file", help="CSV file path")
    read_parser.add_argument("line", type=int, help="Line number (1-indexed)")

    # update command
    update_parser = subparsers.add_parser("update", help="Update a specific line")
    update_parser.add_argument("file", help="CSV file path")
    update_parser.add_argument("line", type=int, help="Line number (1-indexed)")
    update_parser.add_argument("--name", help="Coverpoint name")
    update_parser.add_argument("--goal", help="Goal")
    update_parser.add_argument("--description", dest="desc", help="Description")
    update_parser.add_argument("--expectation", dest="expect", help="Expectation")
    update_parser.add_argument("--bins", help="Bins expression")
    update_parser.add_argument("--spec", help="Spec quote")

    # list command
    list_parser = subparsers.add_parser("list", help="List all lines")
    list_parser.add_argument("file", help="CSV file path")

    args = parser.parse_args()

    if args.command == "read":
        read_line(args.file, args.line)
    elif args.command == "update":
        update_line(args.file, args.line, args.name, args.goal, args.desc, args.expect, args.bins, args.spec)
    elif args.command == "list":
        list_lines(args.file)


if __name__ == "__main__":
    main()
