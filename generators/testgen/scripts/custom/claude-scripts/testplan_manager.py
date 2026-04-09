#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Manage testplan CSVs for isolated coverpoint testing.

Strips CSVs to only the target coverpoint column and removes unrelated
testplans to speed up test generation.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

# All paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[5]  # generators/testgen/scripts/custom/claude-scripts -> root
TESTPLANS_DIR = REPO_ROOT / "testplans"
DUPLICATES_DIR = REPO_ROOT / "working-testplans" / "duplicates"
MAKEFILE_PATH = REPO_ROOT / "Makefile"

# Columns that are always kept in the stripped CSV
ALWAYS_KEEP_COLUMNS = {"Instruction", "Type", "RV32", "RV64", "EFFEW8", "EFFEW16", "EFFEW32", "EFFEW64", "cp_asm_count", "std_vec"}

# Map category -> (custom csv name, base csv name, effew prefix)
CATEGORY_CONFIG = {
    "Vf": {
        "custom_csv": "VfCustom",
        "base_csv": "Vf",
        "custom_save": "VfCustom-save.csv",
        "base_save": "Vf-save.csv",
        "effew_prefix": "VfCustom",
        "effews": ["16", "32", "64"],
    },
    "Vls": {
        "custom_csv": "VlsCustom",
        "base_csv": "Vls",
        "custom_save": "VlsCustom-save.csv",
        "base_save": "Vls-save.csv",
        "effew_prefix": "VlsCustom",
        "effews": ["8", "16", "32", "64"],
    },
}


# Explicit mapping for coverpoints whose names don't prefix-match their CSV column.
# Key: coverpoint name from definitions CSV, Value: column name in VfCustom/VlsCustom CSV.
EXPLICIT_COLUMN_MAP = {
    "cp_custom_vfp_register_state_mstatus_dirty": "cp_custom_vfp_state",
    "cp_custom_vfp_csr_state_mstatus_dirty": "cp_custom_vfp_state",
    "cp_custom_f_freg_write_vl0": "cp_custom_vfp_state",
}


def _resolve_column_name(coverpoint_name: str, header: list[str]) -> str:
    """Resolve a coverpoint name to its column name in the CSV.

    The CSV uses parent column names (e.g. cp_custom_vfp_flags) that contain
    multiple child coverpoints (e.g. cp_custom_vfp_flags_set, cp_custom_vfp_flags_inactive_not_set).
    This function finds the matching column by trying exact match first, then
    explicit mapping, then progressively shorter prefixes.
    """
    # Exact match
    if coverpoint_name in header:
        return coverpoint_name

    # Explicit mapping
    if coverpoint_name in EXPLICIT_COLUMN_MAP:
        mapped = EXPLICIT_COLUMN_MAP[coverpoint_name]
        if mapped in header:
            return mapped

    # Try progressively shorter prefixes
    parts = coverpoint_name.split("_")
    for end in range(len(parts) - 1, 2, -1):  # at least "cp_custom_X"
        candidate = "_".join(parts[:end])
        if candidate in header:
            return candidate

    return coverpoint_name  # fall through to error handling


def _read_header(path: Path) -> list[str]:
    """Read CSV header row."""
    try:
        with open(path, newline="") as f:
            reader = csv.reader(f)
            return next(reader, [])
    except OSError:
        return []


def _is_vector_csv(name: str, header: list[str]) -> bool:
    """Heuristic to identify vector testplan CSVs.

    Future-proofing: treat any V* CSV as vector, and also detect by known
    vector-specific columns in case naming changes.
    """
    stem = name.removesuffix(".csv")
    if stem.startswith("V"):
        return True

    header_set = set(header)
    if "std_vec" in header_set:
        return True
    if any(col.startswith("EFFEW") for col in header):
        return True

    return False


def _vector_csv_names_from_backups() -> list[str]:
    """Return vector CSV names (e.g. VfCustom.csv) based on duplicates backups."""
    names = []
    for save_file in DUPLICATES_DIR.glob("*-save.csv"):
        original_name = save_file.name.replace("-save", "")
        header = _read_header(save_file)
        if _is_vector_csv(original_name, header):
            names.append(original_name)
    return sorted(set(names))


def _disable_other_vector_testplans(selected_csv_name: str) -> None:
    """Delete all vector testplans except the selected one."""
    selected = selected_csv_name if selected_csv_name.endswith(".csv") else f"{selected_csv_name}.csv"
    for csv_name in _vector_csv_names_from_backups():
        if csv_name == selected:
            continue
        path = TESTPLANS_DIR / csv_name
        if path.exists():
            path.unlink()


