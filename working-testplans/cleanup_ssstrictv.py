#!/usr/bin/env python3
"""Clean up SsstrictV.csv per Plan 1: delete duplicates, fill incomplete rows, rename rows, delete noise."""

import csv
from pathlib import Path

CSV_PATH = Path(__file__).parent / "SsstrictV.csv"


def read_csv():
    """Read CSV and return (headers, rows). Each row is a dict."""
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    return headers, rows


def get_name(row):
    """Get the Sr No field value (coverpoint name)."""
    for key in row:
        if "Sr No" in key:
            return (row[key] or "").strip()
    return ""


def get_desc(row):
    """Get Feature Description."""
    return (row.get("Feature Description", "") or "").strip()


def get_goal(row):
    """Get Goal."""
    return (row.get("Goal", "") or "").strip()


def get_spec(row):
    """Get Spec."""
    return (row.get("Spec", "") or "").strip()


def get_expectation(row):
    """Get Expectation."""
    return (row.get("Expectation", "") or "").strip()


def set_name(row, name):
    for key in row:
        if "Sr No" in key:
            row[key] = name


def is_empty_row(row):
    """Check if all fields are empty."""
    return all(not (v or "").strip() for v in row.values())


def is_spec_only_row(row):
    """Check if row has only Feature Description or Spec content (no cp_ name, no goal, no expectation)."""
    name = get_name(row)
    goal = get_goal(row)
    expectation = get_expectation(row)
    desc = get_desc(row)
    spec = get_spec(row)
    feature = (row.get("Feature", "") or "").strip()
    bins_val = (row.get("Bins", "") or "").strip()

    if name.startswith("cp_"):
        return False
    if name and not goal and not expectation and not bins_val:
        # Has a non-cp name but no goal/expectation/bins - could be noise
        return False  # Don't auto-classify these as spec-only
    if not name and not goal and not expectation and (desc or spec):
        return True
    return False


