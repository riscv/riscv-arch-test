#!/usr/bin/env -S uv run
# transpose_csv.py
# Convert wide CSV files into multiple AsciiDoc tables by transposing rows and columns.
# David Harris
# SPDX-License-Identifier: Apache-2.0
#
# /// script
# requires-python = ">=3.10"
# ///

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path


def transpose_csv(rows: list[list[str]]) -> list[list[str]]:
    return list(map(list, zip(*rows, strict=False))) if rows else []


def is_blank_column(col: list[str]) -> bool:
    return all(cell.strip() == "" for cell in col)


def is_blank_row_excluding_first(row: list[str]) -> bool:
    return all(cell.strip() == "" for cell in row[1:])


def split_columns_with_blanks(transposed: list[list[str]], instructions_per_table: int) -> list[list[list[str]]]:
    """Split the transposed table into tables of at most instructions_per_table instruction columns,
    each keeping the coverpoint-name column first.  A blank column in the source also ends a table."""
    if not transposed:
        return []

    first_col = [row[0] for row in transposed]
    total_cols = len(transposed[0])

    chunks: list[list[list[str]]] = []
    start_col = 1

    while start_col < total_cols:
        end_col = start_col
        col_count = 0  # instruction columns in this table; the name column is not counted

        while end_col < total_cols and col_count < instructions_per_table:
            current_col = [row[end_col] for row in transposed]
            if is_blank_column(current_col):
                break
            end_col += 1
            col_count += 1

        chunk = []
        for i, row in enumerate(transposed):
            new_row = [first_col[i], *row[start_col:end_col]]
            if not is_blank_row_excluding_first(new_row):
                chunk.append(new_row)

        chunks.append(chunk)

        if end_col < total_cols and is_blank_column([row[end_col] for row in transposed]):
            start_col = end_col + 1
        else:
            start_col = end_col

    return chunks


def write_asciidoc(filepath: Path, tables: list[list[list[str]]], suite_name: str) -> None:
    """Write all tables directly into .adoc file."""
    with filepath.open("w", encoding="utf-8") as f:
        # Add auto-generation header comment with absolute paths
        argv_abs = [str(Path(arg).resolve()) if Path(arg).exists() else arg for arg in sys.argv]
        command_line = " ".join(argv_abs)
        gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        f.write("// WARNING: This file was automatically generated.\n")
        f.write("// Do not modify by hand.\n")
        f.write("// Generation command: " + command_line + "\n")
        f.write("// Generation date: " + gen_date + "\n")
        f.write("\n")

        # Add table label and caption
        f.write(f"[[t-{suite_name}-coverpoints]]\n")
        f.write(f".{suite_name} Instruction Coverpoints\n")

        for table in tables:
            # The first column holds the coverpoint names, which are longer than the instruction
            # names, so give it 1.5 times the width of an instruction column
            instruction_columns = len(table[0]) - 1 if table else 0
            f.write("[options=header]\n")
            f.write("[%autofit]\n")
            f.write('[cols="' + ",".join(["3", *(["2"] * instruction_columns)]) + '"]\n')
            f.write(",===\n")
            for row in table:
                if row and row[0].strip().lower() == "type":
                    continue
                # Escape commas in cells if needed; here simply join by comma
                f.write(",".join(row) + "\n")
            f.write(",===\n\n")


def process_csv_file_to_adoc(source_path: Path, dest_dir: Path, instructions_per_table: int) -> None:
    base_name = source_path.stem

    with source_path.open(newline="", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    transposed = transpose_csv(rows)
    chunks = split_columns_with_blanks(transposed, instructions_per_table)

    adoc_path = dest_dir / f"{base_name}.adoc"
    write_asciidoc(adoc_path, chunks, base_name)


def main() -> None:
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <source_directory> <destination_directory> <instructions_per_table>")
        sys.exit(1)

    source_dir = Path(sys.argv[1])
    dest_dir = Path(sys.argv[2])
    try:
        instructions_per_table = int(sys.argv[3])
        if instructions_per_table < 1:
            raise ValueError
    except ValueError:
        print("Error: instructions_per_table must be an integer >= 1.")
        sys.exit(1)

    if not source_dir.is_dir():
        print(f"Error: source directory '{source_dir}' does not exist.")
        sys.exit(1)

    dest_dir.mkdir(parents=True, exist_ok=True)

    for entry in sorted(source_dir.iterdir()):
        if entry.suffix.lower() == ".csv":
            print(f"Processing {entry.name}...")
            try:
                process_csv_file_to_adoc(entry, dest_dir, instructions_per_table)
            except (OSError, csv.Error) as e:
                print(f"Error processing {entry.name}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
