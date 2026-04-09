#!/usr/bin/env python3
"""
reassess_rules.py - Programmatically reassess rules that got edge coverpoint mappings.

For _op rules that now have edge coverpoints mapped:
- If they have data-edge coverpoints (cr_vs2_vs1_edges, etc.), mark as "partial"
  because edges test boundary behavior but don't guarantee complete operation coverage
- Generate appropriate explanation and gaps

For non-_op rules still at "none", categorize them.
"""

from __future__ import annotations

import csv
from pathlib import Path

NORM_CSV = Path(__file__).parent / "v-st-ext-normative-rules.csv"


def classify_edge_coverpoints(row):
    """Look at which cp_name slots are filled and classify coverage."""
    cps = []
    for i in range(1, 37):
        cp = row.get(f"cp_name_{i}", "")
        if cp:
            cps.append(cp)
    return cps


def has_data_edges(cps):
    """Check if any coverpoints are data-edge types (not just masking/asm_count)."""
    data_edge_prefixes = [
        "cp_vs2_edges",
        "cp_vs1_edges",
        "cr_vs2_vs1_edges",
        "cp_rs1_edges",
        "cr_vs2_rs1_edges",
        "cp_fs1_edges",
        "cr_vs2_fs1_edges",
        "cr_vs2_imm_edges",
        "cr_vxrm_vs2_vs1_edges",
        "cr_vxrm_vs2_rs1_edges",
        "cr_vxrm_vs2_imm_edges",
        "cp_rs2_edges",
    ]
    return any(cp in data_edge_prefixes for cp in cps)


def assess_op_rule(rule_name, spec_text, cps):
    """Generate assessment for an _op rule with edge coverpoints."""

    has_data = has_data_edges(cps)
    has_masking = "cp_masking_edges" in cps
    has_asm = "cp_asm_count" in cps

    # Build edge CP list for description
    data_cps = [cp for cp in cps if cp not in ("cp_masking_edges", "cp_asm_count")]

    if has_data:
        # Data edge coverpoints exercise the operation with boundary values
        cp_list = ", ".join(data_cps)

        explanation = (
            f"The edge coverpoints ({cp_list}) test {rule_name.replace('_op', '')} operations "
            f"by exercising boundary input values (e.g., 0, 1, -1, max, min for integers; "
            f"±0, ±inf, NaN, subnormals for FP) and verifying output correctness against "
            f"the Sail reference model. This provides strong evidence that the operation is "
            f"implemented correctly for corner cases, though it does not exhaustively test "
            f"all possible input combinations."
        )

        gaps = (
            "Edge coverpoints test boundary values but not all intermediate values; "
            "no randomized or exhaustive input space coverage beyond edges"
        )

        return "partial", explanation, gaps

    elif has_masking:
        explanation = (
            f"The cp_masking_edges coverpoint exercises the {rule_name.replace('_op', '')} "
            f"operation with various masking patterns, verifying the operation produces "
            f"correct results (checked against Sail reference model) under different "
            f"active/inactive element configurations."
        )

        gaps = (
            "Only masking-edge coverage; no data-edge coverpoints testing boundary input values; "
            "operation correctness tested only indirectly through masking patterns"
        )

        return "partial", explanation, gaps

    elif has_asm:
        explanation = (
            f"The cp_asm_count coverpoint verifies that {rule_name.replace('_op', '')} "
            f"instructions are assembled and executed, with results checked against "
            f"the Sail reference model."
        )

        gaps = (
            "Only basic assembly/execution coverage; no edge or boundary value testing; "
            "operation correctness minimally tested"
        )

        return "partial", explanation, gaps

    return "none", "No coverpoints paired to this rule", ""


def main():
    with Path(NORM_CSV).open("r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    for row in rows:
        # Only process rules with empty coverage_status (the ones we just updated)
        if row["coverage_status"] != "":
            continue

        cps = classify_edge_coverpoints(row)
        if not cps:
            # No coverpoints at all - mark as none
            row["coverage_status"] = "none"
            row["explanation"] = "No coverpoints paired to this rule"
            row["gaps"] = ""
            updated += 1
            continue

        status, explanation, gaps = assess_op_rule(row["rule_name"], row["spec_text"], cps)

        row["coverage_status"] = status
        row["explanation"] = explanation
        row["gaps"] = gaps
        updated += 1
        print(f"  {row['rule_name']}: {status}")

    with Path(NORM_CSV).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nReassessed {updated} rules")

    # Print final counts
    counts = {}
    for row in rows:
        s = row["coverage_status"]
        counts[s] = counts.get(s, 0) + 1
    print("\nFinal counts:")
    for k, v in sorted(counts.items()):
        print(f"  {k or '(empty)'}: {v}")


if __name__ == "__main__":
    main()
