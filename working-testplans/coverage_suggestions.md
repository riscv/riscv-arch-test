# Coverage Gap Analysis & Suggested New Coverpoints

## Summary

After systematic analysis of 590 normative rules from the RISC-V V extension specification:

| Status      | Count | Description                                              |
| ----------- | ----- | -------------------------------------------------------- |
| **full**    | 139   | Fully covered by existing coverpoints                    |
| **partial** | 345   | Partially covered (edge testing, implied coverage, etc.) |
| **none**    | 106   | Not covered — breakdown below                            |

### "None" Rule Breakdown

| Category                     | Count | Description                                          |
| ---------------------------- | ----- | ---------------------------------------------------- |
| **needs_new_coverpoint**     | 69    | Testable behavior requiring new coverpoint(s)        |
| **architectural_definition** | 19    | Defines concepts/dependencies, not testable behavior |
| **privileged_only**          | 8     | Requires privileged mode test infrastructure         |
| **implementation_defined**   | 7     | Permissive rules (implementation MAY do X)           |
| **covered_by_smv_smvf**      | 3     | Moved to partial via SmV/SmVF amendments             |

### Recent Amendments (v2)

The following rules were moved from "none" to "partial" based on:

1. **SmV/SmVF coverpoints** (23 rules): CSR access, vsetvl behavior, mstatus.VS/FS dirty transitions, misa.V writability — all already tested in SmV.csv and SmVF.csv
2. **cp_vd semantic correction** (6 rules): `cp_vd` with variant `x` iterates all 32 vd registers (v0-v31), covering the `vmf*_vd_eq_v0` rules
3. **cp_rs2_edges stride coverage** (2 rules): `cp_rs2_edges` with `ls_e*` variant on strided instructions includes 0 and negative stride values

---

## Existing Coverage Sources (SmV/SmVF/Zero-Match)

These coverpoints were not initially mapped to normative rules but provide significant coverage:

### SmV.csv Coverpoints (All marked "Test written: yes")

| Coverpoint                           | Rules Now Covered                                                                  |
| ------------------------------------ | ---------------------------------------------------------------------------------- |
| `cp_vcsrrswc`                        | `vstart_acc`, `vxrm_acc`, `vlenb_acc`, `vlenb_op`, `vcsr-vxrm_op`, `vcsr-vxsat_op` |
| `cp_vcsrs_walking1s`                 | `vstart_sz`, `vxrm_sz`, `vxsat_sz`, `vstart_sz_writable`                           |
| `cp_mstatus_vs_set_dirty_arithmetic` | `mstatus-vs_op_initial_clean` (strengthened)                                       |
| `cp_mstatus_vs_set_dirty_csr`        | `mstatus-vs_op_initial_clean` (strengthened), `vtype-vstart_op`                    |
| `cp_misa_v_clear_set`                | `MUTABLE_MISA_V`, `misa-V_op`                                                      |
| `cp_sew_lmul_vset_i_vli`             | `vsetivli_op`, `vtype-vstart_op`                                                   |
| `cp_sew_lmul_vsetvl`                 | `vtype-vstart_op`                                                                  |
| `cp_vstart_out_of_bounds`            | `vstart_sz_writable` (strengthened)                                                |
| `cp_vtype_vill_set_vl_0`             | `vtype-vstart_op`                                                                  |
| `cp_vsetivli_avl_corners`            | `vsetivli_op`                                                                      |

### SmVF.csv Coverpoints

| Coverpoint                                        | Rules Now Covered                                        |
| ------------------------------------------------- | -------------------------------------------------------- |
| `cp_vectorfp_mstatus_fs_state_affecting_register` | `mstatus-FS_dirty_hypervisor_V_fp` (non-hypervisor part) |
| `cp_vectorfp_mstatus_fs_state_affecting_csr`      | `mstatus-FS_dirty_hypervisor_V_fp`                       |

