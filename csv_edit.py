#!/usr/bin/env python3
"""CSV editing utility for testplan CSVs.

Provides efficient reading (headers + first column only) and targeted cell editing.
"""

import csv
import sys
from pathlib import Path

TESTPLANS_DIR = Path(__file__).resolve().parent / "testplans"


def get_csv_path(name: str) -> Path:
    """Resolve a CSV name to its full path. Accepts 'I', 'I.csv', or full path."""
    p = Path(name)
    if p.is_absolute():
        return p
    if not name.endswith(".csv"):
        name = f"{name}.csv"
    return TESTPLANS_DIR / name


def read_structure(csv_name: str) -> None:
    """Read and print just the header row and first column of a CSV.

    Args:
        csv_name: CSV filename (e.g. 'I', 'I.csv', or full path)
    """
    path = get_csv_path(csv_name)
    with path.open(newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    headers = rows[0]
    print(f"=== {path.name} ===")
    print(f"Columns ({len(headers)}): {', '.join(headers)}")
    print(f"\nRows ({len(rows) - 1}):")
    for row in rows[1:]:
        print(f"  {row[0]}")


def read_full(csv_name: str):
    """Read and return the full CSV as a list of lists."""
    path = get_csv_path(csv_name)
    with path.open(newline="") as f:
        return list(csv.reader(f))


def set_cells(csv_name: str, entries, value: str = "x") -> None:
    """Set specific cells in a CSV file.

    Args:
        csv_name: CSV filename (e.g. 'I', 'I.csv', or full path)
        entries: list of (row_name, col_name) tuples to set
        value: value to write into each cell (default: 'x')
    """
    path = get_csv_path(csv_name)
    with path.open(newline="") as f:
        rows = list(csv.reader(f))

    headers = rows[0]
    col_index = {name: i for i, name in enumerate(headers)}
    row_index = {row[0]: i for i, row in enumerate(rows) if i > 0}

    changed = 0
    for row_name, col_name in entries:
        if row_name not in row_index:
            print(f"WARNING: row '{row_name}' not found, skipping")
            continue
        if col_name not in col_index:
            print(f"WARNING: column '{col_name}' not found, skipping")
            continue
        ri = row_index[row_name]
        ci = col_index[col_name]
        # Extend row if needed
        while len(rows[ri]) <= ci:
            rows[ri].append("")
        rows[ri][ci] = value
        changed += 1

    # Normalize all rows to same length
    max_len = len(headers)
    for row in rows:
        while len(row) < max_len:
            row.append("")

    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Updated {changed}/{len(entries)} cells in {path.name}")


def fill_column(csv_name: str, col_name: str, row_names=None, value: str = "x") -> None:
    """Fill an entire column (or specific rows in that column) with a value.

    Args:
        csv_name: CSV filename
        col_name: column header name
        row_names: list of row names to fill, or None for all rows
        value: value to write (default: 'x')
    """
    path = get_csv_path(csv_name)
    with path.open(newline="") as f:
        rows = list(csv.reader(f))

    headers = rows[0]
    if col_name not in {name for name in headers}:
        print(f"ERROR: column '{col_name}' not found")
        return

    if row_names is None:
        row_names = [row[0] for row in rows[1:]]

    entries = [(r, col_name) for r in row_names]
    # Write back and delegate to set_cells (re-read is fine for correctness)
    set_cells(csv_name, entries, value)


def fill_row(csv_name: str, row_name: str, col_names=None, value: str = "x") -> None:
    """Fill an entire row (or specific columns in that row) with a value.

    Args:
        csv_name: CSV filename
        row_name: first-column value identifying the row
        col_names: list of column names to fill, or None for all data columns
        value: value to write (default: 'x')
    """
    path = get_csv_path(csv_name)
    with path.open(newline="") as f:
        rows = list(csv.reader(f))

    headers = rows[0]
    if col_names is None:
        col_names = headers[1:]  # skip first column (instruction name)

    entries = [(row_name, c) for c in col_names]
    set_cells(csv_name, entries, value)


def clear_cells(csv_name: str, entries) -> None:
    """Clear specific cells (set to empty string).

    Args:
        csv_name: CSV filename
        entries: list of (row_name, col_name) tuples to clear
    """
    set_cells(csv_name, entries, value="")


# CLI interface
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python csv_edit.py structure <csv_name>")
        print("  python csv_edit.py set <csv_name> <row>,<col> [<row>,<col> ...] [--value=x]")
        sys.exit(1)

    cmd = sys.argv[1]
    csv_name = sys.argv[2]

    if cmd == "structure":
        read_structure(csv_name)
    elif cmd == "set":
        value = "x"
        pairs = []
        for arg in sys.argv[3:]:
            if arg.startswith("--value="):
                value = arg.split("=", 1)[1]
            else:
                parts = arg.split(",", 1)
                if len(parts) == 2:
                    pairs.append(tuple(parts))
        set_cells(csv_name, pairs, value)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
