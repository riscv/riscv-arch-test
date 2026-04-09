#!/usr/bin/env python3
"""
triage_none_rules.py - Categorize remaining 'none' rules and update them.

Categories:
- "privileged_only": Requires privileged test infrastructure (mstatus, sstatus, vsstatus, misa)
- "architectural_definition": Defines a concept/structure, not directly testable behavior
- "needs_new_coverpoint": Testable behavior that needs a new coverpoint
- "covered_by_implication": Inherently tested by existing coverpoints/infrastructure
- "implementation_defined": Implementation-specific behavior, not mandated
"""

from __future__ import annotations

import csv
from pathlib import Path

NORM_CSV = Path(__file__).parent / "v-st-ext-normative-rules.csv"

# ============================================================
# CATEGORIZATION RULES
# ============================================================

CATEGORIZATION = {
    # === PRIVILEGED/CSR (need privileged test infra) ===
    "sstatus-vs_op": (
        "privileged_only",
        "Requires privileged mode testing to verify sstatus.VS field shadowing behavior",
    ),
    "vsstatus-vs_op2": ("privileged_only", "Missing normative text; requires privileged mode testing"),
    "vsstatus-sd_op_vs": (
        "privileged_only",
        "Requires privileged mode testing to verify vsstatus.SD reflects VS dirty state",
    ),
    "mstatus-sd_op": (
        "privileged_only",
        "Requires privileged mode testing to verify mstatus.SD reflects VS dirty state",
    ),
    "mstatus-sd_op_vs": (
        "privileged_only",
        "Requires privileged mode testing to verify mstatus.SD reflects VS dirty state",
    ),
    "HW_MSTATUS_VS_DIRTY_UPDATE": (
        "implementation_defined",
        "Implementation MAY update VS to Dirty at any time; not testable as a requirement",
    ),
    "MUTABLE_MISA_V": ("implementation_defined", "Implementation MAY have writable misa.V; not universally required"),
    "MSTATUS_VS_EXISTS": (
        "privileged_only",
        "Requires privileged mode testing of mstatus.VS field existence when misa.V is clear",
    ),
    "VSSTATUS_VS_EXISTS": ("privileged_only", "Requires privileged mode testing with hypervisor extension"),
    "misa-V_op": ("privileged_only", "Requires privileged mode testing to read misa.V bit"),
    "vsstatus-FS_dirty_hypervisor_V_fp": (
        "privileged_only",
        "Requires hypervisor V=1 mode testing to verify FS dirty behavior",
    ),
    "mstatus-FS_dirty_hypervisor_V_fp": (
        "privileged_only",
        "Requires hypervisor V=1 mode testing to verify FS dirty behavior",
    ),
    # === ARCHITECTURAL DEFINITIONS (not directly testable) ===
    "VLEN": (
        "architectural_definition",
        "VLEN is a fixed architectural parameter; its value is tested implicitly by every vector instruction",
    ),
    "VILL_IMPLICIT_ENCODING": (
        "architectural_definition",
        "Describes internal encoding optimization; not externally observable behavior",
    ),
    "VECTOR_LS_WHOLEREG_MISSALIGNED_EXCEPTION": (
        "implementation_defined",
        "Implementation is ALLOWED to raise misaligned exception; permissive rule",
    ),
    "VECTOR_LS_MISSALIGNED_EXCEPTION": (
        "implementation_defined",
        "Implementation choice between handling misaligned or raising exception",
    ),
    "VECTOR_LS_SEG_PARTIAL_ACCESS": (
        "implementation_defined",
        "Implementation-defined whether partial segment accesses occur before trap",
    ),
    "VECTOR_FF_SEG_PARTIAL_ACCESS": (
        "implementation_defined",
        "Implementation-defined whether partial segment is loaded",
    ),
    "VECTOR_LS_SEG_FF_OVERLOAD": (
        "implementation_defined",
        "Implementation may overwrite past trap/trim point; permissive rule",
    ),
    "VECTOR_FF_PAST_TRAP": (
        "implementation_defined",
        "Implementation may update elements past fault-only-first trim point; permissive rule",
    ),
    "vmv-nr-r_enc": (
        "architectural_definition",
        "Encoding format definition; tested implicitly by assembler when encoding vmv<nr>r.v",
    ),
    # === Zve* / V EXTENSION DEPENDENCY DEFINITIONS ===
    "Zve_XLEN": (
        "architectural_definition",
        "Extension compatibility statement; tested by using appropriate XLEN configuration",
    ),
    "Zve32f_Zve64x_dependent_Zve32x": (
        "architectural_definition",
        "Extension dependency hierarchy; verified by configuration",
    ),
    "Zve64f_dependent_Zve32f_Zve64x": (
        "architectural_definition",
        "Extension dependency hierarchy; verified by configuration",
    ),
    "Zve64d_dependent_Zve64f": (
        "architectural_definition",
        "Extension dependency hierarchy; verified by configuration",
    ),
    "Zve32x_dependent_Zicsr": ("architectural_definition", "Extension dependency hierarchy; verified by configuration"),
    "Zve64f_dependent_F": ("architectural_definition", "Extension dependency hierarchy; verified by configuration"),
    "V_dependent_Zvl128b_Zve64d": (
        "architectural_definition",
        "Extension dependency hierarchy; verified by configuration",
    ),
    "Zvfhmin_dependent_Zve32f": (
        "architectural_definition",
        "Extension dependency hierarchy; verified by configuration",
    ),
    "Zvfh_dependent_Zve32f_Zfhmin": (
        "architectural_definition",
        "Extension dependency hierarchy; verified by configuration",
    ),
    # === COVERED BY EXISTING INFRASTRUCTURE ===
    "V_instr": (
        "covered_by_implication",
        "V extension instruction support is tested by all vector instruction coverpoints collectively",
    ),
    "Zvfh_instr": (
        "covered_by_implication",
        "Zvfh instruction support is tested by FP16 vector instruction coverpoints",
    ),
    # === CSR ACCESS/SIZE RULES ===
    "vlenb_op": ("needs_new_coverpoint", "Need coverpoint to read vlenb CSR and verify it equals VLEN/8"),
    "vlenb_acc": ("needs_new_coverpoint", "Need coverpoint to verify vlenb CSR is accessible and readable"),
    "vstart_acc": ("needs_new_coverpoint", "Need coverpoint to verify vstart CSR read/write access"),
    "vstart_sz": ("needs_new_coverpoint", "Need coverpoint to verify vstart is XLEN-bit wide"),
    "vstart_update": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vstart is reset to zero after vector instruction execution",
    ),
    "vstart_unmodified": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vstart is not modified by illegal-instruction-raising vector instructions",
    ),
    "vstart_sz_writable": (
        "needs_new_coverpoint",
        "Need coverpoint to verify only enough bits are writable to hold largest element index",
    ),
    "vxrm_acc": ("needs_new_coverpoint", "Need coverpoint to verify vxrm CSR read/write access"),
    "vxrm_sz": ("needs_new_coverpoint", "Need coverpoint to verify vxrm CSR size and bit layout"),
    "vcsr-vxrm_op": ("needs_new_coverpoint", "Need coverpoint to verify vxrm is reflected in vcsr"),
    "vxsat_sz": ("needs_new_coverpoint", "Need coverpoint to verify vxsat CSR size and bit layout"),
    "vcsr-vxsat_op": ("needs_new_coverpoint", "Need coverpoint to verify vxsat is mirrored in vcsr"),
    "vreg_flmul_op": (
        "needs_new_coverpoint",
        "Need coverpoint to verify fractional LMUL element usage and tail treatment",
    ),
    "vreg_mask_overlap": (
        "covered_by_implication",
        "EEW=1 for mask overlap constraints tested by existing mask register group overlap coverpoints",
    ),
    "vtype-vstart_op": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vl is set to zero when vstart changes via vsetvl",
    ),
    "vsetivli_op": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vsetivli with 5-bit zero-extended immediate AVL encoding",
    ),
    "vtype-vta_val": ("needs_new_coverpoint", "Need coverpoint to verify all four vma/vta combinations are supported"),
    "vreg_mask_tail_agn": (
        "needs_new_coverpoint",
        "Need coverpoint to verify mask destination tail elements use tail-agnostic policy regardless of vta",
    ),
    # === LOAD/STORE BEHAVIOR RULES ===
    "vector_ls_scalar_missaligned_independence": (
        "architectural_definition",
        "Independence statement about misaligned support; not directly testable",
    ),
    "vector_ls_scalar_missaligned_dependence": (
        "needs_new_coverpoint",
        "Need coverpoint to test vector misaligned access atomicity",
    ),
    "vector_ls_seg_indexed_unordered": (
        "covered_by_implication",
        "Tested implicitly by indexed segment load/store tests; ordering is observable only under specific memory conditions",
    ),
    "vector_ls_stride_unordered_precise": (
        "needs_new_coverpoint",
        "Need coverpoint to test precise traps on indexed-unordered stores",
    ),
    "vector_ls_nf_op": ("needs_new_coverpoint", "Need coverpoint to verify nf[2:0] field encoding for segment count"),
    "vector_ls_neg_stride": (
        "needs_new_coverpoint",
        "Need coverpoint to test negative stride values in strided load/store",
    ),
    "vector_ls_zero_stride": (
        "needs_new_coverpoint",
        "Need coverpoint to test zero stride values in strided load/store",
    ),
    "vector_ls_constant-stride_unordered": (
        "covered_by_implication",
        "Element ordering within constant-stride is unordered; not directly testable as a requirement",
    ),
    "vector_ff_no_exception": (
        "needs_new_coverpoint",
        "Need coverpoint to test fault-only-first reducing vl without exception when vstart=0 and vl>0",
    ),
    "vector_ff_interrupt_behavior": (
        "needs_new_coverpoint",
        "Need coverpoint to verify FF load on interrupt sets vstart instead of reducing vl",
    ),
    "vector_ls_seg_unordered": (
        "covered_by_implication",
        "Segment field access ordering is unordered; implicitly tested by segment LS tests",
    ),
    "vector_ls_seg_vstart_dep": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vstart is in units of whole segments",
    ),
    "vector_ls_seg_constant-stride_unordered": (
        "covered_by_implication",
        "Ordering within segments for strided access; implicitly tested",
    ),
    "vector_ls_seg_wholereg_op_cont": (
        "needs_new_coverpoint",
        "Need coverpoint to verify register-to-memory ordering for whole register transfers",
    ),
    "vector_ls_program_order": (
        "covered_by_implication",
        "Program order is maintained by hart execution model; tested by all LS tests",
    ),
    "vector_ls_RVWMO": (
        "covered_by_implication",
        "RVWMO compliance at instruction level; tested by memory ordering tests if present",
    ),
    "vector_ls_indexed-ordered_ordered": (
        "covered_by_implication",
        "Unordered element operations for non-indexed-ordered; implicitly tested",
    ),
    "vector_ls_indexed-ordered_RVWMO": (
        "needs_new_coverpoint",
        "Need coverpoint to test indexed-ordered loads/stores obey RVWMO at element level",
    ),
    "vl_control_dependency": (
        "architectural_definition",
        "Control dependency vs data dependency distinction; affects microarchitecture, not functional correctness",
    ),
    "vector_ls_rvtso": (
        "covered_by_implication",
        "TSO compliance if Ztso implemented; tested by memory model tests if present",
    ),
    # === V_Zfinx ===
    "V_Zfinx_fp_scalar": (
        "needs_new_coverpoint",
        "Need coverpoint to verify FP scalars come from x registers when Zfinx is implemented",
    ),
    # === ADD/SUB WITH CARRY BEHAVIOR ===
    "vadc_masked_write_all_elem": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vadc writes all body elements even though encoded as masked",
    ),
    "vsbc_masked_write_all_elem": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vsbc writes all body elements even though encoded as masked",
    ),
    "vmadc_masked_write_all_elem": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmadc writes all body elements even if masked",
    ),
    "vmsbc_masked_write_all_elem": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsbc writes all body elements even if masked",
    ),
    "vmadc_tail_agnostic": ("needs_new_coverpoint", "Need coverpoint to verify vmadc always uses tail-agnostic policy"),
    "vmsbc_tail_agnostic": ("needs_new_coverpoint", "Need coverpoint to verify vmsbc always uses tail-agnostic policy"),
    "vmsbc_borrow_neg": (
        "covered_by_implication",
        "Borrow semantics tested by cr_vs2_vs1_edges on vmsbc which exercises boundary values",
    ),
    # === COMPARE BEHAVIOR ===
    "vmseq_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmseq AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmsne_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsne AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmsltu_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsltu AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmslt_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmslt AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmsleu_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsleu AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmsle_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsle AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmsgtu_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsgtu AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmsgt_maskundisturbed": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsgt AND-in-mask behavior with vd=v0 under mask-undisturbed",
    ),
    "vmseq_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmsne_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmsltu_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmslt_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmsleu_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmsle_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmsgtu_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    "vmsgt_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for mask-producing compares tested by existing masking infrastructure and Sail comparison",
    ),
    # === MERGE ALL-ELEM ===
    "vmerge_all_elem": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmerge operates on all body elements including inactive ones",
    ),
    "vfmerge_all_elem": ("needs_new_coverpoint", "Need coverpoint to verify vfmerge operates on all body elements"),
    # === FP COMPARE BEHAVIOR ===
    "vmfeq_vd_single_vreg": (
        "covered_by_implication",
        "Destination being single vreg for mask-producing FP compares tested by cp_vd x variant",
    ),
    "vmfne_vd_single_vreg": (
        "covered_by_implication",
        "Destination being single vreg for mask-producing FP compares tested by cp_vd x variant",
    ),
    "vmflt_vd_single_vreg": (
        "covered_by_implication",
        "Destination being single vreg for mask-producing FP compares tested by cp_vd x variant",
    ),
    "vmfle_vd_single_vreg": (
        "covered_by_implication",
        "Destination being single vreg for mask-producing FP compares tested by cp_vd x variant",
    ),
    "vmfgt_vd_single_vreg": (
        "covered_by_implication",
        "Destination being single vreg for mask-producing FP compares tested by cp_vd x variant",
    ),
    "vmfge_vd_single_vreg": (
        "covered_by_implication",
        "Destination being single vreg for mask-producing FP compares tested by cp_vd x variant",
    ),
    "vmfeq_vd_eq_v0": ("needs_new_coverpoint", "Need coverpoint to verify vmfeq with vd=v0 (same as mask register)"),
    "vmfne_vd_eq_v0": ("needs_new_coverpoint", "Need coverpoint to verify vmfne with vd=v0 (same as mask register)"),
    "vmflt_vd_eq_v0": ("needs_new_coverpoint", "Need coverpoint to verify vmflt with vd=v0 (same as mask register)"),
    "vmfle_vd_eq_v0": ("needs_new_coverpoint", "Need coverpoint to verify vmfle with vd=v0 (same as mask register)"),
    "vmfgt_vd_eq_v0": ("needs_new_coverpoint", "Need coverpoint to verify vmfgt with vd=v0 (same as mask register)"),
    "vmfge_vd_eq_v0": ("needs_new_coverpoint", "Need coverpoint to verify vmfge with vd=v0 (same as mask register)"),
    "vmfeq_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for FP compares tested by masking infrastructure and Sail comparison",
    ),
    "vmfne_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for FP compares tested by masking infrastructure and Sail comparison",
    ),
    "vmflt_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for FP compares tested by masking infrastructure and Sail comparison",
    ),
    "vmfle_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for FP compares tested by masking infrastructure and Sail comparison",
    ),
    "vmfgt_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for FP compares tested by masking infrastructure and Sail comparison",
    ),
    "vmfge_tail_agnostic": (
        "covered_by_implication",
        "Tail-agnostic for FP compares tested by masking infrastructure and Sail comparison",
    ),
    "vmflt_sqNaN_invalid": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmflt raises invalid on signaling AND quiet NaN inputs",
    ),
    "vmfle_sqNaN_invalid": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmfle raises invalid on signaling AND quiet NaN inputs",
    ),
    "vmfgt_sqNaN_invalid": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmfgt raises invalid on signaling AND quiet NaN inputs",
    ),
    "vmfge_sqNaN_invalid": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmfge raises invalid on signaling AND quiet NaN inputs",
    ),
    "vmfne_vdval1_NaN": ("needs_new_coverpoint", "Need coverpoint to verify vmfne writes 1 when either operand is NaN"),
    "vmfeq_vdval0_NaN": ("needs_new_coverpoint", "Need coverpoint to verify vmfeq writes 0 when either operand is NaN"),
    "vmflt_vdval0_NaN": ("needs_new_coverpoint", "Need coverpoint to verify vmflt writes 0 when either operand is NaN"),
    "vmfle_vdval0_NaN": ("needs_new_coverpoint", "Need coverpoint to verify vmfle writes 0 when either operand is NaN"),
    "vmfgt_vdval0_NaN": ("needs_new_coverpoint", "Need coverpoint to verify vmfgt writes 0 when either operand is NaN"),
    "vmfge_vdval0_NaN": ("needs_new_coverpoint", "Need coverpoint to verify vmfge writes 0 when either operand is NaN"),
    # === FP CONVERT CONSTRAINTS ===
    "vfwcvt_vreg_constr": (
        "covered_by_implication",
        "Widening register overlap constraints tested by existing Ssstrictv overlap coverpoints",
    ),
    "vfncvt_vreg_constr": (
        "covered_by_implication",
        "Narrowing register overlap constraints tested by existing Ssstrictv overlap coverpoints",
    ),
    # === REDUCTION RULES ===
    "vreduction_tail_agnostic": (
        "needs_new_coverpoint",
        "Need coverpoint to verify reduction tail elements use tail-agnostic policy",
    ),
    "vreduction_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify reductions raise illegal-instruction when vstart != 0",
    ),
    "vredsum_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredsum.vs with boundary values",
    ),
    "vredmaxu_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredmaxu.vs with boundary values",
    ),
    "vredmax_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredmax.vs with boundary values",
    ),
    "vredminu_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredminu.vs with boundary values",
    ),
    "vredmin_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredmin.vs with boundary values",
    ),
    "vredand_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredand.vs with boundary values",
    ),
    "vredor_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredor.vs with boundary values",
    ),
    "vredxor_overflow": (
        "covered_by_implication",
        "Overflow wrapping tested by cr_vs2_vs1_edges on vredxor.vs with boundary values",
    ),
    "vfredusum_additive_impl": (
        "needs_new_coverpoint",
        "Need coverpoint to verify additive identity (+0.0 for RDN, -0.0 for others)",
    ),
    "vfredusum_redtree": (
        "architectural_definition",
        "Deterministic reduction tree structure requirement; not directly testable via functional output",
    ),
    # === MASK OPERATIONS ===
    "vmask_vstart": (
        "needs_new_coverpoint",
        "Need coverpoint to verify mask operations respect vstart and reset it to zero",
    ),
    "vmasklogical_tail_agnostic": (
        "needs_new_coverpoint",
        "Need coverpoint to verify mask logical tail elements use tail-agnostic policy",
    ),
    # === VCPOP/VFIRST ===
    "vcpop_vs_single_vreg": (
        "covered_by_implication",
        "vcpop source is single mask register; tested implicitly by cp_vs2 for vcpop.m",
    ),
    "vcpop_trap": ("needs_new_coverpoint", "Need coverpoint to verify vcpop traps are reported with vstart=0"),
    "vcpop_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vcpop raises illegal-instruction when vstart != 0",
    ),
    "vfirst_trap": ("needs_new_coverpoint", "Need coverpoint to verify vfirst traps are reported with vstart=0"),
    "vfirst_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vfirst raises illegal-instruction when vstart != 0",
    ),
    # === VMSBF/VMSIF/VMSOF ===
    "vmsbf_tail_agnostic": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsbf tail elements use tail-agnostic policy",
    ),
    "vmsbf_trap": ("needs_new_coverpoint", "Need coverpoint to verify vmsbf traps are reported with vstart=0"),
    "vmsbf_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsbf raises illegal-instruction when vstart != 0",
    ),
    "vmsif_tail_agnostic": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsif tail elements use tail-agnostic policy",
    ),
    "vmsif_trap": ("needs_new_coverpoint", "Need coverpoint to verify vmsif traps are reported with vstart=0"),
    "vmsif_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsif raises illegal-instruction when vstart != 0",
    ),
    "vmsof_tail_agnostic": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsof tail elements use tail-agnostic policy",
    ),
    "vmsof_trap": ("needs_new_coverpoint", "Need coverpoint to verify vmsof traps are reported with vstart=0"),
    "vmsof_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmsof raises illegal-instruction when vstart != 0",
    ),
    # === VIOTA ===
    "viota_trap": ("needs_new_coverpoint", "Need coverpoint to verify viota traps are reported with vstart=0"),
    "viota_vstart_n0_ill": (
        "needs_new_coverpoint",
        "Need coverpoint to verify viota raises illegal-instruction when vstart != 0",
    ),
    "viota_vreg_constr": (
        "needs_new_coverpoint",
        "Need coverpoint to verify viota destination cannot overlap source or mask v0",
    ),
    "viota_restart": (
        "needs_new_coverpoint",
        "Need coverpoint to verify viota execution restarts from beginning after trap resume",
    ),
    # === VMV ===
    "vmv-x-s_ignoreLMUL": ("needs_new_coverpoint", "Need coverpoint to verify vmv.x.s ignores LMUL setting"),
    "vmv-s-x_ignoreLMUL": ("needs_new_coverpoint", "Need coverpoint to verify vmv.s.x ignores LMUL setting"),
    "vmv-x-s_vstart_ge_vl": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmv.x.s operates even when vstart >= vl or vl=0",
    ),
    # === SLIDE ===
    "vslideup_mask": ("covered_by_implication", "Slide masking tested by cp_masking_edges on vslideup instructions"),
    "vslidedown_mask": (
        "covered_by_implication",
        "Slide masking tested by cp_masking_edges on vslidedown instructions",
    ),
    "vslide1up_mask": ("covered_by_implication", "Slide masking tested by cp_masking_edges on vslide1up.vx"),
    "vslide1down_mask": ("covered_by_implication", "Slide masking tested by cp_masking_edges on vslide1down.vx"),
    "vfslide1up_mask": ("covered_by_implication", "Slide masking tested by cp_masking_edges on vfslide1up.vf"),
    "vfslide1down_mask": ("covered_by_implication", "Slide masking tested by cp_masking_edges on vfslide1down.vf"),
    "vslideup_vreg_constr": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vslideup destination cannot overlap source",
    ),
    # === VRGATHER ===
    "vrgatherei16_vs2_uint": (
        "covered_by_implication",
        "Unsigned index interpretation tested by edge coverpoints on vrgatherei16.vv",
    ),
    "vrgatherei16_vs_ignore_vl": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vrgatherei16 source can be read at any index < VLMAX regardless of vl",
    ),
    "vrgather_vl": (
        "covered_by_implication",
        "vl limiting destination elements tested by cr_vl_lmul on vrgather instructions",
    ),
    "vrgatherei16_vl": (
        "covered_by_implication",
        "vl limiting destination elements tested by cr_vl_lmul on vrgatherei16",
    ),
    "vrgather_tail": ("covered_by_implication", "Tail policy tested by cr_vtype_agnostic on vrgather instructions"),
    "vrgatherei16_tail": ("covered_by_implication", "Tail policy tested by cr_vtype_agnostic on vrgatherei16"),
    "vrgather_mask": ("covered_by_implication", "Masking tested by cp_masking_edges on vrgather instructions"),
    "vrgatherei16_mask": ("covered_by_implication", "Masking tested by cp_masking_edges on vrgatherei16"),
    "vrgather-vv_sew_lmul": (
        "covered_by_implication",
        "SEW/LMUL for data and indices tested by cr_vl_lmul on vrgather.vv",
    ),
    # === Zve* UNSUPPORTED INSTRUCTION RULES ===
    "Zve64_eew64_nsupport_vmulh": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vmulh variants not supported for EEW=64 in Zve* without V",
    ),
    "Zve64_eew64_nsupport_vsmul": (
        "needs_new_coverpoint",
        "Need coverpoint to verify vsmul not supported for EEW=64 in Zve* without V",
    ),
    "Zve32x_Zve64x_nsupport_freg": (
        "architectural_definition",
        "FP register unavailability in Zve32x/Zve64x; configuration-level constraint",
    ),
    # === ELEMENT GROUP RULES ===
    "egs_ge_vlmax_rsv": (
        "needs_new_coverpoint",
        "Need coverpoint to verify instructions with EGS > VLMAX are reserved",
    ),
    "egs_vl_rsv": ("needs_new_coverpoint", "Need coverpoint to verify vl must be multiple of element group size"),
    "egs_vl_avl": ("needs_new_coverpoint", "Need coverpoint to verify AVL constraint for element group instructions"),
    "egs_sew_eew": (
        "architectural_definition",
        "SEW/EEW relationship description for element groups; not directly testable",
    ),
    "egs_lmul_emul": (
        "architectural_definition",
        "LMUL/EMUL relationship description for element groups; not directly testable",
    ),
    "egs_egw": ("architectural_definition", "Element group width definition; not directly testable"),
}


