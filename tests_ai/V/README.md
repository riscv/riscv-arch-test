# V: rule-derived tests for the vector extension

Four generators share this directory; each section below describes one of them. A test's header names its generator.

- `gen/gen_Vctl.py` (`vctllib.py`): vector control: programmer's model, vector CSRs, mstatus.VS, vset*, element
  mapping, masking and tail/mask policies, prestart/body/tail elements, exception handling, element groups, V/Zve*
  subsets. Mutants `Vctl:<name>`.
- `gen/gen_Vinsn.py` (`vinsnlib.py`): vector arithmetic, fixed-point, floating-point, reduction, mask and permutation
  instructions. Mutants `Vinsn:<name>`.
- `gen/gen_Vmem.py` (`vmemlib.py`): vector loads and stores, alignment and memory ordering. Mutants `Vmem:<name>`.
- `gen/gen_Vzv.py` (`vzvlib.py`): the Zv* extensions, in their own directories. Mutants `Vzv:<name>`.

## Vector control (gen_Vctl.py, vctllib.py)

### How it is tested

One test per `norm:` rule of the programmer's model, vtype/vl/vstart/vxrm/vxsat/vcsr/vlenb, mstatus.VS,
configuration-setting instructions, element mapping, masking, prestart/body/tail elements, the arithmetic format
rules that fix register-group layout, Exception Handling, Vector Element Groups, and the V/Zve* subset rules
(`vector-common.adoc` up to Vector Instruction Formats, plus `v-st-ext.adoc`, `zve32x.adoc` and the mstatus.VS rules
of `machine.adoc` not in `tests_ai/Sm`). 80 files; mutants are `Vctl:<name>`.

- **Requirements.** Rules that hold for every vector extension require `Zve32x` and assemble with `_zve32x`; V-only
  rules (`V_*`, `misa_v_op`) require `V`. Rules about mstatus.VS boot to S-mode (and have an `_Sm` file for M-mode and
  U-from-M); the rest run in the lowest mode. Exception-class rules (prestart/inactive/tail/active elements, precise
  traps, `epc_vstart_op_V_trap`, `vmask_inactive_op`) boot to S-mode and build an Sv39/Sv32 table (under
  `SV39_SUPPORTED`/`SV32_SUPPORTED`) with a valid page P0, an invalid P1 = P0 + 4 KiB and an unmapped page below P0, so
  an element of a unit-stride access can be made to fault.
- **No implementation parameters.** VLEN is read from `vlenb` and every VLMAX is computed from it at run time; ELEN is
  64 with `Zve64x`, else 32. Element indices are chosen to exist at the minimum VLEN (32 for Zve32x, 64 for Zve64x),
  and fractional LMUL is used only where the spec requires it. Values that wrap (SEW=8 `vid.v` at large VLEN) are
  masked or avoided.
- **Checks.** Registers are stored with `vs1r.v` (independent of vtype) and checked byte- or element-wise. Undisturbed
  elements must keep their value exactly; agnostic elements may each keep it or be all 1s; a mask-result tail bit is
  constrained only where every legal outcome (old value, 1, value computed with vl=VLMAX or VLEN) is 1.
- **Traps.** Illegal-instruction traps accept xtval 0 or the instruction bits (read from memory at run time); page
  faults accept xtval 0 or the first faulting byte. Where `norm:vstart_vtype_dep` lets an instruction trap for a
  nonzero vstart (arithmetic, permutations), the test accepts the trap, checks vstart is unchanged, and checks the
  executed path otherwise.
- **Configurations.** Passed on Sail (VLEN 1024), Imperas (512), Whisper (256), Spike and QEMU (128), rv32/rv64,
  `-max`, `-m` and `-mu`, plus two scratch Spike configurations made for this suite: rv32 Zve32x only with VLEN=32 and
  ELEN=32, and rv64 Zve64x only with VLEN=64.

### Rules not tested here