def main():
    headers, rows = read_csv()
    print(f"Loaded {len(rows)} rows")

    # ========== STEP 2: Delete duplicate cp_ rows ==========
    # Track first occurrence of each cp_ name, delete later duplicates
    duplicates_to_delete = {
        "cp_ssstrictv_mask_logical_vm0_reserved",
        "cp_ssstrictv_ls_seg_idx_vd_vs2_overlap",
        "cp_ssstrictv_vadc_vsbc_vd_v0_reserved",
        "cp_ssstrictv_vcompress_vstart_nonzero",
        "cp_ssstrictv_vcompress_vstart_report_zero",
    }

    seen_cp = set()
    dup_indices = []
    for i, row in enumerate(rows):
        name = get_name(row)
        if name in duplicates_to_delete:
            if name in seen_cp:
                dup_indices.append(i)
                print(f"  [DUP DELETE] row {i}: {name}")
            else:
                seen_cp.add(name)

    # ========== STEP 3: Fill in 5 incomplete cp_ rows ==========
    for i, row in enumerate(rows):
        name = get_name(row)

        if name == "cp_ssstrict_ls_nf<nf>_eew<eew>":
            row["Goal"] = "Confirm any NFIELDS * EEW violation is checked, run on all instructions with nf and eew"
            row["Feature Description"] = (
                "Run segment load/store instructions with NFIELDS and EEW combinations where NFIELDS * EEW exceeds the implementation limit, across all segment load/store instruction variants"
            )
            row["Expectation"] = "trap"
            row["Spec"] = (
                "The EMUL setting must be such that EMUL * NFIELDS ≤ 8, otherwise the instruction encoding is reserved."
            )
            print(f"  [FILLED] row {i}: {name}")

        elif name == "cp_ssstrictv_ls_eew_2x_elen":
            if not get_desc(row):
                row["Feature Description"] = (
                    "Run vector load/store instructions with EEW encoded in the width field set to 2 * ELEN (e.g., if ELEN=64, attempt EEW=128 encoding)"
                )
            if not get_expectation(row):
                row["Expectation"] = "trap"
            if not get_spec(row):
                row["Spec"] = (
                    "Vector loads and stores have an EEW encoded directly in the instruction. If the EEW is not a supported width, the instruction encoding is reserved."
                )
            print(f"  [FILLED] row {i}: {name}")

        elif name == "cp_ssstrictv_ls_emul_16":
            if not get_desc(row):
                row["Feature Description"] = (
                    "Run vector load/store instructions with SEW/LMUL/EEW combinations producing (EEW/SEW)*LMUL = 16 (e.g., EEW=64, SEW=8, LMUL=2)"
                )
            if not get_expectation(row):
                row["Expectation"] = "trap"
            if not get_spec(row):
                row["Spec"] = (
                    "If the EMUL would be out of range (EMUL>8 or EMUL<1/8), the instruction encoding is reserved."
                )
            print(f"  [FILLED] row {i}: {name}")

        elif name == "cp_ssstrictv_ls_emul_nfields_16":
            if not get_desc(row):
                row["Feature Description"] = (
                    "Run segment load/store instructions with EMUL and NFIELDS combinations where EMUL * NFIELDS > 8 (e.g., EMUL=2, NFIELDS=5)"
                )
            if not get_expectation(row):
                row["Expectation"] = "trap"
            if not get_spec(row):
                row["Spec"] = (
                    "The EMUL setting must be such that EMUL * NFIELDS ≤ 8, otherwise the instruction encoding is reserved."
                )
            print(f"  [FILLED] row {i}: {name}")

        elif name == "cp_ssstrictv_ls_eew_lt_sewmin":
            row["Goal"] = "Confirm vector load/store instructions trap when EEW < SEWMIN"
            row["Feature Description"] = (
                "Execute a vector load/store instruction with EEW (encoded in width field) smaller than the minimum supported SEW (SEWMIN). For example, vle8.v when SEWMIN > 8"
            )
            row["Expectation"] = "trap"
            row["Spec"] = (
                "Vector loads and stores have an EEW encoded directly in the instruction. If the EEW is not a supported width, the instruction encoding is reserved."
            )
            print(f"  [FILLED] row {i}: {name}")

    # ========== STEP 4: Convert 4 non-cp_ rows to proper entries ==========
    for i, row in enumerate(rows):
        name = get_name(row)

        if name == "csrops_reserved_vcsrs":
            set_name(row, "cp_ssstrictv_reserved_vcsrs")
            row["Goal"] = "Confirm CSR addresses 0x00B-0x00E raise illegal instruction exceptions"
            row["Feature Description"] = (
                "Attempt to read/write CSR addresses 0x00B, 0x00C, 0x00D, 0x00E (reserved for future vector CSRs) and confirm each raises an illegal instruction trap"
            )
            row["Expectation"] = "trap"
            row["Bins"] = "4 CSR address bins"
            print(f"  [RENAMED] row {i}: csrops_reserved_vcsrs → cp_ssstrictv_reserved_vcsrs")

        elif name == "vset_i_vl_i_reserved_vsew":
            set_name(row, "cp_ssstrictv_vsetvli_reserved_vsew")
            row["Goal"] = "Confirm vsetvli/vsetivli with vsew[2:0] = 1xx sets vill"
            row["Feature Description"] = (
                "Run vsetvli or vsetivli with vsew field set to 3'b100, 3'b101, 3'b110, 3'b111 (reserved encodings) and verify vill is set to 1"
            )
            row["Expectation"] = "vill set"
            row["Bins"] = "4 vsew bins"
            print(f"  [RENAMED] row {i}: vset_i_vl_i_reserved_vsew → cp_ssstrictv_vsetvli_reserved_vsew")

        elif name == "lmul_vset_i_vl_i":
            set_name(row, "cp_ssstrictv_vsetvli_lmul_sew_ratio")
            row["Goal"] = "Confirm vsetvli with unsupported LMUL/SEW ratio sets vill"
            row["Feature Description"] = (
                "Run vsetvli with LMUL and SEW combinations where LMUL < minSEW/ELEN (the ratio is unsupported), and verify vill is set"
            )
            row["Expectation"] = "vill set"
            row["Bins"] = "Cross of all LMUL x SEW combinations"
            print(f"  [RENAMED] row {i}: lmul_vset_i_vl_i → cp_ssstrictv_vsetvli_lmul_sew_ratio")

        elif name == "vector_load_mew_set":
            set_name(row, "cp_ssstrictv_ls_mew_reserved")
            row["Goal"] = "Confirm vector load/store instructions trap when mew bit is set"
            row["Feature Description"] = (
                "Run a vector load or store instruction with mew=1 (bit 28 of instruction) and confirm the encoding is reserved"
            )
            row["Expectation"] = "trap"
            row["Bins"] = "1 bin"
            print(f"  [RENAMED] row {i}: vector_load_mew_set → cp_ssstrictv_ls_mew_reserved")

    # ========== STEP 5: Delete covered/empty/noise rows ==========
    # Identify rows to delete by content

    # Names of rows to delete (already covered or noise)
    delete_names = {
        "cp_ssstrictv_emul_gt1_reg_align",  # line 133 - cross-reference to existing
        "lmul2_(vd,vs1,vs2)_off_group",  # line 134
        "lmul4_(vd,vs1,vs2)_off_group",  # line 135
        "lmul8_(vd,vs1,vs2)_off_group",  # line 136
        "vsetvl_i_x0_x0_vlmax_change",  # line 144
        "vsetvl_i_x0_x0_vill_set",  # line 145
        "vector_load_emul_16",  # line 146
        "vector_load_emul_(2,4,8)_vd_off_group",  # line 147
        "cr_vector_load_sew_lmul_nfields",  # line 148
    }

    # Comment/question text patterns
    comment_patterns = [
        "Should this be cominued",
        "Should there be an extensive test",
    ]

    # Spec-only text snippets (rows with just spec text, already covered)
    covered_spec_snippets = [
        "The destination vector register group for a masked vector instruction cannot overlap the source mask register",
        "If the vector register numbers accessed by the segment load",
        "Whole register loads/stores (nf): The encoded number",
        "All vector floating-point operations use the dynamic rounding mode",
        "Vector instructions where any floating-point vector operand's EEW",
        "vadc/vsbc: Encodings corresponding to the unmasked",
        "Vector integer move vmv: The first operand specifier",
        "If the EEW of a vector floating-point operand does not correspond",
        "Vector floating point move: The instruction must have the vs2 field",
        "Vector mask logical instructions are always unmasked",
        "vid.v: The vs2 field of the instruction must be set to v0",
        "The encodings corresponding to the masked versions (vm=0) of vmv.x.s",
        "The encodings corresponding to the masked versions (vm=0) of vfmv.f.s",
        "The destination vector register group for vslideup cannot overlap",
        "For any vrgather instruction, the destination vector register group cannot overlap",
        "The destination vector register group cannot overlap the source vector register group or the source mask register",
        "Whole register move: The value of NREG must be",
        "Whole register move: The source and destination vector register numbers",
        "vcsr top Xlen-3 bits are reserved",
        "Reserved when accessing off group vector elements",
        "run all widening instructions with lmul = 8",
        "The vslide1up instruction requires",
        "What to do when running a load store with an sew",
    ]

    delete_indices = set(dup_indices)

    for i, row in enumerate(rows):
        name = get_name(row)
        desc = get_desc(row)
        goal = get_goal(row)
        spec = get_spec(row)
        expectation = get_expectation(row)

        # Delete by name
        if name in delete_names:
            delete_indices.add(i)
            print(f"  [DELETE name] row {i}: {name}")
            continue

        # Delete row where name = cp_ssstrictv_emul_gt1_reg_align and goal starts with "Covered by"
        if name == "cp_ssstrictv_emul_gt1_reg_align" and goal.startswith("Covered by"):
            delete_indices.add(i)
            print(f"  [DELETE covered] row {i}: {name} (cross-ref)")
            continue

        # Delete empty rows
        if is_empty_row(row):
            delete_indices.add(i)
            print(f"  [DELETE empty] row {i}")
            continue

        # Delete comment/question rows
        if not name.startswith("cp_"):
            for pattern in comment_patterns:
                if pattern in name or pattern in desc or pattern in goal:
                    delete_indices.add(i)
                    print(f"  [DELETE comment] row {i}: {name[:50]}")
                    break

        # Delete spec-only rows (no cp_ name, content is just spec text in any column)
        if not name.startswith("cp_") and not goal:
            # Gather all text from all columns
            all_text = " ".join((v or "") for k, v in row.items() if k is not None)
            for snippet in covered_spec_snippets:
                if snippet in all_text:
                    delete_indices.add(i)
                    print(f"  [DELETE spec-only] row {i}: {all_text[:60]}...")
                    break

    # ========== Apply deletions ==========
    kept_rows = [row for i, row in enumerate(rows) if i not in delete_indices]
    deleted_count = len(rows) - len(kept_rows)
    print(f"\nDeleted {deleted_count} rows, keeping {len(kept_rows)}")

    # ========== Write back ==========
    # Filter out None key from headers and rows (caused by trailing commas)
    clean_headers = [h for h in headers if h is not None]
    for row in kept_rows:
        if None in row:
            del row[None]
    # Write to temp file first to avoid truncation on error
    tmp_path = CSV_PATH.with_suffix(".csv.tmp")
    with tmp_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=clean_headers)
        writer.writeheader()
        writer.writerows(kept_rows)
    tmp_path.replace(CSV_PATH)

    print(f"Written cleaned CSV to {CSV_PATH}")

    # ========== Summary ==========
    cp_count = sum(1 for r in kept_rows if get_name(r).startswith("cp_"))
    section_count = sum(1 for r in kept_rows if get_name(r) and not get_name(r).startswith("cp_"))
    print("\nFinal stats:")
    print(f"  cp_ entries: {cp_count}")
    print(f"  Section headers/other named: {section_count}")
    print(f"  Total rows: {len(kept_rows)}")


if __name__ == "__main__":
    main()
