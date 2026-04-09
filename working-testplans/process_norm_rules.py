#!/usr/bin/env python3
"""
Process normative rule ↔ coverpoint pairings by launching fresh Claude instances.

Phase 1: For each coverpoint CSV row, match it to normative rules.
Phase 2: For each normative rule, assess coverage completeness.

Each row is processed by a completely independent Claude session.

Usage:
    python process_norm_rules.py --phase 1 [options]
    python process_norm_rules.py --phase 1s [options]
    python process_norm_rules.py --phase 2 [options]

Examples:
    python process_norm_rules.py --phase 1                    # Phase 1: all rows in all custom coverpoint CSVs
    python process_norm_rules.py --phase 1 --line 5           # Phase 1: only line 5
    python process_norm_rules.py --phase 1 --start 5 --end 10 # Phase 1: lines 5-10
    python process_norm_rules.py --phase 1s                   # Phase 1s: all columns in all standard CSVs (Vx, Vls, Vf)
    python process_norm_rules.py --phase 1s --csv Vx          # Phase 1s: only Vx CSV
    python process_norm_rules.py --phase 1s --csv Vx --line 3 # Phase 1s: only column 3 in Vx
    python process_norm_rules.py --phase 2                    # Phase 2: all normative rules
    python process_norm_rules.py --phase 2 --line 3           # Phase 2: only norm rule on line 3
    python process_norm_rules.py --dry-run --phase 1          # Show what would be processed
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ===== USER CONFIGURATION =====
NORM_CSV = "v-st-ext-normative-rules.csv"  # e.g. "norm_rules.csv" - normative rule CSV in working-testplans/
COVERPOINT_CSVS = ["SsstrictV.csv"]  # e.g. ["Vector - SsstrictV.csv", "Vx.csv"] - coverpoint CSVs
# completed: "ExceptionsVf.csv", "ExceptionsVls.csv", "Vf_custom_definitions.csv", "Vls_custom_definitions.csv", "Vx_custom_definitions.csv"

# Standard vector testplan CSVs (column-oriented, read-only sources)
STANDARD_CSVS = {
    "Vx": "duplicates/Vx-save.csv",
    "Vls": "duplicates/Vls-save.csv",
    "Vf": "duplicates/Vf-save.csv",
}
COVERPOINT_DEFS_FILE = "v-coverpoints.adoc"

# Columns that are metadata, not coverpoints (skip when iterating columns)
SKIP_COLUMNS = {
    "Instruction",
    "Type",
    "RV32",
    "RV64",
    "EFFEW8",
    "EFFEW16",
    "EFFEW32",
    "EFFEW64",
    "cp_asm_count",
    "cp_custom",
}
# Context columns included with every instruction for Claude
CONTEXT_COLUMNS = ["Instruction", "EFFEW8", "EFFEW16", "EFFEW32", "EFFEW64"]
# ===============================

WORKING_TESTPLANS = Path(__file__).parent
REPO_ROOT = WORKING_TESTPLANS.parent


# ---------------------------------------------------------------------------
# CSV I/O helpers
# ---------------------------------------------------------------------------


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Read CSV, return (fieldnames, rows). Each row dict has '_line_number'."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = []
        for i, row in enumerate(reader, start=2):  # line 1 = header
            row["_line_number"] = i
            rows.append(row)
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    """Write rows back to CSV, stripping internal '_' keys."""
    clean_fields = [f for f in fieldnames if not f.startswith("_")]
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fields)
        writer.writeheader()
        for row in rows:
            clean_row = {k: v for k, v in row.items() if not k.startswith("_")}
            writer.writerow(clean_row)


def resolve_csv_path(name: str) -> Path:
    """Resolve a CSV name to a full path in working-testplans/."""
    p = WORKING_TESTPLANS / name
    if p.exists():
        return p
    # Try adding .csv
    p2 = WORKING_TESTPLANS / f"{name}.csv"
    if p2.exists():
        return p2
    return p  # return original, caller checks existence


def get_field(row: dict, *candidates: str) -> str:
    """Get field value trying multiple possible column names (case-insensitive partial match)."""
    for candidate in candidates:
        for key in row:
            if key.startswith("_"):
                continue
            if candidate.lower() in key.lower():
                val = (row[key] or "").strip()
                if val:
                    return val
    return ""


# ---------------------------------------------------------------------------
# Normative rule CSV helpers
# ---------------------------------------------------------------------------


def read_norm_csv() -> tuple[Path, list[str], list[dict]]:
    """Read the normative rule CSV. Returns (path, fieldnames, rows)."""
    path = resolve_csv_path(NORM_CSV)
    if not path.exists():
        print(f"ERROR: Normative rule CSV not found: {path}")
        sys.exit(1)
    fieldnames, rows = read_csv(path)
    return path, fieldnames, rows


def get_norm_name(row: dict) -> str:
    """Extract normative rule name from row."""
    return get_field(row, "name", "rule", "norm")


def get_norm_description(row: dict) -> str:
    """Extract normative rule description/spec text from row."""
    return get_field(row, "description", "spec", "text", "quote")


def get_existing_coverpoint_pairs(row: dict) -> list[tuple[str, str]]:
    """Extract existing (cp_name, coverage_desc) pairs from a norm rule row."""
    pairs = []
    i = 1
    while True:
        cp_key = f"cp_name_{i}"
        desc_key = f"coverage_desc_{i}"
        cp_val = row.get(cp_key, "").strip()
        desc_val = row.get(desc_key, "").strip()
        if not cp_val and not desc_val:
            break
        if cp_val:
            pairs.append((cp_val, desc_val))
        i += 1
    return pairs


def add_coverpoint_to_norm_row(
    norm_path: Path,
    fieldnames: list[str],
    rows: list[dict],
    norm_rule_name: str,
    cp_name: str,
    coverage_desc: str,
):
    """Add a (cp_name, coverage_desc) column pair to a norm rule row.

    Mutates fieldnames and the matching row in-place. Does NOT write to disk.
    """
    for row in rows:
        if get_norm_name(row) != norm_rule_name:
            continue
        # Find next available pair index
        i = 1
        while f"cp_name_{i}" in row and row[f"cp_name_{i}"].strip():
            # Skip if this exact cp_name already recorded
            if row[f"cp_name_{i}"].strip() == cp_name:
                return  # duplicate
            i += 1
        cp_key = f"cp_name_{i}"
        desc_key = f"coverage_desc_{i}"
        # Ensure columns exist
        for key in (cp_key, desc_key):
            if key not in fieldnames:
                fieldnames.append(key)
        row[cp_key] = cp_name
        row[desc_key] = coverage_desc
        return


def set_coverage_status(
    rows: list[dict],
    fieldnames: list[str],
    norm_rule_name: str,
    status: str,
    explanation: str,
    gaps: list[str],
):
    """Set coverage_status, explanation, gaps columns on a norm rule row (in-place)."""
    for col in ("coverage_status", "explanation", "gaps"):
        if col not in fieldnames:
            fieldnames.append(col)
    for row in rows:
        if get_norm_name(row) != norm_rule_name:
            continue
        row["coverage_status"] = status
        row["explanation"] = explanation
        row["gaps"] = "; ".join(gaps) if gaps else ""
        return


# ---------------------------------------------------------------------------
# Coverpoint CSV helpers
# ---------------------------------------------------------------------------


def add_norm_rules_to_cp_row(
    cp_path: Path,
    fieldnames: list[str],
    rows: list[dict],
    line_number: int,
    norm_rule_names: list[str],
):
    """Append norm rule names to the 'normative rules' column of a coverpoint row.

    Mutates fieldnames and the matching row in-place. Does NOT write to disk.
    """
    col = "Normative Rules"
    if col not in fieldnames:
        fieldnames.append(col)
    for row in rows:
        if row.get("_line_number") != line_number:
            continue
        existing = (row.get(col) or "").strip()
        existing_set = set(x.strip() for x in existing.split(";") if x.strip())
        for name in norm_rule_names:
            existing_set.add(name)
        row[col] = "; ".join(sorted(existing_set))
        return


def format_coverpoint_row(row: dict) -> str:
    """Format a coverpoint row's data for the Claude prompt."""
    parts = []
    for key, val in row.items():
        if key.startswith("_"):
            continue
        val = (val or "").strip()
        if val:
            parts.append(f"  - {key}: {val}")
    return "\n".join(parts)


