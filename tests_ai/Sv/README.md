# Sv, Svade, Svadu, Svnapot, Svpbmt, Svinval: rule-derived tests for supervisor virtual memory

One test per `norm:` rule in the virtual-memory parts of `src/priv/supervisor.adoc` (`sstatus` SUM/MXR, `satp`,
SFENCE.VMA, the PTE format and translation algorithm, Sv32/Sv39/Sv48/Sv57) and in `svadu.adoc`, `svnapot.adoc`,
`svpbmt.adoc` and `svinval.adoc`, plus the `menvcfg.ADUE`/`PBMTE` rules of `machine.adoc` that define Svadu and Svpbmt
behavior. All six suites are written by `tests_ai/gen/gen_Sv.py`, with helpers in `gen/svlib.py`. This README covers
all of them. Mutants are named `Sv:<mutant>`.

## How the extensions are tested

- **Page tables.** Tests boot to S-mode and build page tables at run time in the data section. Each table first
  identity-maps the test image with S-mode superpages: 4 MiB on Sv32, and 1 GiB on Sv39/48/57, through pointer tables
  on Sv48/57. S-mode code, the trap handlers and the data keep running once `satp` is written. Test pages sit at
  constant VAs away from the image, so every expected `stval` is a constant. Superpage accesses go to a data page's
  offset inside the superpage, computed at run time, and `stval` is then checked against that address.
- **Data pages.** Every data page holds a signature at offset 0 and a stub at 0x100 (`addi x7, x0, id; jalr x0,
0(x1)`). A load, a fetch or a store through any mapping shows which physical page it reached. A faulting store is
  checked not to have written.
- **U-mode.** U-mode code runs in a second, user mapping of the image at PA + 4 GiB (RV64) or + 256 MiB (RV32). The
  mapping is registered in the S save area so that T-SBI GOTOs relocate between the two views (`TSBI_RELOCATE_EPC`).
  `sepc`/`sstatus.SPP` are set directly for the `sret` into U. A U-mode trap's `sepc` is checked in that view.
- **Schemes.** Scheme-independent rules use Sv39 (RV64) or Sv32 (RV32). Whether `satp` accepts the scheme is probed
  at run time, and the test does nothing if it does not. Scheme-specific rules (`Sv39_*`, `Sv48_*`, `Sv57_*`,
  `satp_ppn_Sv*`, `satp_mode_sxlen32`) require the scheme's extension and are not probed. They cover:
  - the walk depth, V=0 at each level, a pointer at the last level, and D/A/U in pointers (reserved);
  - every VPN bit, sign extension, and the extremes of the VA space;
  - the PTE stride and PPN width (high PPN bits give access faults, never page faults or aliases);
  - leaves at every level, superpage size, alignment and misalignment (each lower PPN field).
- **Permissions.** `load_/store_/fetch_page_fault_*` sweep all 16 R/W/X/U encodings, including the reserved W-only
  encoding and a last-level pointer, × S/U × SUM × MXR. The U=1 half of each sweep is in `<rule>_U1.S`, so every
  file stays under the 500 KB file-size limit. LR, SC, AMO and CBO.ZERO sweeps run under their extension's macro.
  The loads are word loads; other widths are not swept.
- **Untagged algorithm steps.** The translation algorithm has no tags. Its checks are folded into the closest rule:
  - V and W-without-R: the permission sweeps and `Sv*_levels`;
  - reserved PTE bits: `Sv39_pte_*_rsv`, `Sv*_levels`, `Svpbmt_*`, `Svnapot_*`;
  - misaligned superpages: `Sv*_superpage_align_fault`, and for Sv32 `satp_mode_sxlen32`.
- **A/D.** `menvcfg.ADUE` is written through T-SBI and read back. With ADUE=1, hardware updating is required:
  - A is set by every access, and D only by a completed store;
  - a faulting store leaves D=0;
  - A and D are never cleared.

  With ADUE=0 (Svade), the access faults and the PTE is unchanged. `pte_a_def`/`pte_d_def` accept either scheme when
  ADUE reads 0, but the PTE must agree with the outcome.

- **Fences.** Without a fence (or a complete SFENCE.W.INVAL / SINVAL.VMA / SFENCE.INVAL.IR sequence), a read may
  return any translation valid since the last subsuming fence, or fault when one was invalid. After the fence, only
  the new translation is legal. Each form is checked:
  - leaf and non-leaf changes;
  - global mappings (exempt from ASID fences);
  - other address spaces;
  - superpages;
  - NAPOT ranges;
  - `rs2` with reserved and unimplemented ASID bits set.

  Two-ASID cases run only when ASIDLEN >= 2 (probed).

- **Mutation check.** `MUTANTS` in `gen_Sv.py` holds 80 mutants: wrong permission semantics, wrong causes, ignored
  enables, missing invalidations, wrong NAPOT/PBMT decoding, and so on. Every mutant fails a test on Sail.

## Rules not tested here, or only partly

- **Not observable on one hart, or permissions:**
  - `sfence_vma_local_only`, `asid_hart_private`, `pte_ad_scheme_uniform`: multi-hart.
  - `satp_mode_bare_nonzero_unspec`: UNSPECIFIED.
  - `satp_bare_rsv_custom`: reserved and custom encodings constrain nothing.
  - `Svpbmt_impl_may_override_pmas`, `Svpbmt_aliasing_attribute`, `Svpbmt_cacheable_aliasing_may_cause_coherence_loss`,
    `Svpbmt_noncacheable_aliasing_may_weaken_ordering`: permissions.
  - `Svpbmt_obeys_mem_ordering`, `Svpbmt_io_pma_nc_pbmt_obey_rvwmo`, `Svpbmt_io_pma_nc_pbmt_treated_as_io_and_memory`,
    `Svpbmt_memory_pma_io_pbmt_strong_io_ordering`, `Svpbmt_memory_pma_io_pbmt_treated_as_io_and_memory`,
    `Svpbmt_noncacheable_aliasing_fence_prevents_ordering_loss`: memory ordering, which one hart cannot observe.
