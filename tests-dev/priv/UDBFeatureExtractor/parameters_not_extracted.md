# UDB parameters the feature extractor does not extract

The extractor prints a parameter only when the extension that defines it was detected and the
measurement was conclusive. At the end of the `params` section it prints, commented out with no
value, every parameter that applies to the hart but was not determined, under the comment "The
UDB feature extractor is unable to determine these parameter values". The parameter list with each
one's defining extension is `udb_parameters.h`, generated from riscv-unified-db by
`test/gen_udb_parameters.py`; regenerate it when UDB adds parameters.

This file lists the parameters no probe measures on any hart, with the reason, and the parameters
that are measured only under some condition.

## Not measurable from a single hart in M-mode

- `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE`: atomicity of a misaligned access is only visible to
  another observer (a second hart or a device).
- `ZAWRS_NTO_IS_NOP`: `wrs.nto` with a valid reservation stalls until an interrupt or another
  hart's store, which the extractor has no way to arrange, and on a hart that stalls the probe
  would hang (the Imperas ISS does).
- `PMA_GRANULARITY`: the PMA map is a platform property with no CSR; finding region boundaries
  would mean probing arbitrary addresses, including device registers.
- `PRECISE_SYNCHRONOUS_EXCEPTIONS`: imprecision is defined as unpredictable state, which no probe
  can distinguish from a precise trap.
- `IMPRECISE_VECTOR_TRAP_SETTABLE`: the "privileged configuration bit" it refers to is not a
  standard CSR field, so there is nothing to write.
- `VFREDUSUM_NODE_ROUNDING_BEHAVIOR`: a per-node rounding difference can only be provoked with a
  known reduction tree, and the tree shape is left to the implementation; any input set that shows
  the difference under one tree shows a tree-shape difference under another.
- `DCSR_MPRVEN_TYPE`, `DCSR_STEPIE_TYPE`, `DCSR_STOPCOUNT_TYPE`, `DCSR_STOPTIME_TYPE`: `dcsr` is
  accessible only in debug mode.

## Measured only under a condition

- `REPORT_VA_IN_{MTVAL,STVAL,VSTVAL}_ON_{LOAD,STORE_AMO}_MISALIGNED` and the `TINST_VALUE_ON_*_ADDRESS_MISALIGNED`
  values need a misaligned access that traps, so they are absent on a hart with `MISALIGNED_LDST`
  (and `MISALIGNED_AMO`) true. `REPORT_VA_IN_*_ON_INSTRUCTION_MISALIGNED` needs a hart without C.
- `MISALIGNED_LDST_EXCEPTION_PRIORITY` likewise needs a misaligned access that traps (a load, or an
  AMO when loads do not trap); `MISALIGNED_SPLIT_STRATEGY` needs one that does not.
- `LRSC_MISALIGNED_BEHAVIOR` applies only when misaligned AMOs trap.
- `LRSC_FAIL_ON_NON_EXACT_LRSC` is measured with an `sc.w` inside an `lr.d` reservation, so RV64
  only; `LRSC_RESERVATION_STRATEGY` is measured only when a non-exact SC can succeed, and reports
  `custom` for a set size that is none of the enumerated ones (Sail's 8-byte granule, for example).
- `HPM_EVENTS` tries event numbers 0-255 on `mhpmevent3`; a hart that accepts more than 64 of them
  is taken to be passing the value through and the list is left undetermined.
- `TRAP_ON_UNIMPLEMENTED_INSTRUCTION` is reported (true) only when some extension probe's
  instruction raised an illegal-instruction exception; a hart implementing every probed extension
  gives nothing to observe.
- `VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR` can only be seen when the final node copies (with an
  identity added at the end, the sign of zero is lost either way).
- The fault-only-first, segment, misaligned-edge and VA-synonym parameters need Sv39 (RV64) or Sv32
  (RV32), whose tables fit the scratch area; a hart with only Sv48 or Sv57 leaves them undetermined.
- `REPORT_CAUSE_IN_VSTVAL_ON_SHADOW_STACK_SOFTWARE_CHECK` needs `ssp` accessible in VS-mode, which
  Sail 0.14 refuses with a virtual-instruction exception even with both `SSE` bits set.

## Measured with a caveat

- `HW_MSTATUS_FS_DIRTY_UPDATE` and `HW_MSTATUS_VS_DIRTY_UPDATE` report `precise` whenever one
  instruction leaves the field Dirty; `imprecise` cannot be told apart.
- `MTVEC_ILLEGAL_WRITE_BEHAVIOR` reports `custom` whenever a reserved mode is not retained, which
  includes harts that legalize the mode field.
- `TINST_VALUE_ON_*` reports `always transformed standard instruction` when the value's opcode
  field is a load, store or AMO and `custom` for any other nonzero value.
- `PMLEN` is reported as 16 when the PMM field accepts 3 and 7 when it only accepts 2; the
  configuration yamls carry 17, which matches neither definition in the pointer-masking spec.
- `REPORT_ENCODING_IN_VSTVAL_ON_VIRTUAL_INSTRUCTION` is checked in the tval of the mode that took
  the trap (HS or M), since a virtual-instruction exception is never taken in VS-mode.
- The `TINST_VALUE_ON_*CALL` values come from `mtinst`, since the ecalls reach M-mode.
- `REPORT_CAUSE_IN_*_ON_*_SOFTWARE_CHECK` is true when the tval is exactly 2 (landing pad) or 3
  (shadow stack).
- `VECTOR_LS_INDEX_MAX_EEW` is written as `XLEN` when the widest accepted index EEW equals XLEN,
  as the configuration yamls do, so a yaml that writes `"64"` on RV64 shows as a mismatch.
- `SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED` is the complement of `VILL_SET_ON_RESERVED_VTYPE`, and
  `RESERVED_VSET_X0X0_VILL_SET` needs `vill` to be settable through a reserved vtype first.
- `ARCH_ID_VALUE` and `IMP_ID_VALUE` are printed as 0 when `marchid`/`mimpid` read as zero, with
  `MARCHID_IMPLEMENTED`/`MIMPID_IMPLEMENTED` false saying the value is not meaningful.
- `TRAP_ON_ILLEGAL_WLRL` writes the exception code 0x3FF, which no hart implements, to `mcause`.
- `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH` is whether `menvcfg.CBIE` refuses the value 11, as UDB
  defines it, not whether a cache line is discarded.