def format_active_coverpoints(row: dict) -> str:
    """List column headers marked with 'x' or a variant name (coverpoint columns)."""
    active = []
    for key, val in row.items():
        if key.startswith("_"):
            continue
        val = (val or "").strip().lower()
        if val in ("x", "yes", "1") or (val and val not in ("", "no", "0", "n/a")):
            # Skip metadata columns
            skip = (
                "sr no",
                "goal",
                "feature",
                "expectation",
                "spec",
                "bins",
                "instruction",
                "type",
                "rv32",
                "rv64",
                "description",
                "name",
                "normative",
            )
            if not any(s in key.lower() for s in skip):
                active.append(key)
    return ", ".join(active) if active else "(none detected)"


# ---------------------------------------------------------------------------
# Claude launching
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict | None:
    """Extract the first JSON object from Claude's output."""
    # Try to find JSON block in markdown code fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try to find bare JSON object
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    # Try the whole output
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def launch_claude(prompt: str, dry_run: bool = False) -> dict | None:
    """Launch Claude with a prompt, return parsed JSON or None."""
    if dry_run:
        print(f"[DRY RUN] Would send prompt ({len(prompt)} chars):\n{prompt[:300]}...")
        return None

    try:
        # Unset CLAUDECODE env var to allow nested launches
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        output = result.stdout or ""
        if result.returncode != 0:
            print(f"  Claude exited with code {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")

        parsed = extract_json(output)
        if parsed is None:
            print("  WARNING: Could not parse JSON from Claude output")
            print(f"  Raw output (first 500 chars): {output[:500]}")
        return parsed

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR launching Claude: {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 1: Coverpoint → Normative Rule matching
# ---------------------------------------------------------------------------


def build_phase1a_prompt(row: dict, norm_rule_names: list[str]) -> str:
    """Build Pass A prompt: coverpoint row + rule NAMES only → select relevant rules."""
    instruction = get_field(row, "instruction", "sr no", "name", "sr")
    goal = get_field(row, "goal")
    feature_desc = get_field(row, "feature description", "description")
    expectation = get_field(row, "expectation")
    spec = get_field(row, "spec")

    names_block = "\n".join(f"- {n}" for n in norm_rule_names)

    return f"""You are a normative rule matcher. Given a coverpoint description and a list of normative rule NAMES, select which rules are relevant.

COVERPOINT:
- Name: {instruction}
- Goal: {goal}
- Feature Description: {feature_desc}
- Expectation: {expectation}
- Spec: {spec}

NORMATIVE RULE NAMES:
{names_block}

Select ALL normative rules whose name suggests they are AT LEAST PARTIALLY related to this coverpoint. Be inclusive - if a rule name sounds even slightly relevant, include it. It's better to include too many than miss one.

Output ONLY valid JSON (no markdown, no extra text):
{{"selected_rules": ["rule_name_1", "rule_name_2", ...]}}

If none are relevant: {{"selected_rules": []}}
"""


def build_phase1b_prompt(row: dict, selected_rules: list[tuple[str, str]]) -> str:
    """Build Pass B prompt: coverpoint row + selected rules with full descriptions → pairings."""
    instruction = get_field(row, "instruction", "sr no", "name", "sr")
    goal = get_field(row, "goal")
    feature_desc = get_field(row, "feature description", "description")
    expectation = get_field(row, "expectation")
    spec = get_field(row, "spec")

    rules_block = "\n".join(f"- {name}: {desc}" for name, desc in selected_rules)

    return f"""You are a normative rule matcher. Given a coverpoint and a set of normative rules with their full spec text, determine which rules this coverpoint at least partially covers.

COVERPOINT:
- Name: {instruction}
- Goal: {goal}
- Feature Description: {feature_desc}
- Expectation: {expectation}
- Spec: {spec}

NORMATIVE RULES (name: spec text):
{rules_block}

For each rule that this coverpoint AT LEAST PARTIALLY covers, provide:
- norm_rule_name: exact rule name
- coverage_description: brief explanation of HOW this coverpoint covers that rule

Output ONLY valid JSON (no markdown, no extra text):
{{"matches": [{{"norm_rule_name": "...", "coverage_description": "..."}}]}}

If none match: {{"matches": []}}
"""


def run_phase1(args):
    """Run Phase 1: match coverpoint rows to normative rules (two-pass per row)."""
    norm_path, norm_fields, norm_rows = read_norm_csv()
    print(f"Loaded {len(norm_rows)} normative rules from {NORM_CSV}")

    # Pre-compute rule names and name→description lookup
    all_rule_names = [get_norm_name(r) for r in norm_rows if get_norm_name(r)]
    rule_desc_map = {get_norm_name(r): get_norm_description(r) for r in norm_rows if get_norm_name(r)}

    # Process each coverpoint CSV
    for cp_csv_name in COVERPOINT_CSVS:
        cp_path = resolve_csv_path(cp_csv_name)
        if not cp_path.exists():
            print(f"WARNING: Coverpoint CSV not found: {cp_path}, skipping")
            continue

        cp_fields, cp_rows = read_csv(cp_path)
        print(f"\nProcessing coverpoint CSV: {cp_csv_name} ({len(cp_rows)} rows)")

        # Filter rows by line range and validity
        rows_to_process = filter_rows(cp_rows, args, phase=1)
        print(f"Rows to process: {len(rows_to_process)}")

        success = 0
        fail = 0

        for row in rows_to_process:
            line_num = row["_line_number"]
            row_name = get_field(row, "sr no", "instruction", "name", "sr") or f"line {line_num}"
            print(f"\n{'=' * 60}")
            print(f"Phase 1 - {cp_csv_name} line {line_num}: {row_name}")
            print(f"{'=' * 60}")

            # --- Pass A: names-only selection ---
            prompt_a = build_phase1a_prompt(row, all_rule_names)
            print(f"  Pass A: sending {len(all_rule_names)} rule names ({len(prompt_a)} chars)")
            result_a = launch_claude(prompt_a, dry_run=args.dry_run)

            if args.dry_run:
                success += 1
                continue

            if result_a is None:
                print("  Pass A failed, skipping row")
                fail += 1
                continue

            selected = result_a.get("selected_rules", [])
            # Validate against known names
            selected = [n for n in selected if n in rule_desc_map]
            print(f"  Pass A selected {len(selected)} rules")

            if not selected:
                print("  No rules selected, skipping Pass B")
                success += 1
                continue

            # --- Pass B: full descriptions for selected rules ---
            selected_with_desc = [(n, rule_desc_map[n]) for n in selected]
            prompt_b = build_phase1b_prompt(row, selected_with_desc)
            print(f"  Pass B: sending {len(selected)} rules with descriptions ({len(prompt_b)} chars)")
            result_b = launch_claude(prompt_b, dry_run=args.dry_run)

            if result_b is None:
                print("  Pass B failed, skipping row")
                fail += 1
                continue

            matches = result_b.get("matches", [])
            print(f"  Found {len(matches)} confirmed matches")

            matched_norm_names = []
            for match in matches:
                norm_name = match.get("norm_rule_name", "")
                cov_desc = match.get("coverage_description", "")
                if not norm_name or norm_name not in rule_desc_map:
                    continue
                print(f"    -> {norm_name}: {cov_desc[:80]}")
                add_coverpoint_to_norm_row(
                    norm_path,
                    norm_fields,
                    norm_rows,
                    norm_name,
                    row_name,
                    cov_desc,
                )
                matched_norm_names.append(norm_name)

            if matched_norm_names:
                add_norm_rules_to_cp_row(
                    cp_path,
                    cp_fields,
                    cp_rows,
                    line_num,
                    matched_norm_names,
                )

            success += 1

            # Write incrementally after each row
            if not args.dry_run:
                write_csv(cp_path, cp_fields, cp_rows)
                write_csv(norm_path, norm_fields, norm_rows)

        print(f"Phase 1 results for {cp_csv_name}: {success} succeeded, {fail} failed")
        print(f"\nUpdated {NORM_CSV}")


# ---------------------------------------------------------------------------
# Phase 1s: Standard vector CSV → Normative Rule matching (column-oriented)
# ---------------------------------------------------------------------------


def load_coverpoint_defs() -> str:
    """Load the v-coverpoints.adoc file for coverpoint definitions."""
    path = WORKING_TESTPLANS / COVERPOINT_DEFS_FILE
    if not path.exists():
        print(f"ERROR: Coverpoint definitions file not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def get_coverpoint_columns(fieldnames: list[str]) -> list[str]:
    """Return column names that are actual coverpoints (not metadata/skip columns)."""
    return [f for f in fieldnames if f not in SKIP_COLUMNS and not f.startswith("_")]


def collect_column_instructions(rows: list[dict], col_name: str) -> list[dict]:
    """Collect all instructions that use a coverpoint column (non-empty cell).

    Returns list of dicts with instruction context + cell_value.
    """
    instructions = []
    for row in rows:
        cell = (row.get(col_name) or "").strip()
        if not cell:
            continue
        ctx = {"cell_value": cell}
        for cc in CONTEXT_COLUMNS:
            ctx[cc] = (row.get(cc) or "").strip()
        instructions.append(ctx)
    return instructions


def format_instruction_list(instructions: list[dict]) -> str:
    """Format instruction list as a compact summary grouped by variant value.

    Instead of listing every instruction individually (which can be 200+ lines),
    groups them by cell_value (variant) and shows count + representative examples.
    """
    from collections import defaultdict

    # Group by variant value
    groups: dict[str, list[str]] = defaultdict(list)
    for inst in instructions:
        val = inst.get("cell_value", "x")
        name = inst.get("Instruction", "?")
        groups[val].append(name)

    lines = []
    for variant, names in groups.items():
        if len(names) <= 5:
            names_str = ", ".join(names)
        else:
            names_str = f"{', '.join(names[:3])}, ... ({len(names)} total)"
        lines.append(f"  - variant={variant}: {names_str}")

    return "\n".join(lines)


def format_instruction_list_csv(instructions: list[dict]) -> str:
    """Format instruction list for the mapping CSV (compact summary by variant)."""
    from collections import defaultdict

    groups: dict[str, list[str]] = defaultdict(list)
    for inst in instructions:
        val = inst.get("cell_value", "x")
        name = inst.get("Instruction", "?")
        groups[val].append(name)

    parts = []
    for variant, names in groups.items():
        if len(names) <= 3:
            parts.append(f"{', '.join(names)} ({variant})")
        else:
            parts.append(f"{names[0]}, {names[1]}, ... +{len(names) - 2} more ({variant})")
    return "; ".join(parts)


def read_mapping_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Read an existing mapping CSV, or return empty structure if it doesn't exist."""
    if not path.exists():
        return ["coverpoint_name", "instructions"], []
    return read_csv(path)


def write_mapping_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    """Write the mapping CSV."""
    write_csv(path, fieldnames, rows)


def get_mapping_row(mapping_fields: list[str], mapping_rows: list[dict], cp_name: str) -> dict | None:
    """Find existing row for a coverpoint in the mapping CSV."""
    for row in mapping_rows:
        if row.get("coverpoint_name", "").strip() == cp_name:
            return row
    return None


def add_norm_to_mapping_row(
    mapping_fields: list[str],
    mapping_rows: list[dict],
    cp_name: str,
    instructions_str: str,
    norm_rule_names: list[str],
):
    """Add or update a row in the mapping CSV for a coverpoint column."""
    existing = get_mapping_row(mapping_fields, mapping_rows, cp_name)
    if existing is None:
        existing = {"coverpoint_name": cp_name, "instructions": instructions_str}
        mapping_rows.append(existing)

    # Collect already-assigned norm rules
    assigned = set()
    for key in existing:
        if key.startswith("norm_rule_") and existing[key].strip():
            assigned.add(existing[key].strip())

    # Add new ones
    idx = 1
    while f"norm_rule_{idx}" in existing and existing[f"norm_rule_{idx}"].strip():
        idx += 1
    for name in norm_rule_names:
        if name in assigned:
            continue
        col = f"norm_rule_{idx}"
        if col not in mapping_fields:
            mapping_fields.append(col)
        existing[col] = name
        assigned.add(name)
        idx += 1


def build_phase1s_a_prompt(
    cp_col_name: str,
    cp_definition: str,
    variant_reference: str,
    instructions: list[dict],
    norm_rule_names: list[str],
) -> str:
    """Build Pass A prompt for standard coverpoint column → rule names selection."""
    inst_block = format_instruction_list(instructions)
    names_block = "\n".join(f"- {n}" for n in norm_rule_names)

    return f"""You are a normative rule matcher for RISC-V vector extensions. Given a coverpoint column definition and the instructions that use it, select which normative rules are relevant.

COVERPOINT COLUMN: {cp_col_name}

COVERPOINT DEFINITION (from v-coverpoints.adoc):
{cp_definition}

VARIANT REFERENCE (cell values other than 'x' modify the coverpoint behavior):
{variant_reference}

INSTRUCTIONS USING THIS COVERPOINT (format: instruction(cell_value) [EEW widths]):
{inst_block}

NORMATIVE RULE NAMES:
{names_block}

Select ALL normative rules whose name suggests they are AT LEAST PARTIALLY related to what this coverpoint tests. Consider:
- The coverpoint definition describes what hardware behavior is being verified
- The variant values (emul2, nv0, f, wv, etc.) modify register numbering, edge values, or widths
- The EEW columns show which element widths each instruction operates on
- Rules about register encoding, element widths, masking, LMUL, VL, vtype, etc. may be relevant

Be inclusive - if a rule name sounds even slightly relevant, include it.

Output ONLY valid JSON (no markdown, no extra text):
{{"selected_rules": ["rule_name_1", "rule_name_2", ...]}}

If none are relevant: {{"selected_rules": []}}
"""


def build_phase1s_b_prompt(
    cp_col_name: str,
    cp_definition: str,
    variant_reference: str,
    instructions: list[dict],
    selected_rules: list[tuple[str, str]],
) -> str:
    """Build Pass B prompt for standard coverpoint column → confirmed pairings."""
    inst_block = format_instruction_list(instructions)
    rules_block = "\n".join(f"- {name}: {desc}" for name, desc in selected_rules)

    return f"""You are a normative rule matcher for RISC-V vector extensions. Given a coverpoint column and normative rules with their full spec text, determine which rules this coverpoint at least partially covers.

COVERPOINT COLUMN: {cp_col_name}

COVERPOINT DEFINITION (from v-coverpoints.adoc):
{cp_definition}

VARIANT REFERENCE (cell values other than 'x' modify the coverpoint behavior):
{variant_reference}

INSTRUCTIONS USING THIS COVERPOINT (format: instruction(cell_value) [EEW widths]):
{inst_block}

NORMATIVE RULES (name: spec text):
{rules_block}

For each rule that this coverpoint AT LEAST PARTIALLY covers, provide:
- norm_rule_name: exact rule name from the list above
- coverage_description: brief explanation of HOW this coverpoint column covers that rule (reference the coverpoint definition and relevant variants/instructions)

The cp_name for all matches should be "{cp_col_name}" (the coverpoint column, not individual instructions).

Output ONLY valid JSON (no markdown, no extra text):
{{"matches": [{{"norm_rule_name": "...", "coverage_description": "..."}}]}}

If none match: {{"matches": []}}
"""


def extract_cp_definition(adoc_text: str, cp_name: str) -> str:
    """Extract a coverpoint's definition line from the adoc table."""
    # Look for |cp_name| or |cmp_name| or |cr_name| pattern in the table
    for line in adoc_text.split("\n"):
        if f"|{cp_name}|" in line:
            return line.strip().strip("|").strip()
    # Try partial match (the column name may have variant suffix stripped)
    base_name = cp_name.split("_")[0] + "_" + "_".join(cp_name.split("_")[1:])
    for line in adoc_text.split("\n"):
        if f"|{base_name}|" in line:
            return line.strip().strip("|").strip()
    return f"(No definition found for {cp_name} in v-coverpoints.adoc)"


def extract_variant_reference(adoc_text: str) -> str:
    """Extract the variant reference section (lines about nv0, emul2, etc.)."""
    lines = adoc_text.split("\n")
    variant_lines = []
    capture = False
    for line in lines:
        if "an x in the spreadsheet" in line:
            capture = True
        if capture:
            variant_lines.append(line)
    return "\n".join(variant_lines) if variant_lines else "(No variant reference found)"


def run_phase1s(args):
    """Run Phase 1s: match standard vector coverpoint columns to normative rules."""
    norm_path, norm_fields, norm_rows = read_norm_csv()
    print(f"Loaded {len(norm_rows)} normative rules from {NORM_CSV}")

    # Pre-compute rule names and descriptions
    all_rule_names = [get_norm_name(r) for r in norm_rows if get_norm_name(r)]
    rule_desc_map = {get_norm_name(r): get_norm_description(r) for r in norm_rows if get_norm_name(r)}

    # Load coverpoint definitions
    adoc_text = load_coverpoint_defs()
    variant_ref = extract_variant_reference(adoc_text)

    # Determine which CSVs to process
    csv_filter = args.csv if hasattr(args, "csv") and args.csv else None
    csvs_to_process = {}
    for name, rel_path in STANDARD_CSVS.items():
        if csv_filter and name != csv_filter:
            continue
        csvs_to_process[name] = rel_path

    if not csvs_to_process:
        print(f"ERROR: No matching CSVs found. Available: {list(STANDARD_CSVS.keys())}")
        sys.exit(1)

    for csv_name, csv_rel_path in csvs_to_process.items():
        csv_path = WORKING_TESTPLANS / csv_rel_path
        if not csv_path.exists():
            print(f"WARNING: CSV not found: {csv_path}, skipping")
            continue

        cp_fields, cp_rows = read_csv(csv_path)
        print(f"\nProcessing standard CSV: {csv_name} ({len(cp_rows)} instructions)")

        # Set up output mapping CSV
        mapping_path = WORKING_TESTPLANS / f"{csv_name}_norm_mapping.csv"
        mapping_fields, mapping_rows = read_mapping_csv(mapping_path)

        # Get coverpoint columns
        cp_columns = get_coverpoint_columns(cp_fields)
        print(f"Coverpoint columns: {len(cp_columns)}")

        # Filter columns by --start/--end/--line (treating column index as "line")
        col_indices = list(range(len(cp_columns)))
        if args.line is not None:
            col_indices = [i for i in col_indices if i + 1 == args.line]
        elif args.start is not None:
            if args.end is not None:
                col_indices = [i for i in col_indices if args.start <= i + 1 <= args.end]
            else:
                col_indices = [i for i in col_indices if i + 1 >= args.start]

        print(f"Columns to process: {len(col_indices)}")

        success = 0
        fail = 0

        for col_idx in col_indices:
            col_name = cp_columns[col_idx]

            # Resume support: skip if already in mapping CSV (unless --force)
            force = getattr(args, "force", False)
            existing_row = get_mapping_row(mapping_fields, mapping_rows, col_name)
            if existing_row is not None and not force:
                has_rules = any(
                    k.startswith("norm_rule_") and v.strip() for k, v in existing_row.items() if isinstance(v, str)
                )
                if has_rules or existing_row.get("instructions", "").strip():
                    print(f"\n  [SKIP] {col_name} - already in mapping CSV")
                    success += 1
                    continue
            elif existing_row is not None and force:
                # Remove old row so it gets re-processed
                mapping_rows.remove(existing_row)

            # Collect instructions using this column
            instructions = collect_column_instructions(cp_rows, col_name)
            if not instructions:
                print(f"\n  [SKIP] {col_name} - no instructions use it")
                continue

            # Get coverpoint definition from adoc
            cp_def = extract_cp_definition(adoc_text, col_name)

            print(f"\n{'=' * 60}")
            print(f"Phase 1s - {csv_name} column {col_idx + 1}/{len(cp_columns)}: {col_name}")
            print(f"  {len(instructions)} instructions, definition: {cp_def[:80]}...")
            print(f"{'=' * 60}")

            # --- Pass A: names-only selection ---
            prompt_a = build_phase1s_a_prompt(col_name, cp_def, variant_ref, instructions, all_rule_names)
            print(f"  Pass A: sending {len(all_rule_names)} rule names ({len(prompt_a)} chars)")
            result_a = launch_claude(prompt_a, dry_run=args.dry_run)

            if args.dry_run:
                success += 1
                continue

            if result_a is None:
                print("  Pass A failed, skipping column")
                fail += 1
                continue

            selected = result_a.get("selected_rules", [])
            selected = [n for n in selected if n in rule_desc_map]
            print(f"  Pass A selected {len(selected)} rules")

            if not selected:
                print("  No rules selected, recording empty entry")
                inst_str = format_instruction_list_csv(instructions)
                add_norm_to_mapping_row(mapping_fields, mapping_rows, col_name, inst_str, [])
                write_mapping_csv(mapping_path, mapping_fields, mapping_rows)
                success += 1
                continue

            # --- Pass B: full descriptions for selected rules ---
            selected_with_desc = [(n, rule_desc_map[n]) for n in selected]
            prompt_b = build_phase1s_b_prompt(col_name, cp_def, variant_ref, instructions, selected_with_desc)
            print(f"  Pass B: sending {len(selected)} rules with descriptions ({len(prompt_b)} chars)")
            result_b = launch_claude(prompt_b, dry_run=args.dry_run)

            if result_b is None:
                print("  Pass B failed, skipping column")
                fail += 1
                continue

            matches = result_b.get("matches", [])
            print(f"  Found {len(matches)} confirmed matches")

            matched_norm_names = []
            for match in matches:
                norm_name = match.get("norm_rule_name", "")
                cov_desc = match.get("coverage_description", "")
                if not norm_name or norm_name not in rule_desc_map:
                    continue
                print(f"    -> {norm_name}: {cov_desc[:80]}")
                # Add to norm CSV (cp_name = column name, not instruction)
                add_coverpoint_to_norm_row(
                    norm_path,
                    norm_fields,
                    norm_rows,
                    norm_name,
                    col_name,
                    cov_desc,
                )
                matched_norm_names.append(norm_name)

            # Add to mapping CSV
            inst_str = format_instruction_list_csv(instructions)
            add_norm_to_mapping_row(mapping_fields, mapping_rows, col_name, inst_str, matched_norm_names)

            success += 1

            # Write incrementally
            write_mapping_csv(mapping_path, mapping_fields, mapping_rows)
            write_csv(norm_path, norm_fields, norm_rows)

        print(f"\nPhase 1s results for {csv_name}: {success} succeeded, {fail} failed")
        print(f"  Mapping CSV: {mapping_path}")

    print(f"\nUpdated {NORM_CSV}")


# ---------------------------------------------------------------------------
# Phase 2: Coverage completeness check
# ---------------------------------------------------------------------------


def build_phase2_prompt(norm_row: dict) -> str:
    """Build the Phase 2 prompt for a single normative rule."""
    name = get_norm_name(norm_row)
    desc = get_norm_description(norm_row)
    pairs = get_existing_coverpoint_pairs(norm_row)

    if not pairs:
        pairs_text = "(No coverpoints paired to this rule)"
    else:
        pairs_text = "\n".join(f"- {cp}: {cdesc}" for cp, cdesc in pairs)

    return f"""You are a coverage completeness checker.

NORMATIVE RULE:
- Name: {name}
- Spec text: {desc}

COVERPOINTS PAIRED TO THIS RULE:
{pairs_text}

Determine if this normative rule is FULLY covered by the listed coverpoints.
- "full": Every aspect of the spec text is tested by at least one coverpoint
- "partial": Some aspects are tested but gaps remain
- "none": No meaningful coverage despite pairings (or no pairings at all)

Output ONLY valid JSON (no markdown, no explanation outside the JSON):
{{"coverage_status": "full|partial|none", "explanation": "...", "gaps": ["gap1", "gap2"]}}

Use an empty list for gaps if coverage is full: {{"coverage_status": "full", "explanation": "...", "gaps": []}}"""


def run_phase2(args):
    """Run Phase 2: assess coverage completeness for each normative rule."""
    norm_path, norm_fields, norm_rows = read_norm_csv()
    print(f"Loaded {len(norm_rows)} normative rules from {NORM_CSV}")

    rows_to_process = filter_rows(norm_rows, args, phase=2)
    print(f"Rules to process: {len(rows_to_process)}")

    success = 0
    fail = 0

    # First pass: auto-mark rules with no coverpoints
    auto_count = 0
    for row in rows_to_process:
        name = get_norm_name(row)
        if not name:
            continue
        pairs = get_existing_coverpoint_pairs(row)
        if not pairs and not args.dry_run:
            set_coverage_status(norm_rows, norm_fields, name, "none", "No coverpoints paired to this rule", [])
            auto_count += 1
    if auto_count and not args.dry_run:
        write_csv(norm_path, norm_fields, norm_rows)
    print(f"Auto-marked {auto_count} rules with no coverpoints as 'none'")
    success += auto_count

    # Second pass: Claude assessment for rules with coverpoints
    for row in rows_to_process:
        line_num = row["_line_number"]
        name = get_norm_name(row)
        if not name:
            continue

        pairs = get_existing_coverpoint_pairs(row)
        if not pairs:
            continue  # already handled above

        # Skip if already assessed (resume support)
        existing_status = (row.get("coverage_status") or "").strip()
        if existing_status:
            print(f"  [SKIP] {name} - already assessed as '{existing_status}'")
            success += 1
            continue

        print(f"\n{'=' * 60}")
        print(f"Phase 2 - line {line_num}: {name} ({len(pairs)} coverpoints)")
        print(f"{'=' * 60}")

        prompt = build_phase2_prompt(row)
        result = launch_claude(prompt, dry_run=args.dry_run)

        if args.dry_run:
            success += 1
            continue

        if result is None:
            fail += 1
            continue

        status = result.get("coverage_status", "unknown")
        explanation = result.get("explanation", "")
        gaps = result.get("gaps", [])

        print(f"  Status: {status}")
        print(f"  Explanation: {explanation[:120]}")
        if gaps:
            print(f"  Gaps: {gaps}")

        set_coverage_status(norm_rows, norm_fields, name, status, explanation, gaps)
        success += 1

        # Write after each row so progress is saved incrementally
        if not args.dry_run:
            write_csv(norm_path, norm_fields, norm_rows)

    print(f"\nPhase 2 results: {success} succeeded, {fail} failed")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def is_processable_cp_row(row: dict) -> bool:
    """Determine if a coverpoint CSV row has meaningful data to process.

    Skips blank rows, section headers, parameter notes, and 'Untestable' rows.
    A row is processable if it has a cp_ name OR a non-trivial Goal.
    """
    sr_no = get_field(row, "sr no", "name")
    goal = get_field(row, "goal")
    coverpoint_written = get_field(row, "coverpoint written")

    # Skip rows marked as untestable, parameter, or already covered
    for marker in ("untestable", "parameter", "covered by"):
        if coverpoint_written.lower().startswith(marker):
            return False

    # Must have a cp_ name or a meaningful goal
    if sr_no.startswith("cp_"):
        return True
    if goal and len(goal) > 10:
        return True

    return False


def filter_rows(rows: list[dict], args, phase: int = 1) -> list[dict]:
    """Filter rows by --line, --start, --end arguments and row validity."""
    filtered = rows
    if args.line is not None:
        filtered = [r for r in filtered if r["_line_number"] == args.line]
    elif args.start is not None:
        if args.end is not None:
            filtered = [r for r in filtered if args.start <= r["_line_number"] <= args.end]
        else:
            filtered = [r for r in filtered if r["_line_number"] >= args.start]

    # For phase 1, skip non-processable rows
    if phase == 1:
        filtered = [r for r in filtered if is_processable_cp_row(r)]

    return filtered


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Process normative rule ↔ coverpoint pairings with fresh Claude instances"
    )
    parser.add_argument(
        "--phase",
        type=str,
        required=True,
        choices=["1", "1s", "2"],
        help="Phase 1: custom CSVs (row-oriented). Phase 1s: standard CSVs (column-oriented). Phase 2: check completeness.",
    )
    parser.add_argument("--start", type=int, help="Start line/column number")
    parser.add_argument("--end", type=int, help="End line/column number (inclusive, use with --start)")
    parser.add_argument("--line", type=int, help="Process only this single line/column")
    parser.add_argument("--csv", type=str, help="For phase 1s: process only this CSV (e.g. Vx, Vls, Vf)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--force", action="store_true", help="Re-process even if already in mapping CSV")

    args = parser.parse_args()

    # Validate configuration
    if not NORM_CSV:
        print("ERROR: NORM_CSV is not configured. Edit the USER CONFIGURATION section at the top of this script.")
        sys.exit(1)
    if not COVERPOINT_CSVS and args.phase == "1":
        print(
            "ERROR: COVERPOINT_CSVS is not configured. Edit the USER CONFIGURATION section at the top of this script."
        )
        sys.exit(1)

    if args.phase == "1":
        run_phase1(args)
    elif args.phase == "1s":
        run_phase1s(args)
    else:
        run_phase2(args)


if __name__ == "__main__":
    main()
