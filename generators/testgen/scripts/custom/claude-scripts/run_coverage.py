#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Run coverage for a single coverpoint column in isolation.

Usage:
    python3 run_coverage.py <coverpoint_name> [category] [timeout_minutes]

Example:
    python3 run_coverage.py cp_custom_vfp_flags Vf
    python3 run_coverage.py cp_custom_vfp_flags Vf 2
    python3 run_coverage.py cp_custom_masked_v0_operand Vls
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[4]  # riscv-arch-test-cvw root

sys.path.insert(0, str(SCRIPT_DIR))
from testplan_manager import isolate_column, restore_testplans
from coverage_parser import summarize_coverage


DEFAULT_COVERAGE_TIMEOUT_MINUTES = 2


def run_coverage(coverpoint_name: str, category: str = "Vf", timeout_minutes: int = DEFAULT_COVERAGE_TIMEOUT_MINUTES) -> dict:
    """Isolate one column, build, run coverage, restore CSVs.

    Returns dict with keys: status, coverage_summary, build_log, coverage_log, duration_s
    """
    start = time.time()
    result = {
        "coverpoint": coverpoint_name,
        "category": category,
        "status": "unknown",
        "coverage_summary": {},
        "build_log": "",
        "coverage_log": "",
        "duration_s": 0,
    }

    try:
        # 1. Isolate column
        print(f"[1/4] Isolating column '{coverpoint_name}' for category '{category}'...")
        isolate_column(coverpoint_name, category)

        # 2. Clean
        print("[2/4] Cleaning...")
        proc = subprocess.run(
            ["make", "--jobs=16", "clean"],
            cwd=str(REPO), capture_output=True, text=True, timeout=120
        )
        if proc.returncode != 0:
            result["status"] = "clean_failed"
            result["build_log"] = proc.stderr[-2000:]
            return result

        # 3. Generate tests
        print("[3/4] Generating tests (make vector-tests)...")
        proc = subprocess.run(
            ["make", "--jobs=16", "vector-tests"],
            cwd=str(REPO), capture_output=True, text=True, timeout=600
        )
        if proc.returncode != 0:
            result["status"] = "testgen_failed"
            result["build_log"] = proc.stderr[-3000:]
            return result
        result["build_log"] = proc.stdout[-2000:]

        # 4. Run coverage (timeout defaults to 1 minute to avoid trap hangs)
        print(f"[4/4] Running coverage (timeout {timeout_minutes} min)...")
        timeout_cmd = shutil.which("timeout")
        coverage_cmd = ["make", "--jobs=16", "-k", "coverage"]
        if timeout_cmd:
            cmd = [timeout_cmd, f"{timeout_minutes}m", *coverage_cmd]
            proc = subprocess.run(
                cmd,
                cwd=str(REPO), capture_output=True, text=True,
            )
        else:
            proc = subprocess.run(
                coverage_cmd,
                cwd=str(REPO), capture_output=True, text=True,
                timeout=timeout_minutes * 60
            )
        result["coverage_log"] = proc.stdout[-5000:] + "\n---STDERR---\n" + proc.stderr[-3000:]
        if proc.returncode == 124:
            result["status"] = "timeout"
            result["coverage_log"] += "\n[timeout] Coverage command exceeded configured timeout."
        elif proc.returncode != 0:
            result["status"] = "coverage_partial"
        else:
            result["status"] = "ok"

        # If coverage reports missing, force them by running coverage in work dirs
        for xlen_dir in ["sail-rv32-max", "sail-rv64-max"]:
            summary_file = REPO / "work" / xlen_dir / "reports" / "_overall_summary.txt"
            work_dir = REPO / "work" / xlen_dir
            if work_dir.exists() and not summary_file.exists():
                print(f"  Forcing coverage reports for {xlen_dir}...")
                force_cmd = ["make", "--jobs=16", "-k", "-i", "coverage"]
                if timeout_cmd:
                    force_cmd = [timeout_cmd, f"{timeout_minutes}m", *force_cmd]
                subprocess.run(
                    force_cmd,
                    cwd=str(work_dir), capture_output=True, text=True,
                    timeout=None if timeout_cmd else timeout_minutes * 60
                )

        # 5. Parse reports
        config = {"Vf": {"effews": ["16", "32", "64"], "prefix": "VfCustom"},
                  "Vls": {"effews": ["8", "16", "32", "64"], "prefix": "VlsCustom"}}
        cat_config = config[category]

        summaries = {}
        for xlen in ["rv32", "rv64"]:
            report_dir = str(REPO / "work" / f"sail-{xlen}-max" / "reports")
            summary = summarize_coverage(
                report_dir, coverpoint_name,
                effew_list=cat_config["effews"],
                category=cat_config["prefix"]
            )
            summaries[xlen] = summary

        result["coverage_summary"] = summaries

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except Exception as e:
        result["status"] = "error"
        result["build_log"] = str(e)
    finally:
        print("Restoring testplans...")
        restore_testplans()
        result["duration_s"] = round(time.time() - start, 1)

    return result


def print_result(result: dict) -> None:
    """Pretty-print coverage result."""
    print(f"\n{'='*60}")
    print(f"Coverpoint: {result['coverpoint']} ({result['category']})")
    print(f"Status: {result['status']}")
    print(f"Duration: {result['duration_s']}s")

    for xlen, summary in result.get("coverage_summary", {}).items():
        print(f"\n  {xlen}:")
        print(f"    Total bins: {summary['total_bins']}")
        print(f"    Covered: {summary['covered_bins']}")
        print(f"    Uncovered: {summary['uncovered_bins']}")
        if summary.get("uncovered_list"):
            for item in summary["uncovered_list"]:
                print(f"      - {item}")
        elif summary["total_bins"] > 0:
            print("    All bins covered!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cp_name = sys.argv[1]
    cat = sys.argv[2] if len(sys.argv) > 2 else "Vf"
    timeout_mins = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_COVERAGE_TIMEOUT_MINUTES

    result = run_coverage(cp_name, cat, timeout_minutes=timeout_mins)
    print_result(result)

    # Save result to JSON
    output_file = SCRIPT_DIR / f"coverage_result_{cp_name}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to {output_file}")
