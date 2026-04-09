#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Orchestrate automated coverpoint test generation via Claude CLI.

Parses the custom definitions CSV, and for each coverpoint launches a Claude
CLI subprocess to write the test generation script, run the build/coverage
pipeline, and iterate until coverage is achieved.

Usage:
    python orchestrator.py --category Vf [--start 0] [--end 5] [--resume] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Resolve paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[5]
CUSTOM_DIR = REPO_ROOT / "generators" / "testgen" / "scripts" / "custom"
CLAUDE_SCRIPTS_DIR = CUSTOM_DIR / "claude-scripts"
WORKING_TESTPLANS = REPO_ROOT / "working-testplans"
PROGRESS_FILE = CLAUDE_SCRIPTS_DIR / "progress.json"

# Import sibling modules
sys.path.insert(0, str(CLAUDE_SCRIPTS_DIR))
from coverage_parser import format_coverage_for_prompt, summarize_coverage  # noqa: E402
from prompt_builder import build as build_prompt  # noqa: E402
from prompt_builder import find_coverage_template  # noqa: E402
from testplan_manager import (  # noqa: E402
    get_instructions_for_coverpoint,
    isolate_column,
    restore_testplans,
)


# Category -> definitions CSV filename
DEFINITIONS_CSV = {
    "Vf": "Vf_custom_definitions.csv",
    "Vls": "Vls_custom_definitions.csv",
}

# Category -> report directory pattern
REPORT_DIRS = {
    "Vf": [
        str(REPO_ROOT / "work" / "sail-rv32-max" / "reports"),
        str(REPO_ROOT / "work" / "sail-rv64-max" / "reports"),
    ],
    "Vls": [
        str(REPO_ROOT / "work" / "sail-rv32-max" / "reports"),
        str(REPO_ROOT / "work" / "sail-rv64-max" / "reports"),
    ],
}


def parse_definitions(category: str) -> list[dict]:
    """Parse the custom definitions CSV and return list of coverpoint entries.

    Each entry is a dict with keys: name, goal, feature_description, expectation,
    bins, notes.
    """
    csv_path = WORKING_TESTPLANS / DEFINITIONS_CSV[category]
    entries = []

    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

    # Find column indices by matching known column name patterns
    col_map = {}
    for i, col in enumerate(header):
        col_lower = col.strip().lower()
        if "sr no" in col_lower or "link to coverage" in col_lower:
            col_map["name"] = i
        elif col_lower == "goal":
            col_map["goal"] = i
        elif "feature description" in col_lower:
            col_map["feature_description"] = i
        elif col_lower == "expectation":
            col_map["expectation"] = i
        elif col_lower == "bins":
            col_map["bins"] = i
        elif "notes" in col_lower or "spec" in col_lower:
            if "notes" not in col_map:  # take first match
                col_map["notes"] = i

    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if not row:
                continue
            name_idx = col_map.get("name", 0)
            name = row[name_idx].strip() if name_idx < len(row) else ""

            # Only include rows that look like coverpoint names
            if not name.startswith("cp_custom_"):
                continue

            entry = {
                "name": name,
                "goal": _safe_get(row, col_map.get("goal")),
                "feature_description": _safe_get(row, col_map.get("feature_description")),
                "expectation": _safe_get(row, col_map.get("expectation")),
                "bins": _safe_get(row, col_map.get("bins")),
                "notes": _safe_get(row, col_map.get("notes")),
            }
            entries.append(entry)

    return entries