### Standard CSV Coverpoints (previously zero normative rule matches)

| Coverpoint                      | CSVs | Coverage Impact                                                                                       |
| ------------------------------- | ---- | ----------------------------------------------------------------------------------------------------- |
| `cp_rs2_edges` (ls_e\* variant) | Vls  | Covers `vector_ls_neg_stride` and `vector_ls_zero_stride` — stride edge values include 0 and negative |
| `cp_vd` (variant x)             | Vf   | Covers `vmf*_vd_eq_v0` rules — iterates all 32 vd registers including v0                              |

---

## Suggested New Coverpoints (Grouped by Pattern)

### 1. `cp_vstart_nonzero_ill` — vstart != 0 Illegal Instruction (13 rules)

**Rules covered**: `vcpop_vstart_n0_ill`, `vfirst_vstart_n0_ill`, `vmsbf_vstart_n0_ill`, `vmsif_vstart_n0_ill`, `vmsof_vstart_n0_ill`, `viota_vstart_n0_ill`, `vreduction_vstart_n0_ill`, `vcpop_trap`, `vfirst_trap`, `vmsbf_trap`, `vmsif_trap`, `vmsof_trap`, `viota_trap`

**Description**: Set vstart to a non-zero value, then execute the instruction. Verify an illegal-instruction exception is raised. For the `_trap` variants, verify the trap is reported with vstart=0.

**Bin count**: Per-instruction (vcpop, vfirst, vmsbf, vmsif, vmsof, viota, vred\* = ~15 instructions)

**Priority**: HIGH — these are mandatory behaviors with clear pass/fail criteria.

---

### 2. `cp_compare_maskundisturbed_vd_v0` — Compare AND-in-mask (8 rules)

**Rules covered**: `vmseq_maskundisturbed`, `vmsne_maskundisturbed`, `vmsltu_maskundisturbed`, `vmslt_maskundisturbed`, `vmsleu_maskundisturbed`, `vmsle_maskundisturbed`, `vmsgtu_maskundisturbed`, `vmsgt_maskundisturbed`

**Description**: Execute integer compare with vd=v0 (destination = mask register) under mask-undisturbed policy. Verify that inactive elements in the destination mask AND with the original mask value (effectively AND-in-mask behavior).

**Bin count**: 8 instructions × 2 test patterns (some elements active, some inactive)

**Priority**: HIGH — tests a subtle correctness requirement.

---

### 3. `cp_fp_compare_NaN_behavior` — FP Compare NaN Output (11 rules)

**Rules covered**: `vmfne_vdval1_NaN`, `vmfeq_vdval0_NaN`, `vmflt_vdval0_NaN`, `vmfle_vdval0_NaN`, `vmfgt_vdval0_NaN`, `vmfge_vdval0_NaN`, `vmflt_sqNaN_invalid`, `vmfle_sqNaN_invalid`, `vmfgt_sqNaN_invalid`, `vmfge_sqNaN_invalid`

**Description**: Feed NaN (both signaling and quiet) as operands to FP compare instructions. Verify:

- `vmfne` writes 1 to destination when either operand is NaN
- All other compares write 0 when either operand is NaN
- `vmflt`, `vmfle`, `vmfgt`, `vmfge` raise invalid-operation exception on both sNaN AND qNaN

**Bin count**: 6 instructions × 4 NaN patterns (sNaN/qNaN × operand1/operand2) = 24 bins

**Priority**: HIGH — critical FP correctness behavior.

**Note**: Existing `cr_vs2_vs1_edges` and `cr_vs2_fs1_edges` with 'f' variant include NaN edge values, so this may already be partially covered. Verify by checking if the edge bins include sNaN and qNaN separately.

---

### ~~4. `cp_fp_compare_vd_v0` — FP Compare with vd=v0 (6 rules)~~ **COVERED**

