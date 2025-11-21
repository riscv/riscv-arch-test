#!/usr/bin/env python3
# transpose_csv.py
# Convert wide CSV files into multiple AsciiDoc tables by transposing rows and columns.
# David Harris
# SPDX-License-Identifier: Apache-2.0

import csv
import os
import sys


def transpose_csv(rows):
    return list(map(list, zip(*rows))) if rows else []


def is_blank_column(col):
    return all(cell.strip() == "" for cell in col)


def is_blank_row_excluding_first(row):
    return all(cell.strip() == "" for cell in row[1:])


def split_columns_with_blanks(transposed, max_columns):
    if not transposed:
        return []

    first_col = [row[0] for row in transposed]
    total_cols = len(transposed[0])

    chunks = []
    start_col = 1

    while start_col < total_cols:
        end_col = start_col
        col_count = 1  # count first col

        while end_col < total_cols and col_count < max_columns:
            current_col = [row[end_col] for row in transposed]
            if is_blank_column(current_col):
                break
            end_col += 1
            col_count += 1

        chunk = []
        for i, row in enumerate(transposed):
            new_row = [first_col[i]] + row[start_col:end_col]
            if not is_blank_row_excluding_first(new_row):
                chunk.append(new_row)

        chunks.append(chunk)

        if end_col < total_cols and is_blank_column([row[end_col] for row in transposed]):
            start_col = end_col + 1
        else:
            start_col = end_col

    return chunks


def write_asciidoc(filepath, tables):
    """Write all tables directly into .adoc file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for table in tables:
            f.write("[options=header]\n")
            f.write("[%autofit]\n")
            f.write(",===\n")
            for row in table:
                # Escape commas in cells if needed; here simply join by comma
                f.write(",".join(row) + "\n")
            f.write(",===\n\n")


def process_csv_file_to_adoc(source_path, dest_dir, max_columns):
    base_name = os.path.splitext(os.path.basename(source_path))[0]

    with open(source_path, newline="", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    transposed = transpose_csv(rows)
    chunks = split_columns_with_blanks(transposed, max_columns)

    adoc_path = os.path.join(dest_dir, f"{base_name}.adoc")
    write_asciidoc(adoc_path, chunks)


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <source_directory> <destination_directory> <max_columns>")
        sys.exit(1)

    source_dir = sys.argv[1]
    dest_dir = sys.argv[2]
    try:
        max_columns = int(sys.argv[3])
        if max_columns < 2:
            raise ValueError
    except ValueError:
        print("Error: max_columns must be an integer >= 2.")
        sys.exit(1)

    if not os.path.isdir(source_dir):
        print(f"Error: source directory '{source_dir}' does not exist.")
        sys.exit(1)

    os.makedirs(dest_dir, exist_ok=True)

    for filename in os.listdir(source_dir):
        if filename.lower().endswith(".csv"):
            source_path = os.path.join(source_dir, filename)
            print(f"Processing {filename}...")
            try:
                process_csv_file_to_adoc(source_path, dest_dir, max_columns)
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