- **Other suites.** `vsstatus_vs_sz_acc`, `vsstatus_vs_mstatus_vs_op_off`, `vsstatus_vs_mstatus_vs_op_active`,
  `hw_mstatus_vs_dirty_update`, `vsstatus_sd_op_vs`, `vsstatus_vs_exists` (H: `vsstatus_vs_op`,
  `vsstatus_sd_xs_op`); `mstatus_vs_acc1`, `mstatus_vs_acc2`, `mstatus_vs_rdonly0_s_no_V`, `mstatus_vs_wr`,
  `mstatus_sd_formula`, `mstatus_fs_vs_warl` (Sm); the `*_vstart_n0_ill` rules of reductions, vcpop, vfirst,
  vmsbf/vmsif/vmsof, viota and vcompress, `vreg_scalar_emul`, `V_fp_frm`, `V_inv_frm_rsv`, the `vop-*`/`vfop_*`
  operand rules (vector instructions, gen_Vinsn); every rule from `vector_load_store_semantics` on (vector memory,
  gen_Vmem); `egs_sew_eew`, `egs_lmul_emul`, `egs_egw` (Zvk* instruction definitions).
- **Covered by another file here.** `mstatus_sd_op_vs` (same statement as `mstatus_sd_vs_dirty_op`); `vl_op` (the
  policy tests); `V_masked` (`vmask_vm_enc`, `vreg_vmask`); `eew_emul`, `eew_emul_sew_lmul_dep`, `vnarrowing_eew_emul`
  (`vwop_vd_eew_emul`, `vnop_*`); `vreg_overlap_legal`, `vreg_mask_overlap` (the legal overlaps used by
  `vreg_overlap_agn`); `vtype_vstart_op` and `vtype_vill_val` also cover the untagged "other bits of vtype are zero
  when vill is set".
- **Reserved or permissive, no mandated outcome.** `vtype_fields_sz` (tested as part of `vtype_vill_all_bits`),
  `vtype_lmul_fval_rsv`, `vtype_vset_rsv`, `reserved_vill_set`, `vstart_val_rsv`, `vstart_vtype_dep` (accepted where
  it applies), `vreg_offgroup_lmul{2,4,8}_rsv`, `emul_offgroup_rsv`, `vreg_source_eew_rsv`, `vreg_overlap_rsv`,
  `emul_rsv`, `vreg_vmask_rsv`, `egs_ge_vlmax_rsv`, `egs_vl_rsv`, `mutable_misa_v`, `mstatus_vs_exists`,
  `mstatus_vs_imprecise`, `mstatus_vs_no_change_dirty` (accepted: every state change in the tests really changes the
  state), `Zve64_eew64_nsupport_vmulh`, `Zve64_eew64_nsupport_vsmul`, `Zve_nsupport_eew64_xlen32`,
  `V_instr_ls_eew64_nsupported_xlen32` ("not included/not supported" without a required outcome).
- **Not observable.** `vector_reset_state` (the framework runs `vsetivli` before the test); `elen` (a definition,
  visible only through the supported SEWs, `Zve_eew`/`V_supported_eew`); `vreduction_trap`, `vcpop_trap`,
  `vfirst_trap`, `vmsbf_trap`, `vmsif_trap`, `vmsof_trap`, `viota_trap`, `viota_restart`, `vcompress_trap` (these
  instructions raise no synchronous exception other than illegal-instruction, and an interrupt cannot be placed inside
  one); interrupts in `epc_vstart_op_V_trap` (same reason); `vec_store_nonidempotent_no_update` (needs a
  non-idempotent PMA region); `Zve_xlen`.
- **Support/dependency statements.** `V_instr_config`, `V_instr_red`, `V_instr_mask`, `V_instr_perm`,
  `V_dependent_F_D`, `V_fp_reductions`, `Zve32f_instr_perm`, `Zve64d_instr_perm`, `Zve32x_Zve64x_nsupport_freg`,
  `Zve32f_Zve64f_dependent_F`, `Zve64d_dependent_Zve64f`, `Zve64f_dependent_Zve32f_Zve64x`,
  `Zve32f_Zve64x_dependent_Zve32x`, `Zve32x_dependent_Zicsr`: every instruction at every EEW is exercised by the
  instruction suites; only the distinguishing cases are tested here (`V_instr_int`: vmulh* at SEW=64,
  `V_instr_fixedpt`: vsmul at SEW=64, `V_dependent_Zvl128b_Zve64d`, `V_supported_eew`, `Zve_eew`).

### Subtleties