- **Definitions or software constraints:**
  - `Sv39_pt_sz`, `Sv39_pt_align`: a table is 512 × 8 bytes, checked by `Sv39_pte_count_sz`. Alignment is a software
    obligation that every test meets.
  - `Sv48_sxlen` and `Svnapot_depends_Sv39`/`Svpbmt_depends_Sv39`, `Sv48_requires_Sv39`, `Sv57_requires_Sv48` only
    check that `satp` accepts the mode they name.
- **Other suites:**
  - `sstatus_sum_satp_mode` is in `tests_ai/S`, as an `_Sm` file that probes `satp` from M-mode.
  - `Svnapot_hyp_gstage`, `Svpbmt_hgatp_stage_override_rule`, `Svpbmt_vsatp_stage_override_rule`,
    `Svinval_hinval_vvma_gvma`, `Svinval_hinval_gvma_uses_vmid`: two-stage translation, H suite (not generated
    there yet as Svinval/Svnapot/Svpbmt rules). The validity of HINVAL.* is tested here (`Svinval_*`).
  - machine.adoc: `mstatus_sum_*`, `mstatus_mxr_*`, `mstatus_mprv_*`, `mstatus_tvm_*`, `menvcfg_pbmte_rdonly0`,
    `menvcfg_adue_rdonly0` and the `henvcfg` ADUE/PBMTE rules belong to the Sm/S/H suites.
- **Partial:**
  - `satp_op_active` (`_Sm`): M-mode with MPRV, not speculative walks.
  - `sfence_vma_implicit_access`: an invalid pointer to non-memory, and skipped instructions; speculation itself is
    invisible.
  - `sfence_vma_invalid_va`: only "no exception". Over-fencing is legal, so "no effect" cannot be checked.
  - `satp_op_sfence_vma`, `Svnapot_cache_entries`, the unfenced reads in the fence tests: these catch missing
    invalidation only on harts that cache translations.
  - `lr_sc_rsrv_set_page`: an SC to another physical page fails. Successful SCs are not required.
  - `satp_ppn_Sv*_sz`: PTE PPN bits only. A `satp.PPN` beyond memory cannot be activated without losing the code
    mapping.

## Subtleties

- **The two A/D schemes.** Exactly two schemes exist: Svade, and hardware updating. Svadu only adds ADUE to choose
  between them ([#3450](https://github.com/riscv/riscv-isa-manual/issues/3450), aswaterman: "Svadu is not itself a
  scheme").
- **Changing MODE.** Writing `satp` neither orders nor invalidates (`satp_op_sfence_vma`). Switching between paged
  modes with the same ASID may keep stale entries
  ([#2199](https://github.com/riscv/riscv-isa-manual/issues/2199)), so tests fence after every `satp` write except
  where the rule is about not fencing (Bare <-> paged, ASID changes).
- **Incomplete SINVAL sequences.** Without SFENCE.INVAL.IR, every access uses either the old or the new translation,
  nothing else ([#1936](https://github.com/riscv/riscv-isa-manual/issues/1936)).
- **N=1 in non-leaf PTEs.** N=1 is reserved in non-leaf PTEs and superpage leaves, since i >= 1 there
  ([#823](https://github.com/riscv/riscv-isa-manual/issues/823)).
- **Reserved PTE bits.**
  - With Svrsw60t59b, bits 60-59 are software bits, so `Sv39_pte_future_rsv` checks them only without it.
  - PBMTE=0 makes bits 62-61 reserved on every hart (`menvcfg_pbmte_op`). `Sv39_pte_Svpbmt_rsv` therefore runs
    everywhere.
- **Execute-only CBM.** A CBM instruction on an execute-only page may be permitted (`cbm_access`). If it is not,
  `cbm_unperm_fault` read literally gives a store access fault, since translation permitted a fetch. Whether "does
  not permit any access" counts fetch is not settled ([#3405](https://github.com/riscv/riscv-isa-manual/issues/3405),
  fixed by #3407, only made CBM page faults store page faults). Sail raises a store page fault, so no trap, 7 and
  15 are all accepted.
- **SFENCE.VMA rs2 bits.** Bits ASIDMAX-1:ASIDLEN of rs2 "shall" be ignored. Bits SXLEN-1:ASIDMAX "should be zeroed
  by software and ignored by current implementations", a recommendation. With those bits set,
  `sfence_vma_rs2_bits` therefore accepts the stale translation, then requires the new one after
  SFENCE.VMA x0, x0. Whisper keeps the stale translation (it compares rs2 unmasked).
- **WARL controls.** menvcfg.CBCFE/CBIE/ADUE/PBMTE and mstatus.TVM are WARL. Each test reads back what it set and
  runs only the cases the value allows (TVM, CBCFE, CBIE), or requires the value where an extension makes the field
  writable (ADUE with Svadu, PBMTE with Svpbmt).
- **Console mapping.** The failure reporter prints from the failing mode with satp active. Every table therefore
  also identity-maps the console superpage at 0x10000000 (RW, not X); without it, a failing test hangs on DUTs with
  an MMIO console.
- **Uncached aliases.** NC/IO pages are never touched through a cacheable alias, except in the fence; cbo.flush;
  fence test.
- **Image location.** The upper-level paths of the identity map assume the image lies below 2^39, true of every
  configuration (0x80000000).