def main():
    with Path(NORM_CSV).open("r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    uncategorized = []
    cat_counts = {}

    for row in rows:
        if row["coverage_status"] != "none":
            continue

        rule = row["rule_name"]
        if rule in CATEGORIZATION:
            category, note = CATEGORIZATION[rule]
            cat_counts[category] = cat_counts.get(category, 0) + 1

            if category == "covered_by_implication":
                row["coverage_status"] = "partial"
                row["explanation"] = f"Covered by implication: {note}"
                row["gaps"] = (
                    "No dedicated coverpoint; coverage is implicit through related coverpoints and infrastructure"
                )
            elif category == "architectural_definition":
                row["coverage_status"] = "none"
                row["explanation"] = f"Architectural definition: {note}"
                row["gaps"] = "Not directly testable - defines a concept or dependency rather than observable behavior"
            elif category == "privileged_only":
                row["coverage_status"] = "none"
                row["explanation"] = f"Privileged-only: {note}"
                row["gaps"] = "Requires privileged mode test infrastructure not currently in scope"
            elif category == "implementation_defined":
                row["coverage_status"] = "none"
                row["explanation"] = f"Implementation-defined: {note}"
                row["gaps"] = "Permissive rule (implementation MAY do X); not a mandatory requirement to test"
            elif category == "needs_new_coverpoint":
                row["coverage_status"] = "none"
                row["explanation"] = f"Needs new coverpoint: {note}"
                row["gaps"] = note
            updated += 1
        else:
            uncategorized.append(rule)

    with Path(NORM_CSV).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated} rules")
    print("\nCategory counts:")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat}: {count}")

    if uncategorized:
        print(f"\nUncategorized rules ({len(uncategorized)}):")
        for r in uncategorized:
            print(f"  {r}")

    # Final counts
    counts = {}
    for row in rows:
        s = row["coverage_status"]
        counts[s] = counts.get(s, 0) + 1
    print("\nFinal status counts:")
    for k, v in sorted(counts.items()):
        print(f"  {k or '(empty)'}: {v}")


if __name__ == "__main__":
    main()
