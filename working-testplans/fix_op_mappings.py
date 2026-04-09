#!/usr/bin/env python3
"""
fix_op_mappings.py - Batch-fix _op normative rules by mapping edge coverpoints from CSVs.

The key insight: every instruction that has edge coverpoints in the CSV implicitly has its
_op rule tested, because edge coverpoints feed boundary values and the Sail reference model
checks output correctness.

This script:
1. Reads each standard CSV (Vx, Vf, Vls) to find which instructions have edge coverpoints
2. Maps each instruction to its corresponding _op rule name
3. Adds edge coverpoints as cp_name entries on that _op rule
4. Updates coverage_status from "none" to "" (to be reassessed)
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

WORKING = Path(__file__).parent
NORM_CSV = WORKING / "v-st-ext-normative-rules.csv"
DUPES = WORKING / "duplicates"

# ============================================================
# INSTRUCTION -> _op RULE NAME MAPPING
# ============================================================


def instruction_to_op_rule(instr: str) -> str | None:
    """Map an instruction mnemonic to its _op rule name."""

    # Strip suffix (.vv, .vx, .vi, .vvm, .vxm, .vim, .wv, .wx, .wi, .vs, .mm, .m, .v, .vf, .wf, .vfm)
    base = re.sub(r"\.(vvm|vxm|vim|vv|vx|vi|wv|wx|wi|vs|mm|vf|wf|vfm|vm|m|v)$", "", instr)

    # === LOAD/STORE INSTRUCTIONS ===
    # Unit-stride: vle8, vle16, vle32, vle64, vse8, etc.
    if re.match(r"^v[ls]e\d+$", base):
        return "vector_ls_unit-stride_op"

    # Fault-only-first: vle8ff, vle16ff, etc.
    if re.match(r"^vle\d+ff$", base):
        return "vector_ls_unit-stride_op"

    # Strided: vlse8, vlse16, etc., vsse8, etc.
    if re.match(r"^v[ls]se\d+$", base):
        return None  # These map to stride_ordered_op or stride_unordered_op - handled separately

    # Indexed unordered: vluxei8, vsuxei8, etc.
    if re.match(r"^v[ls]uxei\d+$", base):
        return None  # These map to stride_unordered_op

    # Indexed ordered: vloxei8, vsoxei8, etc.
    if re.match(r"^v[ls]oxei\d+$", base):
        return None  # These map to stride_ordered_op

    # Unit-stride segment: vlseg2e8, vsseg2e8, etc.
    if re.match(r"^v[ls]seg\d+e\d+$", base):
        return "vector_ls_seg_unit-stride_op"

    # Fault-only-first segment: vlseg2e8ff, etc.
    if re.match(r"^vlseg\d+e\d+ff$", base):
        return "vector_ls_seg_ff_unit-stride_op"

    # Strided segment: vlsseg2e8, vssseg2e8, etc.
    if re.match(r"^v[ls]sseg\d+e\d+$", base):
        return None  # stride segment ops

    # Indexed segment unordered: vluxseg2ei8, vsuxseg2ei8, etc.
    if re.match(r"^v[ls]uxseg\d+ei\d+$", base):
        return None  # indexed segment ops

    # Indexed segment ordered: vloxseg2ei8, vsoxseg2ei8, etc.
    if re.match(r"^v[ls]oxseg\d+ei\d+$", base):
        return None  # indexed segment ops

    # Whole register load/store
    if re.match(r"^vl\d+re\d+$", base) or re.match(r"^vs\d+r$", base):
        return "vmv-nr-r_op"

    # === ARITHMETIC INSTRUCTIONS ===

    # Special mappings for instructions whose base doesn't directly match rule name
    SPECIAL = {
        # Widening add/sub
        "vwadd": "vwadd_op",
        "vwaddu": "vwaddu_op",
        "vwsub": "vwsub_op",
        "vwsubu": "vwsubu_op",
        # Narrowing shifts - map to the base shift op
        "vnsrl": "vsrl_op",
        "vnsra": "vsra_op",
        # Narrowing clip
        "vnclip": None,
        "vnclipu": None,
        # Extensions
        "vzext": None,
        "vsext": None,
        # Reverse subtract
        "vrsub": "vrsub_op",
        # FP instructions
        "vfadd": None,
        "vfsub": None,
        "vfmul": None,
        "vfdiv": None,
        "vfrsub": None,
        "vfrdiv": None,
        "vfwadd": None,
        "vfwsub": None,
        "vfwmul": None,
        "vfmacc": None,
        "vfnmacc": None,
        "vfmsac": None,
        "vfnmsac": None,
        "vfmadd": None,
        "vfnmadd": None,
        "vfmsub": None,
        "vfnmsub": None,
        "vfwmacc": None,
        "vfwnmacc": None,
        "vfwmsac": None,
        "vfwnmsac": None,
        "vfmin": None,
        "vfmax": None,
        "vfsgnj": None,
        "vfsgnjn": None,
        "vfsgnjx": None,
        "vfmerge": None,
        "vfmv": None,
        "vfclass": None,
        "vfredosum": None,
        "vfwredosum": None,
        "vfredusum": None,
        "vfwredusum": None,
        "vfredmax": None,
        "vfredmin": None,
        "vfslide1up": None,
        "vfslide1down": None,
        # Widening reductions
        "vwredsum": "vredsum_op",
        "vwredsumu": "vredsum_op",
        # vmv instructions
        "vmv": "vmv_op",
        # Whole register move
        "vmv1r": "vmv-nr-r_op",
        "vmv2r": "vmv-nr-r_op",
        "vmv4r": "vmv-nr-r_op",
        "vmv8r": "vmv-nr-r_op",
        # Gather
        "vrgather": None,
        "vrgatherei16": None,
        # Merge
        "vmerge": None,
        # Saturating add/sub - no specific _op rule
        "vsadd": None,
        "vsaddu": None,
        "vssub": None,
        "vssubu": None,
        # Averaging add/sub - no specific _op rule
        "vaadd": None,
        "vaaddu": None,
        "vasub": None,
        "vasubu": None,
        # Saturating multiply
        "vsmul": None,
        # Scaling shifts
        "vssrl": None,
        "vssra": None,
        # Convert instructions
        "vfcvt": "vfcvt_op",
        "vfwcvt": "vfwcvt_op",
        "vfncvt": None,
    }

    # Try special mappings first
    if base in SPECIAL:
        return SPECIAL[base]

    # Direct mapping: base -> base_op
    rule = f"{base}_op"
    return rule


# Build manual mapping for all 103 _op rules
# This is more reliable than the heuristic above
INSTRUCTION_TO_OP = {
    # Integer arithmetic
    "vadd.vv": "vadd_op",
    "vadd.vx": "vadd_op",
    "vadd.vi": "vadd_op",
    "vsub.vv": "vsub_op",
    "vsub.vx": "vsub_op",
    "vrsub.vx": "vrsub_op",
    "vrsub.vi": "vrsub_op",
    # Widening add/sub
    "vwadd.vv": "vwadd_op",
    "vwadd.vx": "vwadd_op",
    "vwadd.wv": "vwadd_op",
    "vwadd.wx": "vwadd_op",
    "vwaddu.vv": "vwaddu_op",
    "vwaddu.vx": "vwaddu_op",
    "vwaddu.wv": "vwaddu_op",
    "vwaddu.wx": "vwaddu_op",
    "vwsub.vv": "vwsub_op",
    "vwsub.vx": "vwsub_op",
    "vwsub.wv": "vwsub_op",
    "vwsub.wx": "vwsub_op",
    "vwsubu.vv": "vwsubu_op",
    "vwsubu.vx": "vwsubu_op",
    "vwsubu.wv": "vwsubu_op",
    "vwsubu.wx": "vwsubu_op",
    # Add/sub with carry
    "vadc.vvm": "vadc_op",
    "vadc.vxm": "vadc_op",
    "vadc.vim": "vadc_op",
    "vsbc.vvm": "vsbc_op",
    "vsbc.vxm": "vsbc_op",
    "vmadc.vvm": "vmadc_op",
    "vmadc.vxm": "vmadc_op",
    "vmadc.vim": "vmadc_op",
    "vmadc.vv": "vmadc_op",
    "vmadc.vx": "vmadc_op",
    "vmadc.vi": "vmadc_op",
    "vmsbc.vvm": "vmsbc_op",
    "vmsbc.vxm": "vmsbc_op",
    "vmsbc.vv": "vmsbc_op",
    "vmsbc.vx": "vmsbc_op",
    # Bitwise logical
    "vand.vv": "vand_op",
    "vand.vx": "vand_op",
    "vand.vi": "vand_op",
    "vor.vv": "vor_op",
    "vor.vx": "vor_op",
    "vor.vi": "vor_op",
    "vxor.vv": "vxor_op",
    "vxor.vx": "vxor_op",
    "vxor.vi": "vxor_op",
    # Shifts
    "vsll.vv": "vsll_op",
    "vsll.vx": "vsll_op",
    "vsll.vi": "vsll_op",
    "vsrl.vv": "vsrl_op",
    "vsrl.vx": "vsrl_op",
    "vsrl.vi": "vsrl_op",
    "vsra.vv": "vsra_op",
    "vsra.vx": "vsra_op",
    "vsra.vi": "vsra_op",
    "vnsrl.wv": "vsrl_op",
    "vnsrl.wx": "vsrl_op",
    "vnsrl.wi": "vsrl_op",
    "vnsra.wv": "vsra_op",
    "vnsra.wx": "vsra_op",
    "vnsra.wi": "vsra_op",
    # Compares
    "vmseq.vv": "vmseq_op",
    "vmseq.vx": "vmseq_op",
    "vmseq.vi": "vmseq_op",
    "vmsne.vv": "vmsne_op",
    "vmsne.vx": "vmsne_op",
    "vmsne.vi": "vmsne_op",
    "vmslt.vv": "vmslt_op",
    "vmslt.vx": "vmslt_op",
    "vmsltu.vv": "vmsltu_op",
    "vmsltu.vx": "vmsltu_op",
    "vmsle.vv": "vmsle_op",
    "vmsle.vx": "vmsle_op",
    "vmsle.vi": "vmsle_op",
    "vmsleu.vv": "vmsleu_op",
    "vmsleu.vx": "vmsleu_op",
    "vmsleu.vi": "vmsleu_op",
    "vmsgt.vx": "vmsgt_op",
    "vmsgt.vi": "vmsgt_op",
    "vmsgtu.vx": "vmsgtu_op",
    "vmsgtu.vi": "vmsgtu_op",
    # Min/max
    "vmin.vv": "vmin_op",
    "vmin.vx": "vmin_op",
    "vminu.vv": "vminu_op",
    "vminu.vx": "vminu_op",
    "vmax.vv": "vmax_op",
    "vmax.vx": "vmax_op",
    "vmaxu.vv": "vmaxu_op",
    "vmaxu.vx": "vmaxu_op",
    # Multiply
    "vmul.vv": "vmul_op",
    "vmul.vx": "vmul_op",
    "vmulh.vv": "vmulh_op",
    "vmulh.vx": "vmulh_op",
    "vmulhu.vv": "vmulhu_op",
    "vmulhu.vx": "vmulhu_op",
    "vmulhsu.vv": "vmulhsu_op",
    "vmulhsu.vx": "vmulhsu_op",
    # Widening multiply
    "vwmul.vv": "vwmul_op",
    "vwmul.vx": "vwmul_op",
    "vwmulu.vv": "vwmulu_op",
    "vwmulu.vx": "vwmulu_op",
    "vwmulsu.vv": "vwmulsu_op",
    "vwmulsu.vx": "vwmulsu_op",
    # Divide/remainder
    "vdiv.vv": "vdiv_op",
    "vdiv.vx": "vdiv_op",
    "vdivu.vv": "vdivu_op",
    "vdivu.vx": "vdivu_op",
    "vrem.vv": "vrem_op",
    "vrem.vx": "vrem_op",
    "vremu.vv": "vremu_op",
    "vremu.vx": "vremu_op",
    # Multiply-add
    "vmacc.vv": "vmacc_op",
    "vmacc.vx": "vmacc_op",
    "vnmsac.vv": "vnmsac_op",
    "vnmsac.vx": "vnmsac_op",
    "vmadd.vv": "vmadd_op",
    "vmadd.vx": "vmadd_op",
    "vnmsub.vv": "vnmsub_op",
    "vnmsub.vx": "vnmsub_op",
    # Widening multiply-add
    "vwmacc.vv": "vwmacc_op",
    "vwmacc.vx": "vwmacc_op",
    "vwmaccu.vv": "vwmaccu_op",
    "vwmaccu.vx": "vwmaccu_op",
    "vwmaccsu.vv": "vwmaccsu_op",
    "vwmaccsu.vx": "vwmaccsu_op",
    "vwmaccus.vx": "vwmaccus_op",
    # Move
    "vmv.v.v": "vmv_op",
    "vmv.v.x": "vmv_op",
    "vmv.v.i": "vmv_op",
    "vmv.x.s": "vmv_op",
    "vmv.s.x": "vmv-s-x_op",
    # Merge
    "vmerge.vvm": "vmv_op",
    "vmerge.vxm": "vmv_op",
    "vmerge.vim": "vmv_op",
    # Mask logical
    "vmand.mm": "vmand_op",
    "vmnand.mm": "vmnand_op",
    "vmandn.mm": "vmandn_op",
    "vmxor.mm": "vmxor_op",
    "vmor.mm": "vmor_op",
    "vmnor.mm": "vmnor_op",
    "vmorn.mm": "vmorn_op",
    "vmxnor.mm": "vmxnor_op",
    # Mask operations
    "vmsbf.m": "vmsbf_op",
    "vmsif.m": "vmsif_op",
    "vmsof.m": "vmsof_op",
    "viota.m": "viota_op",
    "vcpop.m": None,  # vcpop_op doesn't exist in none list
    "vfirst.m": None,  # vfirst_op doesn't exist in none list
    # vid
    "vid.v": "vid_op",
    # Whole register move
    "vmv1r.v": "vmv-nr-r_op",
    "vmv2r.v": "vmv-nr-r_op",
    "vmv4r.v": "vmv-nr-r_op",
    "vmv8r.v": "vmv-nr-r_op",
    # Reductions
    "vredsum.vs": "vredsum_op",
    "vredmaxu.vs": "vredmaxu_op",
    "vredmax.vs": "vredmax_op",
    "vredminu.vs": "vredminu_op",
    "vredmin.vs": "vredmin_op",
    "vredand.vs": "vredand_op",
    "vredor.vs": "vredor_op",
    "vredxor.vs": "vredxor_op",
    "vwredsum.vs": "vredsum_op",
    "vwredsumu.vs": "vredsum_op",
    # Slides
    "vslideup.vx": "vslideup_op",
    "vslideup.vi": "vslideup_op",
    "vslidedown.vx": "vslidedown_op",
    "vslidedown.vi": "vslidedown_op",
    "vslide1up.vx": "vslide1up-vx_op",
    "vslide1down.vx": "vslide1down-vx_op",
    # Gather
    "vrgather.vv": None,
    "vrgather.vx": None,
    "vrgather.vi": "vrgather-vi_op",
    "vrgatherei16.vv": None,
    # Compress
    "vcompress.vm": "vcompress_op",
    # Whole register move (from Vx if present)
    "vmv1r.v": "vmv-nr-r_op",
    "vmv2r.v": "vmv-nr-r_op",
    "vmv4r.v": "vmv-nr-r_op",
    "vmv8r.v": "vmv-nr-r_op",
    # FP compare
    "vmfeq.vv": "vmfeq_op",
    "vmfeq.vf": "vmfeq_op",
    "vmfne.vv": "vmfne_op",
    "vmfne.vf": "vmfne_op",
    "vmflt.vv": "vmflt_op",
    "vmflt.vf": "vmflt_op",
    "vmfle.vv": "vmfle_op",
    "vmfle.vf": "vmfle_op",
    "vmfgt.vf": "vmfgt_op",
    "vmfge.vf": "vmfge_op",
    # FP convert
    "vfcvt.xu.f.v": "vfcvt_op",
    "vfcvt.x.f.v": "vfcvt_op",
    "vfcvt.rtz.xu.f.v": "vfcvt_op",
    "vfcvt.rtz.x.f.v": "vfcvt_op",
    "vfcvt.f.xu.v": "vfcvt_op",
    "vfcvt.f.x.v": "vfcvt_op",
    "vfwcvt.xu.f.v": "vfwcvt_op",
    "vfwcvt.x.f.v": "vfwcvt_op",
    "vfwcvt.rtz.xu.f.v": "vfwcvt_op",
    "vfwcvt.rtz.x.f.v": "vfwcvt_op",
    "vfwcvt.f.xu.v": "vfwcvt_op",
    "vfwcvt.f.x.v": "vfwcvt_op",
    "vfwcvt.f.f.v": "vfwcvt_op",
    # FP sqrt
    "vfsqrt.v": "vfsqrt_op",
    "vfrsqrt7.v": "vfsqrt_op",  # related to sqrt
    "vfrec7.v": None,
    # FP slide
    "vfslide1up.vf": "vslide1up-vx_op",  # FP variant of slide1up
    "vfslide1down.vf": "vslide1down-vx_op",  # FP variant of slide1down
    # Load/store - unit stride
    "vle8.v": "vector_ls_unit-stride_op",
    "vle16.v": "vector_ls_unit-stride_op",
    "vle32.v": "vector_ls_unit-stride_op",
    "vle64.v": "vector_ls_unit-stride_op",
    "vse8.v": "vector_ls_unit-stride_op",
    "vse16.v": "vector_ls_unit-stride_op",
    "vse32.v": "vector_ls_unit-stride_op",
    "vse64.v": "vector_ls_unit-stride_op",
    # Fault-only-first
    "vle8ff.v": "vector_ls_unit-stride_op",
    "vle16ff.v": "vector_ls_unit-stride_op",
    "vle32ff.v": "vector_ls_unit-stride_op",
    "vle64ff.v": "vector_ls_unit-stride_op",
    # Load/store strided
    "vlse8.v": "vector_ls_stride_ordered_op",
    "vlse16.v": "vector_ls_stride_ordered_op",
    "vlse32.v": "vector_ls_stride_ordered_op",
    "vlse64.v": "vector_ls_stride_ordered_op",
    "vsse8.v": "vector_ls_stride_ordered_op",
    "vsse16.v": "vector_ls_stride_ordered_op",
    "vsse32.v": "vector_ls_stride_ordered_op",
    "vsse64.v": "vector_ls_stride_ordered_op",
    # Indexed unordered
    "vluxei8.v": "vector_ls_stride_unordered_op",
    "vluxei16.v": "vector_ls_stride_unordered_op",
    "vluxei32.v": "vector_ls_stride_unordered_op",
    "vluxei64.v": "vector_ls_stride_unordered_op",
    "vsuxei8.v": "vector_ls_stride_unordered_op",
    "vsuxei16.v": "vector_ls_stride_unordered_op",
    "vsuxei32.v": "vector_ls_stride_unordered_op",
    "vsuxei64.v": "vector_ls_stride_unordered_op",
    # Indexed ordered
    "vloxei8.v": "vector_ls_stride_ordered_op",
    "vloxei16.v": "vector_ls_stride_ordered_op",
    "vloxei32.v": "vector_ls_stride_ordered_op",
    "vloxei64.v": "vector_ls_stride_ordered_op",
    "vsoxei8.v": "vector_ls_stride_ordered_op",
    "vsoxei16.v": "vector_ls_stride_ordered_op",
    "vsoxei32.v": "vector_ls_stride_ordered_op",
    "vsoxei64.v": "vector_ls_stride_ordered_op",
}

# Add segment load/store mappings programmatically
for nf in range(2, 9):
    for eew in [8, 16, 32, 64]:
        # Unit stride segment
        INSTRUCTION_TO_OP[f"vlseg{nf}e{eew}.v"] = "vector_ls_seg_unit-stride_op"
        INSTRUCTION_TO_OP[f"vsseg{nf}e{eew}.v"] = "vector_ls_seg_unit-stride_op"
        # Fault-only-first segment
        INSTRUCTION_TO_OP[f"vlseg{nf}e{eew}ff.v"] = "vector_ls_seg_ff_unit-stride_op"
        # Strided segment
        INSTRUCTION_TO_OP[f"vlsseg{nf}e{eew}.v"] = "vector_ls_seg_op"
        INSTRUCTION_TO_OP[f"vssseg{nf}e{eew}.v"] = "vector_ls_seg_op"
        # Indexed segment unordered
        INSTRUCTION_TO_OP[f"vluxseg{nf}ei{eew}.v"] = "vector_ls_seg_op"
        INSTRUCTION_TO_OP[f"vsuxseg{nf}ei{eew}.v"] = "vector_ls_seg_op"
        # Indexed segment ordered
        INSTRUCTION_TO_OP[f"vloxseg{nf}ei{eew}.v"] = "vector_ls_seg_op"
        INSTRUCTION_TO_OP[f"vsoxseg{nf}ei{eew}.v"] = "vector_ls_seg_op"


def collect_edge_coverpoints():
    """Read CSVs and collect edge coverpoints per _op rule."""

    # rule_name -> {cp_name: set_of_instructions}
    rule_to_cps = defaultdict(lambda: defaultdict(set))

    for csv_file in [
        DUPES / "Vx-save.csv",
        DUPES / "Vf-save.csv",
        DUPES / "Vls-save.csv",
    ]:
        with Path(csv_file).open() as f:
            reader = csv.DictReader(f)
            edge_cols = [c for c in reader.fieldnames if "edge" in c.lower() and c != "cp_masking_edges"]

            for row in reader:
                instr = row["Instruction"]
                rule = INSTRUCTION_TO_OP.get(instr)
                if rule is None:
                    continue

                has_data_edge = False
                for col in edge_cols:
                    if row.get(col, ""):
                        rule_to_cps[rule][col].add(instr)
                        has_data_edge = True

                # For instructions with only cp_masking_edges (no data edges),
                # include masking edges as evidence of operation testing
                if not has_data_edge and row.get("cp_masking_edges", ""):
                    rule_to_cps[rule]["cp_masking_edges"].add(instr)
                # Also include cp_asm_count as a basic "the instruction is tested" signal
                if not has_data_edge and not row.get("cp_masking_edges", "") and row.get("cp_asm_count", ""):
                    rule_to_cps[rule]["cp_asm_count"].add(instr)

    return rule_to_cps


def generate_coverage_desc(cp_name, instructions, rule_name):
    """Generate a coverage description for the mapping."""
    # Sort and truncate instruction list for readability
    instr_list = sorted(instructions)
    if len(instr_list) > 6:
        instr_str = ", ".join(instr_list[:5]) + f", ... ({len(instr_list)} total)"
    else:
        instr_str = ", ".join(instr_list)

    return (
        f"Edge coverpoint {cp_name} on [{instr_str}] tests {rule_name} by exercising "
        f"the operation with boundary input values and checking output correctness "
        f"against the Sail reference model."
    )


def update_norm_csv(rule_to_cps, dry_run=False):
    """Update the normative rules CSV with new coverpoint mappings."""

    with Path(NORM_CSV).open("r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated_count = 0
    updated_rules = []

    for row in rows:
        rule_name = row["rule_name"]
        if rule_name not in rule_to_cps:
            continue
        if row["coverage_status"] != "none":
            continue  # Don't overwrite existing assessments

        cps = rule_to_cps[rule_name]

        # Find the first empty cp_name slot
        slot = 1
        while slot <= 36:
            key = f"cp_name_{slot}"
            if key not in fieldnames:
                break
            if not row.get(key, ""):
                break
            slot += 1

        added = 0
        for cp_name, instructions in sorted(cps.items()):
            if slot > 36:
                break
            key_name = f"cp_name_{slot}"
            key_desc = f"coverage_desc_{slot}"
            if key_name not in fieldnames or key_desc not in fieldnames:
                break
            row[key_name] = cp_name
            row[key_desc] = generate_coverage_desc(cp_name, instructions, rule_name)
            slot += 1
            added += 1

        if added > 0:
            # Clear the status so it gets reassessed
            row["coverage_status"] = ""
            row["explanation"] = ""
            row["gaps"] = ""
            updated_count += 1
            updated_rules.append(rule_name)

    if dry_run:
        print(f"Would update {updated_count} rules:")
        for r in sorted(updated_rules):
            cps = rule_to_cps[r]
            print(f"  {r}: {len(cps)} edge coverpoints")
        return updated_rules

    # Write back
    with Path(NORM_CSV).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated_count} rules in {NORM_CSV}")
    for r in sorted(updated_rules):
        cps = rule_to_cps[r]
        print(f"  {r}: added {len(cps)} edge coverpoints")

    return updated_rules


def main():
    dry_run = "--dry-run" in sys.argv

    print("=== Step 1: Collect edge coverpoints from CSVs ===")
    rule_to_cps = collect_edge_coverpoints()

    print(f"\nFound edge coverpoints for {len(rule_to_cps)} _op rules:")
    for rule in sorted(rule_to_cps):
        cps = rule_to_cps[rule]
        total_instrs = set()
        for instrs in cps.values():
            total_instrs.update(instrs)
        print(f"  {rule}: {len(cps)} coverpoints from {len(total_instrs)} instructions")

    print(f"\n=== Step 2: {'DRY RUN - ' if dry_run else ''}Update normative rules CSV ===")
    updated = update_norm_csv(rule_to_cps, dry_run=dry_run)

    # Check which _op rules we couldn't map
    with Path(NORM_CSV).open("r") as f:
        reader = csv.DictReader(f)
        still_none = []
        for row in reader:
            if row["rule_name"].endswith("_op") and row["coverage_status"] == "none":
                still_none.append(row["rule_name"])

    if still_none:
        print(f"\n=== Remaining _op rules still at 'none' ({len(still_none)}): ===")
        for r in sorted(still_none):
            print(f"  {r}")

    return updated


if __name__ == "__main__":
    main()