- vset* never trap on a nonzero vstart and always clear it
  ([#3408](https://github.com/riscv/riscv-isa-manual/issues/3408)).
- Whole-register loads and stores must not raise illegal-instruction when vill=1; whether `vmv<nr>r.v` depends on vtype
  was left open, so it may trap ([#3067](https://github.com/riscv/riscv-isa-manual/issues/3067)).
- SEW above LMUL*ELEN at a fractional LMUL may be supported
  ([#2353](https://github.com/riscv/riscv-isa-manual/issues/2353),
  [#2359](https://github.com/riscv/riscv-isa-manual/issues/2359)); those cases accept vill either way.
- vstart >= vl updates nothing, not even agnostic tail elements
  ([#3311](https://github.com/riscv/riscv-isa-manual/issues/3311)).
- vill is set with `vsetvl x0, x6, rs2` (rs1 != x0): the keep-vl form `vsetvl x0, x0` is reserved when vill was set or
  VLMAX changes.
- vtype bit 8 is `altfmt` in the Zvfbfa extension (not yet in the manual); it is tested as reserved only without
  Zvfbfa. QEMU `-cpu max` implements Zvfbfa although its configurations do not list it, so it fails that case
  (passes with `zvfbfa=false`).
- vstart writes keep the value modulo VLEN (the largest element index is VLEN-1 at e8, m8); the tests read the
  non-writable upper bits as 0.
- Unit-stride loads and stores can fault at any element, so `vstart_op`/`vstart_update` require them to execute with
  a nonzero vstart (only arithmetic may use `norm:vstart_vtype_dep`).
- The paging tests assume the test image is identity-mapped by root-level superpages away from VA 0x4000_0000 (Sv39)
  or 0x2000_0000 (Sv32), as in the standard ACT link layout.

## Vector instructions (gen_Vinsn.py, vinsnlib.py)

Rules of the Integer Arithmetic, Fixed-Point, Floating-Point, Reduction, Mask, Integer Permutation and FP Permutation
sections of `src/unpriv/vector-common.adoc` (214 rules). 181 of them have a test (183 files: two rules also have an
`_Sm` file). The tests are generated by `tests_ai/gen/gen_Vinsn.py`, with helpers in `tests_ai/gen/vinsnlib.py`.
Mutants are `Vinsn:<name>`.

How the instructions are tested:

- **Data and checks.** Each case loads its operands from data tables with unit-stride loads (`vle*`), sets vtype, vl,
  vstart, vxrm and frm, runs one instruction, then stores the destination group and checks every element. A legal
  set is checked per element, never a single value. Agnostic elements (vta/vma) may keep their value or be all ones.
  A mask-destination bit is checked only where the spec fixes it: an old 1 whose computed value is also 1 must stay 1.
- **VLEN independence.** Only the first 128 bits of each register hold loaded data (V requires Zvl128b), and LMUL is
  chosen so that vl <= VLMAX at VLEN = 128. Rules that depend on VLMAX read it at run time from `vsetvli` or `vlenb`.
  They fill whole registers with `vid.v` and check the result by computing it at run time. These rules are:
  vrgather index >= VLMAX, vslidedown past VLMAX, vzext/vsext with vl = VLMAX, vid/viota overflow at VLEN > 256, and
  whole-register moves compared over all VLEN bits with `vmsne`/`vcpop`. The tests passed at VLEN 128 (Spike, QEMU,
  Whisper), 512 (Imperas) and 1024 (Sail).
- **Reference semantics.** Integer and fixed-point results follow the instruction definitions, with `roundoff` as
  given for vxrm. FP results come from an exact rational IEEE 754 model in `vinsnlib`: binary32 and binary64, all
  five rounding modes, tininess after rounding, and RISC-V NaN rules. It also has vfrec7/vfrsqrt7, built from the
  spec's tables (copied from `vfrec7.edn`/`vfrsqrt7.edn`) and its exponent formulas, and it reproduces the spec's four
  worked examples. No reference model is involved.
- **Edge cases the spec calls out**, not value crosses. The human plans `testplans/Vx.csv`/`Vf.csv` already cross
  operand edges with SEW, LMUL and policies. These are the cases:
  - Integer:
    - division by zero and MIN/-1;
    - shift amounts masked to lg2(SEW), or lg2(2*SEW) for narrowing shifts;
    - vmadc/vmsbc with and without a carry-in, and the unsigned borrow;
    - vadc/vmerge write every body element whatever the mask;
    - vmulhsu signedness, the widening multiply-adds, and the vrsub operand order.
  - Fixed point:
    - every vxrm mode on exact, above-half and below-half remainders;
    - vasub/vasubu wrap-around;
    - vsmul MIN*MIN;
    - vnclip rounding before saturation;
    - vxsat set on any saturating element, and never cleared.
  - FP:
    - flags from active elements only, accrued;
    - the vfrsub/vfrdiv operand order;
    - one rounding for fused FMAs;
    - exact widening;
    - vfrec7/vfrsqrt7 special cases, table indices and exponent extremes, including subnormal inputs and outputs and
      overflow per rounding mode;
    - minimumNumber/maximumNumber;
    - quiet versus signaling compares and NaN results;
    - vfclass;
    - NaN boxing of f-register operands (vfmerge, vfmv, vfmv.s.f, vfslide1*);
    - conversions: NaN, infinity, saturation, -0.5 to unsigned, frm versus rtz, and round-to-odd.
  - Reductions:
    - vl = 0, so vd is not written;
    - vstart != 0 raises illegal-instruction;
    - the scalar is always included;
    - EMUL = 1 for the scalar operands (unaligned vd/vs1 at LMUL = 8);
    - the tail policy;
    - ordered versus unordered sums: vfredosum's order is forced by cancellation; vfredusum is checked only on
      tree-independent values, and its run-to-run determinism;
    - the additive identity's sign per rounding mode.
  - Mask:
    - vcpop/vfirst with vl = 0, and -1 for no set bit;
    - vmsbf/vmsif/vmsof on the spec's examples and with no set bit;
    - viota/vid masked, zero-extended and overflowing;
    - vstart for mask-logical instructions;
    - single-register operation at LMUL = 8.
  - Permutation:
    - vmv.x.s and vfmv.f.s with vl = 0, sign extension and truncation, and NaN boxing;
    - vmv.s.x and vfmv.s.f with vl = 0 or vstart >= vl;
    - slides with vl = 0 (no agnostic tail update), OFFSET >= vl, and OFFSET not truncated to SEW;
    - vslide1down does not read vs2[vl];
    - gather indices are unsigned, may be at or above vl, and give 0 at or above VLMAX;
    - vrgatherei16's 16-bit index EMUL;
    - the vcompress tail below vl;
    - vmv<nr>r: the .word encodings, a full copy whatever vl is, vstart, and vill.
- **Optional traps.** A nonzero vstart on an instruction that does not require it to be 0 may raise
  illegal-instruction (`vstart_vtype_dep`). Those cases accept both outcomes and check the result on the path taken.
  Instructions that require vstart = 0 must trap, with xtval 0 or the instruction bits.
- **FP state.** `mstatus_fs_*` run in S-mode on sstatus.FS, with `_Sm` files in M-mode on mstatus.FS. `vsstatus_*`
  run in VS/VU-mode with H. Dirty is checked only after an instruction that changes FP state: fflags is cleared
  first, so each flag raised is a change.

Rules not tested here:

- **Reserved encodings, untestable.** The spec leaves their outcome open:
  - `vsext_vzext_ill_eew_emul_rsv`, `vadc_vsbc_unmasked_rsv`, `vadc_vsbc_vd_v0_rsv`;
  - `vmv_vs2_nv0_rsv`, `vfmv_vs2_nv0_rsv`, `vid_vs2_nv0_rsv`;
  - `V_fp_eew_ieee_nsupported_rsv`, `vmasklogical_masked_rsv`, `vmv-s-x_vmv-x-s_masked_rsv`, `vfmv-s-f_masked_rsv`;
  - `vcompress_masked_rsv`, `vmv-nr-r_nreg_rsv`, `vmv-nr-r_unaligned_rsv`;
  - the overlap constraints `vfwcvt_vreg_constr`, `vfncvt_vreg_constr`, `vmsbf/vmsif/vmsof/viota_vreg_constr`,
    `vslideup_vreg_constr`, `vslide1up-vx_vreg_constr`, `vrgather_vrgatherei16_vreg_constr`,
    `vcompress_vreg_constr`, `vmv-nr-r_vreg_constr`.
- **"Traps ... are always reported with a vstart of 0", untestable.** These are `vreduction_trap`, `vcpop_trap`,
  `vfirst_trap`, `vmsbf_trap`, `vmsif_trap`, `vmsof_trap`, `viota_trap`, `vcompress_trap` and `viota_restart`. The
  only traps a test can cause on these instructions are illegal-instruction, and an illegal-instruction trap leaves
  vstart unmodified (`vstart_unmodified`). A test cannot force a mid-instruction trap or interrupt.
- **Belongs to another suite.** The operand-sourcing rules of "Vector Arithmetic Instruction Formats" (e.g.
  `vfop_freg_nanbox_lsb_sewbits`, `V_fp_frm`) and the vtype/vill/vstart rules belong to the control agent's part of
  V. The tests here use NaN boxing and vill only where an instruction's own rule depends on them.
- **SEW = 16 FP** needs Zvfh (another suite). The one exception is `vfclass_sewge16`, which also checks e16 under
  `#if ZVFH_SUPPORTED`.

Subtleties:

- **Mask-destination tails.** A tail bit may keep its old value, become 1, or take the value computed with vl = VLMAX.
  For mask-logical and vmsbf/vmsif/vmsof the computation may use the whole register. The policy is per element
  ([#3278](https://github.com/riscv/riscv-isa-manual/issues/3278): "you can update some elements using the regular
  tail-agnostic rules ... and other elements using the result that would've been computed using vl=VLMAX"). The only
  checkable constraint is therefore old = 1 and computed = 1 gives 1. The extent of the region
  [VLMAX, VLEN) is open ([#3288](https://github.com/riscv/riscv-isa-manual/issues/3288)). The tests constrain those
  bits only when every reading gives 1.
- **vmv<nr>r.v depends on vtype.** It uses EEW = SEW, so vill = 1 must make it illegal
  ([#1709](https://github.com/riscv/riscv-isa-manual/issues/1709): "some implementation may use SEW when executing
  vmvnr.v"). Imperas's stock model lacked this check; the engineering build has it (`config/imperas/ci.yaml`).
- **vasubu wraps in SEW+1 bits.** Its difference is formed as a (SEW+1)-bit value: 0 - 0xff gives 0x81 under rnu.
- **vfredusum gives NaN on infinities of both signs.** Every tree must combine +inf and -inf into a NaN with NV, and
  no masked-off element changes the result. A signed-zero result tells +0 from -0, which identifies the additive
  identity whenever the hart treats inactive inputs as the identity rather than copying.
- **FS Dirty is required only on a change.** With FS = Clean, an instruction that re-raises a flag already set in
  fflags changes no state. Sail then leaves FS Clean (its `fflags_dirty_policy` is precise), so the tests clear
  fflags first.

## Vector memory (gen_Vmem.py, vmemlib.py)

### How it is tested

One test per `norm:` rule in vector-common.adoc "Vector Loads and Stores", "Vector Memory Alignment Constraints" and
"Vector Memory Consistency Model" (53 files). Tests require V and assemble with `_zve64x` (integer vector
instructions only). Nothing depends on VLEN: checked elements lie in the first 16 bytes of a register group at
VLEN=128 (read with a whole-register store and a scalar load, or `vmv.x.s` for element 0; 64-bit elements as two words; no slides, so a memory test does not depend on the permutation unit), requested vl never exceeds VLMAX at
VLEN=128, and register-size-dependent addresses (whole-register transfers) are computed from `vlenb` at run time
(buffers assume VLEN <= 4096; the test passes trivially above). Destination registers are pre-filled with 0xA5 bytes
and memory holds pattern bytes in 0x01-0x7e, so undisturbed, loaded and all-ones (agnostic) elements are told apart.

- Unprivileged tests (lowest mode) check data movement: unit-stride, strided (including stride 0, `rs2=x0`,
  negative and page-crossing strides), indexed (byte offsets, zero-extension, wrap at XLEN, index EMUL vs data
  EMUL), segment (NFIELDS, field order, EMUL>1 groups, whole-segment masking, overlapping strided segments),
  whole-register (register count, numbering, contiguity, base alignment), mask loads/stores (`evl = ceil(vl/8)`,
  EMUL=1, tail-agnostic), program order against scalar accesses, and the final value of stores to one address
  (indexed-ordered: the last active element; unordered and strided: any element).
- Fault tests boot to S-mode and build an Sv39 (RV64) / Sv32 (RV32) table (probed; trivially pass without it) with
  page A valid and the following page B absent or read-only, so a chosen element faults. They check xepc, stval
  (0 or the element's address), `vstart` = the faulting element (segments: the segment; whole-register: the
  encoded-EEW element), elements before vstart committed, resumption with vstart written back (prestart elements
  neither reloaded, re-stored, nor accessed), masked-off elements never faulting, fault-only-first trimming
  (`1 <= vl <= k`, a trap only on element 0, vl unchanged on a trap, vl=0), and what stays undisturbed past a trap or
  trim (inactive and tail elements, elements past the original vl).
- Misalignment: element-aligned accesses (and EEW=8 whole-register transfers, including vs<n>r.v at any address) must
  not raise address-misaligned;
  misaligned ones may succeed (data checked), raise address-misaligned or an access fault (pma_mag_exc), with vstart
  naming a misaligned element and stval 0 or its address (for an access fault, any address of the element: the
  faulting portion).
- 36 mutants (`Vmem:*`) flip one expectation each (EEW from SEW, scaled or sign-extended offsets, vstart off by one,
  restart from 0, masked-off faults, ff trapping late or not trimming, segment vstart in fields, ordered stores
  first-wins, ...).

### Rules not tested

- Reserved encodings with no mandated outcome: vector_ls_eew_rsv, vector_ls_emul_rsv, vector_ls_emul_offgroup_rsv,
  vector_ls_ins_rsv, vector_ls_mew_rsv, emul_nfields_rsv, vector_ls_seg_rsv, vector_ls_seg_indexed_vreg_rsv,
  vector_ls_seg_wholereg_nf_rsv; also v-st-ext.adoc V_instr_ls_eew64_nsupported_xlen32 and zve64x.adoc
  Zve_nsupport_eew64_xlen32 (EEW=64 indices on RV32 are reserved), which is why vector_ls_xlen_dep tests only the
  zero-extension and modulo-XLEN halves.
- Not observable on one hart: vector_ls_seg_unordered and vector_ls_seg_indexed_unordered (fields of one segment
  never overlap), vector_ls_scalar_misaligned_dependence (atomicity), vector_ls_rvwmo, vector_ls_rvtso (Ztso),
  vl_control_dependency, vmask_control_dependency (memory-model dependencies), and the strongly-ordered-IO clause of
  vector_ls_stride_unordered_op and the non-idempotent clause of vector_ff_past_trap (need an I/O region with side
  effects).
- No constraint to test: vector_ls_scalar_misaligned_independence (support is independent of scalar support), and
  vector_ff_seg_partial_access (a partially loaded segment past the trap or trim point may hold any value under
  vector_ls_seg_ff_overload / precise-trap relaxation; the store-side counterpart vector_ls_seg_partial_access is
  tested).
- vector_ff_interrupt_behavior is a recommendation ("should") about interrupts mid-instruction, which a test cannot
  place.
- Priv chapters: no vector-memory rules are tagged there (`norm_rules.py --grep 'vector|vstart'` over src/priv finds
  only mstatus.VS/vsstatus.VS and trap-vector rules, which belong to the control area). The machine.adoc note that
  vector accesses ignore the misaligned atomicity granule PMA is untagged.

### Subtleties

- vstart after a fault is taken to be exactly the faulting element: epc_vstart_op_V_trap says vstart holds "the
  element index on which the trap was taken", precise traps commit everything before it, and the standard extensions
  have no imprecise traps. With one faulting element (the others on valid pages) no other value is consistent.
- Accepting a nonzero vstart (vector_ls_vstart) is tested only with values the same instruction just generated, because
  vstart_vtype_dep lets an implementation raise illegal-instruction for vstart values it never produces.
- Fault-only-first loads may trim vl further than the faulting element even without a fault
  (vector_ff_no_exception), so trimmed vl is checked as `1 <= vl <= k`, and elements are checked only below the
  new vl.
- Whole-register loads and stores have an element granularity: vstart after a fault at byte 8 is 8/EEW-bytes (8 for
  vs<n>r.v, whose EEW is 8), and they run with vl=0 and with vtype.vill=1 (vtype_vill_op note).
- vlm.v may write its tail bytes with ones even with vta=0; vl=0 writes nothing (vstart_vl_dep).
- Misaligned accesses may raise access-fault instead of address-misaligned (machine.adoc pma_mag_exc).
- Partial segment stores before a fault differ legally between models: Sail and Spike store field 0 of the faulting
  segment, Whisper stores none of it.

## Zv* extensions (gen_Vzv.py, vzvlib.py)

Placeholder: the Zv* section (in the Zv* directories' own READMEs or here) is to be merged from
`~/act-wt/vzv-readme.md` when it exists.
