# cp_custom_vfredosum_NAN_vl0 — 55.55% Coverage

## Status

55.55% on all SEWs. Cross `cp_custom_vfredosum_NAN_vl0` at 0%.

## Issue 1: Framework limitation with VL=0 data loading

`writeTest(vl=0)` sets VL=0 BEFORE loading data into vector registers. Since all vector
loads (vle16.v, etc.) use VL, they load 0 elements. vs1 never gets the qNaN value.

The test needs:

1. VL > 0 to load qNaN into vs1
2. VL = 0 when executing vfredosum.vs

The framework doesn't support different VLs for data loading vs test instruction.

## Issue 2: Wrong bin values in template for SEW32/SEW64

Template bins for `vs1_0_qNAN`:

- SEW16: `{[64'h07E00:64'h07FFF]}` = `[0x7E00:0x7FFF]` ← CORRECT
- SEW32: `{[64'h0ffef_7E00:64'h0feef_7FFF]}` ← WRONG, should be `{[64'h7FC00000:64'h7FFFFFFF]}`
- SEW64: `{[64'hfffeffffffff_7E00:64'hffffffefffff_7FFF]}` ← WRONG, should be `{[64'h7FF8000000000000:64'h7FFFFFFFFFFFFFFF]}`

## Recommended Fix

1. Fix template bin values for SEW32/64
2. To fix the VL=0 loading issue, either:
   a. Add framework support for "pre-instruction VL" separate from "test VL"
   b. Use manual assembly generation for this test case
   c. Set VL=1 for loading and inject a `vsetvli x0, x0, ...` with avl=0 before the instruction
