# UDB parameters the feature extractor does not extract

The extractor prints a parameter only when the extension that defines it was detected and the
measurement was conclusive. This list tracks the parameters it does not measure at all, grouped by
what it would take, so that groups can be worked through one at a time. When a group is
implemented, remove it here and describe the mechanism in the README.

## Would need a misaligned access that traps

Measurable only on a hart without misaligned support; the extractor already prints them there.

- `REPORT_VA_IN_MTVAL_ON_LOAD_MISALIGNED`, `REPORT_VA_IN_MTVAL_ON_STORE_AMO_MISALIGNED`, and the
  `STVAL`/`VSTVAL` versions, on harts with `MISALIGNED_LDST` true
- `REPORT_VA_IN_*_ON_INSTRUCTION_MISALIGNED` on harts with C

## Memory-system behavior

Would need a second hart, a cache model, or a memory-mapped device to observe.

- `LRSC_RESERVATION_STRATEGY`, `LRSC_FAIL_ON_VA_SYNONYM`, `LRSC_FAIL_ON_NON_EXACT_LRSC`
- `MISALIGNED_LDST_EXCEPTION_PRIORITY`, `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE`,
  `MISALIGNED_SPLIT_STRATEGY`
- `PMA_GRANULARITY`, `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH`, `ZAWRS_NTO_IS_NOP`,
  `PRECISE_SYNCHRONOUS_EXCEPTIONS`

## Unbounded or undefined search

- `HPM_EVENTS` (every event number would have to be written to `mhpmevent3` and read back)
- `TRAP_ON_ILLEGAL_WLRL` (a WLRL field and an illegal value would have to be chosen per hart)
- `TRAP_ON_UNIMPLEMENTED_INSTRUCTION` (no encoding is unimplemented on every hart)

## Control-flow-integrity and debug traps

- `REPORT_CAUSE_IN_MTVAL_ON_LANDING_PAD_SOFTWARE_CHECK`, `REPORT_CAUSE_IN_STVAL_ON_*`,
  `REPORT_CAUSE_IN_VSTVAL_ON_*`, and the `SHADOW_STACK` versions (a landing-pad or shadow-stack
  fault would have to be provoked with the feature enabled)
- `DCSR_MPRVEN_TYPE`, `DCSR_STEPIE_TYPE`, `DCSR_STOPCOUNT_TYPE`, `DCSR_STOPTIME_TYPE` (`dcsr` is
  only accessible in debug mode)

## Vector behavior beyond legality

Each would need a vector instruction run on chosen data and its result inspected.

- `LEGAL_VSTART`, `RESERVED_VSET_X0X0_VILL_SET`, `RESERVED_VSET_X0X0_VLMAX_CHANGE`,
  `RVV_VL_WHEN_AVL_LT_DOUBLE_VLMAX`, `SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED`,
  `FOLLOW_VTYPE_RESET_RECOMMENDATION`, `IMPRECISE_VECTOR_TRAP_SETTABLE`
- `VECTOR_FF_NO_EXCEPTION_TRIM`, `VECTOR_FF_SEG_EXCEPTION_PARTIAL_LOAD`,
  `VECTOR_FF_UPDATE_PAST_TRIM`, `VECTOR_LOAD_PAST_TRAP`,
  `VECTOR_LOAD_SEG_FF_OVERWRITE_ELEMENTS_AFTER_FAULT`
- `VECTOR_LS_INDEX_MAX_EEW`, `VECTOR_LS_SEG_PARTIAL_ACCESS`, `VECTOR_LS_WHOLEREG_MISALIGNED_LEGAL`
- `VFREDUSUM_FINAL_NODE_ELEMENT_BEHAVIOR`, `VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR`,
  `VFREDUSUM_NAN`, `VFREDUSUM_NODE_ROUNDING_BEHAVIOR`

## Measured with a caveat

- `HW_MSTATUS_FS_DIRTY_UPDATE` and `HW_MSTATUS_VS_DIRTY_UPDATE` report `precise` whenever one
  instruction leaves the field Dirty; `imprecise` cannot be told apart.
- `MTVEC_ILLEGAL_WRITE_BEHAVIOR` reports `custom` whenever a reserved mode is not retained, which
  includes harts that legalize the mode field.
- `TINST_VALUE_ON_*` reports `always transformed standard instruction` when the value's opcode
  field is a load, store or AMO and `custom` for any other nonzero value; a hart that transforms
  some faults and not others would need each `TINST_VALUE_*` looked at separately.
- `PMLEN` is reported as 16 when the PMM field accepts 3 and 7 when it only accepts 2; the
  configuration yamls carry 17, which matches neither definition in the pointer-masking spec.
- `REPORT_ENCODING_IN_VSTVAL_ON_VIRTUAL_INSTRUCTION` is checked in the tval of the mode that took
  the trap (HS or M), since a virtual-instruction exception is never taken in VS-mode.
- The `TINST_VALUE_ON_*CALL` values come from `mtinst`, since the ecalls reach M-mode.
