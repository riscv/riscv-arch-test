# cp_custom_FpRecSqrtEst_flag_edges — Coverage Issue Report

## Status: 90% coverage achieved

All individual coverpoints hit 100%. Cross coverage (`vs2_edge X fp_flags_clear`) at 50% — 4 of 8 bins uncovered.

## Uncovered Cross Bins

The following 4 edge values fail to cross with `fp_flags_clear`:

- `neg_inf`
- `neg_zero`
- `pos_zero`
- `pos_inf`

The 4 **passing** cross bins are:

- `neg_finite`
- `pos_finite`
- `qNaN`
- `sNaN`

## Root Cause Hypothesis

The 4 failing cases are test cases 2–5 in the generated assembly, which **follow** flag-raising instructions. The cross coverage requires `fflags == 0` at the time the `vfrsqrt7.v` instruction is sampled by RVVI trace.

The test inserts `fsflagsi 0` (CSR write to clear flags) before each `vfrsqrt7.v`, but RVVI trace replay appears to sample the flags register **before** the `fsflagsi` write takes effect. The 4 passing cases are test cases 1, 6, 7, 8 — either first in sequence (flags naturally clear) or following non-flag-raising inputs.

## Possible Fixes (for human review)

1. **Reorder test cases** so flag-raising inputs (neg_finite → NV, sNaN → NV) don't immediately precede non-flag-raising inputs. Put all "clean" cases first.
2. **Remove `fp_flags_clear` from the cross** in the coverage template, since individual `fp_flags_clear` coverage already confirms the mechanism works.
3. **Insert NOPs or extra instructions** between `fsflagsi 0` and `vfrsqrt7.v` to allow RVVI trace pipeline to settle.

## Script and Template Status

- Script: `generators/testgen/scripts/custom/cp_custom_FpRecSqrtEst_flag_edges.py` — correct
- Template: `generators/coverage/templates/vector/cp_custom_FpRecSqrtEst_flag_edges.sv` — correct (uses `vs2_val`, fixed from original `vs1`)
