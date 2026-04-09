#!/usr/bin/env python3
"""
Process CSV coverpoint lines by launching fresh Claude instances.

Each CSV line is processed by a completely independent Claude session.
No conversation context carries over between lines - only knowledge
explicitly written to .md files persists.

NOTE: Only processes CSVs in ./working-testplans (NOT ./testplans)

Usage:
    python process_csv.py <csv_file> [options]

Examples:
    python process_csv.py "Vector - SsstrictV.csv"                    # Process all lines
    python process_csv.py "Vector - SsstrictV.csv" --start 31         # Process from line 31 to end
    python process_csv.py "Vector - SsstrictV.csv" --start 5 --end 10 # Process lines 5-10
    python process_csv.py "Vector - SsstrictV.csv" --line 5           # Process only line 5
    python process_csv.py "Vector - SsstrictV.csv" --dry-run          # Show what would be processed
"""

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WORKING_TESTPLANS = Path(__file__).parent
TEMPLATES_DIR = REPO_ROOT / "generators" / "coverage" / "templates" / "vector"


def get_coverpoint_name(row: dict) -> str:
    """Extract coverpoint name from row, handling various CSV header formats."""
    # Try different possible column names for the coverpoint name
    for key in row:
        # Match columns that contain "Sr No" or similar
        if "Sr No" in key or "sr no" in key.lower():
            return row[key].strip()
    # Fallback: try 'name' or first column
    if "name" in row:
        return row["name"].strip()
    # Try first non-internal key
    for key, val in row.items():
        if not key.startswith("_") and val:
            return val.strip()
    return ""


def get_row_field(row: dict, *candidates: str) -> str:
    """Get field value trying multiple possible column names."""
    for candidate in candidates:
        for key in row:
            if candidate.lower() in key.lower():
                val = row[key].strip() if row[key] else ""
                if val:
                    return val
    return ""


def read_csv_lines(csv_path: Path) -> list[dict]:
    """Read CSV and return list of row dicts with line numbers."""
    lines = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # Line 1 is header
            row["_line_number"] = i
            row["_cp_name"] = get_coverpoint_name(row)
            lines.append(row)
    return lines


def template_exists(name: str) -> bool:
    """Check if a template file exists in templates/ or templates/priv/ (.txt or .sv)."""
    for ext in (".txt", ".sv"):
        if (TEMPLATES_DIR / f"{name}{ext}").exists() or (TEMPLATES_DIR / "priv" / f"{name}{ext}").exists():
            return True
    return False


def needs_processing(row: dict) -> bool:
    """Determine if a CSV row needs coverpoint work."""
    name = row.get("_cp_name", "").strip()

    # If name starts with cp_, check if template exists
    if name.startswith("cp_"):
        if template_exists(name):
            print(f"  [SKIP] {name} - template already exists")
            return False
        return True

    # If name is empty, check if there's meaningful content in other fields
    if not name:
        goal = get_row_field(row, "Goal")
        description = get_row_field(row, "Feature Description", "description")
        expectation = get_row_field(row, "Expectation")
        spec = get_row_field(row, "Spec")
        # Process if there's any meaningful content to work with
        if goal or description or expectation or spec:
            return True

    # Skip rows with non-cp_ names (like section headers)
    return False


