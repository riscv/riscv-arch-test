#!/usr/bin/env python3
"""
amend_coverage.py - Amend normative rules CSV with SmV/SmVF coverpoints,
cp_vd semantic fixes, and zero-match coverpoint mappings.

This script applies three categories of amendments:
1. SmV/SmVF coverpoints from working-testplans/ CSVs
2. cp_vd=x implies vd=v0 coverage for vmf* compare rules
3. cp_rs2_edges on strided LS covers negative/zero stride rules
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

WORKING = Path(__file__).parent
NORM_CSV = WORKING / "v-st-ext-normative-rules.csv"


def read_norm_csv():
    """Read the normative rules CSV into a list of dicts."""
    with Path(NORM_CSV).open("r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    return fieldnames, rows


def find_next_cp_slot(row, fieldnames):
    """Find the first empty cp_name_N slot in a row."""
    for i in range(1, 37):
        key = f"cp_name_{i}"
        if key not in fieldnames:
            return None
        if not row.get(key, "").strip():
            return i
    return None


def add_coverpoint(row, fieldnames, cp_name, desc):
    """Add a coverpoint to the next empty slot. Returns True if added."""
    slot = find_next_cp_slot(row, fieldnames)
    if slot is None:
        return False
    row[f"cp_name_{slot}"] = cp_name
    row[f"coverage_desc_{slot}"] = desc
    return True


def apply_smv_mappings(rows, fieldnames):
    """Apply SmV coverpoint mappings to normative rules."""
    # SmV coverpoint -> (rule_names, description)
    SMV_MAPPINGS = {
        "cp_vcsrrswc": {
            "vstart_acc": "SmV cp_vcsrrswc tests read/write/clear/set operations on all 7 vector CSRs including vstart, verifying CSR accessibility.",
            "vxrm_acc": "SmV cp_vcsrrswc tests read/write/clear/set operations on all 7 vector CSRs including vxrm, verifying CSR accessibility.",
            "vlenb_acc": "SmV cp_vcsrrswc tests read/write/clear/set operations on all 7 vector CSRs including vlenb, verifying CSR accessibility.",
            "vlenb_op": "SmV cp_vcsrrswc tests read/write/clear/set operations on vlenb CSR, verifying it is readable and read-only.",
            "vcsr-vxrm_op": "SmV cp_vcsrrswc tests read/write/clear/set operations on vcsr, vxrm, and vxsat CSRs, which exercises the vcsr mirroring of vxrm.",
            "vcsr-vxsat_op": "SmV cp_vcsrrswc tests read/write/clear/set operations on vcsr, vxrm, and vxsat CSRs, which exercises the vcsr mirroring of vxsat.",
        },
        "cp_vcsrs_walking1s": {
            "vstart_sz": "SmV cp_vcsrs_walking1s writes all XLEN 1-hot values to writable vector CSRs including vstart, testing bit width.",
            "vxrm_sz": "SmV cp_vcsrs_walking1s writes all XLEN 1-hot values to writable vector CSRs including vxrm, testing bit width.",
            "vxsat_sz": "SmV cp_vcsrs_walking1s writes all XLEN 1-hot values to writable vector CSRs including vxsat, testing bit width.",
            "vstart_sz_writable": "SmV cp_vcsrs_walking1s writes all XLEN 1-hot values to vstart, confirming which bits are writable (only enough to hold largest element index).",
        },
        "cp_mstatus_vs_set_dirty_arithmetic": {
            "mstatus-vs_op_initial_clean": "SmV cp_mstatus_vs_set_dirty_arithmetic runs a vector arithmetic instruction with mstatus.VS={initial,clean} and verifies transition to Dirty.",
        },
        "cp_mstatus_vs_set_dirty_csr": {
            "mstatus-vs_op_initial_clean": "SmV cp_mstatus_vs_set_dirty_csr runs vsetvli with mstatus.VS={initial,clean} and verifies transition to Dirty, covering the CSR-changing variant.",
            "vtype-vstart_op": "SmV cp_mstatus_vs_set_dirty_csr uses vsetvli to change vtype, exercising the vsetvli -> vtype update path.",
        },
        "cp_misa_v_clear_set": {
            "MUTABLE_MISA_V": "SmV cp_misa_v_clear_set attempts to write misa.V field, testing whether it is writable (implementation-defined).",
            "misa-V_op": "SmV cp_misa_v_clear_set conducts a CSR clear to the misa.V field, testing its accessibility and behavior.",
        },
        "cp_sew_lmul_vset_i_vli": {
            "vsetivli_op": "SmV cp_sew_lmul_vset_i_vli crosses eSEW={8/16/32/64} with mLMUL={f8/f4/f2/1/2/4/8} for vsetivli, testing all vtype configurations.",
            "vtype-vstart_op": "SmV cp_sew_lmul_vset_i_vli uses vset{i}vli to set all SEW/LMUL combinations, exercising the vtype update mechanism.",
        },
        "cp_sew_lmul_vsetvl": {
            "vtype-vstart_op": "SmV cp_sew_lmul_vsetvl uses vsetvl with rs2 encoding SEW/LMUL combinations, exercising the vtype update mechanism via vsetvl.",
        },
        "cp_vstart_out_of_bounds": {
            "vstart_sz_writable": "SmV cp_vstart_out_of_bounds writes 2^16 to vstart and checks the result, testing writable bit count boundary.",
        },
        "cp_vtype_vill_set_vl_0": {
            "vtype-vstart_op": "SmV cp_vtype_vill_set_vl_0 verifies that when an unsupported vtype configuration is set, vl is set to zero.",
        },
        "cp_vsetivli_avl_corners": {
            "vsetivli_op": "SmV cp_vsetivli_avl_corners tests vsetivli with all 32 immediate values (0-31) crossed with all supported SEW values.",
        },
    }

    updated = set()
    for row in rows:
        rule_name = row["rule_name"]
        for cp_name, rule_descs in SMV_MAPPINGS.items():
            if rule_name in rule_descs:
                desc = rule_descs[rule_name]
                if add_coverpoint(row, fieldnames, cp_name, desc):
                    updated.add(rule_name)

    print(f"SmV mappings: updated {len(updated)} rules")
    for r in sorted(updated):
        print(f"  {r}")
    return updated


def apply_smvf_mappings(rows, fieldnames):
    """Apply SmVF coverpoint mappings to normative rules."""
    SMVF_MAPPINGS = {
        "cp_vectorfp_mstatus_fs_state_affecting_register": {
            "mstatus-FS_dirty_hypervisor_V_fp": "SmVF cp_vectorfp_mstatus_fs_state_affecting_register tests that vector FP instructions modifying FP register state set mstatus.FS to Dirty (non-hypervisor part).",
        },
        "cp_vectorfp_mstatus_fs_state_affecting_csr": {
            "mstatus-FS_dirty_hypervisor_V_fp": "SmVF cp_vectorfp_mstatus_fs_state_affecting_csr tests that vector FP instructions modifying FP CSR state set mstatus.FS to Dirty.",
        },
    }

    updated = set()
    for row in rows:
        rule_name = row["rule_name"]
        for cp_name, rule_descs in SMVF_MAPPINGS.items():
            if rule_name in rule_descs:
                desc = rule_descs[rule_name]
                if add_coverpoint(row, fieldnames, cp_name, desc):
                    updated.add(rule_name)

    print(f"SmVF mappings: updated {len(updated)} rules")
    for r in sorted(updated):
        print(f"  {r}")
    return updated


def apply_cp_vd_fixes(rows, fieldnames):
    """Fix vmf*_vd_eq_v0 rules: cp_vd=x covers vd=v0 since it iterates all 32 registers."""
    VD_EQ_V0_RULES = [
        "vmfeq_vd_eq_v0",
        "vmfne_vd_eq_v0",
        "vmflt_vd_eq_v0",
        "vmfle_vd_eq_v0",
        "vmfgt_vd_eq_v0",
        "vmfge_vd_eq_v0",
    ]

    updated = set()
    for row in rows:
        rule_name = row["rule_name"]
        if rule_name in VD_EQ_V0_RULES:
            instr_base = rule_name.replace("_vd_eq_v0", "")
            desc = (
                f"cp_vd with variant 'x' on {instr_base} instructions iterates all 32 destination "
                f"registers (v0-v31), which includes the vd=v0 case where the destination "
                f"overwrites the mask register. This covers the {rule_name} requirement."
            )
            if add_coverpoint(row, fieldnames, "cp_vd (variant x)", desc):
                updated.add(rule_name)

    print(f"cp_vd fixes: updated {len(updated)} rules")
    for r in sorted(updated):
        print(f"  {r}")
    return updated


def apply_stride_edge_mappings(rows, fieldnames):
    """Map cp_rs2_edges on strided LS instructions to neg_stride and zero_stride rules."""
    STRIDE_RULES = {
        "vector_ls_neg_stride": (
            "cp_rs2_edges with ls_e* variant on strided load/store instructions (vlse*, vsse*) "
            "includes negative stride edge values (-1, -2, -SEW/8), which directly tests "
            "negative stride behavior."
        ),
        "vector_ls_zero_stride": (
            "cp_rs2_edges with ls_e* variant on strided load/store instructions (vlse*, vsse*) "
            "includes stride=0 as an edge value, which directly tests zero stride behavior."
        ),
    }

    updated = set()
    for row in rows:
        rule_name = row["rule_name"]
        if rule_name in STRIDE_RULES:
            desc = STRIDE_RULES[rule_name]
            if add_coverpoint(row, fieldnames, "cp_rs2_edges (ls_e* variant)", desc):
                updated.add(rule_name)

    print(f"Stride edge mappings: updated {len(updated)} rules")
    for r in sorted(updated):
        print(f"  {r}")
    return updated


def reassess_rules(rows, all_updated):
    """Reassess coverage status for all updated rules."""
    reassessed = 0
    for row in rows:
        rule_name = row["rule_name"]
        if rule_name not in all_updated:
            continue

        old_status = row["coverage_status"]

        # Count total coverpoints on this rule
        cp_count = 0
        for i in range(1, 37):
            if row.get(f"cp_name_{i}", "").strip():
                cp_count += 1

        if old_status == "none":
            row["coverage_status"] = "partial"
            if cp_count >= 3:
                row["explanation"] = (
                    f"Multiple coverpoints ({cp_count}) now address this rule from SmV/SmVF "
                    f"privileged tests and standard edge coverpoints. "
                    f"Coverage is partial because these test specific aspects but may not "
                    f"cover all facets of the normative requirement."
                )
            else:
                row["explanation"] = (
                    "SmV/SmVF or standard coverpoints now address this rule. "
                    "Coverage is partial as not all aspects of the normative requirement may be covered."
                )
            row["gaps"] = "Some aspects of the normative rule may still need dedicated testing."
            reassessed += 1
        elif old_status == "partial":
            # Strengthen the explanation
            existing_explanation = row.get("explanation", "")
            row["explanation"] = (
                existing_explanation + " Additional coverage from SmV/SmVF coverpoints "
                "strengthens the partial assessment."
            ).strip()
            reassessed += 1

    print(f"Reassessed {reassessed} rules")
    return reassessed


def print_summary(rows):
    """Print final coverage status summary."""
    from collections import Counter

    c = Counter(row["coverage_status"] for row in rows)
    print("\n=== Final Coverage Status ===")
    for k in ["full", "partial", "none", ""]:
        if k in c:
            label = k if k else "(blank/needs reassessment)"
            print(f"  {label}: {c[k]}")
    print(f"  Total: {sum(c.values())}")


def write_norm_csv(fieldnames, rows):
    """Write back the normative rules CSV."""
    with Path(NORM_CSV).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWritten to {NORM_CSV}")


def main():
    dry_run = "--dry-run" in sys.argv

    fieldnames, rows = read_norm_csv()

    print("=== Step 1: Apply SmV mappings ===")
    smv_updated = apply_smv_mappings(rows, fieldnames)

    print("\n=== Step 2: Apply SmVF mappings ===")
    smvf_updated = apply_smvf_mappings(rows, fieldnames)

    print("\n=== Step 3: Apply cp_vd fixes (vmf*_vd_eq_v0) ===")
    vd_updated = apply_cp_vd_fixes(rows, fieldnames)

    print("\n=== Step 4: Apply stride edge mappings ===")
    stride_updated = apply_stride_edge_mappings(rows, fieldnames)

    all_updated = smv_updated | smvf_updated | vd_updated | stride_updated

    print(f"\n=== Step 5: Reassess {len(all_updated)} updated rules ===")
    reassess_rules(rows, all_updated)

    print_summary(rows)

    if dry_run:
        print("\n[DRY RUN - no files modified]")
    else:
        write_norm_csv(fieldnames, rows)


if __name__ == "__main__":
    main()