def isolate_column(coverpoint_name: str, category: str = "Vf") -> None:
    """Strip custom CSV to only the target coverpoint column and set up environment.

    Args:
        coverpoint_name: Coverpoint name (may be a child of a broader CSV column)
        category: "Vf" or "Vls"
    """
    config = CATEGORY_CONFIG[category]

    # 1. Read master CSV from duplicates
    master_csv = DUPLICATES_DIR / config["custom_save"]
    rows, header = _read_csv(master_csv)

    # 2. Resolve coverpoint name to CSV column name
    column_name = _resolve_column_name(coverpoint_name, header)
    if column_name not in header:
        available = [h for h in header if h.startswith("cp_custom_")]
        raise ValueError(
            f"Column for '{coverpoint_name}' not found in {master_csv}. "
            f"Available custom columns: {available}"
        )

    # 3. Determine columns to keep
    keep_cols = []
    for i, col in enumerate(header):
        if col in ALWAYS_KEEP_COLUMNS or col == column_name:
            keep_cols.append(i)

    # 4. Write stripped CSV — only rows that have 'x' in the coverpoint column
    stripped_rows = []
    stripped_header = [header[i] for i in keep_cols]
    cp_col_idx_stripped = stripped_header.index(column_name)
    for row in rows:
        stripped_row = [row[i] if i < len(row) else "" for i in keep_cols]
        # Only include rows that have a non-empty Instruction AND 'x' in the coverpoint column
        if stripped_row[0].strip() and stripped_row[cp_col_idx_stripped].strip().lower() == "x":
            stripped_rows.append(stripped_row)

    output_csv = TESTPLANS_DIR / f"{config['custom_csv']}.csv"
    _write_csv(output_csv, stripped_header, stripped_rows)

    # 5. Disable all other vector testplans to avoid generating extra vector tests.
    _disable_other_vector_testplans(f"{config['custom_csv']}.csv")

    # 6. Update EXTENSIONS in Makefile
    extensions = ",".join(f"{config['effew_prefix']}{e}" for e in config["effews"])
    _update_makefile_extensions(extensions)


def restore_testplans() -> None:
    """Restore all testplan CSVs from duplicates directory."""
    for save_file in DUPLICATES_DIR.iterdir():
        if save_file.suffix == ".csv" and save_file.name.endswith("-save.csv"):
            # Derive the original name: "VfCustom-save.csv" -> "VfCustom.csv"
            original_name = save_file.name.replace("-save", "")
            dest = TESTPLANS_DIR / original_name
            shutil.copy2(save_file, dest)

    # Restore EXTENSIONS line to include all categories that have saved CSVs
    all_extensions = []
    for cat_config in CATEGORY_CONFIG.values():
        save_path = DUPLICATES_DIR / cat_config["custom_save"]
        if save_path.exists():
            for e in cat_config["effews"]:
                all_extensions.append(f"{cat_config['effew_prefix']}{e}")
    if all_extensions:
        _update_makefile_extensions(",".join(all_extensions))
    else:
        _update_makefile_extensions("VfCustom16,VfCustom32,VfCustom64")


def get_instructions_for_coverpoint(coverpoint_name: str, category: str = "Vf") -> list[str]:
    """Return list of instruction mnemonics that have 'x' in the coverpoint's column.

    Resolves child coverpoint names to parent CSV column names automatically.

    Args:
        coverpoint_name: Coverpoint name (may be a child of a broader CSV column)
        category: "Vf" or "Vls"

    Returns:
        List of instruction mnemonic strings
    """
    config = CATEGORY_CONFIG[category]
    master_csv = DUPLICATES_DIR / config["custom_save"]
    rows, header = _read_csv(master_csv)

    column_name = _resolve_column_name(coverpoint_name, header)
    if column_name not in header:
        return []

    col_idx = header.index(column_name)
    inst_idx = header.index("Instruction")

    instructions = []
    for row in rows:
        if col_idx < len(row) and row[col_idx].strip().lower() == "x":
            inst = row[inst_idx].strip()
            if inst:
                instructions.append(inst)

    return instructions


def _read_csv(path: Path) -> tuple[list[list[str]], list[str]]:
    """Read a CSV file and return (rows, header)."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return rows, header


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _update_makefile_extensions(extensions: str) -> None:
    """Update the EXTENSIONS line in the Makefile."""
    content = MAKEFILE_PATH.read_text()
    # Match the EXTENSIONS line (may have trailing comment)
    updated = ""
    for line in content.split("\n"):
        if line.startswith("EXTENSIONS") and "?=" in line:
            # Preserve any trailing comment after the value
            updated += f"EXTENSIONS  ?= {extensions} # Extensions to generate tests for. Leave blank to generate for all tests.\n"
        else:
            updated += line + "\n"
    # Remove trailing extra newline from the loop
    if updated.endswith("\n\n") and not content.endswith("\n\n"):
        updated = updated[:-1]
    MAKEFILE_PATH.write_text(updated)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: testplan_manager.py <command> [args...]")
        print("Commands:")
        print("  isolate <coverpoint_name> [category]  - Strip CSVs to one column")
        print("  restore                                - Restore all CSVs from duplicates")
        print("  instructions <coverpoint_name> [cat]   - List instructions for coverpoint")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "isolate":
        cp = sys.argv[2]
        cat = sys.argv[3] if len(sys.argv) > 3 else "Vf"
        isolate_column(cp, cat)
        print(f"Isolated column '{cp}' for category '{cat}'")
    elif cmd == "restore":
        restore_testplans()
        print("Restored all testplans from duplicates")
    elif cmd == "instructions":
        cp = sys.argv[2]
        cat = sys.argv[3] if len(sys.argv) > 3 else "Vf"
        insts = get_instructions_for_coverpoint(cp, cat)
        print(f"Instructions for {cp}: {insts}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
