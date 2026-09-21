# UDB parameters the feature extractor does not extract

The extractor prints a parameter only when the extension that defines it was detected and the
measurement was conclusive. This list tracks the parameters it does not measure at all, grouped by
what it would take, so that groups can be worked through one at a time. When a group is
implemented, remove it here and describe the mechanism in the README.

## Would need a second page-table level

The one-level table in the scratch area gives the ordinary page faults and guest page faults. An
intermediate guest page fault needs a VS-stage table whose own pages sit in a guest-physical region
the G-stage table does not map.

- `REPORT_GPA_IN_TVAL_ON_INTERMEDIATE_GUEST_PAGE_FAULT`
- `TINST_VALUE_ON_LOAD_PAGE_FAULT`, `TINST_VALUE_ON_STORE_AMO_PAGE_FAULT`,
  `TINST_VALUE_ON_FINAL_*_GUEST_PAGE_FAULT` (with the TINST group below)

## Would need traps from VS-mode handled in HS-mode

The VS-mode probes exist; these need the trap left undelegated by `hedeleg` so that HS-mode sees it,
and `htinst` read there.

- `TINST_VALUE_ON_BREAKPOINT`, `TINST_VALUE_ON_INSTRUCTION_ADDRESS_MISALIGNED`,
  `TINST_VALUE_ON_LOAD_ACCESS_FAULT`, `TINST_VALUE_ON_LOAD_ADDRESS_MISALIGNED`,
  `TINST_VALUE_ON_STORE_AMO_ACCESS_FAULT`, `TINST_VALUE_ON_STORE_AMO_ADDRESS_MISALIGNED`,
  `TINST_VALUE_ON_MCALL`, `TINST_VALUE_ON_SCALL`, `TINST_VALUE_ON_UCALL`, `TINST_VALUE_ON_VSCALL`,
  `TINST_VALUE_ON_VIRTUAL_INSTRUCTION`
- `REPORT_ENCODING_IN_VSTVAL_ON_VIRTUAL_INSTRUCTION` (a virtual-instruction exception is never
  taken in VS-mode itself; the parameter's meaning needs checking against UDB first)

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
- `PMLEN` (the configuration yamls do not agree on what it counts)
- `SCTRDEPTH_DEPTH_LEGAL_VALUES` (would write each depth to `sctrdepth`; cheap once Smctr is
  seen on a simulator)

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
