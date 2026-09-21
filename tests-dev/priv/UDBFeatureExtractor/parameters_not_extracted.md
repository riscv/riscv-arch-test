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

## Debug mode

- `DCSR_MPRVEN_TYPE`, `DCSR_STEPIE_TYPE`, `DCSR_STOPCOUNT_TYPE`, `DCSR_STOPTIME_TYPE` (`dcsr` is
  only accessible in debug mode)

## Vector reductions on chosen data

Each would need a reduction run on chosen data with the result inspected.

- `VFREDUSUM_FINAL_NODE_ELEMENT_BEHAVIOR`, `VFREDUSUM_INACTIVE_NODE_ELEMENT_BEHAVIOR`,
  `VFREDUSUM_NAN`, `VFREDUSUM_NODE_ROUNDING_BEHAVIOR`
- `IMPRECISE_VECTOR_TRAP_SETTABLE` (no standard CSR bit selects it)

## In the output

Every parameter that applies to the hart (its defining extension was detected) and was not
determined is printed at the end of the `params` section, commented out with no value, under the
comment "The UDB feature extractor is unable to determine these parameter values". That covers the
groups above and any parameter whose measurement was inconclusive on the hart at hand, such as a
misaligned-access report on a hart that does not trap. The list of parameters and their defining
extensions is `udb_parameters.h`, generated from riscv-unified-db by `test/gen_udb_parameters.py`.

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
- `REPORT_CAUSE_IN_*_ON_*_SOFTWARE_CHECK` is true when the tval is exactly 2 (landing pad) or 3
  (shadow stack). The shadow-stack probe needs a translation mode, since the shadow stack must be a
  page with the shadow-stack permission encoding; on a hart without one it is skipped.
- `VECTOR_LS_INDEX_MAX_EEW` is written as `XLEN` when the widest accepted index EEW equals XLEN,
  as the configuration yamls do, so a yaml that writes `"64"` on RV64 shows as a mismatch.
- `SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED` is the complement of `VILL_SET_ON_RESERVED_VTYPE`, and
  `RESERVED_VSET_X0X0_VILL_SET` needs `vill` to be settable through a reserved vtype first.
- The fault-only-first and segment parameters need Sv39 (RV64) or Sv32 (RV32), whose tables fit
  the scratch area; a hart with only Sv48 or Sv57 leaves them undetermined.
- `ARCH_ID_VALUE` and `IMP_ID_VALUE` are printed as 0 when `marchid`/`mimpid` read as zero, with
  `MARCHID_IMPLEMENTED`/`MIMPID_IMPLEMENTED` false saying the value is not meaningful.