def _safe_get(row: list[str], idx: int | None) -> str:
    """Safely get a value from a row by index."""
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def load_progress() -> dict:
    """Load progress from JSON file."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {}


def save_progress(progress: dict) -> None:
    """Save progress to JSON file."""
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def is_completed(progress: dict, coverpoint_name: str) -> bool:
    """Check if a coverpoint has been successfully completed."""
    entry = progress.get(coverpoint_name, {})
    return entry.get("status") == "completed"


def run_claude(prompt: str, max_budget_usd: float = 5.0) -> tuple[bool, str]:
    """Launch claude CLI with the given prompt.

    Returns:
        (success, output) tuple
    """
    cmd = [
        "claude",
        "-p", prompt,
        "--dangerously-skip-permissions",
        "--max-budget-usd", str(max_budget_usd),
    ]

    # Strip env vars that prevent nested Claude CLI sessions
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_SSE_PORT", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
            cwd=str(REPO_ROOT),
            env=env,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Claude CLI timed out after 30 minutes"
    except FileNotFoundError:
        return False, "Claude CLI not found. Ensure 'claude' is in PATH."


def process_coverpoint(entry: dict, category: str, progress: dict) -> dict:
    """Process a single coverpoint: isolate CSVs, launch claude, verify output.

    Returns:
        Result dict with status, output, timing info
    """
    coverpoint_name = entry["name"]
    result = {
        "name": coverpoint_name,
        "status": "failed",
        "start_time": time.time(),
        "iterations": 0,
        "output_snippets": [],
    }

    script_path = CUSTOM_DIR / f"{coverpoint_name}.py"

    try:
        # 1. Isolate testplan CSVs
        print(f"  Isolating column '{coverpoint_name}'...")
        isolate_column(coverpoint_name, category)

        # 2. Find matching instructions and coverage template
        instructions = get_instructions_for_coverpoint(coverpoint_name, category)
        if not instructions:
            result["status"] = "skipped"
            result["output_snippets"].append("No instructions found for this coverpoint")
            return result

        template_path = find_coverage_template(coverpoint_name)

        # 3. Build and run claude
        prompt = build_prompt(
            coverpoint_name=coverpoint_name,
            instructions=instructions,
            goal=entry.get("goal", ""),
            feature_description=entry.get("feature_description", ""),
            expectation=entry.get("expectation", ""),
            bins=entry.get("bins", ""),
            notes=entry.get("notes", ""),
            template_path=template_path,
            category=category,
        )

        print(f"  Launching Claude CLI (instructions: {len(instructions)}, template: {'yes' if template_path else 'no'})...")
        success, output = run_claude(prompt)
        result["iterations"] = 1
        result["output_snippets"].append(output[-500:] if len(output) > 500 else output)

        # 4. Verify script was created
        if script_path.exists():
            result["status"] = "completed"
            result["script_size"] = script_path.stat().st_size
            print(f"  Script created: {script_path.name} ({result['script_size']} bytes)")
        else:
            print(f"  WARNING: Script not created at {script_path}")
            if not success:
                print(f"  Claude CLI failed (exit code non-zero)")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  ERROR: {e}")

    finally:
        # 5. Restore testplans
        print("  Restoring testplans...")
        try:
            restore_testplans()
        except Exception as e:
            print(f"  WARNING: Failed to restore testplans: {e}")

    result["end_time"] = time.time()
    result["duration_seconds"] = round(result["end_time"] - result["start_time"], 1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate coverpoint test generation via Claude CLI")
    parser.add_argument("--category", default="Vf", choices=list(DEFINITIONS_CSV.keys()),
                        help="Category of coverpoints to process (default: Vf)")
    parser.add_argument("--start", type=int, default=0,
                        help="Start index (0-based) in definitions list")
    parser.add_argument("--end", type=int, default=None,
                        help="End index (exclusive) in definitions list")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-completed coverpoints")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print coverpoints without processing")
    parser.add_argument("--max-budget-usd", type=float, default=5.0,
                        help="Max budget in USD per Claude invocation (default: 5.0)")
    args = parser.parse_args()

    # Parse definitions
    entries = parse_definitions(args.category)
    print(f"Found {len(entries)} coverpoints in {args.category} definitions")

    # Apply range
    end = args.end if args.end is not None else len(entries)
    entries = entries[args.start:end]
    print(f"Processing range [{args.start}:{end}] ({len(entries)} coverpoints)")

    if args.dry_run:
        print("\n--- DRY RUN ---")
        for i, entry in enumerate(entries, start=args.start):
            instructions = get_instructions_for_coverpoint(entry["name"], args.category)
            template = find_coverage_template(entry["name"])
            script_exists = (CUSTOM_DIR / f"{entry['name']}.py").exists()
            print(f"  [{i}] {entry['name']}")
            print(f"      Goal: {entry.get('goal', 'N/A')[:80]}")
            print(f"      Bins: {entry.get('bins', 'N/A')}")
            print(f"      Instructions: {len(instructions)}")
            print(f"      Template: {'found' if template else 'not found'}")
            print(f"      Script exists: {script_exists}")
        return

    # Load progress
    progress = load_progress()

    # Process each coverpoint
    results_summary = {"completed": 0, "failed": 0, "skipped": 0, "error": 0}

    for i, entry in enumerate(entries, start=args.start):
        coverpoint_name = entry["name"]
        print(f"\n[{i}/{end - 1}] Processing: {coverpoint_name}")

        # Check resume
        if args.resume and is_completed(progress, coverpoint_name):
            print("  Already completed, skipping")
            results_summary["skipped"] += 1
            continue

        # Process
        result = process_coverpoint(entry, args.category, progress)
        results_summary[result["status"]] = results_summary.get(result["status"], 0) + 1

        # Save progress
        progress[coverpoint_name] = {
            "status": result["status"],
            "duration_seconds": result.get("duration_seconds", 0),
            "iterations": result.get("iterations", 0),
            "script_size": result.get("script_size", 0),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_progress(progress)

        print(f"  Result: {result['status']} ({result.get('duration_seconds', 0)}s)")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for status, count in results_summary.items():
        if count > 0:
            print(f"  {status}: {count}")
    print(f"  Total: {sum(results_summary.values())}")


if __name__ == "__main__":
    main()
