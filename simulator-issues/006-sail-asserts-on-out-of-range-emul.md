# Issue 006: Sail asserts on out-of-range EMUL_pow before reserved-encoding check

## Summary

Sail's `vext_mem_insts.sail` model unconditionally asserts
`-3 <= EMUL_pow & EMUL_pow <= 3` before reaching the reserved-encoding
check `illegal_load(...) | not(valid_reg_group(...))`.

When a vector load/store has `EMUL_pow = ±4` (i.e. `EMUL == 16` or
`EMUL == 1/16`) — which the spec explicitly defines as a _reserved
encoding_ that should raise `Illegal_Instruction` — Sail aborts with:

```
Assertion failed: extensions/V/vext_mem_insts.sail:303.39-303.40
```

The assertion appears at lines 96, 177, 238, 303 and 365 of
`vext_mem_insts.sail` (one per LS variant: unit-stride, strided, indexed,
strided-segment, indexed-segment).

## Spec reference

Section 7.5 of the RISC‑V Vector spec ("Vector Load/Store Width
Encoding"):

> EMUL must be in the range [1/8, 8]. If the EMUL would be out of this
> range the instruction encoding is _reserved_.

The architectural behaviour is therefore an `Illegal_Instruction` trap,
not an emulator abort.

## How to reproduce

```
$ uv run generators/testgen/scripts/vector-testgen-priv.py
$ make coverage
...
extensions/V/vext_mem_insts.sail:303.39-303.40
```

Any priv test that sets up `vsetivli x0, 1, e8, m8, tu, mu` followed by
e.g. `vle16.v v0, (x10)` (yielding EMUL = (16/8)\*8 = 16, i.e.
`EMUL_pow = 4`) will trigger the assert. Likewise `vsetivli x0, 1, e16,
mf8, tu, mu` followed by `vle8.v v0, (x10)` triggers the lower bound
(EMUL = 1/16, `EMUL_pow = -4`).

## Affected coverpoints

- `cp_ssstrictv_ls_emul_16`
- `cp_ssstrictv_ls_emul_f16`

## Workaround

The two coverpoints above are listed in
`generators/testgen/scripts/priv/_ssstrictv_helpers.SKIP_COVERPOINTS`
so the priv testgen does not emit any tests that would crash Sail.

When the Sail model adds the missing
`if EMUL_pow < -3 | EMUL_pow > 3 then return Illegal_Instruction()`
check before the assertion, remove these entries from `SKIP_COVERPOINTS`
and regenerate.