**Status**: Now covered by `cp_vd` with variant `x` on vmf\* instructions. Since `cp_vd x` iterates all 32 destination registers (v0-v31), the vd=v0 case is included. These 6 rules (`vmfeq_vd_eq_v0` through `vmfge_vd_eq_v0`) have been moved to "partial" in the normative rules CSV.

---

### 5. `cp_mask_tail_agnostic` — Mask-Producing Instruction Tail Policy (13 rules)

**Rules covered**: `vreg_mask_tail_agn`, `vmasklogical_tail_agnostic`, `vmsbf_tail_agnostic`, `vmsif_tail_agnostic`, `vmsof_tail_agnostic`, (also supplements `vmseq_tail_agnostic` through `vmsgt_tail_agnostic` and `vmfeq_tail_agnostic` through `vmfge_tail_agnostic` which are already covered_by_implication)

**Description**: Execute mask-producing instructions with various vta settings and verify tail elements always use tail-agnostic policy (regardless of vta bit in vtype).

**Bin count**: ~15 mask-producing instructions × 2 vta settings = 30 bins

**Priority**: MEDIUM — the Sail model enforces this, so existing tests likely pass, but no dedicated coverpoint validates it.

---

### 6. `cp_vstart_reset` — vstart Reset After Execution (2 rules)

**Rules covered**: `vstart_update`, `vmask_vstart`

**Description**: Set vstart to a non-zero value, execute a vector instruction, then read vstart and verify it has been reset to zero.

**Bin count**: ~5 representative instructions × 3 vstart values = 15 bins

**Priority**: HIGH — fundamental vector execution behavior.

**Note**: SmV `cp_vstart_out_of_bounds` partially addresses this by testing vstart boundary behavior, but does not directly test the post-execution reset to zero.

---

### ~~7. `cp_vcsr_mirror` — vcsr Mirroring of vxrm and vxsat (2 rules)~~ **COVERED**

**Status**: Now covered by SmV `cp_vcsrrswc`, which tests read/write/clear/set operations on all 7 vector CSRs including vcsr, vxrm, and vxsat. The mirroring behavior between vcsr and vxrm/vxsat is exercised through these CSR operations. Rules `vcsr-vxrm_op` and `vcsr-vxsat_op` moved to "partial".

---

### ~~8. `cp_vlenb_value` — vlenb CSR Value (2 rules)~~ **COVERED**

**Status**: Now covered by SmV `cp_vcsrrswc` (read/write/clear/set on vlenb) and `cp_vcsrs_walking1s` (walking 1s into writable CSRs). Rules `vlenb_op` and `vlenb_acc` moved to "partial".

---

### ~~9. `cp_vstart_csr` — vstart CSR Properties (4 rules)~~ **MOSTLY COVERED**

**Status**: 3 of 4 rules now covered by SmV:

- `vstart_acc` — covered by `cp_vcsrrswc`
- `vstart_sz` — covered by `cp_vcsrs_walking1s`
- `vstart_sz_writable` — covered by `cp_vcsrs_walking1s` + `cp_vstart_out_of_bounds`
- `vstart_unmodified` — still needs coverage (vstart preserved when vector instruction raises illegal-instruction exception)

---

### ~~10. `cp_vxrm_vxsat_csr` — Fixed-Point CSR Properties (3 rules)~~ **COVERED**

**Status**: Now covered by SmV `cp_vcsrrswc` (read/write/clear/set) and `cp_vcsrs_walking1s` (walking 1s). Rules `vxrm_acc`, `vxrm_sz`, and `vxsat_sz` moved to "partial".

---

### 11. `cp_merge_all_elements` — Merge Writes All Body Elements (2 rules)

**Rules covered**: `vmerge_all_elem`, `vfmerge_all_elem`

**Description**: Execute vmerge/vfmerge with a mask pattern and verify ALL body elements (both active and inactive per mask) are written, unlike regular arithmetic which only writes active elements.

**Bin count**: 2 instructions × 2 mask patterns = 4 bins