def build_prompt(csv_file: str, line_number: int, row: dict) -> str:
    """Build the prompt for Claude to process this CSV line."""
    name = row.get("_cp_name", "")
    goal = get_row_field(row, "Goal")
    description = get_row_field(row, "Feature Description", "description")
    expectation = get_row_field(row, "Expectation")
    spec = get_row_field(row, "Spec")
    bins = get_row_field(row, "Bins")

    # Determine template subdirectory (priv/ for privileged coverpoints)
    is_priv = name.startswith(("cp_ssstrictv", "cp_exceptionsv")) or csv_file.lower().startswith("vector - ssstrictv")
    template_subdir = "priv/" if is_priv else ""

    # Build task instructions based on whether name exists
    if name:
        name_instruction = f"""2. Create the coverpoint template file at:
   generators/coverage/templates/vector/{template_subdir}{name}.txt"""
    else:
        name_instruction = f"""2. This row has no coverpoint name yet. You must:
   a. Create an appropriate name following the cp_<category>_<description> pattern
   b. Update the CSV file to add the name to the first column of this line
   c. Create the coverpoint template file at:
      generators/coverage/templates/vector/{template_subdir}<your_new_name>.txt"""

    return f"""You are the CSV Editor agent. Process this single CSV line.

READ FIRST: CLAUDE-csv-editor.md (contains all patterns and rules you need)

CSV FILE: working-testplans/{csv_file}
LINE NUMBER: {line_number}

CURRENT ROW DATA:
- name: {name if name else "(EMPTY - you must create one)"}
- goal: {goal}
- feature description: {description}
- expectation: {expectation}
- bins: {bins}
- spec: {spec}

YOUR TASK:
1. Read CLAUDE-csv-editor.md to understand the patterns and format rules
{name_instruction}
3. Validate the template follows all format rules
4. If you learn something new that would help future lines, ADD IT to the appropriate .md file

IMPORTANT:
- You have NO context from previous lines - this is a fresh session
- All knowledge must come from .md files or be added to them
- Do not read other CSV lines - focus only on line {line_number}
- Write the coverpoint template directly (no sub-agents)
- If one description requires MULTIPLE coverpoints, you MAY:
  - Create multiple template files (one per coverpoint)
  - Add multiple rows to the CSV (insert new rows after line {line_number})
  - Each coverpoint needs its own cp_* name and template file

When done, summarize what you created/updated."""


def process_line(csv_file: str, line_number: int, row: dict, dry_run: bool = False) -> tuple[bool, dict]:
    """Launch Claude to process a single CSV line. Returns (success, usage_stats)."""
    prompt = build_prompt(csv_file, line_number, row)

    name = row.get("_cp_name", "unknown")
    print(f"\n{'=' * 60}")
    print(f"Processing line {line_number}: {name}")
    print(f"{'=' * 60}")

    if dry_run:
        print(f"[DRY RUN] Would process with prompt:\n{prompt[:200]}...")
        return True, {}

    try:
        # Launch claude with plain text output
        # Remove CLAUDECODE env vars to allow nested sessions
        env = os.environ.copy()
        for key in list(env.keys()):
            if "CLAUDE" in key.upper():
                del env[key]
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )

        # Print the output
        if result.stdout:
            print(result.stdout)

        usage_stats = {}
        return result.returncode == 0, usage_stats

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        return False, {}
    except Exception as e:
        print(f"ERROR processing line {line_number}: {e}")
        return False, {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Process CSV coverpoint lines with fresh Claude instances")
    parser.add_argument("csv_file", help="CSV file to process (in working-testplans/)")
    parser.add_argument("--start", type=int, help="Start line number (processes from here to end)")
    parser.add_argument("--end", type=int, help="End line number (inclusive, use with --start)")
    parser.add_argument("--line", type=int, help="Process only this single line")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")

    args = parser.parse_args()

    # Resolve CSV path
    csv_path = WORKING_TESTPLANS / args.csv_file
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    # Read all lines
    lines = read_csv_lines(csv_path)
    print(f"Loaded {len(lines)} data rows from {args.csv_file}")

    # Filter by line range if specified
    if args.line is not None:
        # Single line mode
        lines = [row for row in lines if row["_line_number"] == args.line]
    elif args.start is not None:
        if args.end is None:
            # Process from start to end of file
            lines = [row for row in lines if row["_line_number"] >= args.start]
        else:
            lines = [row for row in lines if args.start <= row["_line_number"] <= args.end]

    # Filter to lines needing processing
    to_process = [row for row in lines if needs_processing(row)]
    print(f"Lines to process: {len(to_process)}")

    if not to_process:
        print("No lines need processing.")
        return

    # Process each line
    success_count = 0
    fail_count = 0

    for row in to_process:
        line_num = row["_line_number"]
        success, _ = process_line(args.csv_file, line_num, row, args.dry_run)
        if success:
            success_count += 1
        else:
            fail_count += 1
            # Optionally stop on first failure
            # break

    # Summary
    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {success_count} succeeded, {fail_count} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
