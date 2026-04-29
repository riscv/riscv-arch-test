# Issue 002 — Trap-signature buffer too small for SsstrictV (framework)

## Symptom

Same generic failure as issue 001 (`0xbad0dead` in `x10`,
`The trap handler aborted the test before normal completion`), but the
underlying cause is **not** a Sail bug — it is the M-mode trap handler in
`tests/env/rvtest_trap_handler.h` detecting that the per-trap signature
ring buffer would overflow:

```
// tests/env/rvtest_trap_handler.h:1547-1549
// now see if the pointer has overrun sig_end
add  T1, T1, T2          // construct segment end address
bgtu T4, T1, abort_test  // abort test if pre-incremented value overruns
```

## Reproduction

`tests/env/check_defines.h` previously defaulted to:

```c
#ifndef TRAP_SIGUPD_COUNT
  #define TRAP_SIGUPD_COUNT 15000
```

SsstrictV produces ~7000 test instructions per xlen. The *expected*
trapping subset (mask-vd-overlap, lmul-misalign, reserved encodings, etc.)
generates ~5000 traps. With issue 001 unfixed each test produced a
*pair* of traps (~10000); plus pre-existing ExceptionsV* contributions,
the buffer fills.

## Fix

Bumped the default ceiling to 50000 in `tests/env/check_defines.h`:

```c
#ifndef TRAP_SIGUPD_COUNT
  #define TRAP_SIGUPD_COUNT 50000
```

Combined with issue 001's fix, this is comfortably sufficient.

## Why not file upstream

The buffer size is a test-framework parameter, not a Sail behaviour. There
is nothing to file upstream against `sail-riscv`. This file exists so the
cause is not re-investigated next time the sail run aborts with
`0xbad0dead`.

## Affected generators

None directly. Any vector privileged extension that produces > ~7500
trapping testcases needs this bump. SsstrictV currently does.