**Priority**: HIGH — correctness of merge semantics.

---

### 12. `cp_adc_sbc_all_elements` — ADC/SBC Write All Body Elements (4 rules)

**Rules covered**: `vadc_masked_write_all_elem`, `vsbc_masked_write_all_elem`, `vmadc_masked_write_all_elem`, `vmsbc_masked_write_all_elem`

**Description**: Execute vadc/vsbc/vmadc/vmsbc (encoded as masked vm=0) and verify all body elements are written, not just elements where mask=1.

**Bin count**: 4 instructions × 2 mask patterns = 8 bins

**Priority**: HIGH — subtle encoding behavior.

---

### ~~13. `cp_vsetivli_imm` — vsetivli Immediate Encoding (1 rule)~~ **COVERED**

**Status**: Now covered by SmV `cp_sew_lmul_vset_i_vli` (crosses all SEW/LMUL combinations for vsetivli) and `cp_vsetivli_avl_corners` (tests all 32 immediate values 0-31). Rule `vsetivli_op` moved to "partial".

---

### ~~14. `cp_ls_stride_values` — Load/Store Stride Edge Cases (2 rules)~~ **COVERED**

**Status**: Now covered by `cp_rs2_edges` with `ls_e*` variant on strided load/store instructions. The edge values include stride=0 and negative stride values (-1, -2, -SEW/8). Rules `vector_ls_neg_stride` and `vector_ls_zero_stride` moved to "partial".

---

### 15. `cp_fractional_lmul_tail` — Fractional LMUL Tail Treatment (1 rule)

**Rules covered**: `vreg_flmul_op`

**Description**: With LMUL < 1, verify only the first LMUL×VLEN/SEW elements are used and remaining space is treated as tail.

**Bin count**: 3 fractional LMUL values × ~3 representative instructions = 9 bins

**Priority**: MEDIUM — important for fractional LMUL correctness.

---

### 16. `cp_vmv_ignore_lmul` — vmv.x.s / vmv.s.x LMUL Independence (3 rules)

**Rules covered**: `vmv-x-s_ignoreLMUL`, `vmv-s-x_ignoreLMUL`, `vmv-x-s_vstart_ge_vl`

**Description**: Execute vmv.x.s and vmv.s.x with various LMUL settings and verify they ignore LMUL. Also test vmv.x.s when vstart >= vl or vl=0.

**Bin count**: 2 instructions × 4 LMUL values + 2 edge cases = 10 bins

**Priority**: MEDIUM

---

### 17. `cp_viota_constraints` — viota Register Overlap and Restart (2 rules)

**Rules covered**: `viota_vreg_constr`, `viota_restart`

**Description**: Verify viota destination cannot overlap source or v0 (when masked). Verify viota restarts from beginning when resuming after trap.

**Bin count**: ~6 bins (overlap source, overlap v0, restart)

**Priority**: MEDIUM — register constraint enforcement.

---

### 18. `cp_vslideup_vreg_constr` — vslideup Register Overlap (1 rule)

**Rules covered**: `vslideup_vreg_constr`

**Description**: Verify vslideup destination cannot overlap source vector register group.

**Bin count**: ~4 bins (various overlap configurations)

**Priority**: MEDIUM — likely already partially covered by Ssstrictv overlap tests.

---

### 19. `cp_ff_behavior` — Fault-Only-First Behavior (2 rules)

**Rules covered**: `vector_ff_no_exception`, `vector_ff_interrupt_behavior`

**Description**: Test fault-only-first load reducing vl without raising exception (when vstart=0, vl>0, at least first element succeeds). Test interrupt behavior setting vstart instead of reducing vl.

**Bin count**: ~4 bins

**Priority**: HIGH — important for correct FF semantics.

---

### 20. `cp_vtype_vma_vta_all` — All vma/vta Combinations (1 rule)

**Rules covered**: `vtype-vta_val`

**Description**: Systematically verify all 4 vma/vta combinations (00, 01, 10, 11) are supported.

**Bin count**: 4 bins

**Priority**: MEDIUM

---

## Rules Not Requiring New Coverpoints

### Architectural Definitions (19 rules)

These define concepts, extension dependencies, or encoding formats rather than testable behavior:

- `VLEN`, `VILL_IMPLICIT_ENCODING`, `vmv-nr-r_enc`
- Extension dependencies: `Zve_XLEN`, `Zve32f_Zve64x_dependent_Zve32x`, `Zve64f_dependent_Zve32f_Zve64x`, `Zve64d_dependent_Zve64f`, `Zve32x_dependent_Zicsr`, `Zve64f_dependent_F`, `V_dependent_Zvl128b_Zve64d`, `Zvfhmin_dependent_Zve32f`, `Zvfh_dependent_Zve32f_Zfhmin`, `Zve32x_Zve64x_nsupport_freg`
- Element group definitions: `egs_sew_eew`, `egs_lmul_emul`, `egs_egw`
- Other: `vector_ls_scalar_missaligned_independence`, `vl_control_dependency`, `vfredusum_redtree`

### Privileged-Only (8 rules, down from 10)

These require privileged mode or hypervisor extension test infrastructure:

- `sstatus-vs_op`, `vsstatus-vs_op2`, `vsstatus-sd_op_vs`, `mstatus-sd_op`, `mstatus-sd_op_vs`
- `MSTATUS_VS_EXISTS`, `VSSTATUS_VS_EXISTS`, `vsstatus-FS_dirty_hypervisor_V_fp`

Note: `misa-V_op` and `mstatus-FS_dirty_hypervisor_V_fp` moved to partial via SmV/SmVF coverage (non-hypervisor aspects now covered).

### Implementation-Defined (7 rules, down from 8)

Permissive rules where implementation MAY do something:

- `HW_MSTATUS_VS_DIRTY_UPDATE`
- `VECTOR_LS_WHOLEREG_MISSALIGNED_EXCEPTION`, `VECTOR_LS_MISSALIGNED_EXCEPTION`
- `VECTOR_LS_SEG_PARTIAL_ACCESS`, `VECTOR_FF_SEG_PARTIAL_ACCESS`
- `VECTOR_LS_SEG_FF_OVERLOAD`, `VECTOR_FF_PAST_TRAP`

Note: `MUTABLE_MISA_V` moved to partial via SmV `cp_misa_v_clear_set` coverage.

---

## Priority Summary

| Priority            | Coverpoint Groups                                                                                                        | Rules Covered |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------- |
| **HIGH**            | vstart_nonzero_ill, compare_maskundisturbed, fp_compare_NaN, merge_all_elem, adc_sbc_all_elem, vstart_reset, ff_behavior | 42            |
| **MEDIUM**          | mask_tail_agnostic, fractional_lmul, vmv_ignore_lmul, viota_constraints, vslideup_constr, vma_vta_all                    | 22            |
| **LOW**             | (none remaining)                                                                                                         | 0             |
| **N/A**             | Architectural/Privileged/Impl-defined                                                                                    | 34            |
| **ALREADY COVERED** | fp_compare_vd_v0, vcsr_mirror, vlenb_value, vstart_csr (3/4), vxrm_vxsat_csr, vsetivli_imm, ls_stride                    | 22            |

**Total still needing new coverpoints: 64 of 69 "needs_new_coverpoint" rules** (down from 84 of 92)

The remaining specialized rules (`vector_ls_scalar_missaligned_dependence`, `vector_ls_stride_unordered_precise`, `vector_ls_nf_op`, `vector_ls_seg_vstart_dep`, `vector_ls_seg_wholereg_op_cont`, `vector_ls_indexed-ordered_RVWMO`, `V_Zfinx_fp_scalar`, `vrgatherei16_vs_ignore_vl`) each need individual coverpoint design based on specific DUT capabilities.
